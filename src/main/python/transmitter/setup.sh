#!/usr/bin/bash --
# Corto Transmitter Setup Script
# This script sets up the environment for running the Corto transmitter/controller code on a Raspberry Pi.
# It installs system dependencies, Python, Poetry, and project dependencies.

# Exit on error
set -e

echo "=== Corto Transmitter Setup ==="
echo "This script will set up your Raspberry Pi to run the Corto transmitter/controller code."
echo "It will install system dependencies, Python, Poetry, and project dependencies."
echo "This may take a while..."
echo ""

# Get the script directory and project root
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)

echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo ""

# Update system packages
echo "=== Updating system packages ==="
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install python3-pip python3-venv -y

# Install Poetry
echo "=== Installing Poetry ==="
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# Configure Poetry to create virtual environments in the project directory
poetry config virtualenvs.in-project true

# Install Raspberry Pi specific dependencies
echo "=== Installing Raspberry Pi specific dependencies ==="
sudo raspi-config nonint do_i2c 0  # Enable I2C
sudo raspi-config nonint do_spi 0  # Enable SPI

# Install additional Adafruit dependencies needed for the transmitter
echo "=== Installing Adafruit dependencies ==="
sudo pip3 install --upgrade adafruit-blinka
sudo pip3 install adafruit-circuitpython-busdevice
sudo pip3 install adafruit-circuitpython-ssd1306
sudo pip3 install adafruit-circuitpython-rfm9x
sudo pip3 install adafruit-circuitpython-ads1x15
sudo pip3 install --upgrade adafruit-python-shell click
sudo pip3 install keyboard

# Configure SPI
echo "=== Configuring SPI ==="
sudo -E env PATH="$PATH" python3 "$SCRIPT_DIR/../utils/raspi-spi-reassign.py" --ce0=disabled --ce1=disabled
echo "If you still running into ce0 and ce1 issues, try running the following command:"
echo "sudo -E env PATH=$PATH python3 raspi-spi-reassign.py --ce0=5 --ce1=6"

# Install project dependencies using Poetry
echo "=== Installing project dependencies ==="
cd "$PROJECT_ROOT"
poetry install --with rpi

echo ""
echo "=== Setup Complete ==="
echo "You can now run the transmitter code using the run.sh script."
echo "If you encounter any issues, please check the troubleshooting section in the documentation."
