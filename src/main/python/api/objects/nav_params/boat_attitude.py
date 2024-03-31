from typing import NamedTuple

from api.objects.units.percent import Percent
from api.objects.units.rudder_position import RudderPosition


class BoatAttitude(NamedTuple):
    rudder_position: RudderPosition
    sail_trim: Percent
