from typing import NamedTuple


class Knots(NamedTuple):
    knots: float

    def __eq__(self, other):
        return self.knots == other.knots
