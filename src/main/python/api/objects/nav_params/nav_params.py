import math
from typing import NamedTuple
import ultraimport

Angle = ultraimport("__dir__/../units/angle.py", ["Angle"])[0]
Percent = ultraimport("__dir__/../units/percent.py", ["Percent"])[0]
GPSCoord = ultraimport("__dir__/../units/gps_coord.py", ["GPSCoord"])[0]
Speed = ultraimport("__dir__/../units/speed.py", ["Speed"])[0]


class NavParams(NamedTuple):
    heading: Angle
    rudder_position: Percent
    position: GPSCoord
    motor_throttle: Percent
    speed_over_water: Speed
    true_wind_angle: Angle
    sail_trim: Percent

    def __eq__(self, other):
        return (
            self.heading == other.heading and
            self.rudder_position == other.rudder_position and
            self.position == other.position and
            self.motor_throttle == other.motor_throttle and
            self.speed_over_water == other.speed_over_water and
            self.true_wind_angle == other.true_wind_angle and
            self.sail_trim == other.sail_trim
        )
    def serialize_for_lora(self) -> str:
        return (f"{self.heading.degrees}"
                f"|{self.rudder_position.value}"
                f"|{self.position.serialize_for_lora()}"
                f"|{self.motor_throttle.value}"
                f"|{self.speed_over_water.knots}"
                f"|{self.true_wind_angle.degrees}"
                f"|{self.sail_trim.value}")

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        try:
            NavParams.deserialize_from_lora(data)
        except ValueError:
            return False
        return True

    @staticmethod
    def deserialize_from_lora(data: str) -> 'NavParams':
        """Parse what serialize_for_lora writes. Raises ValueError for anything else (radio noise included)."""
        fields = data.split('|')
        if len(fields) != 7:
            raise ValueError(f"Invalid data for NavParams, expected 7 fields: {data}")
        heading, rudder, position, throttle, speed, wind, trim = fields
        try:
            numbers = [float(value) for value in (heading, rudder, throttle, speed, wind, trim)]
        except ValueError:
            raise ValueError(f"Invalid data for NavParams: {data}") from None
        if not all(math.isfinite(value) for value in numbers):
            raise ValueError(f"Invalid data for NavParams: {data}")
        heading, rudder, throttle, speed, wind, trim = numbers
        # Percent validates with assert, so check the range first and raise a ValueError like everything else here
        for value in (rudder, throttle, trim):
            if not 0 <= value <= 100:
                raise ValueError(f"Invalid percent in NavParams: {data}")
        return NavParams(
            heading=Angle(heading),
            rudder_position=Percent(rudder),
            position=GPSCoord.deserialize_from_lora(position),
            motor_throttle=Percent(throttle),
            speed_over_water=Speed(speed),
            true_wind_angle=Angle(wind),
            sail_trim=Percent(trim),
        )
