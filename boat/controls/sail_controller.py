from api.objects.sail_trim import SailTrim
from boat.controls.servos_controller import ServosController


class SailController:

    def __init__(self, servo_controller: ServosController):
        self.servos_controller: ServosController = servo_controller
        self.SAIL_SERVO_ID = 0

    def set_sail_trim(self, point_of_sail: SailTrim):
        print(f"Setting sail trim {point_of_sail.name}")
        self.servos_controller.set_servo(self.SAIL_SERVO_ID, point_of_sail.value)
