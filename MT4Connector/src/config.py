"""
EA Signal Connector Configuration File
Simply update your connection details for your EA signals
"""

import os
import platform
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("config")

# 👇 EDIT YOUR CONNECTION DETAILS HERE 👇
# ==============================================
# Your MT4 Server details (get from your broker)
MT4_SERVER = os.environ.get('MT4_SERVER', "195.88.127.154")  # Default local MT4 server for testing
MT4_PORT = int(os.environ.get('MT4_PORT', 45543))  # Your MT4 server port
MT4_USERNAME = int(os.environ.get('MT4_LOGIN', os.environ.get('MT4_USERNAME', 66)))  # Your MT4 account number
MT4_PASSWORD = os.environ.get('MT4_PASSWORD', "iybe8ba")  # Your MT4 password

# EA Signal Processing options
AUTO_EXECUTE_SIGNALS = True  # Automatically execute signals from your EA
SIGNAL_CHECK_INTERVAL = 5    # Check for new signals every 5 seconds

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = ""  # Your Telegram bot token from BotFather
TELEGRAM_ADMIN_IDS = []  # List of Telegram user IDs authorized to use the bot
TELEGRAM_NOTIFICATIONS = True  # Send notifications to Telegram

# API Keys (if your EA requires these)
API_KEY = ""     # Your API key for external services (leave empty if not used)
API_SECRET = ""  # Your API secret (leave empty if not used)
# ==============================================

# Internal configuration (no need to edit)
MT4_SERVERS = {
    "Default": {"ip": MT4_SERVER, "port": MT4_PORT, "login": MT4_USERNAME, "password": MT4_PASSWORD}
}
DEFAULT_SERVER = "Default"
CRITERIA_FILE = "criteria.json"

# Create necessary directories
# Adjust BASE_DIR to be the project root, not the src directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# System paths - don't change these
MT4_API_DIR = os.path.join(BASE_DIR, "mt4_api")

# Automatically select the correct DLL based on platform
if platform.system() == "Windows":
    MT4_MANAGER_API_DLL = os.path.join(MT4_API_DIR, "mtmanapi.dll")
    # For 64-bit Windows systems
    if platform.architecture()[0] == "64bit":
        MT4_MANAGER_API_DLL = os.path.join(MT4_API_DIR, "mtmanapi64.dll")
elif platform.system() == "Darwin":  # macOS
    MT4_MANAGER_API_DLL = os.path.join(MT4_API_DIR, "mtmanapi.dylib")
    # If macOS library doesn't exist, try to use Windows DLL with compatibility layer
    if not os.path.exists(MT4_MANAGER_API_DLL):
        MT4_MANAGER_API_DLL = os.path.join(MT4_API_DIR, "mtmanapi.dll")
        logger.warning(f"macOS MT4 API library not found. Using Windows DLL: {MT4_MANAGER_API_DLL}")
else:  # Linux
    MT4_MANAGER_API_DLL = os.path.join(MT4_API_DIR, "libmtmanapi.so")
    # If Linux library doesn't exist, try to use Windows DLL with compatibility layer
    if not os.path.exists(MT4_MANAGER_API_DLL):
        MT4_MANAGER_API_DLL = os.path.join(MT4_API_DIR, "mtmanapi.dll")
        logger.warning(f"Linux MT4 API library not found. Using Windows DLL: {MT4_MANAGER_API_DLL}")

# Verify MT4 API DLL exists
if not os.path.exists(MT4_MANAGER_API_DLL):
    logger.warning(f"MT4 API DLL not found at {MT4_MANAGER_API_DLL}. The application may run in simulation mode.")

# API settings
MT4_MANAGER_API_VERSION = 100
MT4_TRADE_TRANSACTION_MAX_RETRIES = 3
MT4_TRADE_TRANSACTION_RETRY_DELAY = 2

# Create signals directory if it doesn't exist
SIGNALS_DIR = os.path.join(BASE_DIR, "signals")
if not os.path.exists(SIGNALS_DIR):
    os.makedirs(SIGNALS_DIR)
    logger.info(f"Created signals directory: {SIGNALS_DIR}")

# EA Signal file location - path where your EA outputs signals
EA_SIGNAL_FILE = os.path.join(SIGNALS_DIR, "ea_signals.txt")
if not os.path.exists(EA_SIGNAL_FILE):
    # Create empty signals file
    with open(EA_SIGNAL_FILE, 'w') as f:
        f.write('[]')
    logger.info(f"Created empty signal file: {EA_SIGNAL_FILE}")

# Logging
LOGS_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)
    logger.info(f"Created logs directory: {LOGS_DIR}")

LOG_LEVEL = "INFO"