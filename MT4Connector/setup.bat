@echo off
echo ===== EA Signal Connector Setup =====
echo Installing required components...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in your PATH
    echo Please install Python 3.7 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

:: Display Python version
python -c "import sys; print(f'Detected Python version: {sys.version}')"

:: Create necessary directories
echo Creating required directories...
if not exist logs mkdir logs
if not exist signals mkdir signals

:: Create empty signals file if it doesn't exist
if not exist signals\ea_signals.txt (
    echo [] > signals\ea_signals.txt
    echo Created empty signals file.
)

:: Create virtual environment and install requirements
echo Creating Python virtual environment...
python -m venv venv

:: Activate the virtual environment
call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ===== Setup Complete! =====
echo.
echo You can now start the connector by double-clicking start.bat
echo or by running 'start.bat' in Command Prompt
echo.
echo Your EA should write signals to: %cd%\signals\ea_signals.txt
echo.
echo If you encounter any issues, check the logs directory for details.
echo.

pause