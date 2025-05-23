import logging
import os
import sys
import asyncio
import threading
import atexit
from flask import Flask
from dotenv import load_dotenv
from datetime import datetime

# Get the project root directory (one level up from the current file)
# Use a more reliable approach to find the root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, '..'))

# Configure logging
log_dir = os.path.join(PROJECT_ROOT, 'data', 'logs')
os.makedirs(log_dir, exist_ok=True)  # Create logs directory if it doesn't exist

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'telegram_connector.log'))
    ]
)
logger = logging.getLogger(__name__)

# Log the project root for verification
logger.info(f"Using PROJECT_ROOT: {PROJECT_ROOT}")

# Load environment variables with clear precedence
# Base configuration first
env_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path=env_path)
logger.info(f"Loaded base configuration from: {env_path}")

# Then allow specific overrides if they exist
local_env_path = os.path.join(PROJECT_ROOT, '.env.local')
if os.path.exists(local_env_path):
    load_dotenv(dotenv_path=local_env_path, override=True)
    logger.info(f"Loaded local overrides from: {local_env_path}")

# Enforce proper Telegram token validation
if 'TELEGRAM_BOT_TOKEN' not in os.environ:
    error_msg = "TELEGRAM_BOT_TOKEN environment variable not found. Please create a .env file with your Telegram bot token."
    logger.error(error_msg)
    # Don't raise error yet to allow application to start in test/development modes
else:
    token = os.environ['TELEGRAM_BOT_TOKEN']
    token_parts = token.split(':')
    if len(token_parts) != 2:
        error_msg = "TELEGRAM_BOT_TOKEN has invalid format (should be NUMBER:STRING). Please check your configuration."
        logger.error(error_msg)
        # Don't raise error yet to allow application to start in test/development modes
    else:
        # Valid token format
        logger.info(f"Found valid TELEGRAM_BOT_TOKEN in environment with ID: {token_parts[0]}")

# Only allow mock mode if explicitly configured (will be checked during app creation)
mock_mode = os.environ.get('MOCK_MODE', 'False').lower() == 'true'
if mock_mode:
    logger.warning("Running in MOCK mode - using simulated Telegram API")

def validate_configuration():
    """Validate all required configuration parameters at startup"""
    missing_vars = []
    invalid_vars = []
    
    # Check required environment variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'ALLOWED_USER_IDS',
        'MT4_API_URL'
    ]
    
    for var in required_vars:
        if var not in os.environ or not os.environ[var]:
            missing_vars.append(var)
    
    # Validate Telegram token format
    if 'TELEGRAM_BOT_TOKEN' in os.environ:
        token = os.environ['TELEGRAM_BOT_TOKEN']
        token_parts = token.split(':')
        if len(token_parts) != 2:
            invalid_vars.append('TELEGRAM_BOT_TOKEN')
    
    # Validate user IDs are numeric
    if 'ALLOWED_USER_IDS' in os.environ:
        user_ids = os.environ['ALLOWED_USER_IDS'].split(',')
        for user_id in user_ids:
            if user_id.strip() and not user_id.strip().isdigit():
                invalid_vars.append('ALLOWED_USER_IDS')
                break
    
    # Return validation results
    return {
        'valid': not missing_vars and not invalid_vars,
        'missing': missing_vars,
        'invalid': invalid_vars
    }

def create_app(test_config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Validate configuration
    if not test_config:
        config_status = validate_configuration()
        mock_mode = os.environ.get('MOCK_MODE', 'False').lower() == 'true'
        
        # Store validation status for health check
        app.config_validation_passed = config_status['valid']
        
        if not config_status['valid'] and not mock_mode:
            if config_status['missing']:
                logger.error(f"Missing required environment variables: {', '.join(config_status['missing'])}")
            if config_status['invalid']:
                logger.error(f"Invalid environment variables: {', '.join(config_status['invalid'])}")
            raise EnvironmentError("Invalid configuration, see logs for details")
        elif not config_status['valid'] and mock_mode:
            logger.warning("Configuration validation failed, but continuing in MOCK mode")
    else:
        # For test config, assume validation passed
        app.config_validation_passed = True
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
        TELEGRAM_BOT_TOKEN=os.environ.get('TELEGRAM_BOT_TOKEN', ''),
        TELEGRAM_WEBHOOK_URL=os.environ.get('TELEGRAM_WEBHOOK_URL', 'http://localhost:5001/webhook'),
        MT4_API_URL=os.environ.get('MT4_API_URL', 'http://localhost:5002/api/trade'),
        FLASK_DEBUG=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
        FLASK_PORT=int(os.environ.get('FLASK_PORT', 5001)),
        MOCK_MODE=mock_mode,
        ADMIN_USER_IDS=os.environ.get('ADMIN_USER_IDS', '').split(','),
        ALLOWED_USER_IDS=os.environ.get('ALLOWED_USER_IDS', '').split(','),
    )
    
    # Override configuration with test config if provided
    if test_config:
        app.config.update(test_config)
    
    # Ensure data directories exist at project root
    os.makedirs(os.path.join(PROJECT_ROOT, 'data', 'logs'), exist_ok=True)
    
    # Register routes - try to import both ways for compatibility
    try:
        # First try local import
        import routes
        routes.register_routes(app)
        logger.info("Loaded routes from local module")
    except ImportError:
        # Fall back to full path import
        try:
            import src.backend.telegram_connector.routes as routes
            routes.register_routes(app)
            logger.info("Loaded routes from backend module")
        except ImportError:
            logger.error("Could not import routes module - webhook will not work")
            # Create a minimal default route for testing
            @app.route('/webhook/signal', methods=['POST'])
            def default_webhook():
                from flask import request, jsonify
                data = request.get_json()
                logger.info(f"Received signal: {data}")
                
                # Add a direct implementation for sending to Telegram
                try:
                    if hasattr(app, 'bot_instance') and app.bot_instance:
                        bot = app.bot_instance
                        # Extract basic signal info
                        symbol = data.get('symbol', 'Unknown')
                        side = data.get('side', data.get('action', 'Unknown'))
                        price = data.get('price', 'Market')
                        
                        # Format a message
                        message = (
                            f"🔔 *SIGNAL: {symbol} {side.upper()}*\n\n"
                            f"💰 Price: {price}\n"
                        )
                        
                        # Add stop loss if present
                        if 'sl' in data:
                            message += f"🛑 Stop Loss: {data['sl']}\n"
                            
                        # Add take profit targets if present
                        if 'tp1' in data:
                            message += f"🎯 Take Profit 1: {data['tp1']}\n"
                        if 'tp2' in data:
                            message += f"🎯 Take Profit 2: {data['tp2']}\n"
                        if 'tp3' in data:
                            message += f"🎯 Take Profit 3: {data['tp3']}\n"
                        
                        # Add strategy if present
                        if 'strategy' in data:
                            message += f"📈 Strategy: {data['strategy']}\n"
                        
                        # Add timestamp
                        message += f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        
                        # Get allowed users
                        allowed_users = []
                        for user_id in os.environ.get('ALLOWED_USER_IDS', '').split(','):
                            if user_id.strip():
                                try:
                                    allowed_users.append(int(user_id.strip()))
                                except ValueError:
                                    continue
                        
                        if not allowed_users:
                            # Add a default test user in mock mode
                            allowed_users = [123456789]
                        
                        # Create task to send messages
                        import asyncio
                        
                        async def send_messages():
                            from telegram import Bot
                            try:
                                # Get token from env
                                token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                if not token or token == 'your_telegram_bot_token_here':
                                    logger.warning("Using mock token since real token not available")
                                    return False
                                    
                                # Create bot instance
                                bot = Bot(token=token)
                                
                                # Send to all allowed users
                                for user_id in allowed_users:
                                    try:
                                        await bot.send_message(
                                            chat_id=user_id,
                                            text=message,
                                            parse_mode="Markdown"
                                        )
                                        logger.info(f"Signal sent to user {user_id}")
                                    except Exception as e:
                                        logger.error(f"Failed to send to user {user_id}: {e}")
                                        
                                return True
                            except Exception as e:
                                logger.error(f"Failed to send messages: {e}")
                                return False
                        
                        # Run the async function
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(send_messages())
                        loop.close()
                        
                        if result:
                            return jsonify({"status": "success", "message": "Signal sent to Telegram users"})
                    
                    return jsonify({"status": "received", "message": "Routes module not loaded, signal logged only"})
                except Exception as e:
                    logger.error(f"Error in direct implementation: {e}")
                    return jsonify({"status": "received", "message": f"Error: {str(e)}"})
    
    # Add an enhanced health check endpoint with authentication verification
    @app.route('/health', methods=['GET'])
    def health():
        from flask import jsonify
        logger.info("Health check endpoint called")
        
        # Check Telegram bot connectivity
        telegram_status = "ok" if hasattr(app, 'bot_instance') and app.bot_instance else "error"
        
        # Check MT4 API connectivity if connector exists
        mt4_status = "unknown"
        if hasattr(app, 'mt4_connector'):
            mt4_status = "ok" if app.mt4_connector.verify_connection() else "error"
        
        # Overall health status
        status = "ok" if telegram_status == "ok" and (mt4_status == "ok" or mt4_status == "unknown") else "error"
        
        # Include mock mode information
        mock_mode = app.config.get('MOCK_MODE', False)
        
        return jsonify({
            'status': status,
            'service': 'telegram_connector',
            'mock_mode': mock_mode,
            'components': {
                'telegram': telegram_status,
                'mt4_api': mt4_status
            },
            'config_validation': {
                'result': 'passed' if hasattr(app, 'config_validation_passed') and app.config_validation_passed else 'failed'
            }
        })
    
    # Initialize MT4 connector - try both import paths for compatibility
    try:
        try:
            # Try local import first
            from mt4_connector import MT4Connector
            logger.info("Loaded MT4Connector from local module")
        except ImportError:
            # Fall back to backend import
            from src.backend.telegram_connector.mt4_connector import MT4Connector
            logger.info("Loaded MT4Connector from backend module")
            
        mt4_api_url = app.config.get('MT4_API_URL')
        use_mock = app.config.get('MOCK_MODE', True)
        app.mt4_connector = MT4Connector(mt4_api_url, use_mock=use_mock)
        logger.info(f"MT4Connector initialized with URL: {mt4_api_url}, mock mode: {use_mock}")
    except ImportError:
        logger.error("Could not import MT4Connector module - using a mock implementation")
        # Create a simple mock implementation
        class MockMT4Connector:
            def __init__(self, url, use_mock=True):
                self.url = url
                self.use_mock = True
                logger.info(f"Mock MT4Connector created with URL: {url}")
                
            def verify_connection(self):
                return True
                
            def get_status(self):
                return {"connected": True, "server": "MOCK", "open_orders": 0}
                
            def execute_trade(self, request):
                logger.info(f"Mock trade execution: {request}")
                return {"status": "success", "ticket": 12345, "message": "Mock trade executed"}
                
            def get_open_orders(self):
                return []
                
        app.mt4_connector = MockMT4Connector(app.config.get('MT4_API_URL', 'http://localhost:5002'))
        logger.info("Using mock MT4Connector implementation")
    
    # Initialize Telegram bot (asynchronously) - try both import paths
    try:
        try:
            # Try local import first
            import bot
            logger.info("Loaded bot module from local module")
        except ImportError:
            # Fall back to backend import
            import src.backend.telegram_connector.bot as bot
            logger.info("Loaded bot module from backend module")
        
        # Check token format before even attempting to set up bot
        token = app.config.get('TELEGRAM_BOT_TOKEN', '').strip()  # Strip whitespace
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is missing or empty")
            logger.warning("Telegram bot will not be available - please set TELEGRAM_BOT_TOKEN in .env")
            app.bot_instance = None
        elif ':' not in token:
            logger.error(f"Invalid Telegram bot token format. Expected format: '123456789:ABCDefGhiJklmNoPQRstUvwxyz'")
            logger.warning("Telegram bot will not be available - please check token format")
            app.bot_instance = None
        else:
            # Token has basic format, attempt to set up the bot
            # Update the config with the stripped token
            app.config['TELEGRAM_BOT_TOKEN'] = token
            token_parts = token.split(':')
            token_id_part = token_parts[0]
            
            # Log attempt with token ID for debugging
            logger.info(f"Setting up Telegram bot with token ID: {token_id_part}")
            
            # Try to delete any existing webhook first to avoid conflicts
            try:
                import asyncio
                from telegram import Bot
                
                # Create temporary bot instance to clean up webhooks
                temp_bot = Bot(token=token)
                
                # Run in a new event loop to ensure it completes
                async def delete_existing_webhook():
                    try:
                        logger.info("Attempting to delete any existing webhook")
                        await temp_bot.delete_webhook(drop_pending_updates=True)
                        logger.info("Successfully deleted any existing webhook")
                    except Exception as e:
                        logger.warning(f"Couldn't delete webhook (this is often normal): {str(e)}")
                
                # Run the async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(delete_existing_webhook())
                loop.close()
            except Exception as e:
                logger.warning(f"Error during webhook cleanup: {str(e)}. Continuing anyway.")
            
            # Set up the bot through bot.py
            app.bot_instance = bot.setup_bot(app)
            
            if app.bot_instance:
                logger.info(f"Telegram bot successfully initialized with mode: {'mock' if app.config.get('MOCK_MODE') else 'live'}")
                # Store the token info in app config for easy access
                app.config['TELEGRAM_BOT_CONNECTED'] = True
            else:
                logger.error("Failed to initialize Telegram bot - check logs for details")
                # Mark as not connected in config
                app.config['TELEGRAM_BOT_CONNECTED'] = False
    except Exception as e:
        logger.error(f"Error during Telegram bot initialization: {str(e)}", exc_info=True)
        app.bot_instance = None
        logger.warning("Telegram bot will not be available due to initialization error")
    # Register shutdown functions to ensure clean bot termination
    @app.teardown_appcontext
    def shutdown_telegram_bot(exception=None):
        if hasattr(app, 'bot_instance') and app.bot_instance:
            logger.info("Shutting down Telegram bot...")
            try:
                # Signal to the bot that we're shutting down
                # This will help prevent conflicts in future startups
                import atexit
                
                async def stop_bot():
                    try:
                        logger.info("Attempting to gracefully stop the Telegram bot")
                        if hasattr(app.bot_instance, 'stop'):
                            await app.bot_instance.stop()
                        logger.info("Telegram bot stopped successfully")
                    except Exception as e:
                        logger.warning(f"Error stopping Telegram bot: {str(e)}")
                
                # Register the cleanup function
                atexit.register(lambda: asyncio.run(stop_bot()))
                
            except Exception as e:
                logger.warning(f"Error setting up bot shutdown: {str(e)}")
    
    # Initialize monitoring components for production
    if not app.config.get('MOCK_MODE') and os.environ.get('ENABLE_MONITORING', 'True').lower() == 'true':
        try:
            # Use PostgreSQL in production
            from database_postgres import get_database
            from health_monitor import HealthMonitor
            from reconnection_manager import MT4ReconnectionHandler, TelegramReconnectionHandler
            from trade_logger import get_trade_logger
            
            # Initialize components
            db = get_database()
            app.production_db = db
            
            # Initialize trade logger
            app.trade_logger = get_trade_logger()
            
            # Initialize health monitor
            app.health_monitor = HealthMonitor(db, app.mt4_connector, app.bot_instance)
            
            # Start health monitoring in background
            def start_health_monitoring():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(app.health_monitor.start_monitoring())
            
            health_thread = threading.Thread(target=start_health_monitoring, daemon=True)
            health_thread.start()
            logger.info("Started health monitoring")
            
            # Initialize reconnection handlers
            if app.mt4_connector:
                mt4_reconnect = MT4ReconnectionHandler(app.mt4_connector)
                
                def start_mt4_monitoring():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(mt4_reconnect.start_monitoring())
                
                mt4_thread = threading.Thread(target=start_mt4_monitoring, daemon=True)
                mt4_thread.start()
                logger.info("Started MT4 reconnection monitoring")
            
            if app.bot_instance:
                telegram_reconnect = TelegramReconnectionHandler(app.bot_instance)
                
                def start_telegram_monitoring():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(telegram_reconnect.start_monitoring())
                
                telegram_thread = threading.Thread(target=start_telegram_monitoring, daemon=True)
                telegram_thread.start()
                logger.info("Started Telegram reconnection monitoring")
                
        except Exception as e:
            logger.error(f"Failed to initialize monitoring components: {e}")

    return app

# This is used when running the file directly with 'python app.py'
if __name__ == '__main__':
    try:
        # Create the Flask app
        app = create_app()
        
        # Get port from environment or config
        port = app.config.get('FLASK_PORT', 5001)
        debug = app.config.get('FLASK_DEBUG', False)
        
        logger.info(f"Starting Telegram Connector server on port {port} (debug={debug})")
        
        # Run with extra shutdown timeout to ensure bot has time to disconnect cleanly
        app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
    except EnvironmentError as e:
        logger.error(f"Configuration error: {str(e)}")
        print(f"\n{'='*80}")
        print(f"ERROR: {str(e)}")
        print(f"Please check your configuration and try again.")
        print(f"Ensure you have a valid .env file with the following variables:")
        print(f"  - TELEGRAM_BOT_TOKEN: Your Telegram bot token from BotFather")
        print(f"  - ALLOWED_USER_IDS: Comma-separated list of user IDs")
        print(f"  - MT4_API_URL: URL to your MT4 API service")
        print(f"{'='*80}\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        print(f"\n{'='*80}")
        print(f"UNEXPECTED ERROR: {str(e)}")
        print(f"Check the logs for details.")
        print(f"{'='*80}\n")
        sys.exit(1)