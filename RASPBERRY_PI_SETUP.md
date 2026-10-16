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

## Running the Web App on the Controller

The web app shows the boat on a map with its instruments and lets you steer it and send it marks. It runs on the controller Pi, the one with the LoRa radio bonnet, and talks to the boat over the same radio.

1. Both Pis must run this version of the code. The radio driver (`lora/radio.py`) now keeps listening after it sends; before that fix the controller never heard the boat's reply, and the boat stopped listening after its first one.
2. Install the Flask dependencies if the controller's environment does not have them: `pip install flask ultraimport` (or `poetry install`).
3. Start the boat as usual (`src/main/python/boat/run.sh`), then on the controller, from the repo root:
   ```bash
   PYTHONPATH=src/main/python python src/main/python/app/app.py --source boat --host 0.0.0.0 --port 5000
   ```
   and open `http://<the controller's address>:5000` from a laptop or phone on the same network.
4. Only one program can use the radio at a time, so **the app replaces `transmitter/run.sh` (the knobs) while it runs**. Stop one before starting the other.
5. The app has no login: anyone who can reach the address can drive the boat. Bind `0.0.0.0` only on a network you trust (or leave the default `127.0.0.1` and tunnel in with SSH).

Options: `--source {auto,boat,sim}` (default `auto`: the boat if the radio libraries are there and the radio opens, else the simulator, and it says which), `--radio {lora,loopback,silent}` (boat only: `loopback` is a simulated boat behind a fake radio, `silent` never answers), `--poll-interval SECONDS` (default 2), `--host`, `--port`.

### What you should see

* The app asks the boat for telemetry every 2 seconds. The indicator at the top right is **Live** while the last report is at most 5 seconds old, shows its age in amber (for example "12 s ago") up to 20 seconds, and **No link** in red after that, with a banner. **Connecting…** is the first 20 seconds before the first report. The map keeps the last known position, faded.
* The boat currently reports placeholder GPS (0, 0): there is no GPS driver yet. The app shows **No GPS fix** and hides the boat on the map until a position arrives. Heading, wind, speed and rudder are shown as the boat reports them; today the wind vane and speed sensor are not wired either, so expect zeros.
* The rudder, sheet and motor sliders send `R`, `S` and `TR` commands (whole percents). **Stop** sends rudder centre, sheet 0 and motor 0, and stops sending the course. There are no acknowledgements, so commands are best effort. The boat's main loop (`Corto.run_loop`) steers to its last destination (it starts at 0, 0) and overrides manual rudder commands whenever its navigator's attitude changes.
* The **Course** tab keeps the marks in the app. **Send to boat** sends the active mark as a destination (`D<lat>,<lon>`, repeated every 10 seconds) and moves to the next one when the boat reports being within 15 m. The boat has no command to clear its destination, so after Stop or Clear it keeps steering to the last one it was given.
* Not available with the real boat, so hidden: manual/autopilot mode, auto-trim, time warp, wind and current, Reset and the demo course. The API answers 409 for them.

Bench test before the first sail (not part of the automated tests): both Pis on this commit; **Live** within about 2 seconds of starting the app; a rudder slider move turns the servo; power the boat off and the indicator turns amber after 5 seconds and **No link** after 20. The rudder servo's direction (which way a given `RudderPosition` moves it) still needs checking on the bench, and the map needs internet for its tiles (Leaflet and OpenStreetMap load from the web).

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