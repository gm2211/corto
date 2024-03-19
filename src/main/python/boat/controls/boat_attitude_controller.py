from api.objects.nav_params.boat_attitude import BoatAttitude
from api.objects.units.angle import Angle
from boat.controls.rudder_controller import RudderController
from boat.controls.sail_controller import SailController
from boat.controls.servos_controller import ServosController
from boat.telemetry.nav_params_recorder import NavParamsRecorder


class BoatAttitudeController:
    def __init__(
            self,
            servo_controller: ServosController,
            nav_params_recorder: NavParamsRecorder):
        self.nav_params_recorder = nav_params_recorder
        self.servos_controller: ServosController = servo_controller

    def set_attitude(self, boat_attitude: BoatAttitude):
        self.set_rudder_angle(boat_attitude.rudder)
        self.set_sail_trim(boat_attitude.sail_trim)

    def set_sail_trim(self, angle: Angle):
        self.servos_controller.set_servo_1(angle)
        self.nav_params_recorder.record_sail_trim(angle)

    def set_rudder_angle(self, angle: Angle):
        self.servos_controller.set_servo_2(angle)
        self.nav_params_recorder.record_rudder_angle(angle)

    def set_motor_speed(self, speed: float):
        self.servos_controller.set_motor_speed(speed)
        self.nav_params_recorder.record_motor_speed(speed)
