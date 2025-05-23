#!/usr/bin/env python3
"""
SoloTrend X Trading System
Main entry point for running the complete system.
"""

import os
import sys
import logging
import threading
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import components
try:
    from src.telegram_bot import TelegramBot
    from src.webhook import run_webhook_server
    from src.mt4_connector import mt4_api
except ImportError as e:
    logger.error(f"Error importing components: {e}")
    sys.exit(1)

def start_mt4_mock_api():
    """Start the MT4 mock API server"""
    from src.mt4_connector.api_server import app as mt4_api_app
    
    # Connect to MT4 server (mock)
    mt4_api.connect("localhost", 443, 12345, "password")
    
    # Get port from environment or use default
    port = int(os.environ.get('MT4_API_PORT', 5003))
    
    # Run Flask app
    mt4_api_app.run(host='0.0.0.0', port=port, debug=False)

def start_webhook_server(telegram_bot):
    """Start the webhook server"""
    host = os.environ.get('WEBHOOK_HOST', '0.0.0.0')
    port = int(os.environ.get('WEBHOOK_PORT', 5001))
    run_webhook_server(host=host, port=port, telegram_bot=telegram_bot)

def main():
    """Run the complete system"""
    logger.info("Starting SoloTrend X Trading System...")
    
    # Check for required environment variables
    if not os.environ.get('TELEGRAM_BOT_TOKEN'):
        logger.error("TELEGRAM_BOT_TOKEN environment variable not found. "
                    "Please create a .env file with your Telegram bot token.")
        sys.exit(1)
    
    # Create Telegram bot instance
    telegram_bot = TelegramBot()
    
    # Start components in separate threads
    # 1. MT4 Mock API
    mt4_thread = threading.Thread(target=start_mt4_mock_api, daemon=True)
    mt4_thread.start()
    logger.info("MT4 Mock API server started")
    
    # 2. Webhook Server
    webhook_thread = threading.Thread(target=start_webhook_server, args=(telegram_bot,), daemon=True)
    webhook_thread.start()
    logger.info("Webhook server started")
    
    # Allow time for services to start
    time.sleep(2)
    
    # 3. Telegram Bot (main thread)
    logger.info("Starting Telegram bot...")
    telegram_bot.run()

if __name__ == "__main__":
    main()