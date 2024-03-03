import math
from typing import Any

from boat.controls.sail_controller import SailTrim
from boat.objects.angle import Angle
from boat.objects.boat_attitude import BoatAttitude
from boat.objects.gps_coord import GPSCoord
from boat.objects.nav_params import NavParams
from boat.telemetry.gps_locator import GPSLocator
from boat.telemetry.nav_params_recorder import NavParamsRecorder
from boat.telemetry.wind_vane import WindVane


class Navigator:
    def __init__(self, wind_vane: WindVane, locator: GPSLocator, nav_params_recorder: NavParamsRecorder):
        self.wind_vane: WindVane = wind_vane
        self.locator: GPSLocator = locator
        self.nav_params_recorder = nav_params_recorder

    def compute_boat_attitude(self, dest: GPSCoord) -> BoatAttitude:
        cur_pos: GPSCoord = self.locator.get_cur_location()
        nav_params: NavParams = self.nav_params_recorder.get_cur_nav_params()
        cur_heading: Angle = nav_params.heading
        desired_heading: Angle = self.__bearing_to(cur_pos, dest)
        sail_trim: SailTrim = SailTrim.from_angle(self.__angle_diff(cur_heading, self.wind_vane.get_true_wind()))
        return BoatAttitude(desired_heading, sail_trim)

    # Calculate bearing to destination
    @staticmethod
    def __bearing_to(cur_pos: GPSCoord, dest: GPSCoord) -> Angle:
        cur_lat, cur_lon = (math.radians(cur_pos.lat), math.radians(cur_pos.lon))
        dest_lat, dest_lon = (math.radians(dest.lat), math.radians(dest.lon))

        delta_lon = dest_lon - cur_lon
        x = math.cos(dest_lat) * math.sin(delta_lon)
        y = math.cos(cur_lat) * math.sin(dest_lat) - math.sin(cur_lat) * math.cos(dest_lat) * math.cos(delta_lon)
        initial_bearing = math.atan2(x, y)

        # Normalize the bearing to be between 0 and 360 degrees
        initial_bearing = (math.degrees(initial_bearing) + 360) % 360

        return Angle(initial_bearing)

    @staticmethod
    def __angle_diff(a: Angle, b: Angle) -> Angle:
        diff: float = abs(a.degrees - b.degrees) % 360
        if diff > 180:
            return Angle(360 - diff)
        return Angle(diff)
