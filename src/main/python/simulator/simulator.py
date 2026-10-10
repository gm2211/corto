"""Simulated sensors, servos and a small sailing-boat physics model.

Conventions used throughout (and by the UI):

* Angles are degrees. Headings and bearings are compass degrees, 0..360, clockwise from north.
* Wind direction is where the wind comes FROM. Current direction is where the water flows TOWARD.
* Rudder servo: Percent 0 = full left (port), 50 = centre, 100 = full right (starboard), the same as the
  real boat's RudderPosition. Physics and telemetry use the signed value (pct - 50) * 2, -100..100.
  A positive (starboard) rudder makes the heading increase.
* Sail servo: Percent 0 = sheet eased out, 100 = sheeted in tight (the Navigator's mapping: 45 degrees to
  the wind -> 100, 135 degrees -> 0).
* Signed wind angles (twa, awa) are positive when the wind comes over the starboard side.
"""

import math
import threading
import time
from typing import Dict, Optional, Tuple

import ultraimport

# Import dataclasses from api.objects with relative imports using ultraimport
Angle = ultraimport("__dir__/../api/objects/units/angle.py", ["Angle"])[0]
Percent = ultraimport("__dir__/../api/objects/units/percent.py", ["Percent"])[0]
GPSCoord = ultraimport("__dir__/../api/objects/units/gps_coord.py", ["GPSCoord"])[0]
Speed = ultraimport("__dir__/../api/objects/units/speed.py", ["Speed"])[0]
NavParams = ultraimport("__dir__/../api/objects/nav_params/nav_params.py", ["NavParams"])[0]
(
    M_PER_DEG_LAT,
    M_PER_KNOT,
    wrap180,
    wrap360,
) = ultraimport("__dir__/geo.py", ["M_PER_DEG_LAT", "M_PER_KNOT", "wrap180", "wrap360"])

# --- Simulation constants -------------------------------------------------------------------------------

# Open water in Casco Bay, ME (the previous default sat on shore).
DEFAULT_START = (43.6545, -70.2230)
DEFAULT_HEADING = 315.0
# Simulated seconds per wall-clock second. 15 keeps a demo lap short enough to watch.
SIM_TIME_SCALE = 15.0
MIN_TIME_SCALE = 1.0
MAX_TIME_SCALE = 30.0
# Rate of turn (deg per simulated second) with full rudder at 5 knots of boat speed.
TURN_DEG_S_AT_5KN = 12.0
# Boat speed relaxes towards its target with this time constant (simulated seconds): momentum.
MOMENTUM_TAU_S = 8.0
# The rudder still bites a little when almost stopped (prop wash, momentum), so a stalled boat can turn.
MIN_STEERAGE_KN = 0.6
# True wind angles below this give no drive (in irons).
NO_GO_DEG = 30.0
# Physics is integrated in sub-steps of at most this many simulated seconds.
MAX_SUBSTEP_S = 0.4
# Wall-clock period of the background loop.
TICK_WALL_S = 0.05
# Longest wall-clock gap integrated in one tick (protects against a stalled process / laptop sleep).
MAX_WALL_DT_S = 0.5
# Navigator.MIN_WIND_ANGLE / MAX_WIND_ANGLE: sheet fully in at 45 degrees, fully out at 135.
TRIM_MIN_WIND_ANGLE = 45.0
TRIM_MAX_WIND_ANGLE = 135.0
# Speed (knots) per knot of wind at the best point of sail with perfect trim, and full-throttle motor speed.
SAIL_SPEED_FACTOR = 0.4
MOTOR_MAX_KN = 5.0
RUDDER_FULL_DEG = 45.0  # rudder angle at 100% signed deflection, for display
RUDDER_NEUTRAL_PCT = 50

DEFAULT_WIND_SPEED = 12.0
DEFAULT_WIND_DIRECTION = 225.0
DEFAULT_CURRENT_SPEED = 0.0
DEFAULT_CURRENT_DIRECTION = 90.0


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# --- Pure sailing functions (unit-tested) -----------------------------------------------------------------

def signed_true_wind_angle(twd: float, heading: float) -> float:
    """True wind angle relative to the bow, (-180, 180]. Positive = wind over the starboard side."""
    return wrap180(twd - heading)


def optimal_trim(twa_abs: float) -> float:
    """Sheet setting (0..100) the Navigator would choose for this true wind angle: 45 deg -> 100, 135 deg -> 0."""
    t = clamp(abs(twa_abs), TRIM_MIN_WIND_ANGLE, TRIM_MAX_WIND_ANGLE)
    return 100.0 * (1.0 - (t - TRIM_MIN_WIND_ANGLE) / (TRIM_MAX_WIND_ANGLE - TRIM_MIN_WIND_ANGLE))


def polar_factor(twa_abs: float) -> float:
    """Fraction (0..1) of the wind's drive available at this true wind angle: best at 120 deg, zero in irons."""
    twa_abs = abs(twa_abs)
    if twa_abs < NO_GO_DEG:
        return 0.0
    return clamp(1.0 - abs(twa_abs - 120.0) / 120.0, 0.0, 1.0)


def trim_match(trim: float, twa_abs: float) -> float:
    """How well the sheet suits this wind angle: 1 at the optimal trim, 0 when 60 points or more away."""
    return max(0.0, 1.0 - abs(trim - optimal_trim(twa_abs)) / 60.0)


def apparent_wind(tws: float, twd: float, stw: float, hdg: float) -> Tuple[float, float]:
    """Apparent wind as felt on the boat: returns (aws, awa_signed).

    tws/stw in knots, twd (direction the wind comes from) and hdg in degrees. awa is positive when the
    apparent wind comes over the starboard side.
    """
    air_e = -tws * math.sin(math.radians(twd))  # velocity of the air over the ground (east, north)
    air_n = -tws * math.cos(math.radians(twd))
    boat_e = stw * math.sin(math.radians(hdg))
    boat_n = stw * math.cos(math.radians(hdg))
    rel_e, rel_n = air_e - boat_e, air_n - boat_n  # air relative to the boat
    aws = math.hypot(rel_e, rel_n)
    if aws < 1e-9:
        return 0.0, 0.0
    comes_from = math.degrees(math.atan2(-rel_e, -rel_n)) % 360.0
    return aws, wrap180(comes_from - hdg)


def heel_estimate(aws: float, awa_signed: float, trim: float) -> float:
    """Rough heel magnitude in degrees (an estimate, not a hydrodynamic model), capped at 30."""
    return min(30.0, 0.15 * aws ** 2 * abs(math.sin(math.radians(awa_signed))) * trim / 100.0)


# --- Simulated sensors ----------------------------------------------------------------------------------

class SimulatedSensor:
    """Base class for simulated sensors"""

    def __init__(self):
        self._lock = threading.Lock()

    def set_value(self, value):
        with self._lock:
            self._value = value

    def get_value(self):
        with self._lock:
            return self._value


class SimulatedWindVane(SimulatedSensor):
    """Simulated wind vane sensor. The value is the direction the true wind comes FROM."""

    def __init__(self, initial_wind_angle: float = DEFAULT_WIND_DIRECTION):
        super().__init__()
        self._value = Angle(initial_wind_angle)

    def get_true_wind(self) -> Angle:
        return self.get_value()


class SimulatedGPSLocator(SimulatedSensor):
    """Simulated GPS locator sensor"""

    def __init__(self, initial_lat: float = DEFAULT_START[0], initial_lon: float = DEFAULT_START[1]):
        super().__init__()
        self._location = GPSCoord(initial_lat, initial_lon)
        self._heading = Angle(DEFAULT_HEADING)
        self._speed = Speed(0.0)
        self._course = Angle(DEFAULT_HEADING)

    def set_location(self, lat: float, lon: float):
        self._location = GPSCoord(lat, lon)

    def set_heading(self, heading: float):
        self._heading = Angle(heading)

    def set_speed(self, speed: float):
        self._speed = Speed(speed)

    def set_course(self, course: float):
        self._course = Angle(course)

    def cur_location(self) -> GPSCoord:
        return self._location

    def cur_heading(self) -> Angle:
        return self._heading

    def cur_speed_over_ground(self) -> Speed:
        return self._speed

    def cur_course_over_ground(self) -> Angle:
        return self._course


class SimulatedServosController:
    """Simulated servos controller.

    servo_1 = sail trim (0..100), servo_2 = rudder (0 left .. 50 centre .. 100 right), plus the motor.
    """

    def __init__(self):
        self.servo_1_position = Percent(0)  # Sail trim
        self.servo_2_position = Percent(RUDDER_NEUTRAL_PCT)  # Rudder position (50 = centre)
        self.motor_throttle = Percent(0)
        self._callbacks = []

    def register_callback(self, callback):
        """Register a callback to be called when servo positions change"""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        """Notify all callbacks of servo position changes"""
        for callback in self._callbacks:
            callback(self.servo_1_position, self.servo_2_position, self.motor_throttle)

    def set_servo_1(self, position: Percent):
        """Set sail trim servo position"""
        self.servo_1_position = position
        self._notify_callbacks()

    def set_servo_2(self, position: Percent):
        """Set rudder servo position"""
        self.servo_2_position = position
        self._notify_callbacks()

    def set_motor_throttle(self, throttle: Percent):
        """Set motor throttle"""
        self.motor_throttle = throttle
        self._notify_callbacks()

    def reset_servos(self):
        """Reset the sail and motor to zero and centre the rudder"""
        self.servo_1_position = Percent(0)
        self.servo_2_position = Percent(RUDDER_NEUTRAL_PCT)
        self.motor_throttle = Percent(0)
        self._notify_callbacks()


class SimulatedNavParamsRecorder:
    """Simulated navigation parameters recorder"""

    def __init__(self, initial_params: Optional[NavParams] = None):
        self._lock = threading.Lock()
        if initial_params is None:
            self._nav_params = NavParams(
                heading=Angle(DEFAULT_HEADING),
                rudder_position=Percent(RUDDER_NEUTRAL_PCT),
                position=GPSCoord(*DEFAULT_START),
                motor_throttle=Percent(0),
                speed_over_water=Speed(0.0),
                true_wind_angle=Angle(DEFAULT_WIND_DIRECTION),
                sail_trim=Percent(0)
            )
        else:
            self._nav_params = initial_params

    def get_cur_nav_params(self) -> NavParams:
        return self._nav_params

    def _replace(self, **changes):
        with self._lock:
            self._nav_params = self._nav_params._replace(**changes)

    def record_heading(self, heading: Angle):
        self._replace(heading=heading)

    def record_rudder_position(self, position: Percent):
        self._replace(rudder_position=position)

    def record_position(self, position: GPSCoord):
        self._replace(position=position)

    def record_motor_throttle(self, throttle: Percent):
        self._replace(motor_throttle=throttle)

    def record_speed_over_water(self, speed: Speed):
        self._replace(speed_over_water=speed)

    def record_true_wind_angle(self, angle: Angle):
        self._replace(true_wind_angle=angle)

    def record_sail_trim(self, trim: Percent):
        self._replace(sail_trim=trim)


# --- Physics --------------------------------------------------------------------------------------------

class BoatPhysicsSimulator:
    """Simulates boat physics based on control inputs and environmental factors.

    The model is deliberately small: a polar-style drive curve with a no-go zone and a sail-trim
    match, momentum, a speed-dependent rate of turn, current, and apparent wind / heel for display.
    Position is integrated in metres with a cos(latitude) correction on longitude.
    """

    def __init__(
            self,
            gps_locator: SimulatedGPSLocator,
            wind_vane: SimulatedWindVane,
            nav_params_recorder: SimulatedNavParamsRecorder,
            servos_controller: SimulatedServosController,
            autostart: bool = True,
            ):
        self.gps_locator = gps_locator
        self.wind_vane = wind_vane
        self.nav_params_recorder = nav_params_recorder
        self.servos_controller = servos_controller

        # Environmental factors
        self.wind_speed = DEFAULT_WIND_SPEED  # knots
        self.wind_direction = DEFAULT_WIND_DIRECTION  # degrees, wind comes FROM
        self.current_speed = DEFAULT_CURRENT_SPEED  # knots
        self.current_direction = DEFAULT_CURRENT_DIRECTION  # degrees, current flows TOWARD
        self.time_scale = SIM_TIME_SCALE

        # Boat state (the source of truth; mirrored into the simulated sensors every sub-step)
        self._lat, self._lon = DEFAULT_START
        self._heading = DEFAULT_HEADING
        self._stw = 0.0  # speed through water, knots
        self._sim_time = 0.0

        # Optional per-sub-step controller (see autopilot.SimAutopilot): anything with a step() method
        self.autopilot = None

        self._lock = threading.RLock()
        self._telemetry_lock = threading.Lock()
        self._telemetry: Dict[str, float] = {}

        self.wind_vane.set_value(Angle(self.wind_direction))
        self._sync_sensors(0.0, self._heading, 0.0)
        self._publish()

        # Register callback for servo position changes
        self.servos_controller.register_callback(self._on_servo_change)

        # Start simulation thread
        self._running = True
        self._thread = threading.Thread(target=self._simulation_loop, name="boat-physics", daemon=True)
        if autostart:
            self._thread.start()

    # -- configuration ---------------------------------------------------------------------------

    def _on_servo_change(self, sail_trim: Percent, rudder_position: Percent, motor_throttle: Percent):
        """Called when servo positions change"""
        # Update nav params recorder
        self.nav_params_recorder.record_sail_trim(sail_trim)
        self.nav_params_recorder.record_rudder_position(rudder_position)
        self.nav_params_recorder.record_motor_throttle(motor_throttle)
        # Keep the published telemetry (rudder, trim, throttle) in step with the controls
        self.refresh_telemetry()

    def set_autopilot(self, autopilot) -> None:
        self.autopilot = autopilot

    def set_time_scale(self, time_scale: float) -> None:
        with self._lock:
            self.time_scale = clamp(float(time_scale), MIN_TIME_SCALE, MAX_TIME_SCALE)

    def set_environmental_factors(
            self, wind_speed: float, wind_direction: float,
            current_speed: float, current_direction: float
            ):
        """Set environmental factors for simulation"""
        with self._lock:
            self.wind_speed = clamp(float(wind_speed), 0.0, 60.0)
            self.wind_direction = wrap360(float(wind_direction))
            self.current_speed = clamp(float(current_speed), 0.0, 10.0)
            self.current_direction = wrap360(float(current_direction))

            # Update wind vane with new wind direction
            self.wind_vane.set_value(Angle(self.wind_direction))
            self._publish()

    def get_environment(self) -> Dict[str, float]:
        return {
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "current_speed": self.current_speed,
            "current_direction": self.current_direction,
        }

    def reset(self, lat: Optional[float] = None, lon: Optional[float] = None, heading: Optional[float] = None):
        """Put the boat back at rest (default: the start point and heading) with neutral controls."""
        with self._lock:
            self._lat = DEFAULT_START[0] if lat is None else float(lat)
            self._lon = DEFAULT_START[1] if lon is None else float(lon)
            self._heading = wrap360(DEFAULT_HEADING if heading is None else float(heading))
            self._stw = 0.0
            self._sim_time = 0.0
            self.servos_controller.reset_servos()
            self._sync_sensors(0.0, self._heading, 0.0)
            self._publish()

    # -- loop ------------------------------------------------------------------------------------

    def _simulation_loop(self):
        """Main simulation loop"""
        last_time = time.monotonic()

        while self._running:
            now = time.monotonic()
            dt_wall = min(now - last_time, MAX_WALL_DT_S)
            last_time = now

            self.advance(dt_wall * self.time_scale)

            time.sleep(TICK_WALL_S)

    def advance(self, dt_sim: float) -> None:
        """Advance the simulation by `dt_sim` simulated seconds, in sub-steps of at most MAX_SUBSTEP_S.

        The autopilot (if any) runs before every sub-step, like Corto.run_loop runs against the live boat.
        """
        if dt_sim <= 0:
            return
        steps = max(1, math.ceil(dt_sim / MAX_SUBSTEP_S))
        h = dt_sim / steps
        with self._lock:
            for _ in range(steps):
                autopilot = self.autopilot
                if autopilot is not None:
                    autopilot.step()
                self._step(h)
            self._publish()

    def _step(self, dt: float) -> None:
        """One physics sub-step of `dt` simulated seconds."""
        pct = float(self.servos_controller.servo_2_position.value)
        trim = float(self.servos_controller.servo_1_position.value)
        throttle = float(self.servos_controller.motor_throttle.value)
        rudder = (pct - RUDDER_NEUTRAL_PCT) * 2.0  # signed, -100..100, positive = starboard

        twa_abs = abs(signed_true_wind_angle(self.wind_direction, self._heading))

        # Drive: polar curve x trim match, plus the motor, relaxed towards by a time constant (momentum)
        sail_kn = self.wind_speed * polar_factor(twa_abs) * trim_match(trim, twa_abs) * SAIL_SPEED_FACTOR
        motor_kn = throttle / 100.0 * MOTOR_MAX_KN
        target = sail_kn + motor_kn
        self._stw += (target - self._stw) * (1.0 - math.exp(-dt / MOMENTUM_TAU_S))

        # Turn: proportional to rudder and boat speed (with a floor so a stalled boat can still steer)
        steerage_kn = max(self._stw, MIN_STEERAGE_KN)
        turn_deg_s = rudder / 100.0 * steerage_kn / 5.0 * TURN_DEG_S_AT_5KN
        self._heading = wrap360(self._heading + turn_deg_s * dt)

        # Motion over the ground = velocity through the water + current, in metres per second
        h_rad = math.radians(self._heading)
        c_rad = math.radians(self.current_direction)
        v_boat = self._stw * M_PER_KNOT
        v_curr = self.current_speed * M_PER_KNOT
        east = v_boat * math.sin(h_rad) + v_curr * math.sin(c_rad)
        north = v_boat * math.cos(h_rad) + v_curr * math.cos(c_rad)
        self._lat += north * dt / M_PER_DEG_LAT
        self._lon += east * dt / (M_PER_DEG_LAT * math.cos(math.radians(self._lat)))
        self._sim_time += dt

        sog = math.hypot(east, north) / M_PER_KNOT
        cog = wrap360(math.degrees(math.atan2(east, north))) if sog > 1e-6 else self._heading
        self._sync_sensors(sog, cog, self._stw)

    def _sync_sensors(self, sog: float, cog: float, stw: float) -> None:
        """Mirror the boat state into the simulated sensors and the nav params recorder."""
        self.gps_locator.set_location(self._lat, self._lon)
        self.gps_locator.set_heading(self._heading)
        self.gps_locator.set_speed(sog)
        self.gps_locator.set_course(cog)
        self.nav_params_recorder.record_heading(Angle(self._heading))
        self.nav_params_recorder.record_position(GPSCoord(self._lat, self._lon))
        self.nav_params_recorder.record_speed_over_water(Speed(stw))
        self.nav_params_recorder.record_true_wind_angle(Angle(self.wind_direction))

    # -- telemetry ----------------------------------------------------------------------------------

    def _publish(self) -> None:
        """Compute and publish the telemetry dict (atomically replaced under a lock)."""
        hdg = self._heading
        pct = float(self.servos_controller.servo_2_position.value)
        trim = float(self.servos_controller.servo_1_position.value)
        rudder = (pct - RUDDER_NEUTRAL_PCT) * 2.0
        twa = signed_true_wind_angle(self.wind_direction, hdg)
        aws, awa = apparent_wind(self.wind_speed, self.wind_direction, self._stw, hdg)
        heel_mag = heel_estimate(aws, awa, trim)
        sog = self.gps_locator.cur_speed_over_ground().knots
        cog = self.gps_locator.cur_course_over_ground().degrees
        telemetry = {
            "lat": self._lat,
            "lng": self._lon,
            "heading": hdg,
            "cog": cog,
            "sog": sog,
            "stw": self._stw,
            "tws": self.wind_speed,
            "twd": self.wind_direction,
            "twa": twa,  # signed, + = wind over the starboard side
            "aws": aws,
            "awa": awa,  # signed
            "heel": -math.copysign(heel_mag, awa) if heel_mag > 0 else 0.0,  # + = leaning to starboard (est.)
            "rudder": rudder,  # signed, -100..100, + = starboard
            "rudder_deg": rudder / 100.0 * RUDDER_FULL_DEG,
            "trim": trim,
            "opt_trim": optimal_trim(abs(twa)),
            "throttle": float(self.servos_controller.motor_throttle.value),
            "drift": wrap180(cog - hdg),  # COG minus heading: set by the current
            "current_speed": self.current_speed,
            "current_direction": self.current_direction,
            "time_scale": self.time_scale,
            "sim_time": self._sim_time,
        }
        with self._telemetry_lock:
            self._telemetry = telemetry

    def get_telemetry(self) -> Dict[str, float]:
        """A copy of the latest telemetry dict."""
        with self._telemetry_lock:
            return dict(self._telemetry)

    def refresh_telemetry(self) -> None:
        """Re-publish telemetry (e.g. after a control change) without advancing time."""
        with self._lock:
            self._publish()

    def stop(self):
        """Stop the simulation"""
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)


def build_simulator(autostart: bool = True) -> BoatPhysicsSimulator:
    """Create a simulator with fresh simulated components."""
    return BoatPhysicsSimulator(
        gps_locator=SimulatedGPSLocator(),
        wind_vane=SimulatedWindVane(),
        nav_params_recorder=SimulatedNavParamsRecorder(),
        servos_controller=SimulatedServosController(),
        autostart=autostart,
    )


# Singleton instance for global access
_simulator_instance = None
_simulator_lock = threading.Lock()


def get_simulator():
    """Get the global simulator instance"""
    global _simulator_instance
    with _simulator_lock:
        if _simulator_instance is None:
            _simulator_instance = build_simulator()
    return _simulator_instance
