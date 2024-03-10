from typing import NamedTuple

from api.objects.units.angle import Angle


class SetRudderAngle(NamedTuple):
    angle: Angle
    CMD_PREFIX = "RUDDER"

    def __str__(self):
        return f"{self.CMD_PREFIX} {self.angle}"

    @staticmethod
    def can_parse(command: str) -> bool:
        return command.startswith(SetRudderAngle.CMD_PREFIX)

    @staticmethod
    def rudder_angle(command: str) -> "SetRudderAngle | None":
        if SetRudderAngle.can_parse(command):
            return SetRudderAngle(Angle(int(command.split(" ")[1])))
        return None
