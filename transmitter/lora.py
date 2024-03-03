import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board

# Import the SSD1306 module.
import adafruit_ssd1306
# Import the RFM9x radio module.
import adafruit_rfm9x


def create_button(pin):
    button = DigitalInOut(pin)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    return button


btnA = create_button(board.D5)
btnB = create_button(board.D6)
btnC = create_button(board.D12)

# 128x32 OLED Display
i2c = busio.I2C(board.SCL, board.SDA)
reset_pin = DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)

# Clear the display.
display.fill(0)
display.show()
width = display.width
height = display.height

# Configure RFM9x LoRa Radio
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

while True:
    # Clear the image
    display.fill(0)

    # Attempt to set up the RFM9x Module
    try:
        rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
        display.text('RFM9x: Detected', 0, 0, 1)
    except RuntimeError as error:
        # Thrown on version mismatch
        display.text('RFM9x: ERROR', 0, 0, 1)
        print('RFM9x Error: ', error)

    # Check buttons
    if not btnA.value:
        # Button A Pressed
        display.text('Button A pressed', width - 85, height - 7, 1)
        display.show()
        time.sleep(0.1)
    if not btnB.value:
        # Button B Pressed
        display.text('Button B pressed', width - 75, height - 7, 1)
        display.show()
        time.sleep(0.1)
    if not btnC.value:
        # Button C Pressed
        display.text('Button C Pressed', width - 65, height - 7, 1)
        display.show()
        time.sleep(0.1)

    display.show()
    time.sleep(0.1)
