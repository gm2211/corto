"""
Integration module to connect the simulator with the Flask app.
This module provides functions to:
1. Initialize the simulator (and attach the autopilot)
2. Build the boat state the app serves, from simulator telemetry plus the course and mode
3. Pass UI controls to the simulator, clamping and validating everything that comes from the network

Rudder convention (same as the real boat's RudderPosition): the servo takes a Percent where 0 = full left,
50 = centre, 100 = full right. The UI and the API speak a signed rudder, -100 (port) .. +100 (starboard).
"""

import math
from typing import Any, Dict, Optional

import ultraimport

Percent = ultraimport("__dir__/../api/objects/units/percent.py", ["Percent"])[0]
get_simulator = ultraimport("__dir__/simulator.py", ["get_simulator"])[0]
(
    SimAutopilot,
    Course,
    MAX_MARKS,
) = ultraimport("__dir__/autopilot.py", ["SimAutopilot", "Course", "MAX_MARKS"])


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def to_number(value: Any, name: str = "value") -> float:
    """Convert a JSON value to a finite float, or raise ValueError (the app turns that into a 400)."""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def initialize_simulator():
    """Initialize the simulator, attach the autopilot, and return the simulator instance"""
    simulator = get_simulator()
    if simulator.autopilot is None:
        simulator.set_autopilot(SimAutopilot(simulator))
    return simulator


def get_boat_state(simulator) -> Dict[str, Any]:
    """The JSON-able state the UI polls: telemetry + mode + course + leg to the active mark."""
    state = simulator.get_telemetry()
    state.update(simulator.autopilot.status(state["lat"], state["lng"], state["twd"]))
    return state


def parse_marks(raw_marks: Any) -> list:
    """Validate a list of {lat, lng} (or [lat, lng]) marks and return [(lat, lng), ...]."""
    if not isinstance(raw_marks, list):
        raise ValueError("marks must be a list")
    if len(raw_marks) > MAX_MARKS:
        raise ValueError(f"at most {MAX_MARKS} marks are supported")
    marks = []
    for i, raw in enumerate(raw_marks):
        if isinstance(raw, dict):
            lat, lng = raw.get("lat"), raw.get("lng", raw.get("lon"))
        elif isinstance(raw, (list, tuple)) and len(raw) == 2:
            lat, lng = raw
        else:
            raise ValueError(f"mark {i + 1} must be {{lat, lng}} or [lat, lng]")
        lat, lng = to_number(lat, f"mark {i + 1} lat"), to_number(lng, f"mark {i + 1} lng")
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError(f"mark {i + 1} is outside the valid lat/lng range")
        marks.append((lat, lng))
    return marks


def set_course(simulator, raw_marks: Any, loop: Optional[Any] = None, active: Any = 0) -> None:
    marks = parse_marks(raw_marks)
    simulator.autopilot.course.set_marks(marks, loop=None if loop is None else bool(loop),
                                         active=int(to_number(active, "active")))
    simulator.autopilot.course_changed()


def clear_course(simulator) -> None:
    simulator.autopilot.course.clear()
    simulator.autopilot.set_running(False)


def set_demo_course(simulator, scale: Optional[Any] = None) -> None:
    """Replace the course with the demo triangle, from the boat's current position and the current wind."""
    state = simulator.get_telemetry()
    kwargs = {}
    if scale is not None:
        kwargs["scale"] = clamp(to_number(scale, "scale"), 0.25, 5.0)
    simulator.autopilot.course.set_marks(
        Course.demo((state["lat"], state["lng"]), state["twd"], **kwargs).marks, loop=True
    )
    simulator.autopilot.course_changed()


def reset_simulation(simulator, lat: Optional[Any] = None, lng: Optional[Any] = None,
                     heading: Optional[Any] = None) -> None:
    """Boat back to the start (or the given point), controls neutral, autopilot paused on mark 1."""
    kwargs: Dict[str, float] = {}
    if lat is not None or lng is not None:
        if lat is None or lng is None:
            raise ValueError("lat and lng must be given together")
        lat, lng = to_number(lat, "lat"), to_number(lng, "lng")
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError("lat/lng out of range")
        kwargs.update(lat=lat, lon=lng)
    if heading is not None:
        kwargs["heading"] = to_number(heading, "heading")
    autopilot = simulator.autopilot
    autopilot.set_running(False)
    autopilot.set_mode("manual")
    autopilot.set_auto_trim(False)
    autopilot.course.restart()
    simulator.reset(**kwargs)


def process_control_command(command, value, simulator):
    """Process a control command from the UI and update the simulator.

    Raises ValueError for malformed input; out-of-range numbers are clamped rather than rejected.
    """
    servos_controller = simulator.servos_controller

    if command == 'rudder':
        # Signed -100 (full left) .. +100 (full right) onto the servo's 0..100 scale where 50 is centre
        signed = clamp(to_number(value, "rudder"), -100, 100)
        servos_controller.set_servo_2(Percent(round(50 + signed / 2)))
    elif command == 'sails':
        servos_controller.set_servo_1(Percent(round(clamp(to_number(value, "sails"), 0, 100))))
    elif command == 'throttle':
        servos_controller.set_motor_throttle(Percent(round(clamp(to_number(value, "throttle"), 0, 100))))
    elif command == 'emergency_stop':
        servos_controller.reset_servos()
        simulator.autopilot.set_running(False)
        simulator.autopilot.set_mode("manual")
        simulator.autopilot.set_auto_trim(False)
    elif command == 'set_environment':
        # value is a dict with any of wind_speed, wind_direction, current_speed, current_direction;
        # fields that are left out keep their current value
        if not isinstance(value, dict):
            raise ValueError("set_environment needs an object")
        env = simulator.get_environment()
        for key in env:
            if key in value:
                env[key] = to_number(value[key], key)
        simulator.set_environmental_factors(
            env['wind_speed'], env['wind_direction'], env['current_speed'], env['current_direction']
        )
    else:
        raise ValueError(f"unknown command {command!r}")

    simulator.refresh_telemetry()
    # Return success status
    return True


def apply_control_request(simulator, data: Dict[str, Any]) -> None:
    """Apply a /api/control body. Accepts the legacy {command, value} form plus mode / running /
    auto_trim / time_scale (any combination)."""
    autopilot = simulator.autopilot
    handled = False

    if 'mode' in data:
        mode = data['mode']
        if mode not in ('manual', 'auto'):
            raise ValueError("mode must be 'manual' or 'auto'")
        autopilot.set_mode(mode)
        handled = True
    if 'auto_trim' in data:
        autopilot.set_auto_trim(bool(data['auto_trim']))
        handled = True
    if 'running' in data:
        autopilot.set_running(bool(data['running']))
        handled = True
    if 'time_scale' in data:
        simulator.set_time_scale(to_number(data['time_scale'], "time_scale"))
        handled = True
    if 'command' in data:
        process_control_command(data['command'], data.get('value'), simulator)
        handled = True
    if not handled:
        raise ValueError("nothing to do: expected command, mode, running, auto_trim or time_scale")
    simulator.refresh_telemetry()
