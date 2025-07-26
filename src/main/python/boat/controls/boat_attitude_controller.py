from api.objects.nav_params.boat_attitude import BoatAttitude
from api.objects.units.percent import Percent
from api.objects.units.rudder_position import RudderPosition
from controls.servos_controller import ServosController  # Keep for type annotations
from .servos_factory import get_servos_controller
from telemetry.nav_params_recorder import NavParamsRecorder


class BoatAttitudeController:
    def __init__(
            self,
            servo_controller: ServosController,
            nav_params_recorder: NavParamsRecorder):
        self.nav_params_recorder = nav_params_recorder
        self.servos_controller: ServosController = servo_controller
        self.latest_boat_attitude: BoatAttitude = BoatAttitude(RudderPosition(Percent(0)), Percent(0))

    def set_attitude(self, boat_attitude: BoatAttitude):
        if boat_attitude == self.latest_boat_attitude:
            return
        self.latest_boat_attitude = boat_attitude
        self.set_rudder_position(boat_attitude.rudder_position.percent)
        self.set_sail_trim(boat_attitude.sail_trim)

    def set_sail_trim(self, percent: Percent):
        self.servos_controller.set_servo_1(percent)
        self.nav_params_recorder.record_sail_trim(percent)

    def set_rudder_position(self, percent: Percent):
        self.servos_controller.set_servo_2(percent)
        self.nav_params_recorder.record_rudder_position(percent)

    def set_motor_throttle(self, throttle: Percent):
        self.servos_controller.set_motor_throttle(throttle)
        self.nav_params_recorder.record_motor_throttle(throttle)


if __name__ == "__main__":
    b = BoatAttitudeController(get_servos_controller(), NavParamsRecorder())

    input("reset")
    b.servos_controller.reset_servos()

    input("left")
    b.set_attitude(BoatAttitude(RudderPosition.left(Percent(70)), Percent(100)))

    input("right")
    b.set_attitude(BoatAttitude(RudderPosition.right(Percent(70)), Percent(0)))

    input("center")
    b.set_attitude(BoatAttitude(RudderPosition.center(), Percent(50)))

    input("motor")
    b.set_motor_throttle(Percent(60))
    input("end?")

