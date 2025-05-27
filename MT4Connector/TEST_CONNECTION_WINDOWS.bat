@echo off
REM Test MT4 connection on Windows

echo ============================================
echo MT4 CONNECTION TEST
echo ============================================
echo.

REM Set to use real MT4 API
set MOCK_MODE=False

REM Show what we're testing
echo Testing connection to:
echo - Server: 195.88.127.154
echo - Port: 45543
echo - Login: 66
echo.

REM Run the test
python test_connection.py

echo.
echo ============================================
echo TEST COMPLETE
echo ============================================
pause