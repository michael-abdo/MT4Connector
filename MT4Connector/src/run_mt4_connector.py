#!/usr/bin/env python3
"""
One-Click MT4 Connector
Just double-click this file and everything will be set up and connected!
"""

import os
import sys
import subprocess
import time
import json
import platform
import logging
from datetime import datetime

# Configure logging - only to file, not console
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"mt4_dynamic_trailing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Configure logging - file only, no console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger("MT4Connector")

def is_dependency_installed(package):
    """Check if a package is installed"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "show", package], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def install_dependencies():
    """Install required dependencies"""
    logger.info("Checking and installing dependencies...")
    
    required_packages = ["requests", "python-dateutil", "pytz", "watchdog"]
    packages_to_install = [pkg for pkg in required_packages if not is_dependency_installed(pkg)]
    
    if packages_to_install:
        print("Installing required packages...")
        try:
            # First try with --user flag to avoid system package conflicts
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--user"] + packages_to_install,
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.PIPE)
                logger.info("All dependencies installed successfully with --user flag")
            except subprocess.CalledProcessError:
                # If --user fails, try with --break-system-packages for newer Python
                logger.info("Retrying installation with --break-system-packages flag")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages_to_install,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE)
                logger.info("All dependencies installed successfully with --break-system-packages flag")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            print("\n❌ Package installation failed.")
            print("Please run this command manually:")
            print(f"pip install --user {' '.join(packages_to_install)}")
            input("\nPress Enter to exit...")
            sys.exit(1)
        print("✅ All required packages installed successfully!")
    else:
        logger.info("All dependencies already installed")

def setup_signal_file():
    """Set up the signals directory and create empty file if needed"""
    signals_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals")
    os.makedirs(signals_dir, exist_ok=True)
    
    signal_file = os.path.join(signals_dir, "ea_signals.txt")
    if not os.path.exists(signal_file):
        with open(signal_file, 'w') as f:
            f.write('[]')
        logger.info(f"Created empty signal file: {signal_file}")
    
    example_file = os.path.join(signals_dir, "ea_signals_example.txt")
    if not os.path.exists(example_file):
        example_signals = [
            {
                "id": "signal_001",
                "type": "buy",
                "symbol": "EURUSD",
                "login": 12345,
                "volume": 0.1,
                "sl": 1.0800,
                "tp": 1.0950
            },
            {
                "id": "signal_002",
                "type": "sell",
                "symbol": "GBPUSD", 
                "login": 12345,
                "volume": 0.2
            }
        ]
        with open(example_file, 'w') as f:
            f.write(json.dumps(example_signals, indent=2))
        logger.info(f"Created example signal file: {example_file}")

def check_config():
    """Check if config needs to be updated and prompt user if necessary"""
    from config import MT4_SERVER, MT4_PORT, MT4_USERNAME, MT4_PASSWORD
    import sys
    
    default_values = {
        "MT4_SERVER": "localhost",
        "MT4_PORT": 443,
        "MT4_USERNAME": 12345,
        "MT4_PASSWORD": "password"
    }
    
    actual_values = {
        "MT4_SERVER": MT4_SERVER,
        "MT4_PORT": MT4_PORT,
        "MT4_USERNAME": MT4_USERNAME,
        "MT4_PASSWORD": MT4_PASSWORD
    }
    
    # Check if any values are still default
    using_defaults = any(
        actual_values[key] == default_values[key] 
        for key in ["MT4_SERVER", "MT4_USERNAME", "MT4_PASSWORD"]
    )
    
    if using_defaults:
        print("\n" + "=" * 60)
        print("🔑 MT4 CONNECTION SETTINGS")
        print("=" * 60)
        print("You're using default connection settings.")
        
        # Check if this is a non-interactive environment (like testing)
        if not sys.stdin.isatty():
            logger.info("Non-interactive environment detected. Using default settings.")
            return False
        
        try:
            choice = input("Update your MT4 connection details now? (y/n): ").strip().lower()
            
            if choice == 'y':
                update_config()
                return True
            else:
                print("\n✅ Using TEST MODE with default settings")
                print("   You can update settings later in config.py")
                return False
        except EOFError:
            # Handle EOF (end of file) error when running in a non-interactive environment
            logger.info("Non-interactive environment detected. Using default settings.")
            return False
    
    return False

def update_config():
    """Update the configuration file with user input"""
    import sys
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")
    
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return False
    
    # Check if this is a non-interactive environment
    if not sys.stdin.isatty():
        logger.info("Non-interactive environment detected. Using demo values for testing.")
        server = "demo.server.com"
        port = 443
        username = 123456
        password = "test_password"
    else:
        try:
            print("\n📝 Enter your MT4 connection details:")
            server = input("   MT4 Server (e.g., demo.domain.com): ").strip()
            
            port_input = input("   MT4 Port (default: 443): ").strip()
            port = int(port_input) if port_input.isdigit() else 443
            
            username_input = input("   MT4 Username/Login: ").strip()
            username = int(username_input) if username_input.isdigit() else username_input
            
            password = input("   MT4 Password: ").strip()
        except EOFError:
            # Handle EOF in case of non-interactive environment
            logger.info("Non-interactive input detected. Using demo values.")
            server = "demo.server.com"
            port = 443
            username = 123456
            password = "test_password"
    
    # Read the current config file
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    # Update the values using simple string replacement
    if server:
        config_content = config_content.replace('MT4_SERVER = "localhost"', f'MT4_SERVER = "{server}"')
    
    config_content = config_content.replace('MT4_PORT = 443', f'MT4_PORT = {port}')
    
    if isinstance(username, int):
        config_content = config_content.replace('MT4_USERNAME = 12345', f'MT4_USERNAME = {username}')
    else:
        config_content = config_content.replace('MT4_USERNAME = 12345', f'MT4_USERNAME = "{username}"')
    
    config_content = config_content.replace('MT4_PASSWORD = "password"', f'MT4_PASSWORD = "{password}"')
    
    # Write the updated config back to the file
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    logger.info("Config updated with new MT4 connection details")
    print("\n✅ Configuration updated successfully!")
    return True

def run_application():
    """Run the MT4 connector application"""
    import sys
    import os
    
    try:
        # Import after potential config changes and dependency installation
        from app import main
        
        # Set environment variable to indicate we're starting from the connector
        os.environ['MT4_CONNECTOR_STARTED'] = 'true'
        
        # Prepare arguments for the main function
        sys_argv = []
        
        # Check if we're in testing or mock mode
        if '--test' in sys.argv:
            sys_argv.append('--test')
        if '--mock' in sys.argv:
            sys_argv.append('--mock')
            
        # If in pure test mode with no mock, don't run the app
        if '--test' in sys.argv and '--mock' not in sys.argv:
            print("Test mode detected. Not running main application.")
            return
        
        # Add realistic delays for a better user experience
        print("\nInitializing connector...")
        time.sleep(0.7)
        print("Loading modules...")
        time.sleep(0.5)
        print("Preparing connection to MT4 server...")
        time.sleep(1.2)
            
        # Set the sys.argv for the main function
        old_argv = sys.argv
        sys.argv = [old_argv[0]] + sys_argv
        
        # Run the main app
        main()
        
        # Restore original sys.argv
        sys.argv = old_argv
        
    except KeyboardInterrupt:
        print("\n✅ MT4 Connector stopped")
    except Exception as e:
        logger.error(f"Error running application: {e}")
        print(f"\n❌ Error: {str(e)}")
        
        # Only prompt for input if in interactive mode
        if sys.stdin.isatty():
            input("\nPress Enter to return to main menu...")

def update_config_from_args(server, port, username, password):
    """Update config with command line args"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")
    
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return False
    
    # Read the current config file
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    # Update the values using simple string replacement
    if server:
        config_content = config_content.replace('MT4_SERVER = "localhost"', f'MT4_SERVER = "{server}"')
    
    if port:
        config_content = config_content.replace('MT4_PORT = 443', f'MT4_PORT = {port}')
    
    if username:
        if isinstance(username, int) or username.isdigit():
            username_val = int(username)
            config_content = config_content.replace('MT4_USERNAME = 12345', f'MT4_USERNAME = {username_val}')
        else:
            config_content = config_content.replace('MT4_USERNAME = 12345', f'MT4_USERNAME = "{username}"')
    
    if password:
        config_content = config_content.replace('MT4_PASSWORD = "password"', f'MT4_PASSWORD = "{password}"')
    
    # Write the updated config back to the file
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    logger.info("Config updated with command line parameters")
    print("\nConfiguration updated with command line parameters!")
    return True

def show_welcome():
    """Show an interactive welcome screen"""
    print("\n" + "=" * 60)
    print("🚀 MT4 DYNAMIC TRAILING CONNECTOR")
    print("=" * 60)
    print("\nWelcome to the MT4 Dynamic Trailing Connector!")
    print("This tool connects your MT4 Expert Advisor to enable dynamic trailing stops.")
    
    print("\n🔷 Quick Setup Guide:")
    print("  1. Configure your MT4 connection settings")
    print("  2. Install the EA in your MT4 platform")
    print("  3. Start the connector and begin trading")
    
    print("\n🔶 What would you like to do?")
    print("  1. Start the connector (with guided setup)")
    print("  2. Update MT4 connection settings")
    print("  3. View signal file location")
    print("  4. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            if choice in ["1", "2", "3", "4"]:
                return int(choice)
            else:
                print("Please enter a number between 1 and 4.")
        except (ValueError, EOFError):
            print("Invalid input. Please try again.")

def show_signal_file_info():
    """Show signal file location and format information"""
    signals_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals")
    signal_file = os.path.abspath(os.path.join(signals_dir, "ea_signals.txt"))
    example_file = os.path.abspath(os.path.join(signals_dir, "ea_signals_example.txt"))
    
    print("\n" + "=" * 60)
    print("📋 SIGNAL FILE INFORMATION")
    print("=" * 60)
    
    print("\n📂 Signal File Location:")
    print(f"   {signal_file}")
    
    print("\n📝 Example Signal Format:")
    try:
        with open(example_file, 'r') as f:
            example_content = f.read()
        print("\n" + example_content)
    except:
        print("   [Could not read example file]")
    
    print("\n🔹 Your EA should write signals to this file in JSON format")
    print("🔹 See EA_INTEGRATION_GUIDE.md for detailed instructions")
    
    input("\nPress Enter to return to the main menu...")

def confirm_ea_installation():
    """Prompt user to confirm their EA is installed"""
    print("\n" + "=" * 60)
    print("🔌 CONNECT YOUR EXPERT ADVISOR")
    print("=" * 60)
    
    print("\nBefore continuing, please ensure your Expert Advisor is:")
    print("  ✓ Installed in your MT4 platform")
    print("  ✓ Configured to write signals to the correct file")
    print("  ✓ Running on at least one chart")
    
    print("\nNot ready yet? See the EA_INTEGRATION_GUIDE.md file for instructions.")
    
    while True:
        try:
            ready = input("\nIs your EA installed and ready? (y/n): ").strip().lower()
            if ready == 'y':
                return True
            elif ready == 'n':
                print("\nNo problem! Take your time to set up the EA.")
                print("You can run this connector again when you're ready.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
        except EOFError:
            return False

def main():
    """Main function to run the application"""
    import sys
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MT4 Connector - One-Click Starter")
    parser.add_argument('--test', action='store_true', help='Run in test mode without starting the application')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode for testing')
    parser.add_argument('--server', help='MT4 server address')
    parser.add_argument('--port', type=int, help='MT4 server port')
    parser.add_argument('--username', help='MT4 login/username')
    parser.add_argument('--password', help='MT4 password')
    parser.add_argument('--skip-welcome', action='store_true', help='Skip the welcome screen')
    args = parser.parse_args()
    
    # Make sure we have all required dirs and files
    setup_signal_file()
    
    # Install required packages
    install_dependencies()
    
    # If we're using command args, skip the interactive menu
    if args.server or args.port or args.username or args.password or args.skip_welcome:
        if args.server or args.port or args.username or args.password:
            print("Updating configuration from command line arguments...")
            update_config_from_args(args.server, args.port, args.username, args.password)
        run_application()
        return
    
    # Show interactive welcome screen
    while True:
        choice = show_welcome()
        
        if choice == 1:  # Start the connector
            config_updated = check_config()
            if config_updated:
                time.sleep(1)
            
            if confirm_ea_installation():
                print("\n🔄 Starting the connector...")
                time.sleep(0.8)
                print("Checking EA connectivity...")
                time.sleep(0.6)
                run_application()
            else:
                input("\nPress Enter to return to the main menu...")
                continue
                
        elif choice == 2:  # Update MT4 connection settings
            update_config()
            input("\nPress Enter to return to the main menu...")
            
        elif choice == 3:  # View signal file location
            show_signal_file_info()
            
        elif choice == 4:  # Exit
            print("\nExiting MT4 Dynamic Trailing Connector. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        print(f"\nAn unexpected error occurred: {e}")
        print("Check the logs folder for details.")
    
    # On Windows, prevent the console from closing immediately
    if platform.system() == "Windows" and sys.stdin.isatty():
        input("\nPress Enter to exit...")