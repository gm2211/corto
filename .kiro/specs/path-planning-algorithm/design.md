# Path Planning Algorithm Design Document

## Overview

The Path Planning Algorithm extends the existing Navigator system with intelligent tacking strategies for upwind sailing. It uses velocity made good (VMG) optimization and sailing polar data to calculate efficient routes when the destination lies within the boat's no-go zone. The algorithm integrates seamlessly with the current navigation system while providing advanced routing capabilities.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Enhanced Navigator                        │
├─────────────────────────────────────────────────────────────┤
│  Navigator (existing)                                       │
│  ├── compute_boat_attitude() [enhanced]                     │
│  └── Direct navigation logic [preserved]                    │
├─────────────────────────────────────────────────────────────┤
│  Path Planning System [NEW]                                 │
│  ├── PathPlanner                                           │
│  ├── TackingStrategy                                        │
│  ├── SailingPolar                                          │
│  └── RouteOptimizer                                         │
├─────────────────────────────────────────────────────────────┤
│  Waypoint Management [NEW]                                  │
│  ├── WaypointSequence                                      │
│  ├── WaypointTracker                                       │
│  └── ProgressMonitor                                       │
└─────────────────────────────────────────────────────────────┘
```

### Integration Flow

```
Navigator.compute_boat_attitude(dest)
    ↓
PathPlanner.needs_path_planning(current_pos, dest, wind)
    ↓ (if true)
PathPlanner.calculate_route(current_pos, dest, wind_conditions)
    ↓
TackingStrategy.generate_waypoints()
    ↓
WaypointTracker.get_current_target()
    ↓
Navigator.compute_boat_attitude(current_waypoint)
```

## Components and Interfaces

### 1. PathPlanner (Main Coordinator)

**Purpose:** Central component that determines when path planning is needed and coordinates route calculation.

**Key Methods:**
```python
def needs_path_planning(current_pos: GPSCoord, dest: GPSCoord, wind_direction: Angle) -> bool:
    """Determine if destination is in no-go zone requiring tacking"""

def calculate_route(current_pos: GPSCoord, dest: GPSCoord, wind_conditions: WindConditions) -> Route:
    """Generate optimal tacking route using sailing performance data"""

def update_route(current_pos: GPSCoord, wind_conditions: WindConditions) -> Route:
    """Recalculate route when conditions change significantly"""
```

**Integration Points:**
- Called by Navigator.compute_boat_attitude() before direct navigation
- Uses existing wind data from WindVane
- Returns waypoints compatible with existing GPSCoord system

### 2. TackingStrategy (Route Generation)

**Purpose:** Generates optimal tacking patterns based on wind conditions and boat performance.

**Key Methods:**
```python
def calculate_optimal_tack_angle(wind_speed: float, wind_direction: Angle) -> Angle:
    """Determine best tacking angle for current conditions"""

def generate_tacking_waypoints(start: GPSCoord, dest: GPSCoord, wind: WindConditions) -> List[Waypoint]:
    """Create sequence of tacking waypoints"""

def calculate_vmg_optimized_route(start: GPSCoord, dest: GPSCoord, polar: SailingPolar) -> List[Waypoint]:
    """Optimize route for velocity made good toward destination"""
```

**Algorithm Approach:**
- **Upwind Strategy:** Calculate optimal tacking angles (typically 45-60° from wind)
- **VMG Optimization:** Balance boat speed vs. progress toward destination
- **Adaptive Legs:** Adjust tacking leg lengths based on distance to destination
- **Wind Shift Handling:** Recalculate when wind changes exceed thresholds

### 3. SailingPolar (Performance Model)

**Purpose:** Encapsulates boat performance characteristics for different wind conditions.

**Key Methods:**
```python
def get_boat_speed(wind_angle: Angle, wind_speed: float) -> float:
    """Return expected boat speed for given wind conditions"""

def get_optimal_wind_angle(wind_speed: float) -> Angle:
    """Return wind angle for maximum VMG upwind"""

def is_in_no_go_zone(wind_angle: Angle) -> bool:
    """Check if wind angle is too close to wind for effective sailing"""
```

**Default Polar Data:**
```python
# Conservative sailing polar for typical small sailboat
DEFAULT_POLAR = {
    # wind_angle: (efficiency_factor, max_speed_factor)
    45: (0.7, 0.8),   # Close hauled - reduced efficiency
    60: (0.9, 1.0),   # Optimal upwind angle
    90: (1.0, 1.2),   # Beam reach - maximum speed
    135: (0.8, 1.0),  # Broad reach
    180: (0.6, 0.7)   # Running - reduced efficiency
}
```

### 4. WaypointTracker (Navigation State)

**Purpose:** Manages current waypoint sequence and tracks navigation progress.

**Key Methods:**
```python
def set_route(route: Route) -> None:
    """Set new waypoint sequence"""

def get_current_waypoint() -> Waypoint:
    """Return current navigation target"""

def advance_to_next_waypoint(current_pos: GPSCoord) -> bool:
    """Check if current waypoint is reached and advance sequence"""

def get_progress() -> float:
    """Return completion percentage of overall route"""
```

**Waypoint Advancement Logic:**
- Advance when within 50m of current waypoint
- Handle waypoint skipping for efficiency
- Provide smooth transitions between waypoints

## Data Models

### Core Data Structures

```python
@dataclass
class WindConditions:
    speed: float  # knots
    direction: Angle  # true wind direction
    timestamp: datetime

@dataclass
class Waypoint:
    position: GPSCoord
    approach_heading: Angle  # Optimal heading to reach this waypoint
    leg_distance: float  # Distance from previous waypoint
    tack_side: TackSide  # PORT or STARBOARD

@dataclass
class Route:
    waypoints: List[Waypoint]
    total_distance: float
    estimated_time: float
    wind_conditions: WindConditions

@dataclass
class TackingLeg:
    start_pos: GPSCoord
    end_pos: GPSCoord
    heading: Angle
    distance: float
    estimated_speed: float

enum TackSide:
    PORT = "port"
    STARBOARD = "starboard"
```

### Configuration Data

```python
@dataclass
class PathPlanningConfig:
    min_tack_angle: float = 45.0  # Minimum angle from wind
    max_tack_angle: float = 60.0  # Maximum angle from wind
    waypoint_radius: float = 50.0  # Meters - waypoint reached threshold
    wind_shift_threshold: float = 15.0  # Degrees - recalculation trigger
    wind_speed_threshold: float = 5.0  # Knots - recalculation trigger
    max_leg_distance: float = 1000.0  # Meters - maximum tacking leg length
    vmg_weight: float = 0.8  # Balance between speed and progress (0-1)
```

## Algorithm Details

### 1. No-Go Zone Detection

```python
def is_destination_upwind(current_pos: GPSCoord, dest: GPSCoord, wind_direction: Angle) -> bool:
    bearing_to_dest = calculate_bearing(current_pos, dest)
    wind_angle_diff = abs(normalize_angle_difference(bearing_to_dest, wind_direction))
    return wind_angle_diff < MIN_TACK_ANGLE
```

### 2. Optimal Tacking Angle Calculation

**VMG Optimization Formula:**
```
VMG = boat_speed * cos(wind_angle)
optimal_angle = argmax(VMG) for wind_angle in [min_tack_angle, max_tack_angle]
```

**Implementation:**
```python
def calculate_optimal_tack_angle(wind_speed: float) -> Angle:
    best_vmg = 0
    best_angle = MIN_TACK_ANGLE
    
    for angle in range(MIN_TACK_ANGLE, MAX_TACK_ANGLE + 1):
        boat_speed = sailing_polar.get_boat_speed(Angle(angle), wind_speed)
        vmg = boat_speed * math.cos(math.radians(angle))
        
        if vmg > best_vmg:
            best_vmg = vmg
            best_angle = angle
    
    return Angle(best_angle)
```

### 3. Waypoint Generation Strategy

**Symmetric Tacking Pattern:**
1. Calculate optimal tacking angle for current wind conditions
2. Generate alternating port/starboard tacks toward destination
3. Adjust final approach to arrive at destination on optimal heading
4. Limit individual leg lengths to maintain responsiveness to wind changes

**Adaptive Leg Length:**
```python
def calculate_leg_length(distance_to_dest: float, wind_conditions: WindConditions) -> float:
    base_length = min(distance_to_dest * 0.3, MAX_LEG_DISTANCE)
    
    # Shorter legs in variable wind conditions
    if wind_conditions.is_variable():
        base_length *= 0.7
    
    # Longer legs in stable conditions far from destination
    if distance_to_dest > 2000 and wind_conditions.is_stable():
        base_length *= 1.3
    
    return base_length
```

## Error Handling

### Wind Condition Errors
- **Insufficient Wind:** Recommend motor assistance or waiting
- **Excessive Wind:** Use conservative tacking angles and shorter legs
- **Variable Wind:** Increase recalculation frequency and reduce leg lengths

### Navigation Errors
- **GPS Accuracy:** Use larger waypoint radius in poor GPS conditions
- **Sensor Failures:** Fallback to direct navigation mode
- **Route Calculation Failures:** Provide simplified direct route with warnings

### Performance Degradation
- **Calculation Timeout:** Use cached route with periodic updates
- **Memory Constraints:** Limit waypoint sequence length
- **Processing Load:** Reduce recalculation frequency under high load

## Testing Strategy

### Unit Testing
- **Tacking Angle Calculation:** Verify VMG optimization across wind conditions
- **Waypoint Generation:** Test symmetric tacking patterns and leg lengths
- **No-Go Zone Detection:** Validate upwind destination identification
- **Route Optimization:** Test distance and time calculations

### Integration Testing
- **Navigator Integration:** Verify seamless fallback to direct navigation
- **Wind Data Integration:** Test with real wind sensor data
- **Waypoint Tracking:** Validate waypoint advancement and progress tracking

### Performance Testing
- **Route Calculation Speed:** Ensure real-time performance for route updates
- **Memory Usage:** Test with long routes and extended operation
- **Accuracy Validation:** Compare planned vs. actual sailing performance

### Simulation Testing
- **Various Wind Conditions:** Test across different wind speeds and directions
- **Complex Scenarios:** Multi-tack routes with wind shifts
- **Edge Cases:** Very close destinations, extreme wind angles, GPS errors

## Implementation Notes

### Integration with Existing System
- Minimal changes to Navigator.compute_boat_attitude()
- Preserve all existing functionality as fallback
- Use existing data structures (GPSCoord, Angle, etc.)
- Maintain compatibility with current command/control system

### Performance Considerations
- Cache route calculations to avoid repeated computation
- Use incremental updates when wind conditions change slightly
- Limit waypoint sequence length to manage memory usage
- Implement lazy evaluation for complex route optimizations

### Configuration and Tuning
- Expose key parameters for boat-specific tuning
- Provide different polar configurations for various boat types
- Allow runtime adjustment of tacking aggressiveness
- Support custom no-go zone definitions

This design provides a comprehensive foundation for intelligent path planning that enhances the existing navigation system while maintaining full backward compatibility and robust error handling.