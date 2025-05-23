#!/usr/bin/env python3
"""
MT4 Connector with Telegram Integration
Run this script to start the MT4 Connector with Telegram bot for interactive trading.
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"mt4_telegram_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MT4TelegramBot")

def check_token():
    """Check if Telegram bot token is configured"""
    from config import TELEGRAM_BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        print("\n❌ Telegram bot token not configured!")
        print("Please edit config.py and set TELEGRAM_BOT_TOKEN with your token from BotFather.")
        return False
    
    return True

def check_admin_ids():
    """Check if admin IDs are configured"""
    from config import TELEGRAM_ADMIN_IDS
    
    if not TELEGRAM_ADMIN_IDS:
        print("\n⚠️ No admin users configured for Telegram bot!")
        print("Please edit config.py and add your Telegram user ID to TELEGRAM_ADMIN_IDS.")
        print("The bot will run, but no users will be able to receive notifications or control trades.")
        
        choice = input("Continue anyway? (y/n): ").strip().lower()
        return choice == 'y'
    
    return True

def install_dependencies():
    """Install required dependencies"""
    import subprocess
    
    logger.info("Checking and installing dependencies...")
    
    # First check if python-telegram-bot is installed
    try:
        import telegram
        logger.info("python-telegram-bot already installed")
        return True
    except ImportError:
        print("Installing python-telegram-bot...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot==13.7"])
            logger.info("python-telegram-bot installed successfully")
            return True
        except subprocess.CalledProcessError:
            logger.error("Failed to install python-telegram-bot")
            print("\n❌ Failed to install python-telegram-bot.")
            print("Please run this command manually:")
            print("pip install python-telegram-bot==13.7")
            return False

def run_telegram_bot():
    """Run the Telegram bot with MT4 integration"""
    # Import after checking dependencies
    from config import (
        TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS, TELEGRAM_NOTIFICATIONS,
        MT4_SERVERS, DEFAULT_SERVER, EA_SIGNAL_FILE, AUTO_EXECUTE_SIGNALS
    )
    from mt4_api import MT4Manager
    from telegram_bot import TelegramBot
    from telegram_bot.signal_handler import TelegramSignalHandler
    
    print("\n" + "=" * 60)
    print("🤖 MT4 CONNECTOR WITH TELEGRAM BOT")
    print("=" * 60)
    
    # Initialize MT4 API
    print("\n🔄 Initializing MT4 API...")
    mt4_api = MT4Manager(use_mock_mode=True)
    
    # Initialize Telegram bot
    print("🔄 Initializing Telegram bot...")
    try:
        bot = TelegramBot(TELEGRAM_BOT_TOKEN, mt4_api, TELEGRAM_ADMIN_IDS)
        
        # Start the bot
        if not bot.start():
            logger.error("Failed to start Telegram bot")
            print("❌ Failed to start Telegram bot. Check your token and network connection.")
            return 1
        
        print(f"✅ Telegram bot started successfully as @{bot.bot_username}")
        
        # Initialize signal handler
        print("🔄 Initializing signal handler...")
        signal_handler = TelegramSignalHandler(
            telegram_bot=bot,
            mt4_api=mt4_api,
            signal_file=EA_SIGNAL_FILE,
            auto_execute=AUTO_EXECUTE_SIGNALS
        )
        
        # Start signal handler
        if not signal_handler.start():
            logger.error("Failed to start signal handler")
            print("❌ Failed to start signal handler.")
            bot.stop()
            return 1
        
        print(f"✅ Signal handler started successfully")
        print(f"📣 Monitoring signal file: {EA_SIGNAL_FILE}")
        
        # Try to connect to MT4 server
        server_config = MT4_SERVERS[DEFAULT_SERVER]
        print(f"🔄 Connecting to MT4 server {DEFAULT_SERVER}...")
        
        if mt4_api.connect(server_config["ip"], server_config["port"]):
            print(f"✅ Connected to MT4 server {DEFAULT_SERVER}")
            
            # Login to MT4 server
            if mt4_api.login(server_config["login"], server_config["password"]):
                print(f"✅ Logged in to MT4 server as {server_config['login']}")
                
                # Send notification to admin users
                bot.broadcast_message(
                    f"🔌 *MT4 Connector Connected*\n\n"
                    f"✅ Connected to MT4 server: `{DEFAULT_SERVER}`\n"
                    f"✅ Logged in as: `{server_config['login']}`\n\n"
                    f"The bot is now monitoring for trading signals. "
                    f"You'll receive notifications when signals are detected."
                )
            else:
                print(f"⚠️ Failed to login to MT4 server. Running in mock mode.")
                
                # Send notification to admin users
                bot.broadcast_message(
                    f"🔌 *MT4 Connector Started*\n\n"
                    f"⚠️ Running in mock mode (no MT4 connection)\n\n"
                    f"The bot is now monitoring for trading signals. "
                    f"Signals will be displayed but not executed."
                )
        else:
            print(f"⚠️ Failed to connect to MT4 server. Running in mock mode.")
            
            # Send notification to admin users
            bot.broadcast_message(
                f"🔌 *MT4 Connector Started*\n\n"
                f"⚠️ Running in mock mode (no MT4 connection)\n\n"
                f"The bot is now monitoring for trading signals. "
                f"Signals will be displayed but not executed."
            )
        
        # Keep the application running
        print("\n🔹 MT4 Connector with Telegram bot is running")
        print("🔹 Press Ctrl+C to stop")
        
        try:
            # Main loop - keep the program running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🔄 Stopping MT4 Connector with Telegram bot...")
            
            # Stop signal handler and bot
            signal_handler.stop()
            bot.stop()
            
            print("✅ MT4 Connector with Telegram bot stopped")
            return 0
    
    except Exception as e:
        logger.error(f"Error running MT4 Connector with Telegram bot: {e}")
        print(f"\n❌ Error: {str(e)}")
        return 1

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="MT4 Connector with Telegram Bot")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency and configuration checks")
    args = parser.parse_args()
    
    if not args.skip_checks:
        # Check dependencies
        if not install_dependencies():
            return 1
        
        # Check Telegram bot token
        if not check_token():
            return 1
        
        # Check admin IDs
        if not check_admin_ids():
            return 1
    
    # Run the bot
    return run_telegram_bot()

if __name__ == "__main__":
    sys.exit(main())