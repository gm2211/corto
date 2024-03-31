import time

from inventorhatmini import InventorHATMini, SERVO_1, SERVO_2, SERVO_3, SERVO_4
from ioexpander.common import NORMAL_DIR
from ioexpander.servo import Servo
from ioexpander.motor import Motor


class ServosController:
    MOTOR_MIN_SPEED_DUTY_CYCLE = 0.06
    MOTOR_MAX_SPEED_DUTY_CYCLE = 0.12

    def __init__(self):
        self.board = InventorHATMini(init_servos=False, init_leds=False)
        self.servo_1 = Servo(self.board.ioe, self.board.IOE_SERVO_PINS[SERVO_1])
        self.servo_2 = Servo(self.board.ioe, self.board.IOE_SERVO_PINS[SERVO_4])
        self.servo_1_range = (-60, 45) # We need to do it this way and not calibrate, or else we overshoot boat physical limits
        self.servo_2_range = (-45, 45) # We need to do it this way and not calibrate, or else we overshoot boat physical limits 
        self.motor: Motor = self.board.motor_from_servo_pins(SERVO_2, SERVO_3, direction=NORMAL_DIR, freq=60)
        self.motor.disable()

    def set_servo_1(self, percent: int) -> None:
        self.__set_servo(self.servo_1, self.servo_1_range, percent)

    def set_servo_2(self, percent: int) -> None:
        self.__set_servo(self.servo_2, self.servo_2_range, percent)

    def reset_servos(self, zero=1) -> None:
        for i in range(100):
            self.servo_1.value(zero)
            self.servo_2.value(zero)

    def reset_motor(self) -> None:
        print("Disabling motor..")
        self.motor.disable()
        print("Enabling motor..")
        self.motor.enable()
        time.sleep(2)
        print("Setting motor speed to minimum..")
        self.motor.speed(ServosController.MOTOR_MIN_SPEED_DUTY_CYCLE)
        time.sleep(8)

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

        if not self.motor.is_enabled():
            print("Motor not enabled - resetting")
            self.reset_motor()

        motor_speed = to_motor_speed(speed)
        print(f"Setting motor speed to: {speed}, converted to: {motor_speed}")
        self.motor.speed(motor_speed)

    def set_servo(self, servo: Servo, servo_range: (int, int), percent: int) -> None:
        assert 0 <= percent <= 100, f"Angle must be between 0 and 100, not {percent}"
        print(f"Setting servo {servo.pin} to {percent}")
        servo.to_percent(
          percent, 
          in_min=0, 
          in_max=100, 
          value_min=servo_range._1, 
          value_max=servo_range._2, 
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
        s.set_motor_speed(i / 100)
      input("next")

  def spin_servos():
    s.reset_servos()

    for value in range(50):
      print(f"Setting percent to: {50 - value}")
      input("Continue?")
      s.set_servo(s.servo_1, 50 - value)
    for value in range(100):
      print(f"Setting percent to: { value}")
      input("Continue?")
      s.set_servo(s.servo_1, value)
