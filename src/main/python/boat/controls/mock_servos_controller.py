from api.objects.units.percent import Percent


class MockServo:
    def __init__(self, pin):
        self.pin = pin
        self.current_value = 0

    def value(self, val):
        self.current_value = val
        print(f"[MOCK] Setting servo {self.pin} value to {val}")

    def to_percent(self, percent, in_min, in_max, value_min, value_max, load=False, wait_for_load=False):
        print(f"[MOCK] Setting servo {self.pin} to {percent}% (range: {value_min} to {value_max})")
        self.current_value = percent


class MockMotor:
    def __init__(self):
        self.enabled = False
        self.current_speed = 0

    def enable(self):
        self.enabled = True
        print("[MOCK] Motor enabled")

    def disable(self):
        self.enabled = False
        print("[MOCK] Motor disabled")

    def is_enabled(self):
        return self.enabled

    def speed(self, speed_value):
        self.current_speed = speed_value
        print(f"[MOCK] Setting motor speed to {speed_value}")


class MockServosController:
    """
    A mock implementation of the ServosController class for non-Raspberry Pi environments.
    This class mimics the behavior of the real ServosController but doesn't require any
    Raspberry Pi-specific hardware or libraries.
    """
    MOTOR_MIN_SPEED_DUTY_CYCLE = 0.06
    MOTOR_MAX_SPEED_DUTY_CYCLE = 0.12
    SERVO_1_RANGE = (-60, -4, 45)  # Usually sail
    SERVO_2_RANGE = (-45, 1, 45)  # Usually rudder

    def __init__(self):
        print("[MOCK] Initializing MockServosController")
        self.servo_1 = MockServo(1)
        self.servo_2 = MockServo(2)
        self.motor = MockMotor()
        self.motor.disable()

    def set_servo_1(self, percent: Percent) -> None:
        self.__set_servo(self.servo_1, self.SERVO_1_RANGE, percent.value)

    def set_servo_2(self, percent: Percent) -> None:
        self.__set_servo(self.servo_2, self.SERVO_2_RANGE, percent.value)

    def reset_servo_1(self) -> None:
        zero = self.SERVO_1_RANGE[1]
        print(f"[MOCK] Resetting servo 1 to zero value of: {zero}")
        self.servo_1.value(zero)

    def reset_servo_2(self) -> None:
        zero = self.SERVO_2_RANGE[1]
        print(f"[MOCK] Resetting servo 2 to zero value of: {zero}")
        self.servo_2.value(zero)

    def reset_servos(self) -> None:
        self.reset_servo_1()
        self.reset_servo_2()

    def reset_motor(self) -> None:
        print("[MOCK] Disabling motor..")
        self.motor.disable()
        print("[MOCK] Enabling motor..")
        self.motor.enable()
        print("[MOCK] Setting motor speed to minimum..")
        self.motor.speed(MockServosController.MOTOR_MIN_SPEED_DUTY_CYCLE)

    def set_motor_throttle(self, throttle: Percent) -> None:
        def to_motor_speed(user_speed: float):
            assert 0.0 <= user_speed <= 1.0, f"Speed must be between 0.0 and 1.0, not {user_speed}"
            return (user_speed * (MockServosController.MOTOR_MAX_SPEED_DUTY_CYCLE - 
                                 MockServosController.MOTOR_MIN_SPEED_DUTY_CYCLE) + 
                    MockServosController.MOTOR_MIN_SPEED_DUTY_CYCLE)

        if throttle.value == 0:
            self.motor.disable()
            return

        if not self.motor.is_enabled():
            print("[MOCK] Motor not enabled - resetting")
            self.reset_motor()

        motor_speed = to_motor_speed(throttle.value / 100.0)
        print(f"[MOCK] Setting motor throttle to: {throttle.value}, converted to: {motor_speed}")
        self.motor.speed(motor_speed)

    # noinspection PyMethodMayBeStatic
    def __set_servo(self, servo: MockServo, servo_range: (int, int, int), percent: int) -> None:
        assert 0 <= percent <= 100, f"Angle must be between 0 and 100, not {percent}"
        if percent == 50:
            print("[MOCK] Value is 50, resetting servo to zero position..")
            if servo == self.servo_1:
                self.reset_servo_1()
            else:
                self.reset_servo_2()
            return
        print(f"[MOCK] Setting servo {servo.pin} to {percent}")
        servo.to_percent(
            percent,
            in_min=0,
            in_max=100,
            value_min=servo_range[0],
            value_max=servo_range[2],
            load=True,
            wait_for_load=True
        )