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

    @staticmethod
    def deserialize_from_lora(param: str):
        lat, lon = param.split(',')
        lat_in_range = lat in range(-90, 91)
        lon_in_range = lon in range(-180, 181)
        if not lat_in_range or not lon_in_range:
            raise ValueError(f"Invalid data for GPSCoord: {param}")
        return GPSCoord(float(lat), float(lon))
