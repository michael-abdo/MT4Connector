@echo off
title MT4 Dynamic Trailing - One Click Starter
echo =============================================
echo MT4 DYNAMIC TRAILING - ONE CLICK STARTER
echo =============================================
echo.

:: Change to the directory where this batch file is located
cd /d "%~dp0"

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Create folders if they don't exist
if not exist logs mkdir logs
if not exist signals mkdir signals
if not exist examples mkdir examples

:: Run the one-click starter script
python src\run_mt4_connector.py

:: Script will handle its own exit, this is just a fallback
pause