from typing import Dict, Any, Optional, NamedTuple
import threading
import time
import math

# Import dataclasses from api.objects
from ..api.objects.units.angle import Angle
from ..api.objects.units.percent import Percent
from ..api.objects.units.gps_coord import GPSCoord
from ..api.objects.units.speed import Speed
from ..api.objects.units.rudder_position import RudderPosition as OriginalRudderPosition
from ..api.objects.nav_params.boat_attitude import BoatAttitude as OriginalBoatAttitude
from ..api.objects.nav_params.nav_params import NavParams


# Adapter class for RudderPosition to match the simulator's expectations
class RudderPosition:
    """
    Adapter class for RudderPosition that matches the behavior expected by the simulator.
    The original RudderPosition uses a 0-100 scale where 50 is center, 0 is full left, and 100 is full right.
    The simulator expects a 0-100 scale where 0 is center, and the direction is determined by the method used.
    """

    def __init__(self, percent: Percent):
        self.percent = percent

    @staticmethod
    def left(percent: Percent):
        """Create a left rudder position with the given percentage (0-100)"""
        return RudderPosition(percent)

    @staticmethod
    def right(percent: Percent):
        """Create a right rudder position with the given percentage (0-100)"""
        return RudderPosition(percent)

    @staticmethod
    def center():
        """Create a center rudder position"""
        return RudderPosition(Percent(0))

    def __eq__(self, other):
        return self.percent == other.percent

    def to_original(self):
        """Convert to the original RudderPosition format"""
        # This would need to implement the conversion logic
        # For now, just return a center position
        return OriginalRudderPosition.center()


# Adapter class for BoatAttitude to match the simulator's expectations
class BoatAttitude:
    """
    Adapter class for BoatAttitude that matches the behavior expected by the simulator.
    The original BoatAttitude is a NamedTuple, but the simulator expects a regular class.
    """

    def __init__(self, rudder_position: RudderPosition, sail_trim: Percent):
        self.rudder_position = rudder_position
        self.sail_trim = sail_trim

    def __eq__(self, other):
        return (self.rudder_position == other.rudder_position and
                self.sail_trim == other.sail_trim)

    def to_original(self):
        """Convert to the original BoatAttitude format"""
        return OriginalBoatAttitude(
            rudder_position=self.rudder_position.to_original(),
            sail_trim=self.sail_trim
        )


class SimulatedSensor:
    """Base class for simulated sensors"""

    def __init__(self):
        self._lock = threading.Lock()

    def set_value(self, value):
        with self._lock:
            self._value = value

    def get_value(self):
        with self._lock:
            return self._value


class SimulatedWindVane(SimulatedSensor):
    """Simulated wind vane sensor"""

    def __init__(self, initial_wind_angle: float = 45.0):
        super().__init__()
        self._value = Angle(initial_wind_angle)

    def get_true_wind(self) -> Angle:
        return self.get_value()


class SimulatedGPSLocator(SimulatedSensor):
    """Simulated GPS locator sensor"""

    def __init__(self, initial_lat: float = 43.7696, initial_lon: float = -70.2544):
        super().__init__()
        self._location = GPSCoord(initial_lat, initial_lon)
        self._heading = Angle(0.0)
        self._speed = Speed(0.0)

    def set_location(self, lat: float, lon: float):
        self._location = GPSCoord(lat, lon)

    def set_heading(self, heading: float):
        self._heading = Angle(heading)

    def set_speed(self, speed: float):
        self._speed = Speed(speed)

    def cur_location(self) -> GPSCoord:
        return self._location

    def cur_heading(self) -> Angle:
        return self._heading

    def cur_speed_over_ground(self) -> Speed:
        return self._speed

    def cur_course_over_ground(self) -> Angle:
        # In a simple simulation, course over ground is the same as heading
        return self._heading


class SimulatedServosController:
    """Simulated servos controller"""

    def __init__(self):
        self.servo_1_position = Percent(0)  # Sail trim
        self.servo_2_position = Percent(0)  # Rudder position
        self.motor_throttle = Percent(0)
        self._callbacks = []

    def register_callback(self, callback):
        """Register a callback to be called when servo positions change"""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        """Notify all callbacks of servo position changes"""
        for callback in self._callbacks:
            callback(self.servo_1_position, self.servo_2_position, self.motor_throttle)

    def set_servo_1(self, position: Percent):
        """Set sail trim servo position"""
        self.servo_1_position = position
        self._notify_callbacks()

    def set_servo_2(self, position: Percent):
        """Set rudder servo position"""
        self.servo_2_position = position
        self._notify_callbacks()

    def set_motor_throttle(self, throttle: Percent):
        """Set motor throttle"""
        self.motor_throttle = throttle
        self._notify_callbacks()

    def reset_servos(self):
        """Reset all servos to center position"""
        self.set_servo_1(Percent(0))
        self.set_servo_2(Percent(0))
        self.set_motor_throttle(Percent(0))


class SimulatedNavParamsRecorder:
    """Simulated navigation parameters recorder"""

    def __init__(self, initial_params: Optional[NavParams] = None):
        if initial_params is None:
            self._nav_params = NavParams(
                heading=Angle(0.0),
                rudder_position=Percent(0),
                position=GPSCoord(43.7696, -70.2544),
                motor_throttle=Percent(0),
                speed_over_water=Speed(0.0),
                true_wind_angle=Angle(45.0),
                sail_trim=Percent(0)
            )
        else:
            self._nav_params = initial_params

    def get_cur_nav_params(self) -> NavParams:
        return self._nav_params

    def record_heading(self, heading: Angle):
        self._nav_params = self._nav_params._replace(heading=heading)

    def record_rudder_position(self, position: Percent):
        self._nav_params = self._nav_params._replace(rudder_position=position)

    def record_position(self, position: GPSCoord):
        self._nav_params = self._nav_params._replace(position=position)

    def record_motor_throttle(self, throttle: Percent):
        self._nav_params = self._nav_params._replace(motor_throttle=throttle)

    def record_speed_over_water(self, speed: Speed):
        self._nav_params = self._nav_params._replace(speed_over_water=speed)

    def record_true_wind_angle(self, angle: Angle):
        self._nav_params = self._nav_params._replace(true_wind_angle=angle)

    def record_sail_trim(self, trim: Percent):
        self._nav_params = self._nav_params._replace(sail_trim=trim)


class BoatPhysicsSimulator:
    """Simulates boat physics based on control inputs and environmental factors"""

    def __init__(
            self,
            gps_locator: SimulatedGPSLocator,
            wind_vane: SimulatedWindVane,
            nav_params_recorder: SimulatedNavParamsRecorder,
            servos_controller: SimulatedServosController
            ):
        self.gps_locator = gps_locator
        self.wind_vane = wind_vane
        self.nav_params_recorder = nav_params_recorder
        self.servos_controller = servos_controller

        # Environmental factors
        self.wind_speed = 10.0  # knots
        self.wind_direction = 45.0  # degrees
        self.current_speed = 0.0  # knots
        self.current_direction = 90.0  # degrees

        # Register callback for servo position changes
        self.servos_controller.register_callback(self._on_servo_change)

        # Start simulation thread
        self._running = True
        self._thread = threading.Thread(target=self._simulation_loop)
        self._thread.daemon = True
        self._thread.start()

    def _on_servo_change(self, sail_trim: Percent, rudder_position: Percent, motor_throttle: Percent):
        """Called when servo positions change"""
        # Update nav params recorder
        self.nav_params_recorder.record_sail_trim(sail_trim)
        self.nav_params_recorder.record_rudder_position(rudder_position)
        self.nav_params_recorder.record_motor_throttle(motor_throttle)

    def set_environmental_factors(
            self, wind_speed: float, wind_direction: float,
            current_speed: float, current_direction: float
            ):
        """Set environmental factors for simulation"""
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
        self.current_speed = current_speed
        self.current_direction = current_direction

        # Update wind vane with new wind direction
        self.wind_vane.set_value(Angle(wind_direction))

    def _simulation_loop(self):
        """Main simulation loop"""
        last_time = time.time()

        while self._running:
            # Calculate time delta
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            # Get current state
            nav_params = self.nav_params_recorder.get_cur_nav_params()

            # Calculate physics
            self._update_physics(nav_params, dt)

            # Sleep to maintain reasonable CPU usage
            time.sleep(0.1)

    def _update_physics(self, nav_params: NavParams, dt: float):
        """Update physics based on current state and time delta"""
        # Get control inputs
        rudder_position = nav_params.rudder_position.value
        sail_trim = nav_params.sail_trim.value
        motor_throttle = nav_params.motor_throttle.value

        # Current position and heading
        current_position = nav_params.position
        current_heading = nav_params.heading.degrees
        current_speed = nav_params.speed_over_water.knots

        # Calculate turn rate based on rudder position and speed
        # More speed = more responsive turning
        turn_rate = (rudder_position / 100.0) * (current_speed / 5.0) * 30.0  # degrees per second

        # Update heading based on turn rate
        new_heading = (current_heading + turn_rate * dt) % 360

        # Calculate apparent wind angle
        apparent_wind_angle = (self.wind_direction - current_heading) % 360

        # Calculate speed based on sail trim, wind speed, and apparent wind angle
        # Best speed at ~120° apparent wind
        wind_efficiency = abs(
            max(
                0,
                min(
                    1,
                    1.0 - abs(apparent_wind_angle - 120) / 120.0
                    )
                )
        )

        sail_efficiency = sail_trim / 100.0
        wind_speed_contribution = self.wind_speed * wind_efficiency * sail_efficiency * 0.4

        # Add motor contribution
        motor_speed_contribution = abs(motor_throttle) / 100.0 * 5.0  # max 5 knots from motor

        # Calculate new speed
        new_speed = wind_speed_contribution + motor_speed_contribution

        # Calculate drift angle based on speed and rudder
        # More speed or rudder = more drift, max ~15 degrees
        drift_angle = (rudder_position / 100.0) * (new_speed / 10.0) * 15.0

        # Calculate actual movement direction (heading + drift)
        movement_angle = (current_heading + drift_angle) % 360

        # Convert to radians for math
        movement_rad = movement_angle * 3.14159 / 180
        current_rad = self.current_direction * 3.14159 / 180

        # Calculate movement components
        boat_x = new_speed * math.sin(movement_rad)
        boat_y = new_speed * math.cos(movement_rad)
        current_x = self.current_speed * math.sin(current_rad)
        current_y = self.current_speed * math.cos(current_rad)

        # Combine boat movement and current
        total_x = boat_x + current_x
        total_y = boat_y + current_y

        # Update position (simplified - not accounting for Earth's curvature)
        # Scale factor to make movement visible
        scale = 0.0001 * dt
        new_lat = current_position.lat + total_y * scale
        new_lon = current_position.lon + total_x * scale

        # Update simulated sensors and recorder
        self.gps_locator.set_location(new_lat, new_lon)
        self.gps_locator.set_heading(new_heading)
        self.gps_locator.set_speed(new_speed)

        self.nav_params_recorder.record_heading(Angle(new_heading))
        self.nav_params_recorder.record_position(GPSCoord(new_lat, new_lon))
        self.nav_params_recorder.record_speed_over_water(Speed(new_speed))

    def stop(self):
        """Stop the simulation"""
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)


# Singleton instance for global access
_simulator_instance = None


def get_simulator():
    """Get the global simulator instance"""
    global _simulator_instance
    if _simulator_instance is None:
        # Create simulated components
        gps_locator = SimulatedGPSLocator()
        wind_vane = SimulatedWindVane()
        nav_params_recorder = SimulatedNavParamsRecorder()
        servos_controller = SimulatedServosController()

        # Create simulator
        _simulator_instance = BoatPhysicsSimulator(
            gps_locator=gps_locator,
            wind_vane=wind_vane,
            nav_params_recorder=nav_params_recorder,
            servos_controller=servos_controller
        )

    return _simulator_instance
