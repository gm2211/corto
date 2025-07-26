import sys
import importlib.util


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