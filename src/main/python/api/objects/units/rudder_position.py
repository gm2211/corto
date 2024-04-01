from typing import NamedTuple

from api.objects.units.percent import Percent
from utils.range_utils import remap


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
