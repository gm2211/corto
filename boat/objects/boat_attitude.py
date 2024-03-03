from typing import NamedTuple

from boat.controls.sail_controller import SailTrim
from boat.objects.angle import Angle


class BoatAttitude(NamedTuple):
    rudder: Angle
    sail_trim: SailTrim
