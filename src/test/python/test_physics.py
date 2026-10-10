"""Boat physics: drive, steering, no-go zone, position, apparent wind. Stepped deterministically (no thread)."""
import math

import pytest

from api.objects.units.percent import Percent
from navigation.navigator import Navigator
from simulator.geo import haversine_m
from simulator.simulator import (
    DEFAULT_HEADING,
    DEFAULT_START,
    NO_GO_DEG,
    apparent_wind,
    build_simulator,
    optimal_trim,
    polar_factor,
    signed_true_wind_angle,
)

WIND_FROM = 225.0  # wind from the south-west; heading 135 and 315 are the two beam reaches


def make_sim(heading=DEFAULT_HEADING, tws=12.0, twd=WIND_FROM, trim=50, rudder_pct=50, throttle=0):
    sim = build_simulator(autostart=False)
    sim.set_environmental_factors(tws, twd, 0.0, 90.0)
    sim.reset(heading=heading)
    sim.servos_controller.set_servo_1(Percent(trim))
    sim.servos_controller.set_servo_2(Percent(rudder_pct))
    sim.servos_controller.set_motor_throttle(Percent(throttle))
    return sim


def settled_stw(heading, trim=50, seconds=120.0, **kwargs):
    sim = make_sim(heading=heading, trim=trim, **kwargs)
    sim.advance(seconds)
    return sim.get_telemetry()["stw"]


def heading_after(sim, seconds):
    sim.advance(seconds)
    return sim.get_telemetry()["heading"]


def test_port_and_starboard_beam_reaches_match():
    stbd = settled_stw(heading=135)  # wind over the starboard side
    port = settled_stw(heading=315)  # wind over the port side
    assert stbd > 2.0
    assert port == pytest.approx(stbd, rel=0.05)


def test_wind_angle_is_folded_so_port_tack_has_drive():
    assert signed_true_wind_angle(225, 315) == pytest.approx(-90)
    assert signed_true_wind_angle(225, 135) == pytest.approx(90)
    assert polar_factor(abs(signed_true_wind_angle(225, 315))) == polar_factor(90)


def test_starboard_rudder_increases_heading_and_port_decreases_it():
    right = make_sim(heading=100, rudder_pct=75)  # signed +50
    left = make_sim(heading=100, rudder_pct=25)   # signed -50
    assert heading_after(right, 5.0) > 100
    assert heading_after(left, 5.0) < 100


def test_a_stalled_boat_can_still_turn():
    sim = make_sim(heading=100, trim=0, tws=0.0, rudder_pct=100)
    assert sim.get_telemetry()["stw"] == 0.0
    assert heading_after(sim, 5.0) > 100


def test_rudder_is_reported_signed_with_degrees():
    sim = make_sim(rudder_pct=20)
    t = sim.get_telemetry()
    assert t["rudder"] == pytest.approx(-60)
    assert t["rudder_deg"] == pytest.approx(-60 / 100 * 45)
    sim.servos_controller.set_servo_2(Percent(100))
    assert sim.get_telemetry()["rudder"] == pytest.approx(100)
    assert sim.get_telemetry()["rudder_deg"] == pytest.approx(45)
    sim.servos_controller.set_servo_2(Percent(50))
    assert sim.get_telemetry()["rudder"] == 0


@pytest.mark.parametrize("off_wind", [0, 10, 20, 29])
@pytest.mark.parametrize("side", [1, -1])
def test_no_drive_inside_the_no_go_zone(off_wind, side):
    heading = (WIND_FROM + side * off_wind) % 360
    assert settled_stw(heading=heading, trim=100) == pytest.approx(0, abs=1e-6)


def test_drive_returns_just_outside_the_no_go_zone():
    assert settled_stw(heading=(WIND_FROM + NO_GO_DEG + 5) % 360, trim=100) > 0.2


def test_trim_matters_and_optimal_trim_is_best():
    best = settled_stw(heading=135, trim=optimal_trim(90))
    eased = settled_stw(heading=135, trim=0)
    over = settled_stw(heading=135, trim=100)
    assert best > eased and best > over
    assert eased > 0 and over > 0


def test_optimal_trim_matches_the_navigator_mapping():
    # The simulator's "optimal" marker must be what the real Navigator would choose
    from simulator.simulator import SimulatedGPSLocator, SimulatedNavParamsRecorder, SimulatedWindVane
    from api.objects.units.angle import Angle
    from api.objects.units.gps_coord import GPSCoord
    for twa in (0, 30, 45, 60, 90, 120, 135, 160, 180):
        recorder = SimulatedNavParamsRecorder()
        recorder.record_heading(Angle(0.0))
        nav = Navigator(SimulatedWindVane(float(twa)), SimulatedGPSLocator(*DEFAULT_START), recorder)
        trim = nav.compute_boat_attitude(GPSCoord(DEFAULT_START[0] + 0.001, DEFAULT_START[1])).sail_trim.value
        assert optimal_trim(twa) == pytest.approx(trim, abs=1e-6)


def test_motor_drives_without_wind():
    assert settled_stw(heading=0, tws=0.0, trim=0, throttle=100) == pytest.approx(5.0, rel=0.02)


def test_one_hundred_metres_east_is_one_hundred_metres_by_haversine():
    sim = build_simulator(autostart=False)
    sim.set_environmental_factors(0.0, 225.0, 1.943844, 90.0)  # 1 m/s of current setting east
    sim.reset()
    lat0, lon0 = sim.get_telemetry()["lat"], sim.get_telemetry()["lng"]
    sim.advance(100.0)
    t = sim.get_telemetry()
    assert haversine_m(lat0, lon0, t["lat"], t["lng"]) == pytest.approx(100.0, rel=0.01)
    assert t["lat"] == pytest.approx(lat0, abs=1e-7)  # due east: latitude unchanged
    assert t["lng"] > lon0
    assert t["sog"] == pytest.approx(1.943844, rel=0.01)
    assert t["cog"] == pytest.approx(90.0, abs=0.1)


def test_longitude_uses_a_cos_latitude_correction():
    sim = build_simulator(autostart=False)
    sim.set_environmental_factors(0.0, 225.0, 1.943844, 90.0)
    sim.reset(lat=60.0, lon=10.0)
    sim.advance(100.0)
    t = sim.get_telemetry()
    assert haversine_m(60.0, 10.0, t["lat"], t["lng"]) == pytest.approx(100.0, rel=0.01)


def test_current_sets_the_boat_sideways():
    sim = make_sim(heading=0, tws=0.0, trim=0)
    sim.set_environmental_factors(0.0, 225.0, 2.0, 90.0)  # 2 kn of current to the east, boat stationary
    sim.advance(60.0)
    t = sim.get_telemetry()
    assert t["sog"] == pytest.approx(2.0, rel=0.01)
    assert t["cog"] == pytest.approx(90.0, abs=0.1)
    assert t["drift"] == pytest.approx(90.0, abs=0.1)


def test_telemetry_has_every_field_the_ui_reads():
    keys = {"heading", "cog", "sog", "stw", "tws", "twd", "twa", "aws", "awa", "heel", "rudder", "rudder_deg",
            "trim", "opt_trim", "throttle", "drift", "lat", "lng"}
    assert keys <= set(make_sim().get_telemetry())


# --- apparent wind -------------------------------------------------------------------------------------

def test_apparent_wind_head_to_wind_adds_the_speeds():
    aws, awa = apparent_wind(tws=10, twd=0, stw=5, hdg=0)
    assert aws == pytest.approx(15)
    assert awa == pytest.approx(0, abs=1e-9)


def test_apparent_wind_dead_downwind_subtracts_the_speeds():
    aws, awa = apparent_wind(tws=10, twd=180, stw=5, hdg=0)
    assert aws == pytest.approx(5)
    assert abs(awa) == pytest.approx(180)


def test_apparent_wind_moves_forward_on_a_beam_reach():
    aws, awa = apparent_wind(tws=10, twd=90, stw=5, hdg=0)  # wind over the starboard beam
    assert aws == pytest.approx(math.hypot(10, 5))
    assert awa == pytest.approx(math.degrees(math.atan2(10, 5)))  # 63.4: ahead of the beam, positive = starboard
    aws_p, awa_p = apparent_wind(tws=10, twd=270, stw=5, hdg=0)  # same from the port side
    assert aws_p == pytest.approx(aws)
    assert awa_p == pytest.approx(-awa)


def test_apparent_wind_with_no_boat_speed_is_the_true_wind():
    aws, awa = apparent_wind(tws=12, twd=225, stw=0, hdg=315)
    assert aws == pytest.approx(12)
    assert awa == pytest.approx(-90)


def test_heel_is_to_leeward_and_estimated():
    sim = make_sim(heading=135, trim=50, tws=20.0)  # wind over the starboard side -> leans to port
    sim.advance(60.0)
    assert sim.get_telemetry()["heel"] < 0
    sim = make_sim(heading=315, trim=50, tws=20.0)  # wind over the port side -> leans to starboard
    sim.advance(60.0)
    t = sim.get_telemetry()
    assert 0 < t["heel"] <= 30
