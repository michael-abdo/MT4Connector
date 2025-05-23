#!/bin/bash
echo "===== Starting EA Signal Connector ====="

# Create necessary directories
mkdir -p logs
mkdir -p signals

# Check if signals file exists, create if not
if [ ! -f "signals/ea_signals.txt" ]; then
    echo "[]" > signals/ea_signals.txt
    echo "Created empty signals file."
fi

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    # Windows with Git Bash or similar
    source venv/Scripts/activate
fi

# Install dependencies if needed
if ! pip list | grep -q "watchdog"; then
    echo "Installing required dependencies..."
    pip install -r requirements.txt
fi

# Run the application
echo "Starting the connector..."
python src/app.py

# If the application exits, show message
echo
echo "Connector has stopped. Check the logs folder for details."
echo

read -p "Press Enter to continue..."