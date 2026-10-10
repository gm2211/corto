# Corto
As if Corto Maltese was sailing your RC boat, except, you know, it's software

<img alt="corto"  style="border: 5px solid #333;  border-radius: 10px;" src="corto.png"/>

## Overview

Corto is an autonomous sailing boat project that can be controlled remotely or operate autonomously. The system consists of two main components:

1. **Boat**: The autonomous sailing boat that runs the main Corto code
2. **Controller/Transmitter**: A remote control device that allows manual control of the boat

Both components run on Raspberry Pi devices and communicate with each other via LoRa radio.

## Documentation

- [Raspberry Pi Setup Guide](RASPBERRY_PI_SETUP.md): Instructions for setting up and running the Corto boat and controller code on Raspberry Pi devices
- [Platform Compatibility](PLATFORM_COMPATIBILITY.md): Information about how the project handles platform-specific dependencies and provides guidance for development on different platforms

## Try the simulator

You do not need a boat to try the navigation code. The simulator sails a course of marks with the boat's own `Navigator` and shows what it is doing: heading-up wind dial, rudder and sheet bars, wake, and a map with seamarks.

<img alt="The Corto simulator rounding two marks under the Navigator" src="docs/simulator/simulator-demo.gif" width="720"/>

```bash
pip install flask ultraimport
python src/main/python/app/app.py --port 5000
# then open http://127.0.0.1:5000/?demo=1&warp=15
```

The simulator lives on the [`gm/simulator`](https://github.com/gm2211/corto/tree/gm/simulator) branch (it is not on `develop` yet). See [its README](src/main/python/simulator/README.md) for the controls, the physics model and the API. It does not tack yet: upwind legs are flagged, not sailed.

## Getting Started

To get started with Corto:

1. Follow the [Raspberry Pi Setup Guide](RASPBERRY_PI_SETUP.md) to set up the boat and controller
2. For development on non-Raspberry Pi platforms, see the [Platform Compatibility](PLATFORM_COMPATIBILITY.md) guide
