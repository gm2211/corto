from typing import NamedTuple

from boat.controls.sail_controller import SailTrim
from api.objects.angle import Angle
from api.objects.gps_coord import GPSCoord
from api.objects.speed import Speed


class NavParams(NamedTuple):
    heading: Angle
    rudder_angle: Angle
    position: GPSCoord
    speed: Speed
    true_wind_angle: Angle
    point_of_sail: SailTrim
