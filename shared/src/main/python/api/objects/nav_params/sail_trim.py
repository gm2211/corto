from enum import Enum
from typing import Type

from shared.src.main.python.api.objects.units.angle import Angle


class SailTrim(Enum):
    CLOSE_HAULED = 0
    CLOSE_REACH = 1
    BEAM_REACH = 2
    BROAD_REACH = 3
    RUNNING = 4

    @classmethod
    def from_angle(cls: Type["SailTrim"], angle: Angle) -> "SailTrim":
        if angle.degrees in range(0, 45) or angle.degrees in range(315, 360):
            return cls.CLOSE_HAULED
        if angle.degrees in range(45, 79) or angle.degrees in range(281, 315):
            return cls.CLOSE_REACH
        if angle.degrees in range(79, 101) or angle.degrees in range(258, 281):
            return cls.BEAM_REACH
        if angle.degrees in range(101, 160) or angle.degrees in range(202, 258):
            return cls.BROAD_REACH
        return cls.RUNNING

