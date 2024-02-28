from boat.controls.rudder_controller import RudderController
from boat.controls.sail_controller import SailController, SailTrim
from boat.objects.angle import Angle
from boat.objects.boat_attitude import BoatAttitude
from boat.telemetry.nav_params_recorder import NavParamsRecorder


class BoatAttitudeController:
    def __init__(
            self,
            rudder_controller: RudderController,
            sail_controller: SailController,
            nav_params_recorder: NavParamsRecorder):
        self.rudder_controller = rudder_controller
        self.sail_controller = sail_controller
        self.nav_params_recorder = nav_params_recorder

    def set_attitude(self, boat_attitude: BoatAttitude):
        self.__set_rudder_angle(boat_attitude.rudder)
        self.__set_sail_trim(boat_attitude.sail_trim)

    def __set_rudder_angle(self, angle: Angle):
        self.rudder_controller.set_rudder_angle(angle)
        self.nav_params_recorder.record_rudder_angle(angle)

    def __set_sail_trim(self, trim: SailTrim):
        self.sail_controller.set_sail_trim(trim)
        self.nav_params_recorder.record_sail_trim(trim)
