import math
from typing import Any

from boat.objects.angle import Angle
from boat.objects.gps_coord import GPSCoord
from boat.telemetry.gps_locator import GPSLocator
from boat.telemetry.nav_params_recorder import nav_params_recorder
from boat.telemetry.wind_vane import WindVane


class PathPlanner:
    def __init__(self, wind: WindVane, locator: GPSLocator, navParams: nav_params_recorder):
        self.wind: WindVane = wind
        self.locator: GPSLocator = locator
        self.navParams: nav_params_recorder = navParams

    def plan(self, dest: GPSCoord):
        cur_pos: GPSCoord = self.locator.get_cur_location()
        bearing: Angle = self.__bearing_to(cur_pos, dest)
        return [self.start, self.goal]

    # Calculate bearing to destination
    @staticmethod
    def __bearing_to(cur_pos: GPSCoord, dest: GPSCoord) -> Angle:
        bearing = math.atan2(
            dest.lat - cur_pos.lat,
            dest.lon - cur_pos.lon)
        return Angle(bearing)

    @staticmethod
    def __angle_diff(a: Angle, b: Angle) -> Angle:
        diff: float = abs(a.degrees - b.degrees) % 360
        if diff > 180:
            return Angle(360 - diff)
        return Angle(diff)
