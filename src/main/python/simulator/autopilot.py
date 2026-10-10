"""Autopilot for the simulator: a course of marks, driven by the boat's own Navigator.

The Navigator in boat/navigation/navigator.py is the code that runs on the real boat; here it is fed the
simulated wind vane, GPS and nav params recorder, and its attitude (rudder + sail trim) is applied to the
simulated servos the same way Corto.run_loop applies it to the real ones.

Out of scope for now: tacking. The Navigator steers straight at the active mark, so a leg that points
(nearly) into the wind cannot be sailed. Such legs are flagged ("upwind") and the UI warns about them.
"""

import math
import os
import sys
import threading
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

import ultraimport

# The navigator is written against the same import roots boat/run.sh sets up (src/main/python and
# src/main/python/boat), so put them on sys.path before importing it.
_PYTHON_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for _path in (os.path.join(_PYTHON_ROOT, "boat"), _PYTHON_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from navigation.navigator import Navigator  # noqa: E402  (needs the sys.path setup above)
from api.objects.units.gps_coord import GPSCoord  # noqa: E402

Percent = ultraimport("__dir__/../api/objects/units/percent.py", ["Percent"])[0]
(
    bearing_deg,
    distance_m,
    fold180,
    offset,
) = ultraimport("__dir__/geo.py", ["bearing_deg", "distance_m", "fold180", "offset"])

MODE_MANUAL = "manual"
MODE_AUTO = "auto"

ARRIVAL_RADIUS_M = 15.0
# A leg whose bearing is within this many degrees of the wind direction cannot be sailed without tacking.
UPWIND_LIMIT_DEG = 45.0
MAX_MARKS = 50

# The demo triangle: true wind angles of 90, 135 and 65 degrees on the three legs (a beam reach, a broad
# reach and a close reach), rotated to the current wind. Offsets are leg bearing minus wind direction.
DEMO_LEG_OFFSETS_DEG = (90.0, -135.0, -65.0)
DEMO_BASE_LEG_M = 200.0  # length of the last leg at scale 1
# Scale applied to the demo so the course reads at zoom 17 in the UI.
DEMO_SCALE = 1.5


class Mark(NamedTuple):
    lat: float
    lng: float


class Course:
    """An ordered list of marks, the active one, and whether to loop. Thread-safe."""

    def __init__(self, marks: Sequence[Tuple[float, float]] = (), loop: bool = True,
                 radius_m: float = ARRIVAL_RADIUS_M):
        self._lock = threading.RLock()
        self._marks: List[Mark] = [Mark(float(m[0]), float(m[1])) for m in marks]
        self.active = 0
        self.loop = bool(loop)
        self.radius_m = radius_m
        self.finished = False
        self.laps = 0

    # -- construction ----------------------------------------------------------------------------

    @classmethod
    def demo(cls, start: Tuple[float, float], twd: float, scale: float = DEMO_SCALE) -> "Course":
        """A closed triangle from `start` at true wind angles of 90, 135 and 65 degrees, rotated to `twd`.

        For the default start (43.6545, -70.2230) and wind from 225 degrees (scale 1) the marks are about
        (43.65619, -70.22534), (43.65619, -70.22385) and back to the start.
        """
        bearings = [twd + off for off in DEMO_LEG_OFFSETS_DEG]
        s = [(math.sin(math.radians(b)), math.cos(math.radians(b))) for b in bearings]
        last = DEMO_BASE_LEG_M * scale
        # Close the triangle: L1*e1 + L2*e2 + L3*e3 = 0 for the leg lengths, given the last one.
        det = s[0][0] * s[1][1] - s[1][0] * s[0][1]
        rhs_e, rhs_n = -last * s[2][0], -last * s[2][1]
        l1 = (rhs_e * s[1][1] - s[1][0] * rhs_n) / det
        l2 = (s[0][0] * rhs_n - rhs_e * s[0][1]) / det
        m1 = offset(start[0], start[1], bearings[0], l1)
        m2 = offset(m1[0], m1[1], bearings[1], l2)
        return cls([m1, m2, (start[0], start[1])], loop=True)

    def set_marks(self, marks: Sequence[Tuple[float, float]], loop: Optional[bool] = None,
                  active: int = 0) -> None:
        with self._lock:
            self._marks = [Mark(float(m[0]), float(m[1])) for m in marks][:MAX_MARKS]
            self.active = max(0, min(int(active), max(0, len(self._marks) - 1)))
            if loop is not None:
                self.loop = bool(loop)
            self.finished = False
            self.laps = 0

    def clear(self) -> None:
        self.set_marks([])

    def restart(self) -> None:
        """Head for the first mark again."""
        with self._lock:
            self.active = 0
            self.finished = False
            self.laps = 0

    # -- queries ---------------------------------------------------------------------------------

    @property
    def marks(self) -> List[Mark]:
        with self._lock:
            return list(self._marks)

    def __len__(self) -> int:
        with self._lock:
            return len(self._marks)

    def target(self) -> Optional[Mark]:
        """The mark being sailed to, or None if there is none or the course is finished."""
        with self._lock:
            if self.finished or not self._marks:
                return None
            return self._marks[self.active]

    def advance_if_arrived(self, lat: float, lng: float) -> bool:
        """Move on to the next mark when within the arrival radius. Returns True if the mark changed."""
        with self._lock:
            mark = self.target()
            if mark is None or distance_m(lat, lng, mark.lat, mark.lng) > self.radius_m:
                return False
            n = len(self._marks)
            if self.active + 1 < n:
                self.active += 1
            elif self.loop and n > 1:
                self.active = 0
                self.laps += 1
            else:
                self.finished = True
            return True

    @staticmethod
    def is_upwind(bearing: float, twd: float) -> bool:
        """True if sailing on `bearing` points closer than 45 degrees to the wind (needs a tack)."""
        return fold180(bearing - twd) < UPWIND_LIMIT_DEG

    def legs(self, twd: float) -> List[Dict[str, Any]]:
        """Mark-to-mark legs (including the closing leg when looping): bearing, length and an upwind flag."""
        with self._lock:
            marks = list(self._marks)
            loop = self.loop and len(marks) >= 2
        legs = []
        pairs = [(i, i + 1) for i in range(len(marks) - 1)]
        if loop:
            pairs.append((len(marks) - 1, 0))
        for a, b in pairs:
            brg = bearing_deg(marks[a].lat, marks[a].lng, marks[b].lat, marks[b].lng)
            legs.append({
                "from": a,
                "to": b,
                "bearing": brg,
                "distance_m": distance_m(marks[a].lat, marks[a].lng, marks[b].lat, marks[b].lng),
                "upwind": self.is_upwind(brg, twd),
            })
        return legs

    def to_mark(self, lat: float, lng: float, twd: float) -> Optional[Dict[str, Any]]:
        """Bearing and distance from the boat to the active mark (None when there is no target)."""
        mark = self.target()
        if mark is None:
            return None
        with self._lock:
            index = self.active
        brg = bearing_deg(lat, lng, mark.lat, mark.lng)
        return {
            "index": index,
            "bearing": brg,
            "distance_m": distance_m(lat, lng, mark.lat, mark.lng),
            "upwind": self.is_upwind(brg, twd),
        }

    def snapshot(self, twd: float) -> Dict[str, Any]:
        with self._lock:
            return {
                "marks": [{"lat": m.lat, "lng": m.lng} for m in self._marks],
                "active": self.active,
                "loop": self.loop,
                "finished": self.finished,
                "laps": self.laps,
                "radius_m": self.radius_m,
                "legs": self.legs(twd),
            }


class SimAutopilot:
    """Runs the boat's Navigator against the simulator and applies its attitude to the simulated servos.

    Modes:
      manual                      the human drives rudder and sheet (default);
      manual + auto_trim          the human steers, the Navigator trims the sheet to the wind angle;
      auto (while `running`)      the Navigator steers to the active mark and trims the sheet.

    step() is called by the physics loop before every sub-step, mirroring Corto.run_loop.
    """

    def __init__(self, sim, course: Optional[Course] = None):
        self.sim = sim
        self.course = course if course is not None else Course()
        self.navigator = Navigator(sim.wind_vane, sim.gps_locator, sim.nav_params_recorder)
        self.mode = MODE_MANUAL
        self.running = False
        self.auto_trim = False
        self._latest: Optional[Tuple[float, float]] = None
        self._lock = threading.RLock()

    # -- control ---------------------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        if mode not in (MODE_MANUAL, MODE_AUTO):
            raise ValueError(f"mode must be '{MODE_MANUAL}' or '{MODE_AUTO}', not {mode!r}")
        with self._lock:
            if mode != self.mode:
                self.mode = mode
                self.running = False  # switching modes always starts paused
                self._latest = None

    def set_running(self, running: bool) -> None:
        with self._lock:
            running = bool(running)
            if running and self.mode != MODE_AUTO:
                self.mode = MODE_AUTO
            if running and self.course.finished:
                self.course.restart()
            if self.running and not running:
                self._centre_rudder()
            self.running = running
            self._latest = None

    def set_auto_trim(self, enabled: bool) -> None:
        with self._lock:
            self.auto_trim = bool(enabled)
            self._latest = None

    def course_changed(self) -> None:
        """Call after the course is edited so the next step re-applies the attitude."""
        with self._lock:
            self._latest = None

    def _centre_rudder(self) -> None:
        self.sim.servos_controller.set_servo_2(Percent(50))

    # -- the loop --------------------------------------------------------------------------------

    @property
    def steering(self) -> bool:
        return self.mode == MODE_AUTO and self.running

    @property
    def trimming(self) -> bool:
        return self.steering or (self.mode == MODE_MANUAL and self.auto_trim)

    def step(self) -> None:
        """One autopilot iteration: compute the attitude for the active mark and apply it to the servos."""
        with self._lock:
            steering, trimming = self.steering, self.trimming
            if not (steering or trimming):
                return
            here = self.sim.gps_locator.cur_location()
            if steering:
                self.course.advance_if_arrived(here.lat, here.lon)
                mark = self.course.target()
                if mark is None:  # no marks, or the course is finished: centre the helm and stop
                    self._centre_rudder()
                    self.running = False
                    return
                dest = GPSCoord(mark.lat, mark.lng)
            else:
                dest = here  # trim depends on the wind angle only, so any destination will do
            attitude = self.navigator.compute_boat_attitude(dest)
            rudder_pct = attitude.rudder_position.percent.value
            trim_pct = attitude.sail_trim.value
            key = (round(rudder_pct, 3) if steering else None, round(trim_pct, 3) if trimming else None)
            if key == self._latest:
                return
            servos = self.sim.servos_controller
            if steering:
                servos.set_servo_2(Percent(rudder_pct))
            if trimming:
                servos.set_servo_1(Percent(trim_pct))
            self._latest = key

    # -- reporting -------------------------------------------------------------------------------

    def status(self, lat: float, lng: float, twd: float) -> Dict[str, Any]:
        """Mode, course and the leg to the active mark, as returned by the API."""
        course = self.course.snapshot(twd)
        to_mark = self.course.to_mark(lat, lng, twd)
        warnings = []
        if to_mark and to_mark["upwind"]:
            warnings.append("The active mark is upwind: the navigator cannot tack yet.")
        for leg in course["legs"]:
            if leg["upwind"]:
                warnings.append(f"Leg {leg['from'] + 1} to {leg['to'] + 1} is upwind: the navigator cannot tack yet.")
        return {
            "mode": self.mode,
            "running": self.running,
            "auto_trim": self.auto_trim,
            "course": course,
            "to_mark": to_mark,
            "warnings": warnings,
        }
