#!/bin/bash
# MT4 Dynamic Trailing - One Click Starter

# Exit on any error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

echo "============================================="
echo "MT4 DYNAMIC TRAILING - ONE CLICK STARTER"
echo "============================================="
echo ""

# Check if Python is installed - try python3 first, then fall back to python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed or not in PATH."
        echo "Please install Python from https://www.python.org/downloads/"
        echo "Press Enter to exit..."
        read
        exit 1
    else
        PYTHON_CMD="python"
    fi
fi

# Create necessary directories
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/signals"
mkdir -p "$SCRIPT_DIR/examples"

# Make this script and the runner script executable if they aren't already
chmod +x "$SCRIPT_DIR/src/run_mt4_connector.py"
chmod +x "$SCRIPT_DIR/START_CONNECTOR.sh"

# Run the one-click starter script
"$PYTHON_CMD" "$SCRIPT_DIR/src/run_mt4_connector.py"

# Script will handle its own exit, this is just a fallback
echo "Press Enter to exit..."
read