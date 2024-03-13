from typing import NamedTuple

from api.objects.units.angle import Angle


class TurnRudder(NamedTuple):
    angle: Angle
    CMD_STRING = "R"

    def serialize_for_lora(self):
        return f"{TurnRudder.CMD_STRING}{self.angle.degrees:.1f}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        return data.startswith(TurnRudder.CMD_STRING) and data[1:].isdigit()

    @staticmethod
    def deserialize_from_lora(data: str) -> 'TurnRudder':
        if not TurnRudder.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for TurnRudder: {data}")
        degrees = float(data[1:])
        return TurnRudder(Angle(degrees))
