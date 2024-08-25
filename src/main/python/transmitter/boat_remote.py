import argparse
import board
import busio
import time
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

from api.objects.commands.set_sail import SetSail
from api.objects.commands.set_throttle import SetThrottle
from api.objects.commands.turn_rudder import TurnRudder
from api.objects.units.percent import Percent
from lora.radio import Radio


class BoatRemote:
    TX_POWER = 23

    def __init__(self, radio: Radio, from_laptop=False):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1015(self.i2c)
        self.speed_knob = AnalogIn(self.ads, ADS.P1)
        self.rudder_knob = AnalogIn(self.ads, ADS.P2)
        self.sail_knob = AnalogIn(self.ads, ADS.P3)
        self.radio: Radio = radio
        self.from_laptop = from_laptop

    def run_loop(self) -> None:
        rudder = 50
        sail = 50
        throttle = 0

        use_knobs = not self.from_laptop or input("Use knobs to control input? (y/n): ").lower() == "y"

        while True:
            if use_knobs:
                new_rudder, new_sail, new_throttle = self.__read_knobs(rudder, sail, throttle)
                if new_rudder != rudder or new_sail != sail or new_throttle != throttle:
                  self.__show(f"sail {sail} \nrudder {rudder} \nthrottle {throttle}")
                  rudder, sail, throttle = (new_rudder, new_sail, new_throttle)
            else:
                rudder, sail, throttle = self.__prompt_command(rudder, sail, throttle)
                print(f"rudder: {rudder}, sail: {sail}, throttle: {throttle}")

    def __read_knobs(self, rudder, sail, throttle):
        def r(v):
            percent = round(v / 3.3 * 100, 0)
            return max(0, min(100, percent))

        def changed(prev, new):
            return abs(prev - new) > 0.1

        new_rudder = r(self.rudder_knob.voltage)
        new_sail = r(self.sail_knob.voltage)
        new_throttle = r(self.speed_knob.voltage)

        if changed(rudder, new_rudder):
            self.__send_rudder(Percent(new_rudder))
            return new_rudder, sail, throttle
        elif changed(sail, new_sail):
            self.__send_sail(Percent(new_sail))
            return rudder, new_sail, throttle
        elif changed(throttle, new_throttle):
            self.__send_throttle(Percent(new_throttle))
            return rudder, sail, new_throttle
        return rudder, sail, throttle

    def __prompt_command(self, rudder, sail, throttle):
        command = input("Command: ")
        if command == "l":
            rudder = max(0, rudder - 1)
            self.__show(f"left {rudder}")
            self.__send_rudder(Percent(rudder))
            return rudder, sail, throttle
        if command == "r":
            rudder = min(100, rudder + 1)
            self.__show(f"right {rudder}")
            self.__send_rudder(Percent(rudder))
            return rudder, sail, throttle
        if command == "u":
            rudder = 0
            sail = min(100, sail + 1)
            self.__show(f"up {sail}")
            self.__send_sail(Percent(sail))
            return rudder, sail, throttle
        if command == "d":
            sail = max(0, sail - 1)
            self.__show(f"down {sail}")
            self.__send_sail(Percent(sail))
            return rudder, sail, throttle
        if command == "w":
            throttle = min(100, throttle + 10)
            self.__show(f"throttle up {throttle}")
            self.__send_throttle(throttle)
            return rudder, sail, throttle
        if command == "s":
            throttle = max(0, throttle - 10)
            self.__show(f"throttle down {throttle}")
            self.__send_throttle(throttle)
            return rudder, sail, throttle
        return rudder, sail, throttle

    def __send_rudder(self, rudder: Percent):
        serialized = TurnRudder(rudder).serialize_for_lora()
        self.radio.send(serialized)

    def __send_sail(self, sail: Percent):
        serialized = SetSail(sail).serialize_for_lora()
        self.radio.send(serialized)

    def __send_throttle(self, throttle):
        serialized = SetThrottle(throttle).serialize_for_lora()
        self.radio.send(serialized)

    def __show(self, message):
        self.radio.show_on_display(message)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
      prog='Boat Remote',
      description='To control the boat')

    parser.add_argument("--from_laptop", action="store_true")
    args = parser.parse_args()

    remote = BoatRemote(Radio(), from_laptop=args.from_laptop)

    remote.run_loop()
