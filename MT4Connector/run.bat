@echo off
echo ===== Starting EA Signal Connector =====

:: Create necessary directories
if not exist logs mkdir logs
if not exist signals mkdir signals

:: Check if signals file exists, create if not
if not exist signals\ea_signals.txt (
    echo [] > signals\ea_signals.txt
    echo Created empty signals file.
)

:: Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

:: Check if watchdog is installed
pip list | findstr watchdog > nul
if ERRORLEVEL 1 (
    echo Installing required dependencies...
    pip install -r requirements.txt
)

:: Run the application
echo Starting the connector...
python src\app.py

:: If the application exits, show message
echo.
echo Connector has stopped. Check the logs folder for details.
echo.

pause