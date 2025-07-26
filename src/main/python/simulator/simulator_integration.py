"""
Integration module to connect the simulator with the Flask app.
This module provides functions to:
1. Initialize the simulator
2. Update the boat state in app.py based on simulator output
3. Pass UI controls to the simulator
"""

from ..api.objects.units.percent import Percent
from .simulator import get_simulator


# Dictionary to map app.py boat_state to simulator parameters
def initialize_simulator():
    """Initialize the simulator and return the simulator instance"""
    simulator = get_simulator()
    return simulator


def update_app_boat_state(boat_state, simulator):
    """Update the app's boat_state dictionary based on simulator output"""
    # Get the current navigation parameters from the simulator
    nav_params = simulator.nav_params_recorder.get_cur_nav_params()

    # Update boat_state with values from the simulator
    boat_state['lat'] = nav_params.position.lat
    boat_state['lng'] = nav_params.position.lon
    boat_state['heading'] = nav_params.heading.degrees
    boat_state['speed'] = nav_params.speed_over_water.knots
    boat_state['rudder_angle'] = nav_params.rudder_position.value
    boat_state['sail_position'] = nav_params.sail_trim.value
    boat_state['throttle'] = nav_params.motor_throttle.value

    # Calculate movement direction (heading + drift)
    # In a real implementation, this would come from the simulator
    drift_angle = (nav_params.rudder_position.value / 100.0) * (nav_params.speed_over_water.knots / 10.0) * 15.0
    boat_state['movement_direction'] = (nav_params.heading.degrees + drift_angle) % 360

    # Return the updated boat_state
    return boat_state


def process_control_command(command, value, simulator):
    """Process a control command from the UI and update the simulator"""
    servos_controller = simulator.servos_controller

    if command == 'rudder':
        # Convert from -100 to 100 scale to 0 to 100 scale for Percent
        servos_controller.set_servo_2(Percent(abs(value)))
    elif command == 'sails':
        servos_controller.set_servo_1(Percent(value))
    elif command == 'throttle':
        servos_controller.set_motor_throttle(Percent(abs(value)))
    elif command == 'emergency_stop':
        servos_controller.reset_servos()
    elif command == 'set_environment':
        # Special command to set environmental factors
        # value should be a dictionary with wind_speed, wind_direction, current_speed, current_direction
        simulator.set_environmental_factors(
            value.get('wind_speed', 10.0),
            value.get('wind_direction', 45.0),
            value.get('current_speed', 0.0),
            value.get('current_direction', 90.0)
        )

    # Return success status
    return True
