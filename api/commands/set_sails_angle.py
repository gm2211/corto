from typing import NamedTuple

from api.objects.angle import Angle


class SetSailsAngle(NamedTuple):
    angle: Angle
    CMD_PREFIX = "SAILS"

    def __str__(self):
        return f"{self.CMD_PREFIX} {self.angle}"

    @staticmethod
    def can_parse(command: str) -> bool:
        return command.startswith(SetSailsAngle.CMD_PREFIX)

    @staticmethod
    def rudder_angle(command: str) -> "SetSailsAngle | None":
        if SetSailsAngle.can_parse(command):
            return SetSailsAngle(Angle(int(command.split(" ")[1])))
        return None
