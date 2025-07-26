# Platform Compatibility

This document describes how the project handles platform-specific dependencies and provides guidance for development on different platforms.

## Overview

The Corto project is designed to run on Raspberry Pi hardware, but it can also be developed and tested on other platforms like macOS or Windows. To support this, the project uses a platform-specific approach to dependencies and hardware access.

## Dependency Management

The project uses Poetry for dependency management. Raspberry Pi-specific packages are placed in a separate dependency group called `rpi` and are only installed on Linux platforms (which includes Raspberry Pi).

In `pyproject.toml`:

```toml
[tool.poetry.dependencies]
python = "3.11.*"
pyformance = "^0.4"
flask = "^3.1.1"

[tool.poetry.group.rpi.dependencies]
inventorhatmini = {version = "^1.0.0", platform = "linux"}
pimoroni-ioexpander = {version = "^1.0.1", platform = "linux"}
"RPi.GPIO" = {version = "^0.7.1", platform = "linux"}
```

## Hardware Abstraction

For hardware-specific functionality, the project uses a factory pattern to provide appropriate implementations based on the platform:

1. Real implementations for Raspberry Pi hardware
2. Mock implementations for non-Raspberry Pi platforms

### ServosController

The `ServosController` class is used to control servos and motors on the Raspberry Pi. On non-Raspberry Pi platforms, a `MockServosController` is used instead.

The factory function in `boat/controls/servos_factory.py` determines which implementation to use:

```python
def get_servos_controller():
    """
    Factory function that returns the appropriate ServosController implementation
    based on the current platform.
    
    Returns:
        ServosController or MockServosController: The appropriate controller implementation
    """
    # Check if we're running on a Linux platform (which includes Raspberry Pi)
    if sys.platform.startswith('linux'):
        # Check if the required Raspberry Pi packages are available
        inventorhatmini_available = importlib.util.find_spec("inventorhatmini") is not None
        ioexpander_available = importlib.util.find_spec("ioexpander") is not None
        
        if inventorhatmini_available and ioexpander_available:
            # Import and return the real ServosController
            from .servos_controller import ServosController
            return ServosController()
    
    # If we're not on Linux or the required packages aren't available,
    # use the mock implementation
    from .mock_servos_controller import MockServosController
    return MockServosController()
```

## Development on Different Platforms

### Raspberry Pi

On Raspberry Pi, install all dependencies including the Raspberry Pi-specific ones:

```bash
poetry install --with rpi
```

### macOS, Windows, or other non-Raspberry Pi platforms

On non-Raspberry Pi platforms, install only the core dependencies:

```bash
poetry install
```

The mock implementations will be used automatically for hardware-specific functionality.

## Testing

When testing on non-Raspberry Pi platforms, be aware that hardware interactions are simulated by the mock implementations. The mock implementations print messages to indicate what they're doing, prefixed with `[MOCK]` to make it clear that they're using the mock implementation.

For example:

```
[MOCK] Initializing MockServosController
[MOCK] Setting servo 1 to 50% (range: -60 to 45)
[MOCK] Motor enabled
```

## Adding New Hardware Functionality

When adding new hardware-specific functionality:

1. Create the real implementation for Raspberry Pi
2. Create a mock implementation for non-Raspberry Pi platforms
3. Create a factory function to select the appropriate implementation based on the platform
4. Update code that uses the functionality to use the factory function instead of directly instantiating the implementation

This approach ensures that the code can run on any platform, with appropriate behavior for each platform.