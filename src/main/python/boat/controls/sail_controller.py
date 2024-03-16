from api.objects.units.angle import Angle
from boat.controls.servos_controller import ServosController


class SailController:

    def __init__(self, servo_controller: ServosController):
        self.servos_controller: ServosController = servo_controller
        self.SAIL_SERVO_ID = 0

    def set_sail_trim(self, angle: Angle):
        print(f"Setting sail trim to angle: {angle}")
        self.servos_controller.set_servo(self.SAIL_SERVO_ID, angle)
