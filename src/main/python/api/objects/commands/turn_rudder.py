from typing import NamedTuple, Optional

from api.objects.units.percent import Percent


class TurnRudder(NamedTuple):
    percent: Percent
    CMD_STRING = "R"

    def serialize_for_lora(self):
        return f"{TurnRudder.CMD_STRING}{self.percent.value}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        has_cmd_prefix = data.startswith(TurnRudder.CMD_STRING)
        can_parse_num = TurnRudder.__parse_num(data) is not None
        return has_cmd_prefix and can_parse_num

    @staticmethod
    def deserialize_from_lora(data: str) -> 'TurnRudder':
        if not TurnRudder.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for TurnRudder: {data}")
        rudder_percent = TurnRudder.__parse_num(data)
        return TurnRudder(Percent(rudder_percent))

    @staticmethod
    def __parse_num(data: str) -> Optional[int]:
        try:
            return int(data[len(TurnRudder.CMD_STRING):])
        except ValueError:
            return None
