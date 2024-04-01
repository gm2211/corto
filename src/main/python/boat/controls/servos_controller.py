import time 

from inventorhatmini import InventorHATMini, SERVO_1, SERVO_2, SERVO_3, SERVO_4
from ioexpander.common import NORMAL_DIR
from ioexpander.servo import Servo
from ioexpander.motor import Motor

from api.objects.units.percent import Percent
from utils.range_utils import remap


class ServosController:
    MOTOR_MIN_SPEED_DUTY_CYCLE = 0.06
    MOTOR_MAX_SPEED_DUTY_CYCLE = 0.12
    # We need to do it this way and not calibrate, or else we overshoot boat physical limits
    SERVO_1_RANGE = (-60, -4, 45)  # Usually sail
    SERVO_2_RANGE = (-45, 1, 45)  # Usually rudder

    def __init__(self):
        self.board = InventorHATMini(init_servos=False, init_leds=False)
        self.servo_1 = Servo(self.board.ioe, self.board.IOE_SERVO_PINS[SERVO_1])
        self.servo_2 = Servo(self.board.ioe, self.board.IOE_SERVO_PINS[SERVO_4])
        self.motor: Motor = self.board.motor_from_servo_pins(SERVO_2, SERVO_3, direction=NORMAL_DIR, freq=60)
        self.motor.disable()

    def set_servo_1(self, percent: Percent) -> None:
        self.__set_servo(self.servo_1, self.SERVO_1_RANGE, percent.value)

    def set_servo_2(self, percent: Percent) -> None:
        self.__set_servo(self.servo_2, self.SERVO_2_RANGE, percent.value)

    def reset_servo_1(self) -> None:
        zero = self.SERVO_1_RANGE[1]
        print(f"Resetting servo 1 to zero value of: {zero}")
        for i in range(500):
            self.servo_1.value(zero)

    def reset_servo_2(self) -> None:
        zero = self.SERVO_2_RANGE[1]
        print(f"Resetting servo 2 to zero value of: {zero}")
        for i in range(500):
            self.servo_2.value(zero)

    def reset_servos(self) -> None:
        self.reset_servo_1()
        self.reset_servo_2()

    def reset_motor(self) -> None:
        print("Disabling motor..")
        self.motor.disable()
        print("Enabling motor..")
        self.motor.enable()
        time.sleep(2)
        print("Setting motor speed to minimum..")
        self.motor.speed(ServosController.MOTOR_MIN_SPEED_DUTY_CYCLE)
        time.sleep(8)

    def set_motor_throttle(self, throttle: Percent) -> None:
        def to_motor_speed(user_speed: float):
            assert 0.0 <= user_speed <= 1.0, f"Speed must be between 0.0 and 1.0, not {user_speed}"

            return remap(
                user_speed,
                0.0,
                1.0,
                ServosController.MOTOR_MIN_SPEED_DUTY_CYCLE,
                ServosController.MOTOR_MAX_SPEED_DUTY_CYCLE)

        if throttle.value == 0:
            self.motor.disable()
            return

        if not self.motor.is_enabled():
            print("Motor not enabled - resetting")
            self.reset_motor()

        motor_speed = to_motor_speed(throttle.value / 100.0)
        print(f"Setting motor throttle to: {throttle.value}, converted to: {motor_speed}")
        self.motor.speed(motor_speed)

    # noinspection PyMethodMayBeStatic
    def __set_servo(self, servo: Servo, servo_range: (int, int, int), percent: int) -> None:
        assert 0 <= percent <= 100, f"Angle must be between 0 and 100, not {percent}"
        if percent == 50:
            print("Value is 50, resetting servo to zero position..")
            if servo == self.servo_1:
                self.reset_servo_1()
            else:
                self.reset_servo_2()
            return
        print(f"Setting servo {servo.pin} to {percent}")
        servo.to_percent(
            percent,
            in_min=0,
            in_max=100,
            value_min=servo_range[0],
            value_max=servo_range[2],
            load=True,
            wait_for_load=True
        )


if __name__ == "__main__":
    import time

    s = ServosController()


    def spin_motor():
        s.reset_motor()

        while True:
            for i in range(5, 100, 10):
                s.set_motor_throttle(Percent(i))
            input("next")


    def spin_servos():
        s.reset_servos()

        for value in range(50):
            print(f"Setting percent to: {50 - value}")
            input("Continue?")
            s.set_servo_1(Percent(value))
        for value in range(100):
            print(f"Setting percent to: {value}")
            input("Continue?")
            s.set_servo_1(Percent(value))
