#!/bin/bash
# App Run Script
# This script runs the Flask app with the correct Python path.

# Exit on error
set -e

# Get the script directory and project root
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
PYTHON_PATH="$PROJECT_ROOT/src/main/python"

echo "=== Corto App Runner ==="
echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "Python path: $PYTHON_PATH"
echo ""

# Activate the Poetry virtual environment and run the app
echo "=== Starting Corto App ==="
echo "Press Ctrl+C to stop"
echo ""

cd "$PROJECT_ROOT"
PYTHONPATH="$PYTHON_PATH" poetry run python "$SCRIPT_DIR/app.py" --port=5001 "$@"
