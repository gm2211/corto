from typing import NamedTuple

from api.objects.nav_params.sail_trim import SailTrim
from api.objects.units.angle import Angle


class BoatAttitude(NamedTuple):
    rudder: Angle
    sail_trim: SailTrim
