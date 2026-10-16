# Corto
As if Corto Maltese was sailing your RC boat, except, you know, it's software

<img alt="corto"  style="border: 5px solid #333;  border-radius: 10px;" src="corto.png"/>

## Overview

Corto is an autonomous sailing boat project that can be controlled remotely or operate autonomously. The system consists of two main components:

1. **Boat**: The autonomous sailing boat that runs the main Corto code
2. **Controller/Transmitter**: A remote control device that allows manual control of the boat, and runs the web app that shows the boat

Both components run on Raspberry Pi devices and communicate with each other via LoRa radio.

## Documentation

- [Raspberry Pi Setup Guide](RASPBERRY_PI_SETUP.md): Instructions for setting up and running the Corto boat and controller code on Raspberry Pi devices
- [Platform Compatibility](PLATFORM_COMPATIBILITY.md): Information about how the project handles platform-specific dependencies and provides guidance for development on different platforms

## The app

A web app that shows the real boat: where it is on a map, its heading, rudder, sheet and wind, and a link indicator that says how fresh the last report is. You can steer it from the browser (rudder, sheet, motor, Stop) and send it a course of marks. It runs on the controller Pi, the one with the LoRa radio, and asks the boat for telemetry every 2 seconds.

```bash
# on the controller Pi, from the repo root (see RASPBERRY_PI_SETUP.md for the setup)
PYTHONPATH=src/main/python python src/main/python/app/app.py --source boat --host 0.0.0.0 --port 5000
# then open http://<the Pi's address>:5000 from a laptop or phone on the same network
```

* `--source auto` (the default) uses the boat when the machine has the radio libraries and the radio opens, and the simulator otherwise. It says which on startup, and the header always names what you are looking at: **Boat · LoRa** or **Simulator**.
* Only one program can own the radio: the app replaces `boat_remote.py` (the knobs) while it runs.
* The app has no login. Bind `0.0.0.0` only on a network you trust.
* The boat currently reports placeholder GPS, so the map will say **No GPS fix** until a GPS driver exists. See [the setup guide](RASPBERRY_PI_SETUP.md#running-the-web-app-on-the-controller) for what the boat reports today and what is missing.

### Without a boat: the simulator (`--source sim`)

You do not need a boat to try the app or the navigation code. The simulator is a test bench: it sails a course of marks with the boat's own `Navigator` and shows what it is doing: heading-up wind dial, rudder and sheet bars, wake, and a map with seamarks. The header says **Simulator**, and the controls that only make sense there (time warp, wind and current, Reset, demo course, auto-trim, the Autopilot mode) appear only in this mode.

<img alt="The Corto app in simulator mode rounding two marks under the Navigator" src="docs/simulator/simulator-demo.gif" width="720"/>

```bash
pip install flask ultraimport
python src/main/python/app/app.py --source sim --port 5000
# then open http://127.0.0.1:5000/?demo=1&warp=15
```

`--source boat --radio loopback` runs the app against a simulated boat behind a fake radio, which is handy for developing the app without hardware; `--radio silent` never answers, to see the no-link states.

The simulator lives on the [`gm/simulator`](https://github.com/gm2211/corto/tree/gm/simulator) branch (it is not on `develop` yet). See [its README](src/main/python/simulator/README.md) for the controls, the physics model and the API. It does not tack yet: upwind legs are flagged, not sailed.

## Getting Started

To get started with Corto:

1. Follow the [Raspberry Pi Setup Guide](RASPBERRY_PI_SETUP.md) to set up the boat and controller
2. For development on non-Raspberry Pi platforms, see the [Platform Compatibility](PLATFORM_COMPATIBILITY.md) guide
