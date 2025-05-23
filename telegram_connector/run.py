#!/usr/bin/env python3
"""
Run script for Telegram Connector

This script launches the Telegram Connector service which provides:
1. A webhook endpoint for receiving trading signals
2. A Telegram bot for sending signals to users
3. Integration with the MT4 API for trade execution
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('telegram_connector.log')
    ]
)
logger = logging.getLogger(__name__)

# Main function
def main():
    """Run the Telegram connector server"""
    try:
        # Get the project root directory (one level up from the current file)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        
        # Add project root to path for module imports
        sys.path.insert(0, project_root)
        
        # Configure log directory
        log_dir = os.path.join(project_root, 'data', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Load environment variables
        env_path = os.path.join(project_root, '.env')
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Loaded configuration from: {env_path}")
        
        # Check for required environment variables
        required_vars = ['TELEGRAM_BOT_TOKEN', 'ALLOWED_USER_IDS', 'MT4_API_URL']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            print(f"\n{'='*80}")
            print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
            print(f"Please create a .env file with the following variables:")
            for var in required_vars:
                print(f"  - {var}")
            print(f"{'='*80}\n")
            sys.exit(1)
            
        # Import app from the current directory
        sys.path.insert(0, script_dir)
        from app import create_app
        
        print(f"\n{'='*80}")
        print(f"STARTING TELEGRAM CONNECTOR")
        print(f"{'='*80}\n")
        
        # Print path info
        logger.info(f"Project root: {project_root}")
        logger.info(f"Log directory: {log_dir}")
        
        # Create the Flask app
        app = create_app()
        
        # Get port from config
        port = app.config.get('FLASK_PORT', 5001)
        debug = app.config.get('FLASK_DEBUG', False)
        mock_mode = app.config.get('MOCK_MODE', False)
        
        # Print configuration
        logger.info(f"Starting Telegram Connector server:")
        logger.info(f"  - Port: {port}")
        logger.info(f"  - Debug: {debug}")
        logger.info(f"  - Mock mode: {mock_mode}")
        logger.info(f"  - MT4 API URL: {app.config.get('MT4_API_URL')}")
        
        # Print health check URL
        health_url = f"http://localhost:{port}/health"
        logger.info(f"Health check URL: {health_url}")
        
        # Print webhook URL
        webhook_url = f"http://localhost:{port}/webhook/signal"
        logger.info(f"Signal webhook URL: {webhook_url}")
        
        # Print the registered routes
        logger.info("Registered routes:")
        for rule in app.url_map.iter_rules():
            logger.info(f"  - {rule.rule} [{', '.join(rule.methods)}]")
        
        # Run the app
        print(f"\nTelegram connector is running! Press CTRL+C to stop.")
        print(f"Health check: {health_url}")
        print(f"Webhook URL: {webhook_url}\n")
        
        app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False, threaded=True)
        
    except Exception as e:
        logger.error(f"Error starting Telegram Connector: {e}", exc_info=True)
        print(f"\n{'='*80}")
        print(f"ERROR: {str(e)}")
        print(f"Check the logs for details.")
        print(f"{'='*80}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()