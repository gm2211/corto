from typing import NamedTuple


class SendTelemetry(NamedTuple):
    CMD_STRING = "T"

    @staticmethod
    def serialize_for_lora():
        return SendTelemetry.CMD_STRING

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        return data == SendTelemetry.CMD_STRING
