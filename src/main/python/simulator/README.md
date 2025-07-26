# Corto Boat Simulator

This simulator allows you to visualize and test the behavior of the Corto boat control system in a simulated environment. It provides a web-based UI for controlling the boat and visualizing its behavior based on environmental factors like wind and current.

## Features

- Real-time visualization of boat position, heading, and movement
- Controls for rudder, sails, and motor throttle
- Simulated environmental factors (wind speed/direction, current speed/direction)
- Visual indicators for wind and current on the map
- Real-time telemetry display

## Architecture

The simulator consists of several components:

1. **Simulator Core** (`simulator.py`): Implements the physics model and simulated sensors
   - Simulated sensors (WindVane, GPSLocator)
   - Simulated controllers (ServosController)
   - Physics model for boat movement
   - Background thread for continuous simulation

2. **Integration Layer** (`simulator_integration.py`): Connects the simulator to the Flask app
   - Initializes the simulator
   - Updates the boat state based on simulator output
   - Passes UI controls to the simulator

3. **Web UI** (`app.py` and `templates/index.html`): Provides the user interface
   - Interactive map for visualization
   - Control panel for boat controls
   - Environmental controls for wind and current
   - Real-time telemetry display

## How It Works

1. The simulator runs in a background thread, continuously updating the boat's state based on:
   - Control inputs (rudder, sails, throttle)
   - Environmental factors (wind, current)
   - Physics calculations (speed, heading, position)

2. The Flask app periodically fetches the boat's state from the simulator and updates the UI.

3. User inputs from the UI are sent to the simulator via API calls, which then affect the boat's behavior.

## Physics Model

The simulator includes a simplified physics model that accounts for:

- Wind effects on sail propulsion (best speed at ~120° apparent wind angle)
- Rudder effects on turning rate (more speed = more responsive turning)
- Drift due to rudder angle and speed
- Current effects on actual movement
- Motor propulsion

## How to Use

1. Start the Flask app:
   ```
   python src/main/python/app/app.py
   ```

2. Open a web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Use the controls in the UI:
   - **Rudder**: Controls the boat's turning (-100% to 100%)
   - **Sails**: Controls the sail trim (0% to 100%)
   - **Throttle**: Controls the motor (-100% to 100%)
   - **Emergency Stop**: Resets all controls to zero

4. Set environmental factors:
   - **Wind Speed**: 0-30 knots
   - **Wind Direction**: 0-359 degrees
   - **Current Speed**: 0-5 knots
   - **Current Direction**: 0-359 degrees
   - Click **Apply Environment** to update the simulation

5. Observe the boat's behavior on the map and in the telemetry display.

## Extending the Simulator

To extend the simulator with additional features:

1. **Add new sensors**: Create new simulated sensor classes in `simulator.py`
2. **Enhance the physics model**: Modify the `_update_physics` method in `BoatPhysicsSimulator`
3. **Add new UI controls**: Update the HTML template and add corresponding JavaScript handlers
4. **Add new environmental factors**: Add new parameters to `set_environmental_factors` and update the physics calculations

## Limitations

- The physics model is simplified and does not account for all real-world factors
- Earth's curvature is not considered in position calculations
- Wind and current are uniform across the entire map
- No obstacles or landmasses are considered in the simulation