@echo off
REM Windows batch file to start MT4 Connector

echo ============================================
echo MT4 CONNECTOR STARTUP
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Set to use real MT4 API (not mock mode)
set MOCK_MODE=False

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing requirements...
    pip install -r requirements.txt
    pip install websockets
)

REM Show connection details
echo.
echo Connecting to MT4 Server:
echo - Server: 195.88.127.154:45543
echo - Login: 66
echo - Mode: REAL (not mock)
echo.

REM Start the connector
echo Starting MT4 Connector...
echo.
python src\app.py

REM If the script exits, pause to see any error messages
if %errorlevel% neq 0 (
    echo.
    echo ERROR: MT4 Connector exited with error code %errorlevel%
    pause
)