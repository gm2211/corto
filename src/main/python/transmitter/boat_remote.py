import board
import busio

from api.objects.commands.set_sail import SetSail
from api.objects.commands.set_throttle import SetThrottle
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
        throttle = 0

        while True:
            command = input("Command: ")
            if command == "l":
                rudder = max(-100, rudder - 1) % 360
                self.__show(f"left {rudder}")
                self.__send_rudder(rudder)
            elif command == "r":
                rudder = min(100, rudder + 1) % 360
                self.__show(f"right {rudder}")
                self.__send_rudder(rudder)
            elif command == "u":
                rudder = 0
                sail = min(100, sail + 1) % 360
                self.__show(f"up {sail}")
                self.__send_sail(sail)
            elif command == "d":
                sail = max(-100, sail - 1) % 360
                self.__show(f"down {sail}")
                self.__send_sail(sail)
            elif command == "w":
                throttle = min(100, throttle + 10)
                self.__show(f"throttle up {throttle}")
                self.__send_throttle(throttle)
            elif command == "s":
                throttle = max(0, throttle - 10)
                self.__show(f"throttle down {throttle}")
                self.__send_throttle(throttle)

    def __send_rudder(self, rudder):
        serialized = TurnRudder(Angle(rudder)).serialize_for_lora()
        self.radio.send(serialized)

    def __send_sail(self, sail):
        serialized = SetSail(Angle(sail)).serialize_for_lora()
        self.radio.send(serialized)

    def __send_throttle(self, throttle):
        serialized = SetThrottle(throttle).serialize_for_lora()
        self.radio.send(serialized)

    def __show(self, message):
        self.radio.clear_display()
        self.radio.show_on_display(message)


if __name__ == "__main__":
    remote = BoatRemote(Radio())

    remote.run_loop()
