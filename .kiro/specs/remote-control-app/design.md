# Remote Control App Design Document

## Overview

The Remote Control App is a cross-platform desktop application built with Python and Tkinter that provides real-time boat monitoring, control, and simulation capabilities. The app communicates with the Corto boat system via LoRa radio and includes a comprehensive simulation engine for testing autopilot algorithms without physical hardware.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Remote Control App                        │
├─────────────────────────────────────────────────────────────┤
│  GUI Layer (Tkinter)                                        │
│  ├── Map Widget (tkintermapview)                            │
│  ├── Control Panels                                         │
│  └── Status Displays                                        │
├─────────────────────────────────────────────────────────────┤
│  Application Layer                                          │
│  ├── App Controller                                         │
│  ├── Mode Manager (Real/Simulation)                        │
│  └── Scenario Manager                                       │
├─────────────────────────────────────────────────────────────┤
│  Communication Layer                                        │
│  ├── LoRa Communication Manager                            │
│  └── Message Serialization                                 │
├─────────────────────────────────────────────────────────────┤
│  Simulation Engine                                          │
│  ├── Physics Simulator                                     │
│  ├── Environmental Model                                   │
│  └── Sensor Simulator                                      │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

**Real Mode:**
```
Remote App ←→ LoRa Radio ←→ Boat System
```

**Simulation Mode:**
```
Remote App → Simulation Engine → Mock Boat System → Remote App
```

## Components and Interfaces

### 1. Main Application Controller

**Purpose:** Central coordinator managing app state, mode switching, and component orchestration.

**Key Methods:**
- `start_application()`: Initialize GUI and communication systems
- `switch_mode(mode: AppMode)`: Toggle between real and simulation modes
- `update_display()`: Refresh all GUI components with latest data
- `handle_map_click(lat: float, lon: float)`: Process destination setting

### 2. LoRa Communication Manager

**Purpose:** Handle all radio communication with the boat system using existing protocol.

**Key Methods:**
- `connect()`: Establish LoRa connection
- `send_command(command: str)`: Transmit commands to boat
- `register_telemetry_callback(callback)`: Set up telemetry reception
- `request_telemetry()`: Poll boat for current status

**Protocol Integration:**
- Reuses existing command classes: `SetDestination`, `SendTelemetry`, etc.
- Maintains compatibility with boat's `CommandReceiver`
- Handles message serialization/deserialization

### 3. Map Visualization Component

**Purpose:** Interactive map display using tkintermapview library.

**Features:**
- Real-time boat position tracking
- Clickable destination setting
- Heading indicator
- Navigation path display
- Zoom and pan controls

**Key Methods:**
- `update_boat_position(lat: float, lon: float, heading: float)`
- `set_destination_marker(lat: float, lon: float)`
- `draw_navigation_path()`

### 4. Simulation Engine

**Purpose:** Comprehensive physics-based boat simulation for testing.

#### 4.1 Physics Simulator
**Responsibilities:**
- Boat dynamics calculation
- Wind interaction modeling
- Rudder and sail response simulation

**Key Methods:**
- `update_boat_state(dt: float)`: Advance simulation by time step
- `apply_wind_forces(wind_speed: float, wind_direction: float)`
- `calculate_apparent_wind()`: Compute apparent wind from true wind and boat motion

#### 4.2 Environmental Model
**Responsibilities:**
- Wind field simulation
- Water current effects
- Environmental parameter management

**Key Methods:**
- `set_wind_conditions(speed: float, direction: float)`
- `set_current_conditions(speed: float, direction: float)`
- `get_environmental_state()`: Return current conditions

#### 4.3 Sensor Simulator
**Responsibilities:**
- Generate realistic sensor data
- Add appropriate noise and delays
- Simulate sensor failures (optional)

**Key Methods:**
- `get_simulated_gps()`: Return GPS coordinates with realistic accuracy
- `get_simulated_wind_vane()`: Return wind direction with sensor characteristics
- `get_simulated_nav_params()`: Generate complete telemetry data

### 5. Scenario Management System

**Purpose:** Save, load, and manage simulation scenarios.

**Key Methods:**
- `save_scenario(name: str, scenario: SimulationScenario)`
- `load_scenario(name: str) -> SimulationScenario`
- `list_scenarios() -> List[str]`
- `delete_scenario(name: str)`

## Data Models

### Core Data Structures

```python
@dataclass
class AppState:
    mode: AppMode  # REAL or SIMULATION
    boat_position: GPSCoord
    boat_heading: Angle
    destination: Optional[GPSCoord]
    telemetry: NavParams
    connection_status: ConnectionStatus

@dataclass
class SimulationScenario:
    name: str
    wind_speed: float
    wind_direction: float
    current_speed: float
    current_direction: float
    initial_boat_position: GPSCoord
    initial_boat_heading: Angle

@dataclass
class EnvironmentalConditions:
    wind_speed: float  # knots
    wind_direction: float  # degrees
    current_speed: float  # knots
    current_direction: float  # degrees
```

### GUI State Management

```python
class GUIState:
    map_widget: TkinterMapView
    telemetry_panel: TelemetryPanel
    control_panel: ControlPanel
    simulation_panel: SimulationPanel
    status_bar: StatusBar
```

## Error Handling

### Communication Errors
- **Connection Loss:** Automatic reconnection attempts with exponential backoff
- **Message Corruption:** Checksum validation and retransmission
- **Timeout Handling:** Configurable timeout periods with user notification

### Simulation Errors
- **Invalid Parameters:** Input validation with user-friendly error messages
- **Physics Instability:** Simulation bounds checking and reset capabilities
- **Scenario Loading:** Graceful handling of corrupted scenario files

### GUI Errors
- **Map Loading:** Fallback to offline tiles or simplified display
- **Widget Failures:** Component isolation to prevent cascade failures

## Testing Strategy

### Unit Testing
- **Communication Layer:** Mock LoRa radio for protocol testing
- **Simulation Engine:** Physics calculation verification
- **Data Models:** Serialization/deserialization testing
- **Scenario Management:** File I/O and data persistence testing

### Integration Testing
- **Real Mode:** End-to-end communication with boat system
- **Simulation Mode:** Complete simulation workflow testing
- **Mode Switching:** State preservation during transitions

### User Interface Testing
- **Map Interaction:** Click handling and coordinate conversion
- **Control Responsiveness:** Real-time update verification
- **Error Display:** User notification system testing

### Performance Testing
- **Simulation Speed:** Real-time performance under various conditions
- **Memory Usage:** Long-running session stability
- **Communication Latency:** LoRa message timing analysis

## Implementation Notes

### Technology Stack
- **GUI Framework:** Tkinter (built-in Python GUI)
- **Map Component:** tkintermapview for interactive maps
- **LoRa Communication:** Reuse existing adafruit_rfm9x integration
- **Data Persistence:** JSON files for scenario storage
- **Physics Engine:** Custom implementation using numpy for calculations

### Development Phases
1. **Core GUI Structure:** Basic window layout and navigation
2. **Communication Integration:** LoRa protocol implementation
3. **Map Visualization:** Interactive map with boat tracking
4. **Simulation Engine:** Physics-based boat simulation
5. **Scenario Management:** Save/load functionality
6. **Polish and Testing:** Error handling and user experience improvements

### Platform Considerations
- **Cross-platform compatibility:** Tkinter works on Windows, macOS, and Linux
- **LoRa Hardware:** Requires compatible radio module on development machine
- **Map Tiles:** Internet connection needed for map data (with offline fallback)

This design provides a comprehensive foundation for building a professional remote control and simulation application that meets all specified requirements while maintaining compatibility with the existing Corto boat system.