from api.objects.units.angle import Angle
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

    # Implement or remove
    @staticmethod
    def __reconcile(wind_vane_direction, estimated_from_heading_and_track) -> Angle:
        return (wind_vane_direction + estimated_from_heading_and_track) / 2
