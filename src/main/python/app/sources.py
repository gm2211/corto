"""Where the app's boat comes from.

The app shows the real boat: BoatSource (boat_link.py) polls it over LoRa. The simulator is a test bench
for trying the app and the navigation code without a boat; SimSource wraps it. Both answer the same calls and
serve the same /api/state keys, so the UI does not care which one it is talking to. Values the real boat's
protocol does not carry are None.

A source has:
    kind, label, note      "boat" | "sim", the name shown in the header, and an optional line printed at startup
    state()                the JSON-able dict /api/state serves (STATE_KEYS plus source, link, capabilities, commanded)
    control(data)          a /api/control body
    set_course / clear_course / demo_course / reset
    close()
Anything a source cannot do raises NotAvailable (a ValueError the app turns into a 409).
"""

import importlib.util
import sys
from typing import Any, Dict, Optional

import ultraimport

(
    initialize_simulator,
    get_boat_state,
    apply_control_request,
    set_course,
    clear_course,
    set_demo_course,
    reset_simulation,
) = ultraimport("__dir__/../simulator/simulator_integration.py", [
    "initialize_simulator",
    "get_boat_state",
    "apply_control_request",
    "set_course",
    "clear_course",
    "set_demo_course",
    "reset_simulation",
])

# Every source serves exactly these keys (plus the four extras below), in sim and boat mode alike.
STATE_KEYS = (
    "lat", "lng", "heading", "cog", "sog", "stw", "tws", "twd", "twa", "aws", "awa", "heel",
    "rudder", "rudder_deg", "trim", "opt_trim", "throttle", "drift",
    "current_speed", "current_direction", "time_scale", "sim_time",
    "mode", "running", "auto_trim", "course", "to_mark", "warnings",
)
# Added by the source itself: "boat" | "sim"; link health; what the UI may offer; what was last sent to the boat.
EXTRA_STATE_KEYS = ("source", "link", "capabilities", "commanded")

# What the UI may offer. The simulator can do everything; see boat_link.BOAT_CAPABILITIES for the boat.
SIM_CAPABILITIES = {
    "manual": True, "auto_trim": True, "mode": True, "course": True, "run_course": True,
    "demo": True, "environment": True, "time_scale": True, "reset": True,
}

SOURCE_NAMES = ("auto", "boat", "sim")
RADIO_NAMES = ("lora", "loopback", "silent")
# The same packages boat/controls/servos_factory.py looks for before using hardware, for the radio bonnet.
LORA_MODULES = ("board", "busio", "digitalio", "adafruit_rfm9x", "adafruit_ssd1306")


class NotAvailable(ValueError):
    """The source cannot do this (the real boat has no command for it). A ValueError so that ultraimport loading
    this file twice cannot break the app's handler; http_status makes it a 409 instead of a 400."""
    http_status = 409


class SourceUnavailable(RuntimeError):
    """The requested source cannot be started (no radio, ...). The message says what to try instead."""


class SimSource:
    """The simulator as a source: a test bench, not the boat."""
    kind = "sim"
    label = "Simulator"
    note: Optional[str] = None

    def __init__(self, autostart: bool = True):
        # autostart=False: a fresh simulator with no physics thread (tests)
        self.simulator = initialize_simulator(autostart)

    def state(self) -> Dict[str, Any]:
        state = get_boat_state(self.simulator)
        state.update(
            source=self.kind,
            link={"kind": "sim", "state": "ok", "age_s": 0, "fix": True, "rssi": None, "polls": None, "replies": None},
            capabilities=dict(SIM_CAPABILITIES),
            commanded=None,
        )
        return state

    def control(self, data: Dict[str, Any]) -> None:
        apply_control_request(self.simulator, data)

    def set_course(self, raw_marks: Any, loop: Optional[Any] = None, active: Any = 0) -> None:
        set_course(self.simulator, raw_marks, loop, active)

    def clear_course(self) -> None:
        clear_course(self.simulator)

    def demo_course(self, scale: Optional[Any] = None) -> None:
        set_demo_course(self.simulator, scale)

    def reset(self, lat: Optional[Any] = None, lng: Optional[Any] = None, heading: Optional[Any] = None) -> None:
        reset_simulation(self.simulator, lat, lng, heading)

    def close(self) -> None:
        self.simulator.stop()


def lora_radio_available() -> bool:
    """True on a Linux machine that has the radio bonnet's Python packages (the controller Pi)."""
    if not sys.platform.startswith("linux"):
        return False
    return all(importlib.util.find_spec(module) is not None for module in LORA_MODULES)


def build_source(name: str = "auto", radio: Optional[str] = None, poll_interval_s: float = 2.0):
    """The source for `--source` / `--radio`. Raises SourceUnavailable when it cannot be started.

    auto: the boat over LoRa when this machine has the radio libraries and the radio opens, else the simulator
    (source.note says why). --radio loopback or silent only make sense with the boat, so they imply it.
    """
    if name not in SOURCE_NAMES:
        raise ValueError(f"source must be one of {', '.join(SOURCE_NAMES)}")
    if radio is not None and radio not in RADIO_NAMES:
        raise ValueError(f"radio must be one of {', '.join(RADIO_NAMES)}")

    if name == "sim":
        if radio is not None:
            raise SourceUnavailable("--radio only applies to --source boat")
        return SimSource()

    if name == "auto" and radio in (None, "lora"):
        if not lora_radio_available():
            return _simulator_instead("this machine has no LoRa radio libraries (run with --source boat on the controller Pi)")
        try:
            return _build_boat("lora", poll_interval_s)
        except SourceUnavailable as error:
            return _simulator_instead(str(error))

    return _build_boat(radio or "lora", poll_interval_s)


def _simulator_instead(reason: str) -> SimSource:
    source = SimSource()
    source.note = f"Showing the simulator, not the boat: {reason}"
    return source


def _build_boat(radio: str, poll_interval_s: float):
    # Lazy: boat_link.py needs nothing from the hardware, but the real radio module touches the GPIO at import
    BoatSource, LoopbackRadio, SilentRadio = ultraimport(
        "__dir__/boat_link.py", ["BoatSource", "LoopbackRadio", "SilentRadio"])
    if radio == "loopback":
        simulator = initialize_simulator()
        simulator.set_time_scale(1.0)  # a boat moves in real time
        return BoatSource(LoopbackRadio(simulator), poll_interval_s=poll_interval_s, label="Boat · Loopback")
    if radio == "silent":
        return BoatSource(SilentRadio(), poll_interval_s=poll_interval_s, label="Boat · Silent")
    try:
        Radio = ultraimport("__dir__/../lora/radio.py", ["Radio"])[0]
        return BoatSource(Radio(), poll_interval_s=poll_interval_s, label="Boat · LoRa")
    except Exception as error:  # ImportError/NotImplementedError off the Pi, or no radio wired / SPI off
        raise SourceUnavailable(
            f"Could not open the LoRa radio ({type(error).__name__}: {error}). "
            "Use --source sim to try the app without a boat, or --radio loopback to develop against a fake one."
        ) from error
