from boat.objects.angle import Angle
from boat.objects.nav_params import NavParams


class NavParamsRecorder:
    def get_latest(self) -> NavParams:
        return None

    def record_rudder_angle(self, angle):
        pass