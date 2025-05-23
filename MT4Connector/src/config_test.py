"""
Test configuration that matches expected test values
"""
import os
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("config")

# Test configuration values
MT4_SERVER = "localhost"  # Expected by tests
MT4_PORT = 443  # Expected by tests
MT4_USERNAME = 12345  # Test account
MT4_PASSWORD = "test_password"  # Test password

# EA Signal Processing options
AUTO_EXECUTE_SIGNALS = True
SIGNAL_CHECK_INTERVAL = 5

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_ADMIN_IDS = []
TELEGRAM_NOTIFICATIONS = True

# API Keys
API_KEY = ""
API_SECRET = ""

# Internal configuration
MT4_SERVERS = {
    "Default": {"ip": MT4_SERVER, "port": MT4_PORT, "login": MT4_USERNAME, "password": MT4_PASSWORD}
}
DEFAULT_SERVER = "Default"
CRITERIA_FILE = "criteria.json"

# Set BASE_DIR to src directory for tests
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# System paths
MT4_API_DIR = os.path.join(BASE_DIR, "..", "mt4_api")
SIGNALS_DIR = os.path.join(BASE_DIR, "..", "signals")
LOGS_DIR = os.path.join(BASE_DIR, "..", "logs")

# Create directories
for directory in [MT4_API_DIR, SIGNALS_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# MT4 Trade Transaction Configuration
MT4_TRADE_TRANSACTION_MAX_RETRIES = 3
MT4_TRADE_TRANSACTION_RETRY_DELAY = 2

# Logging
LOG_LEVEL = "INFO"

# Signal file
SIGNAL_FILE = os.path.join(SIGNALS_DIR, "ea_signals.txt")

# DLL Selection based on platform
import platform
system = platform.system()
is_64bit = platform.machine().endswith('64')

if system == "Windows":
    MT4_MANAGER_DLL = os.path.join(MT4_API_DIR, "mtmanapi64.dll" if is_64bit else "mtmanapi.dll")
elif system == "Darwin":  # macOS
    MT4_MANAGER_DLL = os.path.join(MT4_API_DIR, "mtmanapi.dylib")
    if not os.path.exists(MT4_MANAGER_DLL):
        # Fallback to Windows DLL for mock mode
        MT4_MANAGER_DLL = os.path.join(MT4_API_DIR, "mtmanapi.dll")
        logger.warning(f"macOS MT4 API library not found. Using Windows DLL: {MT4_MANAGER_DLL}")
else:  # Linux
    MT4_MANAGER_DLL = os.path.join(MT4_API_DIR, "mtmanapi.so")

# Mock mode configuration
MOCK_MODE = os.environ.get('MOCK_MODE', 'True').lower() == 'true'

# Create signal file if it doesn't exist
if not os.path.exists(SIGNAL_FILE):
    open(SIGNAL_FILE, 'w').close()
    logger.info(f"Created signal file: {SIGNAL_FILE}")