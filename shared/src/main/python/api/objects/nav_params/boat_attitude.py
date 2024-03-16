from typing import NamedTuple

from boat.controls.sail_controller import SailTrim
from shared.src.main.python.api.objects.units.angle import Angle


class BoatAttitude(NamedTuple):
    rudder: Angle
    sail_trim: SailTrim
