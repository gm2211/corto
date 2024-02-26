from boat.controls.sail_controller import PointOfSail
from boat.objects.angle import Angle
from boat.objects.gps_coord import GPSCoord


class NavParams:
    def __init__(
            self,
            heading: Angle,
            rudder_angle: Angle,
            position: GPSCoord,
            true_wind_angle: Angle,
            point_of_sail: PointOfSail):
        self.heading = heading
        self.rudder_angle = rudder_angle
        self.position = position
        self.true_wind_angle = true_wind_angle
        self.point_of_sail = point_of_sail
