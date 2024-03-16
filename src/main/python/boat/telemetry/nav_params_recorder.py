from api.objects.nav_params.nav_params import NavParams
from api.objects.nav_params.sail_trim import SailTrim
from api.objects.units.angle import Angle


class NavParamsRecorder:
    def get_latest(self) -> NavParams | None:
        return None

    def record_rudder_angle(self, angle: Angle) -> None:
        pass

    def record_sail_trim(self, angle: Angle) -> None:
        trim = SailTrim.from_angle(angle)
        pass

    def get_cur_nav_params(self) -> NavParams:
        pass
