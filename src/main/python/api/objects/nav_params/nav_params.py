from typing import NamedTuple

from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.speed import Speed


class NavParams(NamedTuple):
    heading: Angle
    rudder_angle: Angle
    position: GPSCoord
    speed: Speed
    true_wind_angle: Angle
    sail_trim: Angle

    def serialize_for_lora(self) -> str:
        return (f"{self.heading.degrees}"
                f"|{self.rudder_angle.degrees}"
                f"|{self.position.serialize_for_lora()}"
                f"|{self.speed.knots}"
                f"|{self.true_wind_angle.degrees}"
                f"|{self.sail_trim.degrees}")
