from typing import NamedTuple

from api.objects.angle import Angle
from api.objects.gps_coord import GPSCoord


class SetDestination(NamedTuple):
    coord: GPSCoord
    CMD_PREFIX = "DEST"

    def __str__(self):
        return f"{self.CMD_PREFIX} {self.coord}"

    @staticmethod
    def can_parse(command: str) -> bool:
        return command.startswith(SetDestination.CMD_PREFIX)

    @staticmethod
    def rudder_angle(command: str) -> "SetDestination | None":
        if SetDestination.can_parse(command):
            lat, lon = command.split(" ")[1].split(",")
            return SetDestination(GPSCoord(float(lat), float(lon)))
        return None
