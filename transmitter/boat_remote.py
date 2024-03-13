import random

import adafruit_ssd1306
import board
import busio
from digitalio import DigitalInOut
import keyboard as k

from boat.comms.lora.boat_radio import BoatRadio


class BoatRemote:
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    CS = DigitalInOut(board.CE1)
    RESET = DigitalInOut(board.D25)
    TX_POWER = 23

    def __init__(self, boat_radio: BoatRadio):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(128, 32, self.i2c, reset=DigitalInOut(board.D4))
        self.boar_radio: BoatRadio = boat_radio


def clear_display(self) -> None:
    self.display.fill(0)
    self.display.show()


def run_loop(self) -> None:
    rudder = 0
    sail = 0

    while True:
        if k.is_pressed(BoatRemote.LEFT):
            rudder -= 1
            rudder = max(-100, rudder)
            self.boar_radio.send_rudder(rudder)
        elif k.is_pressed(BoatRemote.RIGHT):
            rudder += 1
            rudder = min(100, rudder)
            self.boar_radio.send_rudder(rudder)
        elif k.is_pressed(BoatRemote.UP):
            rudder = 0
            sail += 1
            sail = min(100, sail)
            self.boar_radio.send_sail(sail)
        elif k.is_pressed(BoatRemote.DOWN):
            rudder = 0
            sail -= 1
            sail = max(-100, sail)
            self.boar_radio.send_sail(sail)
