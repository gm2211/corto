from typing import NamedTuple

from api.objects.units.angle import Angle


class TurnRudder(NamedTuple):
    angle: Angle
    CMD_STRING = "R"

    def serialize_for_lora(self):
        return f"{TurnRudder.CMD_STRING}{self.angle.degrees:.1f}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        has_cmd_prefix = data.startswith(TurnRudder.CMD_STRING)
        can_parse_num = TurnRudder.__parse_num(data) is not None
        return has_cmd_prefix and can_parse_num

    @staticmethod
    def deserialize_from_lora(data: str) -> 'TurnRudder':
        if not TurnRudder.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for TurnRudder: {data}")
        degrees = TurnRudder.__parse_num(data)
        return TurnRudder(Angle(degrees))

    @staticmethod
    def __parse_num(data: str) -> float | None:
        try:
            return float(data[len(TurnRudder.CMD_STRING):])
        except ValueError:
            return None
