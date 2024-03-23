from typing import NamedTuple

from api.objects.units.angle import Angle


class SetSail(NamedTuple):
    angle: Angle
    CMD_STRING = "S"

    def serialize_for_lora(self):
        return f"{SetSail.CMD_STRING}{self.angle.degrees:.1f}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        has_cmd_prefix = data.startswith(SetSail.CMD_STRING)
        can_parse_num = SetSail.__parse_num(data) is not None
        return has_cmd_prefix and can_parse_num

    @staticmethod
    def deserialize_from_lora(data: str) -> 'SetSail':
        if not SetSail.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for SetSail: {data}")
        degrees = SetSail.__parse_num(data)
        return SetSail(Angle(degrees))

    @staticmethod
    def __parse_num(data: str) -> float | None:
        try:
            return float(data[len(SetSail.CMD_STRING):])
        except ValueError:
            return None
