from typing import NamedTuple


class SetSail(NamedTuple):
    angle: int
    CMD_STRING = "S"

    def serialize_for_lora(self):
        return f"{SetSail.CMD_STRING}{self.angle}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        return data.startswith(SetSail.CMD_STRING) and data[1:].isdigit()

    @staticmethod
    def deserialize_from_lora(data: str) -> 'SetSail':
        if not SetSail.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for SetSail: {data}")
        return SetSail(int(data[1:]))
