import time

from inventorhatmini import InventorHATMini, SERVO_1, SERVO_2, SERVO_3, SERVO_4
from ioexpander.common import NORMAL_DIR
from ioexpander.servo import Servo
from ioexpander.motor import Motor


class ServosController:
    MOTOR_MIN_SPEED_DUTY_CYCLE = 0.04
    MOTOR_MAX_SPEED_DUTY_CYCLE = 0.1

    def __init__(self):
        self.board = InventorHATMini(init_servos=False, init_leds=False)
        self.servo_1 = Servo(self.board.ioe, self.board.IOE_SERVO_PINS[SERVO_1])
        self.servo_2 = Servo(self.board.ioe, self.board.IOE_SERVO_PINS[SERVO_4])
        self.motor: Motor = self.board.motor_from_servo_pins(SERVO_2, SERVO_3, direction=NORMAL_DIR, freq=50)

    def set_servo_1(self, angle: int) -> None:
        self.__set_servo(self.servo_1, angle)

    def set_servo_2(self, angle: int) -> None:
        self.__set_servo(self.servo_2, angle)

    def reset_motor(self) -> None:
        print("Disabling motor")
        self.motor.disable()
        time.sleep(2)
        print("Re-enabling motor")
        self.motor.enable()
        self.motor.coast()
        time.sleep(2)
        speed = ServosController.MOTOR_MIN_SPEED_DUTY_CYCLE - 0.01
        print(f"Setting low but stable duty cycle '{speed}' to clear any potential motor lock")
        self.motor.speed(speed)

    def set_motor_speed(self, speed: float) -> None:
        def to_motor_speed(user_speed: float):
            assert 0.0 <= user_speed <= 1.0, f"Speed must be between 0.0 and 1.0, not {user_speed}"

            return ServosController.MOTOR_MIN_SPEED_DUTY_CYCLE + (
                    user_speed *
                    (ServosController.MOTOR_MAX_SPEED_DUTY_CYCLE - ServosController.MOTOR_MIN_SPEED_DUTY_CYCLE)
            )

        if speed == 0:
            self.motor.disable()
            return

        motor_speed = to_motor_speed(speed)
        print(f"Setting motor speed to: {speed}, converted to: {motor_speed}")
        self.motor.speed(motor_speed)

    @staticmethod
    def __set_servo(servo: Servo, angle: int) -> None:
        assert 0 <= angle <= 360, f"Angle must be between 0 and 360, not {angle}"
        portion = angle / 360.0
        value = servo.min_value() + ((servo.max_value() - servo.min_value()) * portion)
        print(f"Setting servo {servo.pin} to {angle}")
        servo.value(value)
