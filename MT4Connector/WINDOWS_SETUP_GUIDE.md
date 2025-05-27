# Windows Setup Guide for MT4 Connector

## Prerequisites
- Windows 10/11 or Windows Server
- Python 3.8 or higher
- Git (optional, for cloning the repository)

## Step 1: Transfer Files to Windows VM

### Option A: Using Git
```bash
git clone [your-repository-url]
cd MT4Connector
```

### Option B: Manual Transfer
1. ZIP the entire MT4Connector folder on your Mac
2. Transfer to Windows VM via:
   - Shared folders
   - Cloud storage (Google Drive, Dropbox)
   - USB drive
   - Network share

## Step 2: Install Python on Windows

1. Download Python from https://www.python.org/downloads/
2. During installation, **CHECK** "Add Python to PATH"
3. Verify installation:
```cmd
python --version
pip --version
```

## Step 3: Install Dependencies

Open Command Prompt as Administrator and navigate to the MT4Connector directory:

```cmd
cd C:\path\to\MT4Connector

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install additional dependencies for pumping mode
pip install websockets
```

## Step 4: Configure MT4 Connection

The credentials are already configured in `src/config.py`:
- Server: 195.88.127.154
- Port: 45543
- Login: 66
- Password: iybe8ba

To use real mode instead of mock mode, set the environment variable:
```cmd
set MOCK_MODE=False
```

Or permanently in Windows:
1. Right-click "This PC" → Properties
2. Advanced system settings → Environment Variables
3. Add new User variable: `MOCK_MODE` = `False`

## Step 5: Run the Connector

### Option A: Interactive Mode
```cmd
python src\run_mt4_connector.py
```
Then choose option 1 to start the connector.

### Option B: Direct Execution
```cmd
python src\app.py
```

### Option C: Test Connection First
```cmd
# Copy the test script if not already there
python test_connection.py
```

## Step 6: Verify MT4 Manager API DLL

Ensure the MT4 Manager API DLLs are present:
- `mt4_api\mtmanapi.dll` (32-bit)
- `mt4_api\mtmanapi64.dll` (64-bit)

These are Windows-specific files that enable communication with the MT4 server.

## Step 7: Running with Pumping Mode

To test the new pumping mode feature with real-time data:

```cmd
# Run the pumping mode example
python examples\pumping_mode_example.py
```

Then open `examples\websocket_client_example.html` in a web browser to see real-time quotes.

## Step 8: Troubleshooting

### Common Issues:

1. **"DLL not found" error**
   - Ensure you're running on Windows (not Wine/WSL)
   - Check that mtmanapi.dll exists in mt4_api folder
   - Install Visual C++ Redistributables if needed

2. **"Connection failed" error**
   - Verify server is accessible: `ping 195.88.127.154`
   - Check firewall settings
   - Ensure port 45543 is not blocked

3. **"Invalid credentials" error**
   - Double-check login/password in config.py
   - Ensure the account is active on the MT4 server

4. **Python module errors**
   - Make sure virtual environment is activated
   - Reinstall requirements: `pip install -r requirements.txt --force-reinstall`

## Step 9: Production Deployment

For production use:

1. **Create Windows Service**
   ```cmd
   # Install as Windows service
   python -m pip install pywin32
   python src\create_windows_service.py install
   ```

2. **Enable Auto-Start**
   - Services → MT4 Connector → Properties → Startup type: Automatic

3. **Configure Logging**
   - Logs are saved in the `logs` directory
   - Configure log rotation in production

4. **Security**
   - Change default API passwords in config.py
   - Use environment variables for sensitive data
   - Enable Windows Firewall rules

## Step 10: Testing the Connection

Once everything is set up, you should see:
```
2025-05-26 10:00:00 - MT4 Real API initialized successfully
2025-05-26 10:00:01 - Connected to MT4 server: 195.88.127.154:45543
2025-05-26 10:00:01 - Logged in successfully with account 66
2025-05-26 10:00:01 - Signal monitoring started...
```

## Quick Start Commands

```cmd
# Full setup and run
git clone [repository]
cd MT4Connector
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install websockets
set MOCK_MODE=False
python test_connection.py
python src\app.py
```

## Support

If you encounter issues:
1. Check the logs in the `logs` directory
2. Ensure all prerequisites are installed
3. Verify network connectivity to the MT4 server
4. Check Windows Event Viewer for system-level errors