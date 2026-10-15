"""The boat's wire format: telemetry (NavParams), GPSCoord and the destination command, as the boat and the app exchange them."""
import pytest

from api.objects.commands.set_destination import SetDestination
from api.objects.nav_params.nav_params import NavParams
from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.percent import Percent
from api.objects.units.speed import Speed

PLACEHOLDER = "0|0|0,0|0|0|0|0"  # what the boat answers today: no GPS, no wind vane


# --- wire format ------------------------------------------------------------------------------------------

def test_nav_params_round_trip_with_float_rudder_and_negative_longitude():
    params = NavParams(
        heading=Angle(315.5), rudder_position=Percent(62.5), position=GPSCoord(43.6545, -70.223),
        motor_throttle=Percent(20), speed_over_water=Speed(3.5), true_wind_angle=Angle(225.0), sail_trim=Percent(60))
    assert NavParams.can_parse_lora_data(params.serialize_for_lora()) is True
    assert NavParams.deserialize_from_lora(params.serialize_for_lora()) == params


def test_the_boats_placeholder_telemetry_parses():
    params = NavParams.deserialize_from_lora(PLACEHOLDER)
    assert params.position == GPSCoord(0, 0) and params.rudder_position == Percent(0) and params.heading == Angle(0)


@pytest.mark.parametrize("text", [
    "", "setup", "R50", "T", "1|2|3", "1|2|3|4|5|6|7|8",
    "nan|50|1,1|0|0|0|0", "0|50|1,1|0|inf|0|0", "0|abc|1,1|0|0|0|0",
    "0|150|1,1|0|0|0|0", "0|-1|1,1|0|0|0|0", "0|50|1,1|101|0|0|0", "0|50|1,1|0|0|0|100.5",
    "0|50|91,0|0|0|0|0", "0|50|0,181|0|0|0|0", "0|50|1,2,3|0|0|0|0", "0|50|1|0|0|0|0",
])
def test_garbage_is_not_telemetry(text):
    assert NavParams.can_parse_lora_data(text) is False
    with pytest.raises(ValueError):
        NavParams.deserialize_from_lora(text)


def test_gps_coord_parses_and_validates():
    # Regression: this used to test `lat in range(-90, 91)` on a string, so nothing ever parsed, and
    # can_parse_lora_data returned None for good data
    assert GPSCoord.can_parse_lora_data("43.6545,-70.223") is True
    assert GPSCoord.deserialize_from_lora("43.6545,-70.223") == GPSCoord(43.6545, -70.223)
    assert GPSCoord.deserialize_from_lora("-90,180") == GPSCoord(-90, 180)
    for bad in ("91,0", "0,181", "-90.5,0", "abc,1", "1", "1,2,3", "nan,0", "0,inf", ""):
        assert GPSCoord.can_parse_lora_data(bad) is False
        with pytest.raises(ValueError):
            GPSCoord.deserialize_from_lora(bad)


def test_set_destination_round_trips():
    command = SetDestination(GPSCoord(43.6561, -70.2251))
    assert command.serialize_for_lora() == "D43.6561,-70.2251"
    assert SetDestination.can_parse_lora_data("D43.6561,-70.2251") is True
    assert SetDestination.deserialize_from_lora(command.serialize_for_lora()) == command
    for bad in ("D", "D91,0", "D1", "43.6,-70.2", "Dnan,0"):
        assert SetDestination.can_parse_lora_data(bad) is False
