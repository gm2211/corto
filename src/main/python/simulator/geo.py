"""Small geodesy helpers shared by the simulator, the autopilot course and the tests.

Everything is in degrees and metres. The simulator works on a local flat-earth approximation with a
cos(latitude) correction on longitude, which is accurate to well under 1% over the few hundred metres
the boat sails; haversine is provided as the reference the tests compare against.
"""

import math

EARTH_RADIUS_M = 6_371_000.0
M_PER_DEG_LAT = 111_320.0
M_PER_KNOT = 0.514444  # metres per second in one knot


def wrap360(angle_deg: float) -> float:
    """Normalise an angle to [0, 360)."""
    return angle_deg % 360.0


def wrap180(angle_deg: float) -> float:
    """Normalise an angle to (-180, 180]."""
    a = angle_deg % 360.0
    return a - 360.0 if a > 180.0 else a


def fold180(angle_deg: float) -> float:
    """Fold an angle to 0..180 (the magnitude of the signed angle)."""
    return abs(wrap180(angle_deg))


def offset(lat: float, lon: float, bearing_deg: float, dist_m: float) -> tuple:
    """Move `dist_m` metres from (lat, lon) along `bearing_deg` and return the new (lat, lon)."""
    b = math.radians(bearing_deg)
    dlat = dist_m * math.cos(b) / M_PER_DEG_LAT
    dlon = dist_m * math.sin(b) / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def local_delta_m(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> tuple:
    """(east_m, north_m) from the first point to the second, flat-earth with cos(lat) correction."""
    mid_lat = math.radians((from_lat + to_lat) / 2.0)
    east = (to_lon - from_lon) * M_PER_DEG_LAT * math.cos(mid_lat)
    north = (to_lat - from_lat) * M_PER_DEG_LAT
    return east, north


def distance_m(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> float:
    """Distance in metres (flat-earth, fast; used on the per-step arrival check)."""
    east, north = local_delta_m(from_lat, from_lon, to_lat, to_lon)
    return math.hypot(east, north)


def bearing_deg(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> float:
    """Initial great-circle bearing from the first point to the second, in [0, 360)."""
    lat1, lat2 = math.radians(from_lat), math.radians(to_lat)
    dlon = math.radians(to_lon - from_lon)
    x = math.cos(lat2) * math.sin(dlon)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def haversine_m(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> float:
    """Great-circle distance in metres (reference implementation, used by the tests)."""
    p1, p2 = math.radians(from_lat), math.radians(to_lat)
    dp = p2 - p1
    dl = math.radians(to_lon - from_lon)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
