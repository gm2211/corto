import math

from api.objects.nav_params.boat_attitude import BoatAttitude
from api.objects.nav_params.nav_params import NavParams
from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.percent import Percent
from api.objects.units.rudder_position import RudderPosition
from boat.telemetry.nav_params_recorder import NavParamsRecorder
from boat.telemetry.sensors.gps_locator import GPSLocator
from boat.telemetry.sensors.wind_vane import WindVane
from utils.range_utils import remap


class Navigator:
    MIN_WIND_ANGLE = 45
    MAX_WIND_ANGLE = 135

    def __init__(self, wind_vane: WindVane, locator: GPSLocator, nav_params_recorder: NavParamsRecorder):
        self.wind_vane: WindVane = wind_vane
        self.locator: GPSLocator = locator
        self.nav_params_recorder = nav_params_recorder

    def compute_boat_attitude(self, dest: GPSCoord) -> BoatAttitude:
        cur_pos: GPSCoord = self.locator.cur_location()
        nav_params: NavParams = self.nav_params_recorder.get_cur_nav_params()
        cur_heading: Angle = nav_params.heading
        desired_heading: Angle = self.__bearing_to(cur_pos, dest)
        heading_diff: Angle = self.__angle_diff(cur_heading, desired_heading)
        # TODO: Be more granular with rudder position
        rudder_position: RudderPosition = (RudderPosition.left(Percent(100))
                                           if heading_diff.degrees > 0 else RudderPosition.right(Percent(100)))
        # Normalize the angle to be between 0 and 180 degrees
        angle_between_boat_and_wind: int = abs(
            self.__normalize_with_sign(
                self.__angle_diff(cur_heading, self.wind_vane.get_true_wind())
            ).degrees
        )
        angle_between_boat_and_wind = Angle(min(
          self.MAX_WIND_ANGLE, 
          max(self.MIN_WIND_ANGLE, angle_between_boat_and_wind)
        ))
        sail_trim: Percent = Percent(
          remap(
            angle_between_boat_and_wind.degrees, 
            self.MIN_WIND_ANGLE, 
            self.MAX_WIND_ANGLE, 
            100, 
            0
          )
        )
        return BoatAttitude(rudder_position, sail_trim)

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
        diff: float = (a.degrees - b.degrees) % 360
        if a.degrees < b.degrees:
            return Angle(360 - diff)
        return Angle(diff)

    @staticmethod
    def __normalize_with_sign(angle: Angle):
        if angle.degrees < 180:
            return angle
        return Angle(angle.degrees - 360)
