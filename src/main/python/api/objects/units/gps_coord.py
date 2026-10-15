import math
from typing import NamedTuple


class GPSCoord(NamedTuple):
    lat: float
    lon: float

    def serialize_for_lora(self) -> str:
        return f"{self.lat},{self.lon}"

    @staticmethod
    def can_parse_lora_data(param: str) -> bool:
        try:
            GPSCoord.deserialize_from_lora(param)
        except ValueError:
            return False
        return True

    @staticmethod
    def deserialize_from_lora(param: str) -> 'GPSCoord':
        try:
            lat, lon = (float(part) for part in param.split(','))
        except ValueError:
            raise ValueError(f"Invalid data for GPSCoord: {param}") from None
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Invalid data for GPSCoord: {param}")
        return GPSCoord(lat, lon)

    def __eq__(self, other):
        return self.lat == other.lat and self.lon == other.lon
