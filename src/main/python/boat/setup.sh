#!/usr/bin/bash --
# Corto Boat Setup Script
# This script sets up the environment for running the Corto boat code on a Raspberry Pi.
# It installs system dependencies, Python, Poetry, and project dependencies.

# Exit on error
set -e

echo "=== Corto Boat Setup ==="
echo "This script will set up your Raspberry Pi to run the Corto boat code."
echo "It will install system dependencies, Python, Poetry, and project dependencies."
echo "This may take a while..."
echo ""

# Get the script directory
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

# Install project dependencies using Poetry
echo "=== Installing project dependencies ==="
cd "$PROJECT_ROOT"
poetry install --with rpi

echo ""
echo "=== Setup Complete ==="
echo "You can now run the boat code using the run.sh script."
echo "If you encounter any issues, please check the troubleshooting section in the documentation."