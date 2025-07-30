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
