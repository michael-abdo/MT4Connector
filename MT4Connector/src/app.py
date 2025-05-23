#!/usr/bin/env python
"""
EA Signal Connector Application.
Connects to MT4 servers and processes EA signals to execute trades automatically.
"""

import os
import sys
import time
import logging
import argparse
import traceback
from datetime import datetime

# Adjust imports to work when run from different locations
import sys
from pathlib import Path

# Add the parent directory to sys.path if not already there
src_dir = Path(__file__).parent
root_dir = src_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    # First try importing directly from the current directory
    from config import (
        MT4_SERVERS, DEFAULT_SERVER, LOGS_DIR, LOG_LEVEL,
        API_KEY, API_SECRET, SIGNAL_CHECK_INTERVAL, AUTO_EXECUTE_SIGNALS
    )
    from mt4_api import MT4Manager
    from dx_integration import DXIntegration
    from signal_processor import SignalProcessor
except ImportError:
    # If that fails, try importing from src
    from src.config import (
        MT4_SERVERS, DEFAULT_SERVER, LOGS_DIR, LOG_LEVEL,
        API_KEY, API_SECRET, SIGNAL_CHECK_INTERVAL, AUTO_EXECUTE_SIGNALS
    )
    from src.mt4_api import MT4Manager
    from src.dx_integration import DXIntegration
    from src.signal_processor import SignalProcessor

# Set up logging - file only, no console output
log_file = os.path.join(LOGS_DIR, f"ea_connector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

class EASignalConnector:
    """
    Main application class for EA Signal Connector.
    Connects to MT4 servers and processes EA signals.
    """
    
    def __init__(self):
        """Initialize the EA Signal Connector application."""
        # Initialize with mock mode when DLL is not available
        self.mt4_api = MT4Manager(use_mock_mode=True)
        self.dx_api = DXIntegration()
        self.signal_processor = SignalProcessor(self.mt4_api, self.dx_api)
        self.connected = False
        self.running = True
        
        logger.info("EA Signal Connector initialized")
    
    def connect(self, server_name=DEFAULT_SERVER):
        """
        Connect to MT4 server.
        
        Args:
            server_name (str, optional): Server name from MT4_SERVERS
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        # Verify server exists in config
        if server_name not in MT4_SERVERS:
            logger.error(f"Server {server_name} not found in configuration")
            return False
        
        # Get server details
        server_config = MT4_SERVERS[server_name]
        server_ip = server_config["ip"]
        server_port = server_config["port"]
        server_login = server_config.get("login", 0)
        server_password = server_config.get("password", "")
        
        # Connect to server
        if not self.signal_processor.connect(server_ip, server_port, server_login, server_password):
            logger.error(f"Failed to connect to MT4 server {server_name} ({server_ip}:{server_port})")
            return False
        
        logger.info(f"Successfully connected to MT4 server {server_name}")
        self.connected = True
        
        # Set up DX API if needed
        if API_KEY and API_SECRET:
            self.dx_api.set_auth_credentials(API_KEY, API_SECRET)
            logger.info("DX API credentials configured")
        
        return True
    
    def disconnect(self):
        """
        Disconnect from MT4 server.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        if self.connected:
            result = self.signal_processor.disconnect()
            if result:
                logger.info("Successfully disconnected from MT4 server")
                self.connected = False
            else:
                logger.error("Failed to disconnect from MT4 server")
            
            return result
        
        return True
    
    def run(self):
        """
        Run the EA Signal Connector main loop.
        """
        if not self.connected:
            logger.error("Not connected to MT4 server")
            return
        
        try:
            # Start signal processing
            self.signal_processor.run()
        except KeyboardInterrupt:
            logger.info("EA Signal Connector stopped by user")
        except Exception as e:
            logger.error(f"Error in EA Signal Connector: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.disconnect()
    
    def stop(self):
        """Stop the application."""
        self.running = False
        logger.info("Application stopping")
        self.disconnect()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="EA Signal Connector Application")
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"MT4 server name (default: {DEFAULT_SERVER})")
    parser.add_argument("--mock", action="store_true", help="Force mock mode for testing")
    
    args = parser.parse_args()
    
    # Print banner (only if not started from run_mt4_connector.py)
    if not os.environ.get('MT4_CONNECTOR_STARTED') == 'true':
        print("=" * 60)
        print("  🔌 MT4 SIGNAL CONNECTOR")
        print("=" * 60)
    
    # Create the application with mock mode if requested or if running in test mode
    app = EASignalConnector()
    
    # Force connected state if in mock mode
    if args.mock:
        logger.info("Running in MOCK MODE for testing")
        print("🔄 Initializing test environment...")
        time.sleep(0.8)
        print("✅ Running in TEST MODE (no actual trades)")
        app.connected = True
        
        # Initialize signal processor manually in mock mode
        app.signal_processor.connected = True
        print("🔄 Setting up file monitoring...")
        time.sleep(0.6)
        
        # Run signal processing directly
        app.signal_processor.start_file_monitoring()
        app.signal_processor.process_signals()
        
        try:
            # Adjust path for signals file - we're now in src directory
            signals_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'signals/ea_signals.txt')
            print(f"🔹 Signal file: {signals_path}")
            print(f"🔹 Waiting for signals from your EA...")
            print("🔹 Signals will be displayed in this console when detected")
            print("🔹 Press Ctrl+C to stop")
            
            # Keep checking for signals in a loop
            while True:
                app.signal_processor.check_signal_file()
                time.sleep(SIGNAL_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print()
            print("✅ Connector stopped")
            app.signal_processor.stop_file_monitoring()
            return 0
        except Exception as e:
            logger.error(f"Unhandled exception in mock mode: {e}")
            app.signal_processor.stop_file_monitoring()
            print(f"❌ Error: {str(e)}")
            return 1
    
    # Normal mode with real connection
    try:
        # Connect to server
        print("🔄 Connecting to MT4 server...")
        time.sleep(1.2)
        print("🔄 Authenticating...")
        time.sleep(0.8)
        
        if not app.connect(args.server):
            logger.error("Failed to connect to server, exiting")
            print("❌ Failed to connect to MT4 server.")
            print("   Please check your server details in config.py")
            return 1
        
        print(f"✅ Connected to MT4 server!")
        time.sleep(0.5)
        print("🔄 Initializing signal processor...")
        time.sleep(0.7)
        # Adjust path for signals file - we're now in src directory
        signals_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'signals/ea_signals.txt')
        print(f"🔹 Signal file: {signals_path}")
        print(f"🔹 Waiting for signals from your EA...")
        print("🔹 Press Ctrl+C to stop")
        
        # Run the application
        app.run()
    except KeyboardInterrupt:
        print()
        print("✅ Connector stopped")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        print(f"❌ Error: {str(e)}")
        return 1
    finally:
        # Ensure proper cleanup
        app.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())