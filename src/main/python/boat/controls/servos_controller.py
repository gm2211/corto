from inventorhatmini import InventorHATMini

from api.objects.units.angle import Angle


class ServosController:

    def __init__(self):
        self.board = InventorHATMini(init_leds=False)

    def set_servo(self, servo_id: int, angle: Angle):
        portion = angle.degrees / 360
        servo = self.board.servos[servo_id]
        value = (servo.max_value() - servo.min_value()) * portion
        print("Setting servo", servo_id, "to", angle)
        servo.value(value)

    # TODO: the code below works but needs to be reworked to make this method more useful
    def set_pwm(self):
        import time, sys
        import RPi.GPIO as GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(7, GPIO.OUT)

        p = GPIO.PWM(7, 50)

        p.start(0)
        p.ChangeDutyCycle(3)
        print("Starting, will hear beeps")
        time.sleep(5)

        while True:
            try:
                i = 4
                while i < 10:
                    print(i)
                    p.ChangeDutyCycle(i)
                    time.sleep(.05)
                    i += .02
                while i > 4:
                    print(i)
                    p.ChangeDutyCycle(i)
                    time.sleep(.05)
                    i -= .05
            except KeyboardInterrupt:
                print("Stopping..")
                p.ChangeDutyCycle(0)
                time.sleep(5)
                p.stop()
                time.sleep(1)
                sys.exit(0)
