from inventorhatmini import InventorHATMini


class ServosController:

    def __init__(self):
        self.board = InventorHATMini(init_leds=False)

    def set_servo(self, servo_id, angle):
        portion = angle.degrees / 360
        servo = self.board.servos[servo_id]
        value = (servo.max_value() - servo.min_value()) * portion
        print("Setting servo", servo_id, "to", angle)
        servo.value(value)
