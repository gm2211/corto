"""Flask web application for controlling and monitoring a boat simulator."""

import threading
import time
import ultraimport
from flask import Flask, render_template, jsonify, request

# Using ultraimport for importing modules relative to this file's location
(
    initialize_simulator,
    update_app_boat_state,
    process_control_command
) = ultraimport("__dir__/../simulator/simulator_integration.py", [
    "initialize_simulator",
    "update_app_boat_state",
    "process_control_command"
])

app = Flask(__name__)


class BoatController:
    """Controller class to manage boat state and simulator interactions."""

    def __init__(self):
        """Initialize the boat controller with simulator and initial state."""
        self.simulator = initialize_simulator()
        self.boat_state = {
            "lat": 40.7450,  # New York Harbor coordinates (in main shipping channel)
            "lng": -74.0150,
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
        self.simulator.set_environmental_factors(
            self.boat_state["wind_speed"],
            self.boat_state["wind_direction"],
            self.boat_state["current_speed"],
            self.boat_state["current_direction"]
        )

    def get_state(self):
        """Get a copy of the current boat state."""
        return self.boat_state.copy()

    def update_state_from_simulator(self):
        """Update boat state from simulator."""
        self.boat_state = update_app_boat_state(self.boat_state, self.simulator)

    def process_command(self, command, value):
        """Process a control command and update state if needed."""
        print(f"Processing command: {command}, Value: {value}")

        # Pass the command to the simulator
        process_control_command(command, value, self.simulator)

        # For environmental factor updates, update the local boat_state as well
        if command == 'set_environment':
            if isinstance(value, dict):
                # Create a copy to modify
                updated_state = self.boat_state.copy()
                for key, val in value.items():
                    if key in updated_state:
                        updated_state[key] = val

                # Update the state
                self.boat_state = updated_state

                # Update the simulator with the new environmental factors
                self.simulator.set_environmental_factors(
                    self.boat_state["wind_speed"],
                    self.boat_state["wind_direction"],
                    self.boat_state["current_speed"],
                    self.boat_state["current_direction"]
                )


# Initialize the boat controller
boat_controller = BoatController()


# Start a background thread to periodically update the boat state from the simulator
def update_boat_state_thread():
    """Background thread to continuously update boat state from simulator."""
    while True:
        boat_controller.update_state_from_simulator()
        time.sleep(0.1)  # Update 10 times per second


update_thread = threading.Thread(target=update_boat_state_thread)
update_thread.daemon = True
update_thread.start()


def get_boat_state():
    """Get the current state of the boat."""
    return boat_controller.get_state()


def update_boat_state(command, value):
    """Update the boat state based on control inputs by passing them to the simulator."""
    boat_controller.process_command(command, value)
    # The boat state will be updated by the background thread


@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')


@app.route('/api/boat-location')
def boat_location():
    """API endpoint to get current boat location and state."""
    return jsonify(get_boat_state())


@app.route('/api/control', methods=['POST'])
def control():
    """API endpoint to process boat control commands."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400

    command = data.get('command')
    value = data.get('value')

    update_boat_state(command, value)
    print(f"Received command: {command} with value: {value}")
    print(f"Updated boat state: {get_boat_state()}")

    return jsonify({"status": "success", "message": f"Command {command} executed"})


if __name__ == '__main__':
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Corto boat simulator app')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the app on')
    args = parser.parse_args()

    app.run(debug=True, port=args.port)
