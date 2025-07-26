#!/usr/bin/bash --
# Corto Boat Run Script
# This script runs the Corto boat code on a Raspberry Pi.
# It sets up the Python path and activates the Poetry virtual environment.

# Exit on error
set -e

# Get the script directory and project root
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
PYTHON_PATH="$PROJECT_ROOT/src/main/python"

echo "=== Corto Boat Runner ==="
echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "Python path: $PYTHON_PATH"
echo ""

# Check if setup has been run
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Poetry virtual environment not found. Running setup script..."
    "$SCRIPT_DIR/setup.sh"
    echo ""
fi

# Activate the Poetry virtual environment and run the boat code
echo "=== Starting Corto Boat ==="
echo "Press Ctrl+C to stop"
echo ""

cd "$PROJECT_ROOT"
PYTHONPATH="$PYTHON_PATH" poetry run python "$SCRIPT_DIR/corto.py" "$@"