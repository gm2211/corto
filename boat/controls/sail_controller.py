from enum import Enum


class PointOfSail(Enum):
    CLOSE_HAULED = 0
    CLOSE_REACH = 1
    BEAM_REACH = 2
    BROAD_REACH = 3
    RUNNING = 4


class SailController:
    def set_point_of_sail(self, point_of_sail: PointOfSail):
        print("Setting point of sail to", point_of_sail.name)
