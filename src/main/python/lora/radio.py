import board
import busio
import digitalio
import adafruit_rfm9x

# Display
import adafruit_ssd1306
from digitalio import DigitalInOut

UTF_8 = "utf-8"


class Radio:
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
        self.interrupt_initialized = False

    def register_callback(self, callback):
        import RPi.GPIO as gpio

        self.__init_interrupt_if_not_initd()

        def packet_received_callback(_ignored):
            # Check to see if this was a "receive" interrupt - ignore "transmit" interrupts
            if not self.radio.rx_done:
                return None

            packet = self.radio.receive(timeout=None)

            if packet is None:
                return None

            packet_content = packet.decode(UTF_8)
            self.show_on_display(f"Received: {packet_content}")
            callback(packet_content)

        gpio.add_event_callback(self.INTERRUPT_PIN, packet_received_callback)

    def send(self, message: str):
        self.radio.send(bytes(message, UTF_8))
        self.show_on_display(f"Sent: {message}")

    def show_on_display(self, message):
        self.display.text(message, 0, 0, 1)
        self.display.show()

    def clear_display(self) -> None:
        self.display.fill(0)
        self.display.show()

    def __init_interrupt_if_not_initd(self) -> None:
        import RPi.GPIO as gpio
        
        if self.interrupt_initialized:
            return None

        gpio.setmode(gpio.BCM)
        gpio.setup(self.INTERRUPT_PIN, gpio.IN, pull_up_down=gpio.PUD_DOWN)  # activate input
        gpio.add_event_detect(self.INTERRUPT_PIN, gpio.RISING)

        # Send a packet just to be able to keep listening
        self.radio.send(bytes("setup", UTF_8), keep_listening=True)

        self.interrupt_initialized = True
