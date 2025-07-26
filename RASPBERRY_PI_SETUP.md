# Raspberry Pi Setup Guide for Corto

This guide explains how to set up and run the Corto boat and controller code on Raspberry Pi devices.

## System Architecture

The Corto system consists of two main components:

1. **Boat**: The autonomous sailing boat that runs the main Corto code
2. **Controller/Transmitter**: A remote control device that allows manual control of the boat

Both components run on Raspberry Pi devices and communicate with each other via LoRa radio.

### Boat Component

The boat component consists of:
- Raspberry Pi running the Corto boat code
- Servos for controlling the rudder and sail
- Motor for propulsion
- GPS for location tracking
- Wind vane for wind direction sensing
- LoRa radio for communication with the controller

### Controller/Transmitter Component

The controller component consists of:
- Raspberry Pi running the Corto transmitter code
- Analog knobs for controlling rudder, sail, and throttle
- LoRa radio for communication with the boat
- Display for showing status information

## Setting Up the Boat

### Hardware Setup

1. Connect the servos to the Raspberry Pi according to your hardware configuration
2. Connect the GPS module
3. Connect the wind vane
4. Connect the LoRa radio module

### Software Setup

1. Clone the Corto repository to your Raspberry Pi:
   ```bash
   git clone https://github.com/yourusername/corto.git
   cd corto
   ```

2. Run the setup script:
   ```bash
   cd src/main/python/boat
   chmod +x setup.sh
   ./setup.sh
   ```

   This script will:
   - Update system packages
   - Install Python and pip
   - Install Poetry (Python package manager)
   - Configure Poetry to create virtual environments in the project directory
   - Enable I2C and SPI interfaces
   - Install project dependencies using Poetry

3. Make the run script executable:
   ```bash
   chmod +x run.sh
   ```

## Setting Up the Controller/Transmitter

### Hardware Setup

1. Connect the analog knobs to the ADS1015 analog-to-digital converter
2. Connect the ADS1015 to the Raspberry Pi via I2C
3. Connect the LoRa radio module
4. Connect the display (if applicable)

### Software Setup

1. Clone the Corto repository to your Raspberry Pi:
   ```bash
   git clone https://github.com/yourusername/corto.git
   cd corto
   ```

2. Run the setup script:
   ```bash
   cd src/main/python/transmitter
   chmod +x setup.sh
   ./setup.sh
   ```

   This script will:
   - Update system packages
   - Install Python and pip
   - Install Poetry (Python package manager)
   - Configure Poetry to create virtual environments in the project directory
   - Enable I2C and SPI interfaces
   - Install Adafruit libraries for the hardware components
   - Configure SPI
   - Install project dependencies using Poetry

3. Make the run script executable:
   ```bash
   chmod +x run.sh
   ```

## Running the Boat

1. Navigate to the boat directory:
   ```bash
   cd src/main/python/boat
   ```

2. Run the boat code:
   ```bash
   ./run.sh
   ```

   The script will:
   - Check if the Poetry virtual environment exists, and run the setup script if it doesn't
   - Activate the Poetry virtual environment
   - Run the boat code

3. To stop the boat code, press `Ctrl+C`.

## Running the Controller/Transmitter

1. Navigate to the transmitter directory:
   ```bash
   cd src/main/python/transmitter
   ```

2. Run the transmitter code:
   ```bash
   ./run.sh
   ```

   The script will:
   - Check if the Poetry virtual environment exists, and run the setup script if it doesn't
   - Activate the Poetry virtual environment
   - Run the transmitter code

3. Use the knobs to control the boat:
   - Rudder knob: Controls the rudder position (left/right)
   - Sail knob: Controls the sail position (in/out)
   - Throttle knob: Controls the motor throttle (speed)

4. If running from a laptop (without physical knobs), use the following commands:
   - `l`: Turn rudder left
   - `r`: Turn rudder right
   - `u`: Increase sail trim
   - `d`: Decrease sail trim
   - `w`: Increase throttle
   - `s`: Decrease throttle

5. To stop the transmitter code, press `Ctrl+C`.

## Troubleshooting

### Common Issues

#### SPI Issues

If you encounter SPI issues, try running:
```bash
sudo -E env PATH=$PATH python3 raspi-spi-reassign.py --ce0=5 --ce1=6
```

#### I2C Issues

If you encounter I2C issues, make sure I2C is enabled:
```bash
sudo raspi-config
```
Navigate to "Interfacing Options" > "I2C" and enable it.

#### Permission Issues

If you encounter permission issues, make sure the scripts are executable:
```bash
chmod +x setup.sh run.sh
```

#### Poetry Not Found

If Poetry is not found, add it to your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```
You may want to add this line to your `~/.bashrc` or `~/.zshrc` file.

### Logs

Check the logs for error messages:
- The boat code logs to the console
- The transmitter code logs to the console

### Getting Help

If you encounter issues not covered in this guide, please:
1. Check the project documentation
2. Open an issue on the project's GitHub repository
3. Contact the project maintainers