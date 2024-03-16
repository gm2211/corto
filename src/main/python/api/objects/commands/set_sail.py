from typing import NamedTuple

from api.objects.units.angle import Angle


class SetSail(NamedTuple):
    angle: Angle
    CMD_STRING = "S"

    def serialize_for_lora(self):
        return f"{SetSail.CMD_STRING}{self.angle.degrees:.1f}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        return data.startswith(SetSail.CMD_STRING) and data[1:].isdigit()

    @staticmethod
    def deserialize_from_lora(data: str) -> 'SetSail':
        if not SetSail.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for SetSail: {data}")
        degrees = float(data[1:])
        return SetSail(Angle(degrees))
