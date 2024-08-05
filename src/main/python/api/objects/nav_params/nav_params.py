from typing import NamedTuple

from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.percent import Percent
from api.objects.units.speed import Speed


class NavParams(NamedTuple):
    heading: Angle
    rudder_position: Percent
    position: GPSCoord
    motor_throttle: Percent
    speed_over_water: Speed
    true_wind_angle: Angle
    sail_trim: Percent

    def serialize_for_lora(self) -> str:
        return (f"{self.heading.degrees}"
                f"|{self.rudder_position.value}"
                f"|{self.position.serialize_for_lora()}"
                f"|{self.motor_throttle.value}"
                f"|{self.speed_over_water.knots}"
                f"|{self.true_wind_angle.degrees}"
                f"|{self.sail_trim.value}")
