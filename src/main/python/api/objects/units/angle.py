from typing import NamedTuple


class Angle(NamedTuple):
    degrees: float


    def __eq__(self, other):
        return self.degrees == other.degrees