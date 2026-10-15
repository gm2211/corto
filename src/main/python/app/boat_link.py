"""The real boat over LoRa: the shore side of the link.

The boat (boat/corto.py) is a Pi that answers short text packets from its CommandReceiver:
    T                 reply with NavParams.serialize_for_lora()
    R<n> S<n> TR<n>   rudder (servo percent, 50 = centre), sheet, motor throttle: integers 0..100
    D<lat>,<lon>      steer to this point (the boat always steers to the last one it was given)
There are no acknowledgements and no other commands. BoatSource polls `T`, sends those commands, and turns the
replies into the same state dict the simulator serves (see sources.py), plus a `link` section that says how
fresh it is. The boat sends no timestamp, so freshness is measured from when the packet arrived here.

LoRa is half-duplex and the radio is shared, so there is exactly one transmitting thread (the link thread);
the Flask threads only leave the latest wanted value per channel in an outbox. Nothing is sent while a telemetry
reply may be on its way, and each channel is rate-limited.
"""

import math
import sys
import threading
import time
from typing import Any, Callable, Dict, Optional

import ultraimport

# The simulator's autopilot module first: it puts src/main/python on sys.path, which the api.* modules need.
Course = ultraimport("__dir__/../simulator/autopilot.py", ["Course"])[0]
(
    RUDDER_FULL_DEG,
    optimal_trim,
    signed_true_wind_angle,
) = ultraimport("__dir__/../simulator/simulator.py", ["RUDDER_FULL_DEG", "optimal_trim", "signed_true_wind_angle"])
(
    clamp,
    parse_marks,
    to_number,
) = ultraimport("__dir__/../simulator/simulator_integration.py", ["clamp", "parse_marks", "to_number"])
NavParams = ultraimport("__dir__/../api/objects/nav_params/nav_params.py", ["NavParams"])[0]
GPSCoord = ultraimport("__dir__/../api/objects/units/gps_coord.py", ["GPSCoord"])[0]
Percent = ultraimport("__dir__/../api/objects/units/percent.py", ["Percent"])[0]
SendTelemetry = ultraimport("__dir__/../api/objects/commands/send_telemetry.py", ["SendTelemetry"])[0]
SetDestination = ultraimport("__dir__/../api/objects/commands/set_destination.py", ["SetDestination"])[0]
SetSail = ultraimport("__dir__/../api/objects/commands/set_sail.py", ["SetSail"])[0]
SetThrottle = ultraimport("__dir__/../api/objects/commands/set_throttle.py", ["SetThrottle"])[0]
TurnRudder = ultraimport("__dir__/../api/objects/commands/turn_rudder.py", ["TurnRudder"])[0]
(
    NotAvailable,
    STATE_KEYS,
    SIM_CAPABILITIES,
) = ultraimport("__dir__/sources.py", ["NotAvailable", "STATE_KEYS", "SIM_CAPABILITIES"])

# Telemetry is requested this often (a ~80 byte reply at SF7/BW125 is about 150 ms of airtime).
POLL_INTERVAL_S = 2.0
# After asking for telemetry, stay quiet this long (or until the reply arrives) so we do not talk over the boat.
REPLY_WINDOW_S = 0.8
# A channel (rudder, sheet, throttle, destination) is sent at most this often; only the latest value goes out.
MIN_COMMAND_GAP_S = 0.25
# There are no acks, so while a course is being sent the active mark is repeated this often.
DEST_RESEND_S = 10.0
# Link health, from the age of the last report: ok up to FRESH_S, stale up to LOST_S, lost after that.
FRESH_S = 5.0
LOST_S = 20.0
LINK_TICK_S = 0.05

# The order commands are sent in when several are waiting
CHANNELS = ("rudder", "sails", "throttle", "dest")

# The boat's protocol cannot switch modes, trim by itself, or be reset; the environment and the clock are the
# simulator's. Everything else works.
BOAT_CAPABILITIES = dict(
    SIM_CAPABILITIES, auto_trim=False, mode=False, demo=False, environment=False, time_scale=False, reset=False)
SIM_ONLY_KEYS = ("mode", "auto_trim", "time_scale")


class BoatSource:
    """The boat behind `radio`: anything with register_callback(fn), send(text) and (optionally) last_rssi."""
    kind = "boat"
    note: Optional[str] = None

    def __init__(self, radio, clock: Callable[[], float] = time.monotonic, poll_interval_s: float = POLL_INTERVAL_S,
                 autostart: bool = True, label: str = "Boat · LoRa"):
        self.radio = radio
        self.label = label
        self.course = Course()  # the marks live on shore; only the active one is ever sent
        self.errors = 0  # radio errors, counted not raised: a flaky SPI transfer must not kill the link
        self._clock = clock
        self._poll_interval_s = max(float(poll_interval_s), REPLY_WINDOW_S)
        self._lock = threading.RLock()
        self._started_at = clock()
        self._nav = None  # the latest NavParams the boat reported
        self._rx_at: Optional[float] = None  # shore clock time of that report
        self._rssi = None
        self._polls = self._replies = self._ignored = 0
        self._last_poll_at: Optional[float] = None
        self._quiet_until = 0.0
        self._outbox: Dict[str, str] = {}
        self._urgent = set()
        self._sent_at: Dict[str, float] = {}
        self._commanded: Dict[str, Optional[int]] = {"rudder": None, "trim": None, "throttle": None}
        self._commanded_dest: Optional[Dict[str, Any]] = None
        self._running = False  # sending the course
        self._dest_key = None  # (index, lat, lng) of the destination last queued
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        radio.register_callback(self._on_packet)
        if autostart:
            self._thread = threading.Thread(target=self._run, name="boat-link", daemon=True)
            self._thread.start()

    # -- the link thread ---------------------------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as error:  # never let the link thread die
                self._count_error(error)
            self._stop.wait(LINK_TICK_S)

    def tick(self) -> None:
        """One pass of the link: send the next waiting command, otherwise poll for telemetry when it is due."""
        now = self._clock()
        with self._lock:
            message = self._next_command(now) or self._next_poll(now)
        if message is None:
            return
        try:
            self.radio.send(message)
        except Exception as error:
            self._count_error(error)

    def _next_command(self, now: float) -> Optional[str]:
        self._queue_destination(now)
        if now < self._quiet_until:
            return None
        for channel in CHANNELS:
            message = self._outbox.get(channel)
            if message is None:
                continue
            if channel not in self._urgent and now - self._sent_at.get(channel, -math.inf) < MIN_COMMAND_GAP_S:
                continue
            del self._outbox[channel]
            self._urgent.discard(channel)
            self._sent_at[channel] = now
            if channel == "dest" and self._commanded_dest is not None:
                self._commanded_dest["sent_at"] = now
            return message
        return None

    def _next_poll(self, now: float) -> Optional[str]:
        if self._last_poll_at is not None and now - self._last_poll_at < self._poll_interval_s:
            return None
        self._last_poll_at = now
        self._quiet_until = now + REPLY_WINDOW_S
        self._polls += 1
        return SendTelemetry.serialize_for_lora()

    def _queue_destination(self, now: float) -> None:
        """While a course is being sent, keep the boat pointed at the active mark (and repeat it: there are no acks)."""
        if not self._running:
            return
        mark = self.course.target()
        if mark is None:
            self._running = False
            return
        key = (self.course.active, mark.lat, mark.lng)
        if key != self._dest_key or now - self._sent_at.get("dest", -math.inf) >= DEST_RESEND_S:
            self._dest_key = key
            self._commanded_dest = {"index": key[0], "lat": mark.lat, "lng": mark.lng, "sent_at": None}
            self._queue("dest", SetDestination(GPSCoord(mark.lat, mark.lng)).serialize_for_lora())

    def _count_error(self, error: Exception) -> None:
        with self._lock:
            self.errors += 1
            count = self.errors
        if count == 1 or count % 50 == 0:
            print(f"LoRa link error #{count}: {type(error).__name__}: {error}", file=sys.stderr)

    # -- what the boat says ------------------------------------------------------------------------------

    def _on_packet(self, text: str) -> None:
        """Radio callback (the GPIO thread on the Pi). Anything that is not telemetry is counted and ignored."""
        try:
            nav = NavParams.deserialize_from_lora(text)
        except ValueError:
            with self._lock:
                self._ignored += 1
            return
        now = self._clock()
        rssi = getattr(self.radio, "last_rssi", None)
        with self._lock:
            self._nav, self._rx_at, self._rssi = nav, now, rssi
            self._replies += 1
            self._quiet_until = 0.0  # the reply is in: commands may go out again
            self._advance_course(nav)

    def _advance_course(self, nav) -> None:
        """Move on to the next mark once the boat reports being inside the arrival radius."""
        if not self._running or self._has_no_fix(nav):
            return
        if self.course.advance_if_arrived(nav.position.lat, nav.position.lon):
            self._dest_key = None  # send the new active mark
            if self.course.finished:
                self._running = False

    @staticmethod
    def _has_no_fix(nav) -> bool:
        # The boat has no GPS driver yet and reports exactly (0, 0); real fixes are never that
        return nav.position.lat == 0 and nav.position.lon == 0

    # -- commands from the app ---------------------------------------------------------------------------

    def _queue(self, channel: str, message: str, urgent: bool = False) -> None:
        self._outbox[channel] = message
        if urgent:
            self._urgent.add(channel)

    def control(self, data: Dict[str, Any]) -> None:
        """Apply a /api/control body. Only {command, value} (rudder, sails, throttle, emergency_stop) and
        {running} mean anything to the boat; the rest is the simulator's and raises NotAvailable (409)."""
        unavailable = [key for key in SIM_ONLY_KEYS if key in data]
        if data.get("command") == "set_environment":
            unavailable.append("set_environment")
        if unavailable:
            raise NotAvailable(f"{', '.join(unavailable)}: the boat has no command for it")

        command_action = self._command_action(data["command"], data.get("value")) if "command" in data else None
        if "running" not in data and command_action is None:
            raise ValueError("nothing to do: expected command or running")
        if "running" in data:
            self._set_running(bool(data["running"]))
        if command_action is not None:
            command_action()

    def _command_action(self, command: Any, value: Any) -> Callable[[], None]:
        """Validate a command now, return what applies it (so a bad body changes nothing)."""
        if command == "rudder":
            # Signed -100 (port) .. +100 (starboard) onto the servo's 0..100 scale where 50 is centre
            pct = int(round(50 + clamp(to_number(value, "rudder"), -100, 100) / 2))
            return lambda: self._send_rudder(pct)
        if command == "sails":
            pct = int(round(clamp(to_number(value, "sails"), 0, 100)))
            return lambda: self._send("sails", SetSail(Percent(pct)), trim=pct)
        if command == "throttle":
            pct = int(round(clamp(to_number(value, "throttle"), 0, 100)))
            return lambda: self._send("throttle", SetThrottle(Percent(pct)), throttle=pct)
        if command == "emergency_stop":
            return self._emergency_stop
        raise ValueError(f"unknown command {command!r}")

    def _send_rudder(self, pct: int, urgent: bool = False) -> None:
        self._send("rudder", TurnRudder(Percent(pct)), urgent=urgent, rudder=(pct - 50) * 2)

    def _send(self, channel: str, command, urgent: bool = False, **commanded: int) -> None:
        with self._lock:
            self._queue(channel, command.serialize_for_lora(), urgent)
            self._commanded.update(commanded)

    def _emergency_stop(self) -> None:
        """Rudder centre, sheet eased, motor off, and stop sending the course. Best effort: there are no acks."""
        self._set_running(False)
        self._send_rudder(50, urgent=True)
        self._send("sails", SetSail(Percent(0)), urgent=True, trim=0)
        self._send("throttle", SetThrottle(Percent(0)), urgent=True, throttle=0)

    def _set_running(self, running: bool) -> None:
        with self._lock:
            if running:
                if not len(self.course):
                    raise ValueError("add at least one mark before sending a course")
                if self.course.finished:
                    self.course.restart()
                self._dest_key = None
            else:
                self._outbox.pop("dest", None)
            self._running = running

    def set_course(self, raw_marks: Any, loop: Optional[Any] = None, active: Any = 0) -> None:
        marks = parse_marks(raw_marks)
        active = int(to_number(active, "active"))
        with self._lock:
            self.course.set_marks(marks, loop=None if loop is None else bool(loop), active=active)
            self._dest_key = None  # if the course is being sent, send the active mark again

    def clear_course(self) -> None:
        """Clears the marks here. The boat keeps steering to the last destination it was sent."""
        with self._lock:
            self.course.clear()
            self._set_running(False)

    def demo_course(self, scale: Optional[Any] = None) -> None:
        raise NotAvailable("the demo course is the simulator's")

    def reset(self, lat: Optional[Any] = None, lng: Optional[Any] = None, heading: Optional[Any] = None) -> None:
        raise NotAvailable("reset is the simulator's")

    # -- state for the app -------------------------------------------------------------------------------

    def _link_state(self, now: float) -> str:
        if self._rx_at is None:
            return "connecting" if now - self._started_at < LOST_S else "lost"
        age = now - self._rx_at
        return "ok" if age <= FRESH_S else "stale" if age <= LOST_S else "lost"

    def state(self) -> Dict[str, Any]:
        with self._lock:
            now = self._clock()
            state = dict.fromkeys(STATE_KEYS)
            nav, fix, twd = self._nav, False, None
            if nav is not None:
                fix = not self._has_no_fix(nav)
                heading = nav.heading.degrees
                # The codebase keeps the wind's direction (where it comes FROM) in the field called true_wind_angle:
                # the wind vane reads a compass direction and the Navigator subtracts the heading from it.
                twd = nav.true_wind_angle.degrees
                twa = signed_true_wind_angle(twd, heading)
                rudder = (nav.rudder_position.value - 50) * 2.0  # servo percent -> signed, as the simulator
                state.update(
                    lat=nav.position.lat if fix else None, lng=nav.position.lon if fix else None,
                    heading=heading, stw=nav.speed_over_water.knots, twd=twd, twa=twa, opt_trim=optimal_trim(abs(twa)),
                    rudder=rudder, rudder_deg=rudder / 100.0 * RUDDER_FULL_DEG,
                    trim=nav.sail_trim.value, throttle=nav.motor_throttle.value,
                )

            # Before the first report the wind is unknown, so no leg or mark is flagged upwind
            course = self.course.snapshot(twd if twd is not None else 0.0)
            if twd is None:
                for leg in course["legs"]:
                    leg["upwind"] = False
            to_mark = self.course.to_mark(state["lat"], state["lng"], twd) if fix else None
            warnings = []  # same wording as SimAutopilot.status
            if to_mark and to_mark["upwind"]:
                warnings.append("The active mark is upwind: the navigator cannot tack yet.")
            for leg in course["legs"]:
                if leg["upwind"]:
                    warnings.append(f"Leg {leg['from'] + 1} to {leg['to'] + 1} is upwind: the navigator cannot tack yet.")
            state.update(running=self._running, course=course, to_mark=to_mark, warnings=warnings)

            destination = None
            if self._commanded_dest is not None:
                sent_at = self._commanded_dest["sent_at"]
                destination = {
                    "index": self._commanded_dest["index"], "lat": self._commanded_dest["lat"],
                    "lng": self._commanded_dest["lng"],
                    "age_s": None if sent_at is None else round(now - sent_at, 1),
                }
            state.update(
                source=self.kind,
                link={
                    "kind": "boat", "state": self._link_state(now), "fix": fix, "rssi": self._rssi,
                    "age_s": None if self._rx_at is None else round(now - self._rx_at, 1),
                    "polls": self._polls, "replies": self._replies,
                },
                capabilities=dict(BOAT_CAPABILITIES),
                commanded=dict(self._commanded, destination=destination),
            )
            return state

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)


# -- stand-ins for the radio ------------------------------------------------------------------------------

class SilentRadio:
    """A radio that never hears anything, to see the app's no-link states."""
    last_rssi = None

    def register_callback(self, callback) -> None:
        pass

    def send(self, message: str) -> None:
        pass


class LoopbackRadio:
    """The simulator standing in for the boat, behind a fake radio, for developing the app without hardware.

    It handles packets like CommandReceiver does (same command classes, same order): T is answered at once with
    the simulated boat's NavParams, R/S/TR move the simulated servos, and D makes the simulated autopilot steer
    to that point. Unlike the real boat's run_loop it does not steer until it has been given a destination, so
    manual commands work from the start.
    """
    last_rssi = None

    def __init__(self, simulator):
        self.simulator = simulator
        self._callback: Optional[Callable[[str], None]] = None

    def register_callback(self, callback) -> None:
        self._callback = callback

    def send(self, message: str) -> None:
        servos = self.simulator.servos_controller
        try:
            if SetSail.can_parse_lora_data(message):
                servos.set_servo_1(SetSail.deserialize_from_lora(message).percent)
            elif TurnRudder.can_parse_lora_data(message):
                servos.set_servo_2(TurnRudder.deserialize_from_lora(message).percent)
            elif SendTelemetry.can_parse_lora_data(message):
                reply = self.simulator.nav_params_recorder.get_cur_nav_params().serialize_for_lora()
                if self._callback is not None:
                    self._callback(reply)
            elif SetDestination.can_parse_lora_data(message):
                destination = SetDestination.deserialize_from_lora(message).destination
                autopilot = self.simulator.autopilot
                autopilot.course.set_marks([(destination.lat, destination.lon)], loop=False)
                autopilot.course_changed()
                autopilot.set_running(True)
            elif SetThrottle.can_parse_lora_data(message):
                servos.set_motor_throttle(SetThrottle.deserialize_from_lora(message).throttle)
        except (ValueError, AssertionError):
            pass  # Percent asserts its range; the boat would call this "unknown command"
