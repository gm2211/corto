"""Course (marks, arrival, looping, upwind legs), the demo triangle, and the autopilot driving a lap."""
import pytest

from api.objects.units.percent import Percent
from simulator.autopilot import ARRIVAL_RADIUS_M, Course, SimAutopilot
from simulator.geo import fold180, haversine_m, offset
from simulator.simulator import DEFAULT_START, build_simulator

WIND_FROM = 225.0


def marks_around(start, n=3, spacing_m=100.0):
    out, pos = [], start
    for i in range(n):
        pos = offset(pos[0], pos[1], 90.0, spacing_m)
        out.append(pos)
    return out


def test_marks_advance_on_arrival():
    marks = marks_around(DEFAULT_START)
    course = Course(marks, loop=False)
    assert course.active == 0
    # 50 m away from mark 1: not arrived
    far = offset(marks[0][0], marks[0][1], 0.0, 50.0)
    assert course.advance_if_arrived(*far) is False and course.active == 0
    # just outside / just inside the arrival radius
    assert course.advance_if_arrived(*offset(marks[0][0], marks[0][1], 0.0, ARRIVAL_RADIUS_M + 1)) is False
    assert course.advance_if_arrived(*offset(marks[0][0], marks[0][1], 0.0, ARRIVAL_RADIUS_M - 1)) is True
    assert course.active == 1
    assert course.target().lat == pytest.approx(marks[1][0])


def test_course_loops_back_to_the_first_mark():
    marks = marks_around(DEFAULT_START)
    course = Course(marks, loop=True)
    for mark in marks:
        assert course.advance_if_arrived(*mark)
    assert course.active == 0 and course.laps == 1 and not course.finished
    assert course.advance_if_arrived(*marks[0]) and course.active == 1


def test_course_finishes_when_not_looping():
    marks = marks_around(DEFAULT_START)
    course = Course(marks, loop=False)
    for mark in marks:
        course.advance_if_arrived(*mark)
    assert course.finished and course.target() is None
    assert course.advance_if_arrived(*marks[0]) is False
    course.restart()
    assert course.active == 0 and not course.finished and course.target() is not None


def test_empty_course_has_no_target():
    course = Course()
    assert course.target() is None and course.advance_if_arrived(*DEFAULT_START) is False
    assert course.legs(WIND_FROM) == [] and course.to_mark(*DEFAULT_START, WIND_FROM) is None


def test_upwind_legs_are_flagged():
    start = DEFAULT_START
    upwind_mark = offset(start[0], start[1], WIND_FROM, 200.0)               # dead upwind
    near_upwind = offset(start[0], start[1], WIND_FROM + 40, 200.0)          # 40 degrees off the wind: still no-go
    beam_mark = offset(start[0], start[1], WIND_FROM + 90, 200.0)            # beam reach: fine
    course = Course([start, upwind_mark], loop=False)
    assert [leg["upwind"] for leg in course.legs(WIND_FROM)] == [True]
    assert Course([start, near_upwind], loop=False).legs(WIND_FROM)[0]["upwind"] is True
    assert Course([start, beam_mark], loop=False).legs(WIND_FROM)[0]["upwind"] is False
    # Same leg, wind turned 90 degrees: no longer upwind
    assert course.legs(WIND_FROM + 90)[0]["upwind"] is False
    # Boat-to-mark leg gets the flag too
    assert Course([upwind_mark]).to_mark(*start, WIND_FROM)["upwind"] is True
    assert Course([beam_mark]).to_mark(*start, WIND_FROM)["upwind"] is False


def test_loop_adds_a_closing_leg():
    marks = marks_around(DEFAULT_START)
    assert len(Course(marks, loop=False).legs(WIND_FROM)) == 2
    legs = Course(marks, loop=True).legs(WIND_FROM)
    assert len(legs) == 3 and (legs[-1]["from"], legs[-1]["to"]) == (2, 0)


def test_demo_course_is_the_validated_triangle():
    course = Course.demo(DEFAULT_START, WIND_FROM, scale=1.0)
    m1, m2, m3 = course.marks
    assert (m1.lat, m1.lng) == pytest.approx((43.65619, -70.22534), abs=2e-5)
    assert (m2.lat, m2.lng) == pytest.approx((43.65619, -70.22385), abs=2e-5)
    assert (m3.lat, m3.lng) == pytest.approx(DEFAULT_START)
    # Legs (1->2, 2->3, then the closing 3->1) sit at true wind angles of 135, 65 and 90 degrees, none of them
    # upwind, and the triangle closes
    legs = course.legs(WIND_FROM)
    assert [round(fold180(leg["bearing"] - WIND_FROM)) for leg in legs] == [135, 65, 90]
    assert not any(leg["upwind"] for leg in legs)
    last = offset(m2.lat, m2.lng, legs[1]["bearing"], legs[1]["distance_m"])
    assert haversine_m(last[0], last[1], *DEFAULT_START) < 1.0


def test_demo_course_rotates_to_the_wind_and_scales():
    for twd in (0.0, 90.0, 225.0, 300.0):
        legs = Course.demo(DEFAULT_START, twd).legs(twd)
        assert [round(fold180(leg["bearing"] - twd)) for leg in legs] == [135, 65, 90]
        assert not any(leg["upwind"] for leg in legs)
    small = Course.demo(DEFAULT_START, WIND_FROM, scale=1.0).legs(WIND_FROM)
    big = Course.demo(DEFAULT_START, WIND_FROM, scale=2.0).legs(WIND_FROM)
    assert big[0]["distance_m"] == pytest.approx(2 * small[0]["distance_m"], rel=1e-3)


def test_to_mark_reports_bearing_and_distance():
    mark = offset(DEFAULT_START[0], DEFAULT_START[1], 45.0, 300.0)
    info = Course([mark]).to_mark(*DEFAULT_START, WIND_FROM)
    assert info["bearing"] == pytest.approx(45.0, abs=0.1)
    assert info["distance_m"] == pytest.approx(300.0, rel=0.01)
    assert info["index"] == 0


def run_lap(seconds_wall=60.0, scale=1.0):
    """Drive the demo course with the autopilot at 15x, like the UI does; returns (sim, autopilot, rounding log)."""
    sim = build_simulator(autostart=False)
    sim.set_environmental_factors(12.0, WIND_FROM, 0.0, 90.0)
    sim.reset()
    autopilot = SimAutopilot(sim, Course.demo(DEFAULT_START, WIND_FROM, scale=scale))
    sim.set_autopilot(autopilot)
    autopilot.set_running(True)
    log, last_active, laps = [], autopilot.course.active, 0
    for tick in range(int(seconds_wall / 0.05)):
        sim.advance(0.05 * sim.time_scale)
        active = autopilot.course.active
        if active != last_active or autopilot.course.laps != laps:
            log.append((round((tick + 1) * 0.05, 2), last_active))
            last_active, laps = active, autopilot.course.laps
    return sim, autopilot, log


def test_autopilot_sails_the_demo_course_with_the_boats_own_navigator():
    sim, autopilot, log = run_lap(60.0)
    # Marks 1, 2, 3 rounded at about 10, 14 and 23 wall-clock seconds at 15x (scale 1)
    first_lap = {index: t for t, index in log[:3]}
    assert first_lap[0] == pytest.approx(10, abs=3)
    assert first_lap[1] == pytest.approx(14, abs=3)
    assert first_lap[2] == pytest.approx(23, abs=3)
    assert autopilot.course.laps >= 1  # keeps going round: the course loops
    assert autopilot.course.active in (0, 1, 2)


@pytest.mark.parametrize("mark_bearing,sign", [(315.0, -1), (45.0, 1)])
def test_autopilot_steers_towards_the_mark_on_either_side(mark_bearing, sign):
    sim = build_simulator(autostart=False)
    sim.reset(heading=0.0)
    mark = offset(DEFAULT_START[0], DEFAULT_START[1], mark_bearing, 400.0)
    autopilot = SimAutopilot(sim, Course([mark], loop=False))
    sim.set_autopilot(autopilot)
    autopilot.set_running(True)
    sim.advance(0.4)
    assert sign * sim.get_telemetry()["rudder"] > 50  # port (negative) for a mark to the left, starboard to the right
    sim.advance(20.0)
    assert abs(((sim.get_telemetry()["heading"] - mark_bearing + 540) % 360) - 180) < 5


def test_manual_mode_with_auto_trim_only_touches_the_sheet():
    sim = build_simulator(autostart=False)
    sim.reset(heading=135)  # beam reach on the starboard side
    autopilot = SimAutopilot(sim, Course())
    sim.set_autopilot(autopilot)
    autopilot.set_auto_trim(True)
    sim.servos_controller.set_servo_2(Percent(60))
    sim.advance(1.0)
    t = sim.get_telemetry()
    assert t["rudder"] == pytest.approx(20)  # untouched
    assert t["trim"] == pytest.approx(t["opt_trim"], abs=2.0)


def test_paused_autopilot_does_nothing():
    sim = build_simulator(autostart=False)
    autopilot = SimAutopilot(sim, Course.demo(DEFAULT_START, WIND_FROM))
    sim.set_autopilot(autopilot)
    autopilot.set_mode("auto")
    assert autopilot.running is False
    sim.advance(10.0)
    t = sim.get_telemetry()
    assert t["rudder"] == 0 and t["trim"] == 0
