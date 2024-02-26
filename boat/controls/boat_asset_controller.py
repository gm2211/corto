from boat.controls.rudder_controller import RudderController
from boat.controls.sail_controller import SailController
from boat.telemetry.nav_params_recorder import NavParamsRecorder


class BoatAssetController:
    def __init__(
            self,
            rudder_controller: RudderController,
            sail_controller: SailController,
            nav_params_recorder: NavParamsRecorder):
        self.rudder_controller = rudder_controller
        self.sail_controller = sail_controller
        self.nav_params_recorder = nav_params_recorder

    def set_rudder_angle(self, angle):
        self.rudder_controller.set_rudder_angle(angle)
        self.nav_params_recorder.record_rudder_angle(angle)
