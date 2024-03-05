from boat.controls.sail_controller import SailTrim
from api.objects.angle import Angle
from api.objects.nav_params import NavParams


class NavParamsRecorder:
    def get_latest(self) -> NavParams | None:
        return None

    def record_rudder_angle(self, angle: Angle) -> None:
        pass

    def record_sail_trim(self, trim: SailTrim) -> None:
        pass

    def get_cur_nav_params(self) -> NavParams:
        pass
