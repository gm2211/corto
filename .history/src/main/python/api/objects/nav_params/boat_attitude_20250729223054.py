from typing import NamedTuple
import ultraimport

Percent = ultraimport("__dir__/../units/percent.py", ["Percent"])[0]
RudderPosition = ultraimport("__dir__/../units/rudder_position.py", ["RudderPosition"])[0]


class BoatAttitude(NamedTuple):
    rudder_position: RudderPosition
    sail_trim: Percent

    def __eq__(self, other):
        return self.rudder_position == other.rudder_position and self.sail_trim == other.sail_trim
