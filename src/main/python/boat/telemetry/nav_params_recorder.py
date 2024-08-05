from api.objects.nav_params.nav_params import NavParams
from api.objects.units.angle import Angle
from api.objects.units.knots import Knots
from api.objects.units.percent import Percent
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.speed import Speed


class NavParamsRecorder:

    def __init__(self):
        self.cur_nav_params = NavParams(
            heading=Angle(0),
            rudder_position=Percent(0),
            position=GPSCoord(0, 0),
            motor_throttle=Percent(0),
            speed_over_water=Speed(0),
            true_wind_angle=Angle(0),
            sail_trim=Percent(0)
        )

    def record_rudder_position(self, percent: Percent) -> None:
        pass

    def record_sail_trim(self, percent: Percent) -> None:
        pass

    def record_motor_throttle(self, throttle: Percent) -> None:
        pass

    def record_speed_over_water(self, speed: Knots) -> None:
        pass

    def get_cur_nav_params(self) -> NavParams:
        return self.cur_nav_params
