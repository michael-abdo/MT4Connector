import logging
import asyncio
import os
import traceback
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import InvalidToken, TelegramError
# Try both import paths for the MT4Connector
try:
    # Try local import first
    from mt4_connector import MT4Connector
    from database import get_database
except ImportError:
    # Fall back to full path import
    from src.backend.telegram_connector.mt4_connector import MT4Connector
    from src.backend.telegram_connector.database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store user data
user_data_store = {}

# Initialize MT4 Connector and Database
mt4_connector = None
db = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Check if user is allowed
    if user_id not in context.bot_data.get("allowed_users", []):
        logger.warning(f"Unauthorized access attempt by user {user_id}")
        await update.message.reply_text(
            "⚠️ You are not authorized to use this bot. Please contact the administrator."
        )
        return
    
    # Welcome message
    await update.message.reply_text(
        f"👋 Welcome to SoloTrend X Trading Bot, {user_name}!\n\n"
        "I'll notify you about trading signals and help you execute trades.\n\n"
        "Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help information when the command /help is issued."""
    await update.message.reply_text(
        "🔍 *SoloTrend X Trading Bot Commands*\n\n"
        "/start - Start the bot\n"
        "/register - Register your account\n"
        "/help - Show this help message\n"
        "/status - Check bot and connection status\n"
        "/settings - Configure your trading parameters\n"
        "/orders - View your open orders\n"
        "/stats - View your trading statistics\n"
        "/cancel - Cancel current operation\n\n"
        "When you receive a signal, you can use the buttons below it to execute trades.",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check status of the trading bot and MT4 connection."""
    # Check MT4 connection status
    status = mt4_connector.get_status()
    
    await update.message.reply_text(
        f"📊 *SoloTrend X Trading Bot Status*\n\n"
        f"Bot status: ✅ Running\n"
        f"MT4 connection: {'✅ Connected' if status.get('connected') else '❌ Disconnected'}\n"
        f"Mode: {'🔵 Mock' if context.bot_data.get('mock_mode') else '🟢 Live'}\n"
        f"Server: {status.get('server', 'N/A')}\n"
        f"Active signals: {len(context.bot_data.get('active_signals', []))}\n"
        f"Open orders: {status.get('open_orders', 0)}",
        parse_mode="Markdown"
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configure trading settings."""
    user_id = update.effective_user.id
    
    # Initialize database if needed
    global db
    if db is None:
        db = get_database()
    
    # Check if user is registered
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text(
            "❌ You are not registered yet.\n"
            "Use /register to create your account."
        )
        return
    
    # Get settings from database
    settings = db.get_user_settings(user_id)
    
    # Store in memory for current session
    user_data_store[str(user_id)] = settings
    
    # Create settings keyboard
    keyboard = [
        [InlineKeyboardButton(f"Risk: {settings['risk_percent']}%", callback_data="settings_risk")],
        [InlineKeyboardButton(f"Lot Size: {settings['default_lot_size']}", callback_data="settings_lot")],
        [InlineKeyboardButton(f"Auto-Trade: {'On' if settings['auto_trade'] else 'Off'}", callback_data="settings_auto")],
        [InlineKeyboardButton(f"Notifications: {'On' if settings['notifications'] else 'Off'}", callback_data="settings_notify")],
        [InlineKeyboardButton("Save Settings", callback_data="settings_save")]
    ]
    
    await update.message.reply_text(
        "⚙️ *Trading Settings*\n\n"
        "Configure your personal trading preferences:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View open orders."""
    # Get open orders from MT4 connector
    orders = mt4_connector.get_open_orders()
    
    if not orders:
        await update.message.reply_text("📭 You don't have any open orders.")
        return
    
    # Format orders message
    message = "📋 *Your Open Orders*\n\n"
    for order in orders:
        message += (
            f"Ticket: #{order['ticket']}\n"
            f"Symbol: {order['symbol']}\n"
            f"Type: {order['type']}\n"
            f"Size: {order['volume']}\n"
            f"Open Price: {order['open_price']}\n"
            f"Current Price: {order['current_price']}\n"
            f"SL: {order['sl']}\n"
            f"TP: {order['tp']}\n"
            f"Profit: {order['profit']}\n\n"
        )
        
        # Add buttons for each order
        keyboard = [
            [
                InlineKeyboardButton("Close", callback_data=f"close_{order['ticket']}"),
                InlineKeyboardButton("Modify", callback_data=f"modify_{order['ticket']}")
            ]
        ]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Register user account."""
    user = update.effective_user
    user_id = user.id
    
    # Initialize database if needed
    global db
    if db is None:
        db = get_database()
    
    # Check if already registered
    existing_user = db.get_user(user_id)
    if existing_user:
        await update.message.reply_text(
            f"✅ You are already registered!\n\n"
            f"Account: {existing_user['mt4_account']}\n"
            f"Registered: {existing_user['registered_at']}\n\n"
            f"Use /settings to configure your preferences."
        )
        return
    
    # Register new user
    success = db.register_user(
        telegram_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        mt4_account=12345  # Default single account for Phase 3
    )
    
    if success:
        await update.message.reply_text(
            f"🎉 Welcome {user.first_name}!\n\n"
            f"You have been successfully registered.\n"
            f"MT4 Account: 12345\n\n"
            f"Use /settings to configure your trading preferences.\n"
            f"Use /help to see all available commands."
        )
    else:
        await update.message.reply_text(
            "❌ Registration failed. Please try again or contact support."
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user trading statistics."""
    user_id = update.effective_user.id
    
    # Initialize database if needed
    global db
    if db is None:
        db = get_database()
    
    # Check if user is registered
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text(
            "❌ You are not registered yet.\n"
            "Use /register to create your account."
        )
        return
    
    # Get statistics
    stats = db.get_user_stats(user_id)
    
    # Format statistics message
    total_trades = stats.get('total_trades', 0)
    executed_trades = stats.get('executed_trades', 0)
    rejected_trades = stats.get('rejected_trades', 0)
    total_profit = stats.get('total_profit', 0) or 0
    total_loss = stats.get('total_loss', 0) or 0
    win_rate = stats.get('win_rate', 0)
    net_profit = total_profit + total_loss  # Loss is negative
    
    message = (
        "📊 *Your Trading Statistics*\n\n"
        f"Total Signals: {total_trades}\n"
        f"Executed: {executed_trades}\n"
        f"Rejected: {rejected_trades}\n\n"
        f"Win Rate: {win_rate:.1f}%\n"
        f"Total Profit: ${total_profit:.2f}\n"
        f"Total Loss: ${abs(total_loss):.2f}\n"
        f"Net P&L: ${net_profit:.2f}\n\n"
        f"Account: {user['mt4_account']}"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel current operation."""
    await update.message.reply_text("Operation canceled.")
    return

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("trade_"):
        # Handle trade request
        _, signal_id, action = callback_data.split("_")
        await handle_trade_action(update, context, signal_id, action)
    
    elif callback_data.startswith("settings_"):
        # Handle settings update
        _, setting = callback_data.split("_")
        await handle_settings_update(update, context, setting)
    
    elif callback_data.startswith("close_"):
        # Handle order close request
        _, ticket = callback_data.split("_")
        await handle_close_order(update, context, ticket)
    
    elif callback_data.startswith("modify_"):
        # Handle order modify request
        _, ticket = callback_data.split("_")
        await handle_modify_order(update, context, ticket)

async def handle_trade_action(update: Update, context: ContextTypes.DEFAULT_TYPE, signal_id: str, action: str) -> None:
    """Handle trading actions from callback buttons."""
    query = update.callback_query
    
    # Get the signal from bot_data
    signals = context.bot_data.get("active_signals", {})
    if signal_id not in signals:
        await query.edit_message_text("⚠️ This signal has expired or is no longer valid.")
        return
    
    signal = signals[signal_id]
    
    if action == "accept":
        # Get user settings for lot size
        user_id = str(update.effective_user.id)
        user_settings = user_data_store.get(user_id, {"default_lot_size": 0.01})
        lot_size = user_settings.get("default_lot_size", 0.01)
        
        # Prepare trade request
        trade_request = {
            "symbol": signal.get("symbol"),
            "direction": signal.get("direction", "BUY"),
            "volume": lot_size,
            "sl": signal.get("stop_loss"),
            "tp": signal.get("take_profit")
        }
        
        # Execute trade through MT4 connector
        try:
            result = mt4_connector.execute_trade(trade_request)
            
            if result.get("status") == "success":
                # Save to signal history
                global db
                if db is None:
                    db = get_database()
                
                # Prepare signal data for history
                signal_history = {
                    'signal_id': signal_id,
                    'telegram_id': int(user_id),
                    'mt4_account': 12345,  # Default account for Phase 3
                    'symbol': signal.get('symbol'),
                    'action': signal.get('direction', 'BUY'),
                    'volume': lot_size,
                    'price': result.get('price', 0),
                    'sl': signal.get('stop_loss', 0),
                    'tp': signal.get('take_profit', 0),
                    'status': 'executed'
                }
                
                db.add_signal_history(signal_history)
                db.update_signal_status(signal_id, 'executed', 
                                      ticket=result.get('ticket'),
                                      executed_at=datetime.now())
                
                await query.edit_message_text(
                    f"✅ Trade executed successfully!\n\n"
                    f"Ticket: {result.get('ticket', 'N/A')}\n"
                    f"Symbol: {signal.get('symbol')}\n"
                    f"Direction: {signal.get('direction')}\n"
                    f"Lot Size: {lot_size}\n"
                    f"Entry Price: {result.get('price', 'Market')}\n"
                    f"SL: {signal.get('stop_loss')}\n"
                    f"TP: {signal.get('take_profit')}",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    f"❌ Trade execution failed!\n\n"
                    f"Error: {result.get('message', 'Unknown error')}\n\n"
                    f"Please try again or contact support.",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            await query.edit_message_text(
                f"❌ Error executing trade: {str(e)}\n\n"
                f"Please try again or contact support.",
                parse_mode="Markdown"
            )
    
    elif action == "reject":
        await query.edit_message_text(
            f"❌ Signal rejected:\n\n"
            f"Symbol: {signal.get('symbol')}\n"
            f"Direction: {signal.get('direction')}\n",
            parse_mode="Markdown"
        )
        
        # Remove from active signals
        if signal_id in signals:
            del signals[signal_id]
    
    elif action == "custom":
        # Show custom trade parameters form
        keyboard = [
            [InlineKeyboardButton("0.01", callback_data=f"lot_0.01_{signal_id}")],
            [InlineKeyboardButton("0.05", callback_data=f"lot_0.05_{signal_id}")],
            [InlineKeyboardButton("0.1", callback_data=f"lot_0.1_{signal_id}")],
            [InlineKeyboardButton("0.5", callback_data=f"lot_0.5_{signal_id}")],
            [InlineKeyboardButton("1.0", callback_data=f"lot_1.0_{signal_id}")],
            [InlineKeyboardButton("Cancel", callback_data=f"trade_{signal_id}_reject")]
        ]
        
        await query.edit_message_text(
            f"Select lot size for {signal.get('symbol')} {signal.get('direction')}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_settings_update(update: Update, context: ContextTypes.DEFAULT_TYPE, setting: str) -> None:
    """Handle settings updates."""
    query = update.callback_query
    user_id = str(update.effective_user.id)
    
    # Initialize user settings if not exists
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            "risk_percent": 1.0,
            "default_lot_size": 0.01,
            "auto_trade": False,
            "notifications": True
        }
    
    settings = user_data_store[user_id]
    
    if setting == "risk":
        # Cycle through risk percentages
        risk_options = [0.5, 1.0, 2.0, 3.0, 5.0]
        current_index = risk_options.index(settings["risk_percent"]) if settings["risk_percent"] in risk_options else 0
        new_index = (current_index + 1) % len(risk_options)
        settings["risk_percent"] = risk_options[new_index]
    
    elif setting == "lot":
        # Cycle through lot sizes
        lot_options = [0.01, 0.05, 0.1, 0.5, 1.0]
        current_index = lot_options.index(settings["default_lot_size"]) if settings["default_lot_size"] in lot_options else 0
        new_index = (current_index + 1) % len(lot_options)
        settings["default_lot_size"] = lot_options[new_index]
    
    elif setting == "auto":
        # Toggle auto-trade
        settings["auto_trade"] = not settings["auto_trade"]
    
    elif setting == "notify":
        # Toggle notifications
        settings["notifications"] = not settings["notifications"]
    
    elif setting == "save":
        # Save settings to database
        global db
        if db is None:
            db = get_database()
        
        # Save to database
        success = db.update_user_settings(int(user_id), settings)
        
        if success:
            await query.edit_message_text(
                "✅ Your settings have been saved successfully.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "❌ Failed to save settings. Please try again.",
                parse_mode="Markdown"
            )
        return
    
    # Update keyboard with new settings
    keyboard = [
        [InlineKeyboardButton(f"Risk: {settings['risk_percent']}%", callback_data="settings_risk")],
        [InlineKeyboardButton(f"Lot Size: {settings['default_lot_size']}", callback_data="settings_lot")],
        [InlineKeyboardButton(f"Auto-Trade: {'On' if settings['auto_trade'] else 'Off'}", callback_data="settings_auto")],
        [InlineKeyboardButton(f"Notifications: {'On' if settings['notifications'] else 'Off'}", callback_data="settings_notify")],
        [InlineKeyboardButton("Save Settings", callback_data="settings_save")]
    ]
    
    await query.edit_message_text(
        "⚙️ *Trading Settings*\n\n"
        "Configure your personal trading preferences:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_close_order(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket: str) -> None:
    """Handle order close request."""
    query = update.callback_query
    
    try:
        result = mt4_connector.close_order(ticket)
        
        if result.get("status") == "success":
            await query.edit_message_text(
                f"✅ Order #{ticket} closed successfully!\n\n"
                f"Profit: {result.get('profit', 'N/A')}",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ Failed to close order #{ticket}!\n\n"
                f"Error: {result.get('message', 'Unknown error')}",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error closing order: {e}")
        await query.edit_message_text(
            f"❌ Error closing order: {str(e)}",
            parse_mode="Markdown"
        )

async def handle_modify_order(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket: str) -> None:
    """Handle order modification request."""
    query = update.callback_query
    
    # Get order details
    order = next((o for o in mt4_connector.get_open_orders() if o['ticket'] == int(ticket)), None)
    
    if not order:
        await query.edit_message_text(
            f"⚠️ Order #{ticket} not found or already closed.",
            parse_mode="Markdown"
        )
        return
    
    # Set context for conversation
    context.user_data["modifying_order"] = order
    
    # Show modification options
    keyboard = [
        [InlineKeyboardButton("Modify Stop Loss", callback_data=f"mod_sl_{ticket}")],
        [InlineKeyboardButton("Modify Take Profit", callback_data=f"mod_tp_{ticket}")],
        [InlineKeyboardButton("Cancel", callback_data="mod_cancel")]
    ]
    
    await query.edit_message_text(
        f"🔧 *Modify Order #{ticket}*\n\n"
        f"Symbol: {order['symbol']}\n"
        f"Type: {order['type']}\n"
        f"Open Price: {order['open_price']}\n"
        f"Current Price: {order['current_price']}\n"
        f"Current SL: {order['sl']}\n"
        f"Current TP: {order['tp']}\n\n"
        f"Select what you want to modify:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def setup_bot(app):
    """Initialize and configure the Telegram bot."""
    global mt4_connector
    
    # Get token directly from environment (our single source of truth)
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise EnvironmentError("Telegram bot token not provided in environment variables")
    
    # Validate token format
    token_parts = token.split(':')
    if len(token_parts) != 2:
        raise ValueError("Invalid Telegram bot token format. Expected format: '123456789:ABCDefGhiJklmNoPQRstUvwxyz'")
    
    # Validate token parts
    try:
        # Validate first part is a number
        token_num = int(token_parts[0])
        
        # Validate second part is a non-empty string
        if not token_parts[1]:
            raise ValueError("Second part of token after ':' is empty")
        
        # Warning for short token keys but continue anyway
        if len(token_parts[1]) < 20:  
            logger.warning(f"Telegram token part after ':' is shorter than expected")
    except ValueError as e:
        # Only allow mock mode to continue with invalid token if explicitly configured
        mock_mode = app.config.get('MOCK_MODE', False)
        if mock_mode:
            logger.warning(f"Invalid token format: {str(e)}. Continuing in MOCK mode.")
            token = "mock:token_for_testing_purposes"
        else:
            raise ValueError(f"Invalid Telegram bot token: {str(e)}")
    
    # Clean any whitespace
    token = token.strip()
    
    # Test the token by creating a Bot instance
    mock_mode = app.config.get('MOCK_MODE', False)
    try:
        if not token.startswith("mock:"):
            test_bot = Bot(token=token)
            logger.info("Successfully created test Bot instance with the provided token")
    except InvalidToken as e:
        if not mock_mode:
            raise ValueError(f"The provided Telegram token is invalid: {e}")
        logger.warning(f"Invalid token: {e}. Continuing in MOCK mode with mock token.")
        token = "mock:token_for_testing_purposes"
    except TelegramError as e:
        if not mock_mode:
            raise ValueError(f"Telegram API error: {e}")
        logger.warning(f"Telegram API error: {e}. Continuing in MOCK mode.")
    except Exception as e:
        if not mock_mode:
            raise ValueError(f"Error testing token: {e}")
        logger.warning(f"Error testing token: {e}. Continuing in MOCK mode.")
    
    # Process user IDs directly from environment variables
    try:
        # Get allowed user IDs
        allowed_user_ids_raw = os.environ.get('ALLOWED_USER_IDS', '')
        allowed_user_ids = []
        
        for user_id in allowed_user_ids_raw.split(','):
            if user_id.strip():
                try:
                    allowed_user_ids.append(int(user_id.strip()))
                except ValueError:
                    logger.warning(f"Invalid user ID '{user_id}', must be numeric. Skipping.")
        
        # Get admin user IDs
        admin_user_ids_raw = os.environ.get('ADMIN_USER_IDS', '')
        admin_user_ids = []
        
        for user_id in admin_user_ids_raw.split(','):
            if user_id.strip():
                try:
                    admin_id = int(user_id.strip())
                    admin_user_ids.append(admin_id)
                    # Include admin users in allowed users list
                    if admin_id not in allowed_user_ids:
                        allowed_user_ids.append(admin_id)
                except ValueError:
                    logger.warning(f"Invalid admin ID '{user_id}', must be numeric. Skipping.")
        
        # Log the configured users
        logger.info(f"Configured admin users: {admin_user_ids}")
        logger.info(f"Configured allowed users: {allowed_user_ids}")
        
        # If no allowed users and in mock mode, add a default test user
        if not allowed_user_ids and mock_mode:
            default_user = 123456789
            logger.warning(f"No allowed users configured, adding default test user: {default_user}")
            allowed_user_ids.append(default_user)
        elif not allowed_user_ids:
            logger.warning("No allowed users configured. No users will be able to use the bot.")
    except Exception as e:
        logger.error(f"Error processing user IDs: {e}")
        raise ValueError(f"Error processing user IDs: {e}")
    
    # Use MT4 connector from app
    global mt4_connector
    mt4_connector = app.mt4_connector
    
    try:
        # Create the Application with proper builder pattern
        application = Application.builder().token(token).build()
        
        # Store configuration in bot_data
        application.bot_data["mock_mode"] = mock_mode
        application.bot_data["admin_users"] = admin_user_ids
        application.bot_data["allowed_users"] = allowed_user_ids
        application.bot_data["active_signals"] = {}  # Store active signals
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("register", register_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CommandHandler("orders", orders_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        
        # Add callback query handler for buttons
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Start the bot polling
        async def start_polling():
            await application.initialize()
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot polling started successfully")
            
        # Create a new async task to run the polling
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(start_polling())
        logger.info("Telegram bot setup completed successfully")
        
        return application
    except Exception as e:
        logger.error(f"Error initializing Telegram bot: {str(e)}")
        if not mock_mode:
            raise ValueError(f"Failed to initialize Telegram bot: {str(e)}")
        return None

# We have replaced _start_polling with a direct implementation inside setup_bot
# This function is kept for compatibility but will not be used
def _start_polling(application):
    """Deprecated: Start polling in a separate function to better handle errors"""
    logger.warning("_start_polling is deprecated - using integrated polling in setup_bot")
    return None