from typing import NamedTuple

from api.objects.units.angle import Angle


class BoatAttitude(NamedTuple):
    rudder: Angle
    sail_trim: Angle
