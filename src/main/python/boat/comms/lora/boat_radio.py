import time
import board
import busio
import digitalio
import RPi.GPIO as gpio
import adafruit_rfm9x

# Display
import adafruit_ssd1306
from digitalio import DigitalInOut

from utils import lora_utils as lora

UTF_8 = "utf-8"


class BoatRadio:
    RADIO_FREQ_MHZ = 915.0
    CS = digitalio.DigitalInOut(board.CE1)
    RESET = digitalio.DigitalInOut(board.D25)
    INTERRUPT_PIN = 22

    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(128, 32, self.i2c, reset=DigitalInOut(board.D4))
        self.spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        self.radio = adafruit_rfm9x.RFM9x(self.spi, self.CS, self.RESET, self.RADIO_FREQ_MHZ)
        self.radio.tx_power = 23  # 23 is the maximum power

        gpio.setmode(gpio.BCM)
        gpio.setup(self.INTERRUPT_PIN, gpio.IN, pull_up_down=gpio.PUD_DOWN)  # activate input
        gpio.add_event_detect(self.INTERRUPT_PIN, gpio.RISING)

        # Send a packet just to be able to keep listening
        self.radio.send(bytes("setup", UTF_8), keep_listening=True)

    def register_callback(self, callback):
        def packet_received_callback(_ignore):
            # Check to see if this was a "receive" interrupt - ignore "transmit" interrupts
            if not self.radio.rx_done:
                return None

            packet = self.radio.receive(timeout=None)

            if packet is not None:
                decoded = packet.decode(UTF_8)
                self.display.text("Received: {}".format(decoded), 0, 0, 1)
                self.display.show()
                callback(packet)

        gpio.add_event_callback(self.INTERRUPT_PIN, packet_received_callback)

    def send(self, message):
        self.radio.send(bytes(message, UTF_8))
        lora.show_msg(self.display, "Sent: {}".format(message))


boat_receiver = BoatRadio()

while True:
    time.sleep(0.1)
