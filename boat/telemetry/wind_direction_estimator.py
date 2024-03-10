from api.objects.angle import Angle
from boat.telemetry.sensors.gps_locator import GPSLocator
from boat.telemetry.sensors.speed_over_water_sensor import SpeedOverWaterSensor
from boat.telemetry.sensors.wind_vane import WindVane


class WindDirectionEstimator:

    def __init__(self, wind_vane: WindVane, locator: GPSLocator, speed_over_water_sensor: SpeedOverWaterSensor):
        self.speed_over_water: SpeedOverWaterSensor = speed_over_water_sensor
        self.wind_vane: WindVane = wind_vane
        self.locator: GPSLocator = locator

    def get_wind_direction(self) -> Angle:
        wind_vane_direction: Angle = self.wind_vane.get_true_wind()
        return wind_vane_direction

    # TODO: Implement or remove
    def __estimate_wind_direction_from_heading_and_track(self) -> Angle | None:
        heading: Angle = self.locator.cur_heading()
        # Speed can be calculated as follows, but easier to just use the sensor
        # speed = (
        #   (dist(pos1, pos2) / (time_end - time_start)
        #   - speed_of_current
        #   * cos(course_over_ground - direction_of_current)
        # )
        # * cos(course_over_ground - avg(heading))
        # true_wind_angle: Angle = abs(
        #     math.arrcos(
        #         math.avg(apparent_wind_speed) * math.cos(math.avg(apparent_wind_angle)) - speed_over_water)
        #     / true_wind_speed
        # speed_over_water: Knots = self.speed_over_water.cur_speed()
        # If we do compute wind angle like this we also need a proper reconciliation algorithm (e.g. Kalman filter -
        # see https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6707739/)
        return None

    # Implement or remove
    @staticmethod
    def __reconcile(wind_vane_direction, estimated_from_heading_and_track) -> Angle:
        return (wind_vane_direction + estimated_from_heading_and_track) / 2
