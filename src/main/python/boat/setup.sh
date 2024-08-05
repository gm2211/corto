#!/bin/bash --
SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install python3-pip -y
if ! pyenv &> /dev/null
then
  curl https://pyenv.run | bash
  echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
  echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
  echo 'eval "$(pyenv init -)"' >> ~/.zshrc
  pyenv install 3.11.8
fi
pyenv virtualenv 3.11.8 corto
pyenv activate corto
curl -sSL https://install.python-poetry.org | python3 -
pip install --upgrade adafruit-blinka
pip install inventorhatmini
pip install RPi.GPIO
sudo raspi-config nonint do_i2c 0
pip install adafruit-circuitpython-busdevice
pip install adafruit-circuitpython-ssd1306
pip install adafruit-circuitpython-rfm9x
pip install --upgrade adafruit-python-shell click
sudo -E env PATH="$PATH" python3 "$SCRIPT_DIR/../utils/raspi-spi-reassign.py" --ce0=disabled --ce1=disabled
echo "If you still running into ce0 and ce1 issues, try running the following command:"
echo "sudo -E env PATH=$PATH python3 raspi-spi-reassign.py --ce0=5 --ce1=6"
sudo raspi-config nonint do_i2c 0
