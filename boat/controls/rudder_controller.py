from api.objects.units.angle import Angle
from boat.controls.servos_controller import ServosController


class RudderController:

    def __init__(self, servo_controller: ServosController):
        self.servos_controller: ServosController = servo_controller
        self.SAIL_SERVO_ID = -1

    def set_rudder_angle(self, angle: Angle):
        print(f"Setting rudder angle {angle}")
        self.servos_controller.set_servo(self.SAIL_SERVO_ID, point_of_sail.value)
