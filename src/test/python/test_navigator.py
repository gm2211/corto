"""The boat's Navigator: signed rudder from the heading error, sail trim from the wind angle."""
import pytest

from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from navigation.navigator import Navigator
from simulator.geo import offset
from simulator.simulator import (
    DEFAULT_START,
    SimulatedGPSLocator,
    SimulatedNavParamsRecorder,
    SimulatedWindVane,
)

CENTRE = 50  # RudderPosition percent: 0 = full left, 50 = centre, 100 = full right


def make_navigator(heading: float, wind_from: float = 225.0):
    gps = SimulatedGPSLocator(*DEFAULT_START)
    recorder = SimulatedNavParamsRecorder()
    recorder.record_heading(Angle(heading))
    return Navigator(SimulatedWindVane(wind_from), gps, recorder)


def attitude(heading: float, bearing: float, wind_from: float = 225.0):
    """Navigator output with the boat on `heading` and the destination 500 m away on `bearing`."""
    dest = GPSCoord(*offset(DEFAULT_START[0], DEFAULT_START[1], bearing, 500.0))
    return make_navigator(heading, wind_from).compute_boat_attitude(dest)


def rudder_pct(heading: float, bearing: float) -> float:
    return attitude(heading, bearing).rudder_position.percent.value


def test_destination_to_starboard_gives_right_rudder():
    assert rudder_pct(heading=0, bearing=90) > CENTRE
    assert rudder_pct(heading=0, bearing=90) == pytest.approx(100)


def test_destination_to_port_gives_left_rudder():
    assert rudder_pct(heading=180, bearing=90) < CENTRE
    assert rudder_pct(heading=180, bearing=90) == pytest.approx(0)


def test_it_no_longer_always_steers_left():
    # The bug: __angle_diff was always >= 0 so the rudder was always full left.
    pcts = {rudder_pct(h, 90) for h in (0, 45, 135, 180, 270)}
    assert any(p > CENTRE for p in pcts) and any(p < CENTRE for p in pcts)


def test_shortest_way_round_across_north():
    assert rudder_pct(heading=350, bearing=10) > CENTRE  # +20 degrees: right
    assert rudder_pct(heading=10, bearing=350) < CENTRE  # -20 degrees: left


@pytest.mark.parametrize("error", [0.0, 0.3, -0.3, 0.9, -0.9])
def test_deadband_centres_the_rudder(error):
    assert rudder_pct(heading=90 - error, bearing=90) == pytest.approx(CENTRE, abs=0.05)


def test_response_is_proportional_up_to_full_deflection():
    errors = [2, 5, 10, 15, 20, 25, 30]
    right = [rudder_pct(heading=90 - e, bearing=90) for e in errors]
    left = [rudder_pct(heading=90 + e, bearing=90) for e in errors]
    assert right == sorted(right) and left == sorted(left, reverse=True)
    # Half deflection (75 on the 50..100 scale) at half of the 30 degree full-lock error
    assert rudder_pct(heading=75, bearing=90) == pytest.approx(75, abs=0.5)
    assert rudder_pct(heading=105, bearing=90) == pytest.approx(25, abs=0.5)
    # Saturates beyond 30 degrees
    assert rudder_pct(heading=45, bearing=90) == pytest.approx(100)
    assert rudder_pct(heading=135, bearing=90) == pytest.approx(0)


@pytest.mark.parametrize("heading,expected", [
    (180, 100),  # wind from 225: 45 degrees off the wind -> sheeted fully in
    (270, 100),
    (225, 100),  # head to wind: clamped to the 45 degree end
    (135, 50),   # 90 degrees (beam reach) -> mid trim
    (315, 50),
    (90, 0),     # 135 degrees -> eased fully out
    (45, 0),     # dead downwind -> still fully out
])
def test_sail_trim_follows_wind_angle(heading, expected):
    assert attitude(heading=heading, bearing=90).sail_trim.value == pytest.approx(expected, abs=0.01)


def test_sail_trim_is_independent_of_the_steering_direction():
    for heading in (0, 80, 135, 200, 315):
        to_port = attitude(heading=heading, bearing=(heading - 60) % 360).sail_trim.value
        to_starboard = attitude(heading=heading, bearing=(heading + 60) % 360).sail_trim.value
        assert to_port == pytest.approx(to_starboard)


def test_sail_trim_is_symmetric_between_tacks():
    # 90 degrees to the wind on either tack -> the same mid trim
    assert attitude(heading=135, bearing=0).sail_trim.value == pytest.approx(50)
    assert attitude(heading=315, bearing=0).sail_trim.value == pytest.approx(50)
