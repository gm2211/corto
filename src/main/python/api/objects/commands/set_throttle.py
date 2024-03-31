from typing import NamedTuple

from api.objects.units.percent import Percent


class SetThrottle(NamedTuple):
    throttle: Percent
    CMD_STRING = "TR"

    def serialize_for_lora(self):
        return f"{SetThrottle.CMD_STRING}{self.throttle.value}"

    @staticmethod
    def can_parse_lora_data(data: str) -> bool:
        has_cmd_prefix = data.startswith(SetThrottle.CMD_STRING)
        can_parse_num = SetThrottle.__parse_num(data) is not None
        return has_cmd_prefix and can_parse_num

    @staticmethod
    def deserialize_from_lora(data: str) -> 'SetThrottle':
        if not SetThrottle.can_parse_lora_data(data):
            raise ValueError(f"Invalid data for SetThrottle: {data}")
        throttle_percent = SetThrottle.__parse_num(data)
        assert 0 <= throttle_percent <= 100, f"Throttle percent must be between 0 and 100, got {throttle_percent}"
        return SetThrottle(Percent(throttle_percent))

    @staticmethod
    def __parse_num(data: str) -> int | None:
        try:
            return int(data[len(SetThrottle.CMD_STRING):])
        except ValueError:
            return None
