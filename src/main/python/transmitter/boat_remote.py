import board
import busio
import keyboard as k

from api.objects.commands.set_sail import SetSail
from api.objects.commands.turn_rudder import TurnRudder
from api.objects.units.angle import Angle
from lora.radio import Radio


class BoatRemote:
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    TX_POWER = 23

    def __init__(self, radio: Radio):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.radio: Radio = radio

    def run_loop(self) -> None:
        rudder = 0
        sail = 0

        while True:
            if k.is_pressed(BoatRemote.LEFT):
                rudder -= 1
                rudder = max(-100, rudder)
                self.__send_rudder(rudder)
            elif k.is_pressed(BoatRemote.RIGHT):
                rudder += 1
                rudder = min(100, rudder)
                self.__send_rudder(rudder)
            elif k.is_pressed(BoatRemote.UP):
                rudder = 0
                sail += 1
                sail = min(100, sail)
                self.__send_sail(sail)
            elif k.is_pressed(BoatRemote.DOWN):
                rudder = 0
                sail -= 1
                sail = max(-100, sail)
                self.__send_sail(sail)

    def __send_rudder(self, rudder):
        self.radio.send(TurnRudder(Angle(rudder)))

    def __send_sail(self, sail):
        self.radio.send(SetSail(Angle(sail)))


if __name__ == "__main__":
    remote = BoatRemote(Radio())

    remote.run_loop()
