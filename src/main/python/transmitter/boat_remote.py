import board
import busio

from api.objects.commands.set_sail import SetSail
from api.objects.commands.turn_rudder import TurnRudder
from api.objects.units.angle import Angle
from lora.radio import Radio


class BoatRemote:
    TX_POWER = 23

    def __init__(self, radio: Radio):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.radio: Radio = radio

    def run_loop(self) -> None:
        rudder = 0
        sail = 0

        while True:
            command = input("Command: ")
            if command == "l":
                self.radio.clear_display()
                self.radio.show_on_display("left")
                rudder = max(-100, rudder - 1)
                self.__send_rudder(rudder)
            elif command == "r":
                self.radio.clear_display()
                self.radio.show_on_display("right")
                rudder = min(100, rudder + 1)
                self.__send_rudder(rudder)
            elif command == "u":
                self.radio.clear_display()
                self.radio.show_on_display("up")
                rudder = 0
                sail += 1
                sail = min(100, sail)
                self.__send_sail(sail)
            elif command == "d":
                self.radio.clear_display()
                self.radio.show_on_display("dwon")
                rudder = 0
                sail -= 1
                sail = max(-100, sail)
                self.__send_sail(sail)

    def __send_rudder(self, rudder):
        self.radio.send(TurnRudder(Angle(rudder)).serialize_for_lora())

    def __send_sail(self, sail):
        self.radio.send(SetSail(Angle(sail)).serialize_for_lora())


if __name__ == "__main__":
    remote = BoatRemote(Radio())

    remote.run_loop()
