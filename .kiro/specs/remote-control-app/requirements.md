# Requirements Document

## Introduction

A comprehensive remote control and visualization application for the Corto sailing boat system that provides real-time boat monitoring, destination setting, and simulation capabilities for testing autopilot performance under various environmental conditions.

## Glossary

- **Remote_Control_App**: The desktop/mobile application that communicates with the boat's control system
- **Boat_System**: The onboard Corto sailing boat control system running on Raspberry Pi
- **LoRa_Radio**: The long-range radio communication system between app and boat
- **Simulation_Mode**: Operating mode where environmental conditions are mocked for testing
- **Real_Mode**: Operating mode where the app connects to the actual boat hardware
- **Map_Visualization**: Interactive map display showing boat position, destination, and navigation data
- **Telemetry_Data**: Navigation parameters including position, heading, wind data, and control states
- **Environmental_Parameters**: Simulated conditions including wind direction, wind speed, and water current

## Requirements

### Requirement 1

**User Story:** As a boat operator, I want to view the boat's real-time position and status on an interactive map, so that I can monitor the boat's navigation and performance.

#### Acceptance Criteria

1. WHEN the Remote_Control_App connects to the Boat_System, THE Remote_Control_App SHALL display the boat's current GPS position on an interactive map
2. WHILE connected to the Boat_System, THE Remote_Control_App SHALL continuously update the boat's position, heading, and telemetry data every 2 seconds
3. THE Remote_Control_App SHALL display boat heading, rudder position, sail trim, speed over water, and true wind angle in real-time
4. THE Remote_Control_App SHALL maintain connection status indicators showing LoRa_Radio connectivity
5. IF connection to the Boat_System is lost, THEN THE Remote_Control_App SHALL display a disconnection warning and attempt automatic reconnection

### Requirement 2

**User Story:** As a boat operator, I want to set the boat's target destination by clicking on the map, so that the autopilot can navigate to the desired location.

#### Acceptance Criteria

1. WHEN the user clicks on the Map_Visualization, THE Remote_Control_App SHALL set that GPS coordinate as the target destination
2. THE Remote_Control_App SHALL transmit the destination coordinates to the Boat_System via LoRa_Radio within 1 second
3. THE Remote_Control_App SHALL display the target destination as a distinct marker on the Map_Visualization
4. THE Remote_Control_App SHALL draw a line connecting the boat's current position to the target destination
5. WHEN the destination is successfully set, THE Remote_Control_App SHALL display a confirmation message

### Requirement 3

**User Story:** As a developer, I want to run the app in simulation mode with configurable environmental conditions, so that I can test the autopilot's performance without needing the physical boat.

#### Acceptance Criteria

1. THE Remote_Control_App SHALL provide a simulation mode toggle that switches between Real_Mode and Simulation_Mode
2. WHILE in Simulation_Mode, THE Remote_Control_App SHALL allow setting wind direction between 0-360 degrees
3. WHILE in Simulation_Mode, THE Remote_Control_App SHALL allow setting wind speed between 0-50 knots
4. WHILE in Simulation_Mode, THE Remote_Control_App SHALL allow setting water current direction and speed
5. WHEN Environmental_Parameters are changed, THE Remote_Control_App SHALL update the simulated boat sensors within 0.5 seconds

### Requirement 4

**User Story:** As a developer, I want the simulation to provide realistic boat physics and sensor responses, so that I can accurately test autopilot algorithms.

#### Acceptance Criteria

1. WHILE in Simulation_Mode, THE Remote_Control_App SHALL simulate boat movement based on wind conditions, sail trim, and rudder position
2. THE Remote_Control_App SHALL calculate apparent wind angle based on boat heading, speed, and true wind conditions
3. THE Remote_Control_App SHALL simulate GPS position updates based on calculated boat velocity and heading
4. THE Remote_Control_App SHALL apply water current effects to the boat's ground track without affecting sensor readings
5. THE Remote_Control_App SHALL generate realistic Telemetry_Data that matches the configured Environmental_Parameters

### Requirement 5

**User Story:** As a boat operator, I want to save and load different simulation scenarios, so that I can repeatedly test specific conditions and compare autopilot performance.

#### Acceptance Criteria

1. THE Remote_Control_App SHALL allow saving current Environmental_Parameters and boat state as named scenarios
2. THE Remote_Control_App SHALL allow loading previously saved scenarios to restore Environmental_Parameters
3. THE Remote_Control_App SHALL maintain a list of saved scenarios with descriptive names
4. WHEN a scenario is loaded, THE Remote_Control_App SHALL apply all Environmental_Parameters within 1 second
5. THE Remote_Control_App SHALL allow deleting saved scenarios from the scenario list