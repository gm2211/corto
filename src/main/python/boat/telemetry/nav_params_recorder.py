from api.objects.nav_params.nav_params import NavParams
from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.speed import Speed


class NavParamsRecorder:

    def __init__(self):
        self.cur_nav_params = NavParams(
            heading=Angle(0),
            rudder_angle=Angle(0),
            position=GPSCoord(0, 0),
            speed=Speed(0),
            true_wind_angle=Angle(0),
            sail_trim=Angle(0)
        )

    def record_rudder_angle(self, angle: Angle) -> None:
        pass

    def record_sail_trim(self, angle: Angle) -> None:
        pass

    def record_motor_speed(self, speed) -> None:
        pass

    def get_cur_nav_params(self) -> NavParams:
        return self.cur_nav_params
