from flask import Flask, render_template, jsonify, request
import threading
import time

# Import simulator integration
from ..simulator.simulator_integration import initialize_simulator, update_app_boat_state, process_control_command

app = Flask(__name__)

# Initialize the simulator
simulator = initialize_simulator()

# Boat state - initial values will be updated by the simulator
boat_state = {
    "lat": 43.7696,  # Portland, ME coordinates
    "lng": -70.2544,
    "heading": 0,  # Direction boat is pointing (degrees)
    "speed": 0,  # Speed through water (knots)
    "rudder_angle": 0,  # Rudder position (-100 to 100)
    "sail_position": 0,  # Sail position (0 to 100)
    "throttle": 0,  # Motor throttle (-100 to 100)
    "wind_speed": 10,  # Wind speed in knots
    "wind_direction": 45,  # Wind direction in degrees
    "current_speed": 0,  # Water current speed in knots
    "current_direction": 90,  # Water current direction in degrees
    "turn_rate": 0,  # Rate of turn in degrees per second
    "drift_angle": 0,  # Angle between heading and actual movement
    "movement_direction": 0  # Actual movement direction
}

# Set initial environmental factors in the simulator
simulator.set_environmental_factors(
    boat_state["wind_speed"],
    boat_state["wind_direction"],
    boat_state["current_speed"],
    boat_state["current_direction"]
)


# Start a background thread to periodically update the boat state from the simulator
def update_boat_state_thread():
    while True:
        global boat_state
        boat_state = update_app_boat_state(boat_state, simulator)
        time.sleep(0.1)  # Update 10 times per second


update_thread = threading.Thread(target=update_boat_state_thread)
update_thread.daemon = True
update_thread.start()


def get_boat_state():
    """Get the current state of the boat."""
    return boat_state.copy()


def update_boat_state(command, value):
    """Update the boat state based on control inputs by passing them to the simulator."""
    global boat_state

    print(f"Processing command: {command}, Value: {value}")

    # Pass the command to the simulator
    process_control_command(command, value, simulator)

    # For environmental factor updates, update the local boat_state as well
    if command == 'set_environment':
        if isinstance(value, dict):
            for key, val in value.items():
                if key in boat_state:
                    boat_state[key] = val

            # Update the simulator with the new environmental factors
            simulator.set_environmental_factors(
                boat_state["wind_speed"],
                boat_state["wind_direction"],
                boat_state["current_speed"],
                boat_state["current_direction"]
            )

    # The boat state will be updated by the background thread


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/boat-location')
def boat_location():
    return jsonify(get_boat_state())


@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    command = data.get('command')
    value = data.get('value')

    update_boat_state(command, value)
    print(f"Received command: {command} with value: {value}")
    print(f"Updated boat state: {boat_state}")

    return jsonify({"status": "success", "message": f"Command {command} executed"})


if __name__ == '__main__':
    app.run(debug=True)
