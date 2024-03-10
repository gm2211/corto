from typing import NamedTuple


class TurnRudder(NamedTuple):
    angle: int
    CMD_STRING = "R"

    def serialize_for_lora(self):
        return f"{TurnRudder.CMD_STRING}{self.angle}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        return data.startswith(TurnRudder.CMD_STRING) and data[1:].isdigit()

    @staticmethod
    def deserialize_from_lora(data: str) -> 'TurnRudder':
        if not TurnRudder.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for TurnRudder: {data}")
        return TurnRudder(int(data[1:]))
