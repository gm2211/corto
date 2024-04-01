from typing import NamedTuple


class Speed(NamedTuple):
    knots: float

    def __eq__(self, other):
        return self.knots == other.knots