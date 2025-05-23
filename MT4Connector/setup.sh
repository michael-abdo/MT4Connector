#!/bin/bash
echo "===== EA Signal Connector Setup ====="
echo "Installing required components..."

# Detect Python command
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "ERROR: Python is not installed or not in your PATH"
        echo "Please install Python 3.7 or higher:"
        echo "  - Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
        echo "  - CentOS/RHEL: sudo yum install python3 python3-pip"
        echo "  - macOS: brew install python3"
        echo "  - Windows: Download from https://www.python.org/downloads/"
        exit 1
    fi
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Detected Python version: $PYTHON_VERSION"

# Create necessary directories
echo "Creating required directories..."
mkdir -p logs
mkdir -p signals

# Create empty signals file if it doesn't exist
if [ ! -f "signals/ea_signals.txt" ]; then
    echo "[]" > signals/ea_signals.txt
    echo "Created empty signals file."
fi

# Create virtual environment and install requirements
echo "Creating Python virtual environment..."
$PYTHON_CMD -m venv venv

# Activate the virtual environment based on platform
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows using Git Bash or similar
    source venv/Scripts/activate
else
    # Linux, macOS, etc.
    source venv/bin/activate
fi

echo "Installing dependencies..."
pip install --upgrade pip

# Try different installation methods to handle system Python restrictions
if ! pip install -r requirements.txt 2>/dev/null; then
    echo "Standard pip install failed, trying with --user flag..."
    if ! pip install --user -r requirements.txt 2>/dev/null; then
        echo "Trying with --break-system-packages flag for newer Python..."
        pip install --break-system-packages -r requirements.txt
    fi
fi

# Make the scripts executable
chmod +x start.sh
chmod +x setup.sh

# Create logs directory
mkdir -p logs

echo
echo "===== Setup Complete! ====="
echo
echo "You can now start the connector by running:"
echo "  - On Windows: double-click start.bat or run 'start.bat' in Command Prompt"
echo "  - On macOS/Linux: ./start.sh"
echo
echo "Your EA should write signals to: $(pwd)/signals/ea_signals.txt"
echo
echo "If you encounter any issues, check the logs directory for details."
echo

read -p "Press Enter to continue..."