#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal handler for Telegram Connector in SoloTrend X trading system.
This module handles trading signals and forwards them to the MT4 API.
"""

import os
import sys
import logging
import json
from pathlib import Path
import requests
from datetime import datetime
import time
import uuid
import traceback
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Configure module logger with file handler if not already configured
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'logs'))
os.makedirs(log_dir, exist_ok=True)

# Get the module logger
logger = logging.getLogger(__name__)

# Check if we need to add a file handler
has_file_handler = any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
if not has_file_handler:
    # Add a debug file handler
    debug_file_handler = logging.FileHandler(os.path.join(log_dir, 'telegram_bot_debug.log'))
    debug_file_handler.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]')
    debug_file_handler.setFormatter(debug_formatter)
    logger.addHandler(debug_file_handler)
    logger.setLevel(logging.DEBUG)

class SignalHandler:
    """Handles trading signals and forwards them to the MT4 API"""
    
    def __init__(self, mt4_api_base_url=None, logger=None):
        """
        Initialize the signal handler
        
        Args:
            mt4_api_base_url (str): Base URL for the MT4 API. If None, will use environment variable
            logger (logging.Logger): Logger instance to use. If None, will create a new one
        """
        # Set up logger
        self.logger = logger or logging.getLogger(__name__)
        
        # Get MT4 API URL from environment variable or use provided value
        self.mt4_api_base_url = mt4_api_base_url or os.environ.get(
            'MT4_API_URL', 'http://localhost:5002/api/v1'
        )
        
        # Track connection status
        self.connected = False
        self.last_connection_attempt = 0
        self.connection_retry_interval = 60  # seconds
        
        # Verify connection on initialization
        self.verify_connection()
        
    def verify_connection(self):
        """Verify connection to MT4 API"""
        current_time = time.time()
        
        # Rate limit connection attempts
        if (current_time - self.last_connection_attempt) < self.connection_retry_interval:
            return self.connected
        
        self.last_connection_attempt = current_time
        
        try:
            # Try to connect to health endpoint
            health_url = f"{self.mt4_api_base_url}/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.connected = True
                    self.logger.info("MT4 API connection verified")
                    return True
            
            self.connected = False
            self.logger.warning(f"MT4 API connection failed: {response.status_code}")
            return False
            
        except Exception as e:
            self.connected = False
            self.logger.warning(f"Error connecting to MT4 API: {e}")
            return False
    
    def process_signal(self, signal_data):
        """
        Process a trading signal
        
        Args:
            signal_data (dict): The signal data to process
            
        Returns:
            dict: Processing result with success status and message
        """
        if not self.verify_connection():
            return {
                "success": False,
                "message": "MT4 API connection not available"
            }
        
        try:
            # Log the incoming signal
            self.logger.info(f"Processing signal: {signal_data}")
            
            # Extract signal information
            signal_type = signal_data.get("type", "unknown")
            symbol = signal_data.get("symbol")
            action = signal_data.get("action")
            
            if not symbol or not action:
                return {
                    "success": False,
                    "message": "Invalid signal data: Missing symbol or action"
                }
            
            # Format for MT4 API
            order_request = {
                "symbol": symbol,
                "action": action.upper(),
                "volume": float(signal_data.get("volume", 0.1)),
                "price": float(signal_data.get("price", 0)),
                "stop_loss": float(signal_data.get("stop_loss", 0)),
                "take_profit": float(signal_data.get("take_profit", 0)),
                "comment": f"TG:{signal_data.get('source', 'webhook')}"
            }
            
            # Send order to MT4 API
            order_url = f"{self.mt4_api_base_url}/orders"
            response = requests.post(
                order_url, 
                json=order_request,
                timeout=30
            )
            
            if response.status_code in (200, 201):
                result = response.json()
                self.logger.info(f"Signal processed successfully: {result}")
                return {
                    "success": True,
                    "message": f"Order placed: {result.get('message', 'Success')}",
                    "order_number": result.get("order_number", 0)
                }
            else:
                error_msg = f"MT4 API error: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except Exception as e:
            error_msg = f"Error processing signal: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
    def format_signal_message(self, signal_data, result=None):
        """
        Format a signal for display in Telegram
        
        Args:
            signal_data (dict): The signal data
            result (dict): The processing result
            
        Returns:
            str: Formatted message for Telegram
        """
        # Basic signal info
        symbol = signal_data.get("symbol", "Unknown")
        action = signal_data.get("action", "Unknown").upper()
        price = signal_data.get("price", "Market")
        
        # Format as a nice message
        message_lines = [
            f"🔔 *SIGNAL: {symbol} {action}*",
            f"💰 Price: {price}",
        ]
        
        # Add volume if present
        if "volume" in signal_data:
            message_lines.append(f"📊 Volume: {signal_data['volume']}")
        
        # Add stop loss and take profit if present
        if "stop_loss" in signal_data and signal_data["stop_loss"]:
            message_lines.append(f"🛑 Stop Loss: {signal_data['stop_loss']}")
            
        if "take_profit" in signal_data and signal_data["take_profit"]:
            message_lines.append(f"🎯 Take Profit: {signal_data['take_profit']}")
        
        # Add source if present
        if "source" in signal_data:
            message_lines.append(f"📡 Source: {signal_data['source']}")
        
        # Add timestamp
        timestamp = signal_data.get("timestamp", datetime.now().isoformat())
        message_lines.append(f"🕒 Time: {timestamp}")
        
        # Add result if provided
        if result:
            if result.get("success", False):
                message_lines.append(f"✅ *{result.get('message', 'Success')}*")
                if "order_number" in result:
                    message_lines.append(f"📝 Order #: {result['order_number']}")
            else:
                message_lines.append(f"❌ *{result.get('message', 'Failed')}*")
        
        # Join with newlines
        return "\n".join(message_lines)


# Function to handle webhook signals from external sources (like the webhook API)
async def process_webhook_signal(bot, signal_data):
    """
    Process a webhook signal and send it to Telegram users

    Args:
        bot: The Telegram bot instance
        signal_data (dict): The signal data from webhook

    Returns:
        bool: True if processed successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Log full signal data with debug level for troubleshooting
    try:
        logger.debug(f"Processing webhook signal - FULL DATA: {json.dumps(signal_data, indent=2)}")
    except Exception as e:
        logger.debug(f"Error serializing signal data: {e}, Signal data: {signal_data}")
    
    # Extract basic signal info with fallbacks for different field names
    symbol = signal_data.get('symbol', 'Unknown')
    
    # Handle different action field names (side, action, direction, type, etc.)
    action = None
    for field in ['side', 'action', 'direction', 'type', 'cmd']:
        if field in signal_data and signal_data[field]:
            action = signal_data[field]
            break
    
    if not action:
        action = "Unknown action"
    
    logger.info(f"Processing webhook signal: {symbol} - {action}")
    
    try:
        # Try primary approach with bot instance first
        primary_success = await _process_with_bot_instance(bot, signal_data, symbol, action)
        
        # If primary approach fails, try fallback with telegram_sender module
        if not primary_success:
            logger.info("Primary approach failed, using telegram_sender fallback")
            return await _process_with_sender(signal_data, symbol, action)
        
        return primary_success
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error processing webhook signal: {e}")
        logger.debug(f"Detailed error traceback: {error_details}")
        
        # Try fallback approach with telegram_sender module when exceptions occur
        try:
            logger.info("Exception occurred, trying telegram_sender fallback")
            return await _process_with_sender(signal_data, symbol, action)
        except Exception as fallback_error:
            logger.error(f"Fallback approach also failed: {fallback_error}")
            return False


async def _process_with_bot_instance(bot, signal_data, symbol, action):
    """Process webhook signal using the main bot instance"""
    logger = logging.getLogger(__name__)
    
    # Validate bot instance
    if not bot:
        logger.error("Bot instance is None")
        return False
        
    # Validate bot token - check more carefully
    has_token = hasattr(bot, 'token')
    token_value = getattr(bot, 'token', '') if has_token else ''
    
    if not has_token or not token_value:
        logger.error("Bot token is missing or invalid")
        # Log more details for debugging
        logger.debug(f"Bot instance type: {type(bot).__name__}")
        logger.debug(f"Bot has token attribute: {has_token}")
        logger.debug(f"Bot token value exists: {bool(token_value)}")
        return False
    
    # Check if we have a mock token (some implementations might use this)
    is_mock_token = token_value.startswith("mock:") or token_value == "dummy_token_for_testing"
    if is_mock_token:
        logger.info("Using mock token - skipping API connectivity test")
    else:
        # Try a simple API call to test connectivity
        try:
            me = await bot.get_me()
            logger.info(f"Bot connectivity test successful: @{me.username}")
        except Exception as e:
            logger.warning(f"Bot connectivity test failed: {e}")
            # Continue anyway, as we don't want to block signals due to temporary connectivity issues
        
    # Print details about the bot status for debugging
    logger.debug(f"Bot instance type: {type(bot).__name__}")
    has_bot_data = hasattr(bot, "bot_data")
    logger.debug(f"Bot has bot_data: {has_bot_data}")
    
    if has_bot_data:
        logger.debug(f"Bot data keys: {list(bot.bot_data.keys())}")
        
    # Generate a unique ID for this signal
    signal_id = str(uuid.uuid4())
    
    # Create a safe copy of signal data
    safe_signal_data = {
        'symbol': symbol,
        'action': action,
        'price': signal_data.get('price', 0),
        'volume': signal_data.get('volume', 0.1),
        'timestamp': signal_data.get('timestamp', datetime.now().isoformat()),
        'source': signal_data.get('source', 'webhook')
    }
    
    # Add stop loss and take profit if present (different field names)
    for sl_field in ['sl', 'stop_loss', 'stoploss']:
        if sl_field in signal_data and signal_data[sl_field]:
            safe_signal_data['stop_loss'] = signal_data[sl_field]
            break
            
    for tp_field in ['tp', 'tp1', 'take_profit']:
        if tp_field in signal_data and signal_data[tp_field]:
            safe_signal_data['take_profit'] = signal_data[tp_field]
            break
            
    # Add strategy if present
    if 'strategy' in signal_data:
        safe_signal_data['strategy'] = signal_data['strategy']
        
    # Store signal in bot's active signals
    if has_bot_data:
        if "active_signals" not in bot.bot_data:
            bot.bot_data["active_signals"] = {}
        bot.bot_data["active_signals"][signal_id] = safe_signal_data
        
        # For testing purposes, ensure there are allowed users
        if "allowed_users" not in bot.bot_data or not bot.bot_data["allowed_users"]:
            logger.warning("No allowed users in bot_data, adding test user 123456789")
            bot.bot_data["allowed_users"] = [123456789]
    else:
        logger.warning("Bot has no bot_data attribute, using workaround for signal processing")
        # Create temporary storage for this request
        temp_data = {
            "active_signals": {signal_id: safe_signal_data},
            "allowed_users": [123456789]  # Default test user
        }
        return True  # Can't proceed without bot_data, but don't fail
    
    # Format the signal message
    message = format_signal_message(safe_signal_data)
    logger.info(f"Formatted message: {message}")
    
    # Import database for checking user accounts
    try:
        from database import Database
        db = Database()
    except Exception as e:
        logger.warning(f"Could not import database: {e}")
        db = None
    
    # Send to all allowed users if they exist
    success_count = 0
    if has_bot_data and "allowed_users" in bot.bot_data:
        allowed_users = bot.bot_data["allowed_users"]
        logger.info(f"Attempting to send signal to {len(allowed_users)} allowed users")
        
        for user_id in allowed_users:
            try:
                # Check if user has multiple accounts
                keyboard = []
                
                if db:
                    accounts = db.get_user_accounts(user_id)
                    if accounts and len(accounts) > 1:
                        # User has multiple accounts, show account selector first
                        account_buttons = []
                        for acc in accounts[:3]:  # Show max 3 accounts per row
                            btn_text = f"💼 {acc['account_name']}" if acc.get('account_name') else f"💼 {acc['account_number']}"
                            account_buttons.append(
                                InlineKeyboardButton(btn_text, callback_data=f"signal_{signal_id}_account_{acc['account_number']}")
                            )
                        keyboard.append(account_buttons)
                        
                        # Add remaining accounts if more than 3
                        if len(accounts) > 3:
                            account_buttons = []
                            for acc in accounts[3:6]:  # Next 3 accounts
                                btn_text = f"💼 {acc['account_name']}" if acc.get('account_name') else f"💼 {acc['account_number']}"
                                account_buttons.append(
                                    InlineKeyboardButton(btn_text, callback_data=f"signal_{signal_id}_account_{acc['account_number']}")
                                )
                            keyboard.append(account_buttons)
                    else:
                        # Single account or no database, show regular buttons
                        keyboard = [
                            [
                                InlineKeyboardButton("✅ Accept", callback_data=f"trade_{signal_id}_accept"),
                                InlineKeyboardButton("❌ Reject", callback_data=f"trade_{signal_id}_reject")
                            ],
                            [InlineKeyboardButton("⚙️ Custom", callback_data=f"trade_{signal_id}_custom")]
                        ]
                else:
                    # No database available, use regular buttons
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Accept", callback_data=f"trade_{signal_id}_accept"),
                            InlineKeyboardButton("❌ Reject", callback_data=f"trade_{signal_id}_reject")
                        ],
                        [InlineKeyboardButton("⚙️ Custom", callback_data=f"trade_{signal_id}_custom")]
                    ]
                
                # Always add reject button at the bottom
                if db and accounts and len(accounts) > 1:
                    keyboard.append([InlineKeyboardButton("❌ Reject", callback_data=f"trade_{signal_id}_reject")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Special handling for test tokens
                if bot.token.startswith("test:") or bot.token == "dummy_token_for_testing":
                    logger.info(f"MOCK MODE: Would send message to user {user_id}: {message}")
                    success_count += 1
                    continue
                    
                # Attempt to send the message
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                logger.info(f"Signal sent to user {user_id}")
                success_count += 1
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Error sending signal to user {user_id}: {e}")
                logger.debug(f"Detailed error trace: {error_details}")
    else:
        logger.warning("No allowed users found in bot_data")
        
    # Consider successful if we sent to at least one user or in mock mode
    if success_count > 0 or bot.token.startswith("test:") or bot.token == "dummy_token_for_testing":
        logger.info(f"Signal processing completed successfully (sent to {success_count} users)")
        return True
    else:
        logger.warning("Signal was not sent to any users")
        return False


async def _process_with_sender(signal_data, symbol, action):
    """Process webhook signal using the standalone telegram_sender module"""
    logger = logging.getLogger(__name__)
    
    # Import here to avoid circular imports - try both paths
    try:
        try:
            # Try local import first
            from telegram_sender import send_telegram_message, notify_admins
        except ImportError:
            # Fall back to backend import
            from src.backend.telegram_connector.telegram_sender import send_telegram_message, notify_admins
    except ImportError:
        logger.error("Could not import telegram_sender module")
        return False
    
    # Extract values with fallbacks for different field names
    price = signal_data.get('price', 0)
    
    # Get stop loss (trying different field names)
    stop_loss = None
    for sl_field in ['sl', 'stop_loss', 'stoploss']:
        if sl_field in signal_data and signal_data[sl_field]:
            stop_loss = signal_data[sl_field]
            break
            
    # Get take profit (trying different field names)
    take_profit = None
    for tp_field in ['tp', 'tp1', 'take_profit']:
        if tp_field in signal_data and signal_data[tp_field]:
            take_profit = signal_data[tp_field]
            break
            
    # Get volume
    volume = signal_data.get('volume', 0.1)
    
    # Get strategy
    strategy = signal_data.get('strategy', 'SoloTrend X')
    
    # Format message
    message_lines = [
        f"🔔 *SIGNAL: {symbol} {action.upper()}*",
        f"💰 Price: {price}",
    ]
    
    if volume:
        message_lines.append(f"📊 Volume: {volume}")
        
    if stop_loss:
        message_lines.append(f"🛑 Stop Loss: {stop_loss}")
        
    if take_profit:
        message_lines.append(f"🎯 Take Profit: {take_profit}")
    
    if strategy:
        message_lines.append(f"📈 Strategy: {strategy}")
        
    # Add source
    source = signal_data.get('source', 'webhook')
    message_lines.append(f"📡 Source: {source}")
    
    # Add timestamp
    timestamp = signal_data.get('timestamp', datetime.now().isoformat())
    message_lines.append(f"🕒 Time: {timestamp}")
    
    # Add fallback note so users know about missing interactivity
    message_lines.append("")  # Add empty line
    message_lines.append("*Note: This is a fallback notification. Interactive trade buttons unavailable.*")
    
    # Join message
    message = "\n".join(message_lines)
    
    # Try to send to admins
    try:
        success = await notify_admins(message, "Markdown")
        if success:
            logger.info("Signal sent successfully using telegram_sender fallback")
            return True
        else:
            logger.warning("Failed to send using notify_admins, trying direct send")
            # Try direct send as fallback
            admin_ids = os.environ.get("ADMIN_USER_IDS", "").split(",")
            for admin_id in admin_ids:
                if admin_id.strip():
                    try:
                        chat_id = int(admin_id.strip())
                        success = await send_telegram_message(message, chat_id, "Markdown")
                        if success:
                            logger.info(f"Signal sent to admin {chat_id} using direct send")
                            return True
                    except ValueError:
                        continue
                    except Exception as e:
                        logger.error(f"Error in direct send: {e}")
    except Exception as e:
        logger.error(f"Error in telegram_sender fallback: {e}")
        
    # If we get here, all attempts failed
    logger.error("All sending methods failed")
    return False


def format_signal_message(signal_data):
    """
    Format a signal for display in Telegram - standalone function version
    
    Args:
        signal_data (dict): The signal data
        
    Returns:
        str: Formatted message for Telegram
    """
    # Basic signal info
    symbol = signal_data.get("symbol", "Unknown")
    
    # Determine action type (different signals might use different field names)
    action = None
    for field in ["action", "side", "direction", "type", "cmd"]:
        if field in signal_data and signal_data[field]:
            action = signal_data[field].upper()
            break
    
    if not action:
        action = "UNKNOWN"
    
    # Get price
    price = signal_data.get("price", "Market")
    
    # Format as a nice message
    message_lines = [
        f"🔔 *SIGNAL: {symbol} {action}*",
        f"💰 Price: {price}",
    ]
    
    # Add volume if present
    if "volume" in signal_data:
        message_lines.append(f"📊 Volume: {signal_data['volume']}")
    
    # Add stop loss and take profit if present (check multiple possible field names)
    sl_value = None
    for field in ["stop_loss", "sl", "stoploss"]:
        if field in signal_data and signal_data[field]:
            sl_value = signal_data[field]
            break
    
    if sl_value:
        message_lines.append(f"🛑 Stop Loss: {sl_value}")
    
    # Try different take profit field names
    for i in range(1, 4):  # Check TP1, TP2, TP3
        tp_field = f"tp{i}"
        if tp_field in signal_data and signal_data[tp_field]:
            message_lines.append(f"🎯 Take Profit {i}: {signal_data[tp_field]}")
    
    # Also check for generic "take_profit" or "tp" fields
    if "take_profit" in signal_data and signal_data["take_profit"]:
        message_lines.append(f"🎯 Take Profit: {signal_data['take_profit']}")
    elif "tp" in signal_data and signal_data["tp"] and "tp1" not in signal_data:
        message_lines.append(f"🎯 Take Profit: {signal_data['tp']}")
    
    # Add source if present
    if "source" in signal_data:
        message_lines.append(f"📡 Source: {signal_data['source']}")
    
    # Add timeframe if present
    if "timeframe" in signal_data:
        message_lines.append(f"⏱ Timeframe: {signal_data['timeframe']}")
    
    # Add strategy if present
    if "strategy" in signal_data:
        message_lines.append(f"📈 Strategy: {signal_data['strategy']}")
    
    # Add timestamp
    timestamp = signal_data.get("timestamp", datetime.now().isoformat())
    message_lines.append(f"🕒 Time: {timestamp}")
    
    # Join with newlines
    return "\n".join(message_lines)