from typing import NamedTuple
import ultraimport
import ultraimport

Percent = ultraimport("__dir__/percent.py", ["Percent"])[0]


class RudderPosition:
    """Rudder position class that represents the position of the rudder.
    Uses a 0-100 scale where 50 is center, 0 is full left, and 100 is full right.
    """

    def __init__(self, percent: Percent):
        self.percent = percent

    @staticmethod
    def left(percent: Percent):
        """Create a left rudder position with the given percentage (0-50)"""
        value = max(0, min(50, percent.value))
        return RudderPosition(Percent(value))

    @staticmethod
    def right(percent: Percent):
        """Create a right rudder position with the given percentage (50-100)"""
        value = max(50, min(100, percent.value))
        return RudderPosition(Percent(value))

    @staticmethod
    def center():
        """Create a center rudder position"""
        return RudderPosition(Percent(50))

    def __eq__(self, other):
        return self.percent.value == other.percent.value
Percent = ultraimport("__dir__/percent.py", ["Percent"])[0]
remap = ultraimport("__dir__/../../../utils/range_utils.py", ["remap"])[0]


class RudderPosition(NamedTuple):
    percent: Percent

    @staticmethod
    def right(percent: Percent) -> 'RudderPosition':
        remapped = remap(percent.value, 0, 100, 50, 100)
        return RudderPosition(Percent(remapped))

    @staticmethod
    def left(percent: Percent) -> 'RudderPosition':
        remapped = remap(percent.value, 0, 100, 50, 0)
        return RudderPosition(Percent(remapped))

    @staticmethod
    def center() -> 'RudderPosition':
        return RudderPosition(Percent(50))

    def __eq__(self, other):
        return self.percent == other.percent
