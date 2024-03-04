import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import math
# Import the servos board
from inventorhatmini import InventorHATMini, SERVO_1, SERVO_4, LED_SERVO_1
# Import the SSD1306 module.
import adafruit_ssd1306
# Import the RFM9x radio module.
import adafruit_rfm9x


def create_button(pin):
    button = DigitalInOut(pin)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    return button


btn1 = create_button(board.D5)
btn2 = create_button(board.D6)
btn3 = create_button(board.D12)

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

# Setup servo board
servo_board = InventorHATMini(init_leds=False)
rudder = servo_board.servos[SERVO_1]
sail = servo_board.servos[SERVO_4]

rudder.enable()
sail.enable()

done = False

while not done:
    # Clear the image
    display.fill(0)

    # Attempt to set up the RFM9x Module
    try:
        rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
        display.text('RFM9x: Detected', 0, 0, 1)
        display.show()
    except RuntimeError as error:
        # Thrown on version mismatch
        display.text('RFM9x: ERROR', 0, 0, 1)
        display.show()
        print('RFM9x Error: ', error)

    # Check buttons
    if not btn1.value or not btn2.value:
        display.text('Fruit', width - 75, height - 7, 1)
        btn_name = (not btn1.value and "btn1") or (not btn2.value and "btn2") or (not btn3.value and "btn3")
        display.text('Btn: {}'.format(btn_name), width - 65, height - 7, 1)
        display.show()
        time.sleep(0.1)

        for i in range(int(rudder.min_value()), int(rudder.max_value()) + 1):
            rudder.value(i)
            sail.value(i)
            time.sleep(0.1)
    done = btn3.value

    display.show()
    time.sleep(0.1)

rudder.disable()
sail.disable()
