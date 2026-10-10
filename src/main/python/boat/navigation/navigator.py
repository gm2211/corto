from __future__ import annotations

import math
from typing import TYPE_CHECKING

from api.objects.nav_params.boat_attitude import BoatAttitude
from api.objects.nav_params.nav_params import NavParams
from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.percent import Percent
from api.objects.units.rudder_position import RudderPosition
from utils.range_utils import remap

if TYPE_CHECKING:
    # Only used as type hints. Keeping them out of the runtime imports means the navigator can be
    # driven by the simulator (or the tests) without pulling in the hardware drivers and pyformance.
    from telemetry.nav_params_recorder import NavParamsRecorder
    from telemetry.sensors.gps_locator import GPSLocator
    from telemetry.sensors.wind_vane import WindVane


class Navigator:
    MIN_WIND_ANGLE = 45
    MAX_WIND_ANGLE = 135
    # Heading error (degrees) at which the rudder reaches full deflection; smaller errors are proportional.
    FULL_RUDDER_ERROR_DEG = 30
    # Heading errors smaller than this (degrees) leave the rudder centred.
    RUDDER_DEADBAND_DEG = 1

    def __init__(self, wind_vane: WindVane, locator: GPSLocator, nav_params_recorder: NavParamsRecorder):
        self.wind_vane: WindVane = wind_vane
        self.locator: GPSLocator = locator
        self.nav_params_recorder = nav_params_recorder

    def compute_boat_attitude(self, dest: GPSCoord) -> BoatAttitude:
        cur_pos: GPSCoord = self.locator.cur_location()
        nav_params: NavParams = self.nav_params_recorder.get_cur_nav_params()
        cur_heading: Angle = nav_params.heading
        desired_heading: Angle = self.__bearing_to(cur_pos, dest)
        rudder_position: RudderPosition = self.__rudder_for_heading_error(
            self.__signed_heading_error(cur_heading, desired_heading)
        )
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
    def __signed_heading_error(cur_heading: Angle, desired_heading: Angle) -> float:
        """Shortest signed turn from the current to the desired heading, in degrees (-180, 180).

        Positive means the desired heading is to starboard (turn right), negative means port (turn left).
        """
        return Navigator.__normalize_with_sign(Angle((desired_heading.degrees - cur_heading.degrees) % 360)).degrees

    @staticmethod
    def __rudder_for_heading_error(error_deg: float) -> RudderPosition:
        """Proportional rudder: deadband around zero, full deflection at FULL_RUDDER_ERROR_DEG."""
        if abs(error_deg) < Navigator.RUDDER_DEADBAND_DEG:
            return RudderPosition.center()
        deflection = Percent(min(100, abs(error_deg) * 100 / Navigator.FULL_RUDDER_ERROR_DEG))
        return RudderPosition.right(deflection) if error_deg > 0 else RudderPosition.left(deflection)

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
