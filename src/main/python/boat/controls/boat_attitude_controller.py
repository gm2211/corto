from api.objects.nav_params.boat_attitude import BoatAttitude
from api.objects.units.angle import Angle
from boat.controls.servos_controller import ServosController
from boat.telemetry.nav_params_recorder import NavParamsRecorder


class BoatAttitudeController:
    def __init__(
            self,
            servo_controller: ServosController,
            nav_params_recorder: NavParamsRecorder):
        self.nav_params_recorder = nav_params_recorder
        self.servos_controller: ServosController = servo_controller
        self.latest_boat_attitude: BoatAttitude = BoatAttitude(Angle(0), Angle(0))

    def set_attitude(self, boat_attitude: BoatAttitude):
        if boat_attitude == self.latest_boat_attitude:
            return
        self.latest_boat_attitude = boat_attitude
        self.set_rudder_angle(boat_attitude.rudder)
        self.set_sail_trim(boat_attitude.sail_trim)

    def set_sail_trim(self, angle: Angle):
        self.servos_controller.set_servo_1(angle)
        self.nav_params_recorder.record_sail_trim(angle)

    def set_rudder_angle(self, angle: Angle):
        self.servos_controller.set_servo_2(angle)
        self.nav_params_recorder.record_rudder_angle(angle)

    def set_motor_throttle(self, speed: float):
        self.servos_controller.set_motor_speed(speed)
        self.nav_params_recorder.record_motor_speed(speed)
