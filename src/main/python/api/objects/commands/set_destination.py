from typing import NamedTuple

from api.objects.units.gps_coord import GPSCoord


class SetDestination(NamedTuple):
    destination: GPSCoord
    CMD_STRING = "D"

    def serialize_for_lora(self):
        return f"{SetDestination.CMD_STRING}{self.destination.serialize_for_lora()}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        return data.startswith(SetDestination.CMD_STRING) and GPSCoord.can_parse_lora_data(data[1:])

    @staticmethod
    def deserialize_from_lora(data: str) -> 'SetDestination':
        if not SetDestination.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for SetDestination: {data}")
        return SetDestination(GPSCoord.deserialize_from_lora(data[len(SetDestination.CMD_STRING):]))
