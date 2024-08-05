from typing import NamedTuple

from api.objects.units.percent import Percent
from api.objects.units.rudder_position import RudderPosition


class BoatAttitude(NamedTuple):
    rudder_position: RudderPosition
    sail_trim: Percent

    def __eq__(self, other):
        return self.rudder_position == other.rudder_position and self.sail_trim == other.sail_trim
