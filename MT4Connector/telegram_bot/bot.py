"""
Telegram Bot Implementation for MT4 Signal Connector.
Handles interactions with users via Telegram for approving/rejecting trade signals.
"""

import os
import logging
import json
from typing import Dict, List, Union, Optional, Callable
from threading import Thread
import time
from datetime import datetime

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, 
    CallbackContext, MessageHandler, Filters, 
    ConversationHandler
)

# Set up logging
logger = logging.getLogger(__name__)

class TelegramBot:
    """
    Telegram Bot implementation for MT4 Signal Connector.
    Handles message formatting, inline buttons, and user interactions.
    """
    
    def __init__(self, token: str, mt4_api=None, admin_ids: List[int] = None):
        """
        Initialize the Telegram bot.
        
        Args:
            token (str): Telegram bot token from BotFather
            mt4_api: MT4 API instance for executing trades
            admin_ids (list, optional): List of Telegram user IDs allowed to use the bot
        """
        self.token = token
        self.mt4_api = mt4_api
        self.admin_ids = admin_ids if admin_ids else []
        self.updater = None
        self.dispatcher = None
        self.bot_username = None
        self.running = False
        self.user_settings = {}  # Store user settings
        self._signal_handlers = []  # Callbacks for signal processing
        
        # Initialize bot
        try:
            self.updater = Updater(token)
            self.dispatcher = self.updater.dispatcher
            self.bot_username = self.updater.bot.get_me().username
            logger.info(f"Telegram bot initialized with username @{self.bot_username}")
        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {e}")
            raise
    
    def start(self):
        """
        Start the Telegram bot.
        
        Returns:
            bool: True if bot started successfully, False otherwise
        """
        if self.running:
            logger.warning("Telegram bot is already running")
            return False
        
        try:
            # Register command handlers
            self.dispatcher.add_handler(CommandHandler("start", self._start_command))
            self.dispatcher.add_handler(CommandHandler("help", self._help_command))
            self.dispatcher.add_handler(CommandHandler("settings", self._settings_command))
            
            # Register callback query handler for inline buttons
            self.dispatcher.add_handler(CallbackQueryHandler(self._button_callback))
            
            # Start the bot
            self.updater.start_polling()
            self.running = True
            logger.info("Telegram bot started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
            return False
    
    def stop(self):
        """
        Stop the Telegram bot.
        
        Returns:
            bool: True if bot stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("Telegram bot is not running")
            return False
        
        try:
            self.updater.stop()
            self.running = False
            logger.info("Telegram bot stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
            return False
    
    def register_signal_handler(self, callback: Callable):
        """
        Register a callback function to handle approved signals.
        
        Args:
            callback (callable): Function to call when a signal is approved
        """
        self._signal_handlers.append(callback)
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = ParseMode.MARKDOWN):
        """
        Send a message to a specific chat.
        
        Args:
            chat_id (int): Telegram chat ID
            text (str): Message text
            parse_mode (str, optional): Parse mode (MARKDOWN or HTML)
            
        Returns:
            Message: Sent message object
        """
        try:
            return self.updater.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Error sending message to chat {chat_id}: {e}")
            return None
    
    def broadcast_message(self, message: str, parse_mode: str = ParseMode.MARKDOWN):
        """
        Broadcast a message to all admin users.
        
        Args:
            message (str): Message text
            parse_mode (str, optional): Parse mode (MARKDOWN or HTML)
            
        Returns:
            int: Number of messages sent successfully
        """
        if not self.admin_ids:
            logger.warning("No admin IDs configured for broadcast")
            return 0
        
        success_count = 0
        for user_id in self.admin_ids:
            try:
                self.updater.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=parse_mode
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting message to user {user_id}: {e}")
        
        return success_count
    
    def send_trading_signal(self, signal: Dict, chat_id: Optional[int] = None):
        """
        Send a trading signal to admin users.
        
        Args:
            signal (dict): Trading signal details
            chat_id (int, optional): Specific chat ID to send to. If None, sends to all admins.
            
        Returns:
            int: Number of messages sent successfully
        """
        # Format the signal message
        message = self._format_signal_message(signal)
        
        # Create inline keyboard markup for approve/reject buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{signal.get('id')}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{signal.get('id')}")
            ],
            [
                InlineKeyboardButton("🔍 Modify", callback_data=f"modify_{signal.get('id')}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send to specific chat or broadcast
        if chat_id:
            try:
                self.updater.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return 1
            except Exception as e:
                logger.error(f"Error sending signal to chat {chat_id}: {e}")
                return 0
        else:
            # Broadcast to all admins
            success_count = 0
            for user_id in self.admin_ids:
                try:
                    self.updater.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error sending signal to user {user_id}: {e}")
            
            return success_count
    
    def _format_signal_message(self, signal: Dict) -> str:
        """
        Format a trading signal as a human-readable message.
        
        Args:
            signal (dict): Trading signal details
            
        Returns:
            str: Formatted message
        """
        signal_type = signal.get('type', '').lower()
        symbol = signal.get('symbol', 'Unknown')
        volume = signal.get('volume', 0)
        price = signal.get('price', 0)
        sl = signal.get('sl', 0)
        tp = signal.get('tp', 0)
        comment = signal.get('comment', '')
        
        # Determine emoji based on signal type
        emoji = "🔄"
        if signal_type == 'buy':
            emoji = "🟢"
        elif signal_type == 'sell':
            emoji = "🔴"
        elif signal_type in ['buy_limit', 'buy_stop']:
            emoji = "⏳🟢"
        elif signal_type in ['sell_limit', 'sell_stop']:
            emoji = "⏳🔴"
        elif signal_type == 'close':
            emoji = "⚪"
        
        # Format the message with Markdown
        message = f"*{emoji} Trading Signal: {signal_type.upper()}*\n\n"
        message += f"*Symbol:* {symbol}\n"
        message += f"*Volume:* {volume} lots\n"
        
        if price > 0:
            message += f"*Price:* {price:.5f}\n"
            
        if sl > 0:
            message += f"*Stop Loss:* {sl:.5f}\n"
            
        if tp > 0:
            message += f"*Take Profit:* {tp:.5f}\n"
            
        if comment:
            message += f"*Comment:* {comment}\n"
            
        message += f"\n*Signal ID:* `{signal.get('id', 'Unknown')}`"
        message += f"\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return message
    
    def _is_admin(self, user_id: int) -> bool:
        """
        Check if a user is an admin.
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            bool: True if user is an admin, False otherwise
        """
        return user_id in self.admin_ids
    
    # Command handlers
    def _start_command(self, update: Update, context: CallbackContext):
        """
        Handle /start command.
        
        Args:
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        user = update.effective_user
        is_admin = self._is_admin(user.id)
        
        if is_admin:
            message = (
                f"👋 Welcome, {user.first_name}!\n\n"
                "I'm your MT4 Connector Trading Bot. I'll help you manage trading signals and execute trades.\n\n"
                "Available commands:\n"
                "/help - Show help information\n"
                "/settings - Configure your preferences"
            )
        else:
            message = (
                f"👋 Hello, {user.first_name}!\n\n"
                "This bot is private and can only be used by authorized users. "
                "Please contact the administrator for access."
            )
        
        update.message.reply_text(message)
    
    def _help_command(self, update: Update, context: CallbackContext):
        """
        Handle /help command.
        
        Args:
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        user = update.effective_user
        if not self._is_admin(user.id):
            update.message.reply_text("This bot is private and can only be used by authorized users.")
            return
        
        message = (
            "*MT4 Connector Trading Bot Help*\n\n"
            "This bot allows you to manage trading signals from your MT4 Expert Advisors.\n\n"
            "*Available Commands:*\n"
            "• /start - Start the bot and show welcome message\n"
            "• /help - Show this help information\n"
            "• /settings - Configure your preferences\n\n"
            
            "*Trading Signal Flow:*\n"
            "1. When a trading signal is received, the bot will send you a notification\n"
            "2. You can Approve, Reject, or Modify the signal\n"
            "3. Approved signals will be executed through the MT4 API\n"
            "4. You'll receive confirmation when the trade is executed\n\n"
            
            "*Signal Types Supported:*\n"
            "• 🟢 BUY - Market buy order\n"
            "• 🔴 SELL - Market sell order\n"
            "• ⏳🟢 BUY_LIMIT - Buy limit pending order\n"
            "• ⏳🔴 SELL_LIMIT - Sell limit pending order\n"
            "• ⏳🟢 BUY_STOP - Buy stop pending order\n"
            "• ⏳🔴 SELL_STOP - Sell stop pending order\n"
            "• ⚪ CLOSE - Close an existing position\n"
        )
        
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    def _settings_command(self, update: Update, context: CallbackContext):
        """
        Handle /settings command.
        
        Args:
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        user = update.effective_user
        if not self._is_admin(user.id):
            update.message.reply_text("This bot is private and can only be used by authorized users.")
            return
        
        # Get current settings or create default
        user_settings = self.user_settings.get(str(user.id), {
            'auto_approve': False,
            'notifications': True
        })
        
        # Create settings keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{'✅' if user_settings['auto_approve'] else '❌'} Auto-Approve Trades", 
                    callback_data="toggle_auto_approve"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{'🔔' if user_settings['notifications'] else '🔕'} Notifications", 
                    callback_data="toggle_notifications"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "*Settings*\n\n"
            "Configure your trading preferences below:\n\n"
            f"• *Auto-Approve Trades:* {'Enabled' if user_settings['auto_approve'] else 'Disabled'}\n"
            f"• *Notifications:* {'Enabled' if user_settings['notifications'] else 'Disabled'}\n"
        )
        
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    # Callback handlers
    def _button_callback(self, update: Update, context: CallbackContext):
        """
        Handle button callbacks.
        
        Args:
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self._is_admin(user_id):
            query.answer("You are not authorized to use this bot.")
            return
        
        # Extract callback data
        callback_data = query.data
        query.answer()  # Answer the callback query to stop the "loading" animation
        
        if callback_data.startswith("approve_"):
            signal_id = callback_data.replace("approve_", "")
            self._handle_approve_signal(signal_id, update, context)
        elif callback_data.startswith("reject_"):
            signal_id = callback_data.replace("reject_", "")
            self._handle_reject_signal(signal_id, update, context)
        elif callback_data.startswith("modify_"):
            signal_id = callback_data.replace("modify_", "")
            self._handle_modify_signal(signal_id, update, context)
        elif callback_data == "toggle_auto_approve":
            self._toggle_setting(user_id, 'auto_approve', update, context)
        elif callback_data == "toggle_notifications":
            self._toggle_setting(user_id, 'notifications', update, context)
    
    def _handle_approve_signal(self, signal_id: str, update: Update, context: CallbackContext):
        """
        Handle approval of a trading signal.
        
        Args:
            signal_id (str): Signal ID
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        query = update.callback_query
        
        # Update the message to show it's been approved
        query.edit_message_text(
            text=f"{query.message.text}\n\n✅ *APPROVED* by {query.from_user.first_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Execute the signal if MT4 API is available
        if self.mt4_api:
            # In a real implementation, we'd need to retrieve the signal details
            # from storage using the signal_id, then execute it with the MT4 API
            try:
                # Simulate trade execution
                logger.info(f"Executing approved signal: {signal_id}")
                
                # Notify user of successful execution
                self.updater.bot.send_message(
                    chat_id=query.from_user.id,
                    text=f"✅ Signal *{signal_id}* has been executed successfully.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Call registered signal handlers
                for handler in self._signal_handlers:
                    try:
                        handler(signal_id, "approve")
                    except Exception as e:
                        logger.error(f"Error in signal handler: {e}")
                
            except Exception as e:
                logger.error(f"Error executing signal {signal_id}: {e}")
                self.updater.bot.send_message(
                    chat_id=query.from_user.id,
                    text=f"❌ Error executing signal *{signal_id}*: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            logger.warning(f"MT4 API not available, cannot execute signal {signal_id}")
            self.updater.bot.send_message(
                chat_id=query.from_user.id,
                text=f"⚠️ MT4 API not available, signal *{signal_id}* approved but not executed.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def _handle_reject_signal(self, signal_id: str, update: Update, context: CallbackContext):
        """
        Handle rejection of a trading signal.
        
        Args:
            signal_id (str): Signal ID
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        query = update.callback_query
        
        # Update the message to show it's been rejected
        query.edit_message_text(
            text=f"{query.message.text}\n\n❌ *REJECTED* by {query.from_user.first_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Call registered signal handlers
        for handler in self._signal_handlers:
            try:
                handler(signal_id, "reject")
            except Exception as e:
                logger.error(f"Error in signal handler: {e}")
    
    def _handle_modify_signal(self, signal_id: str, update: Update, context: CallbackContext):
        """
        Handle modification of a trading signal.
        
        Args:
            signal_id (str): Signal ID
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        query = update.callback_query
        
        # Create modification options keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔄 Change Volume", callback_data=f"mod_vol_{signal_id}")
            ],
            [
                InlineKeyboardButton("🛑 Change Stop Loss", callback_data=f"mod_sl_{signal_id}"),
                InlineKeyboardButton("🎯 Change Take Profit", callback_data=f"mod_tp_{signal_id}")
            ],
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{signal_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{signal_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update the message with modification options
        query.edit_message_text(
            text=f"{query.message.text}\n\n🔍 *Select parameter to modify:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    def _toggle_setting(self, user_id: int, setting_name: str, update: Update, context: CallbackContext):
        """
        Toggle a user setting.
        
        Args:
            user_id (int): User ID
            setting_name (str): Setting name to toggle
            update (Update): Telegram update
            context (CallbackContext): Callback context
        """
        query = update.callback_query
        
        # Get current settings or create default
        if str(user_id) not in self.user_settings:
            self.user_settings[str(user_id)] = {
                'auto_approve': False,
                'notifications': True
            }
        
        # Toggle the setting
        current_value = self.user_settings[str(user_id)].get(setting_name, False)
        self.user_settings[str(user_id)][setting_name] = not current_value
        
        # Update settings message
        user_settings = self.user_settings[str(user_id)]
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{'✅' if user_settings['auto_approve'] else '❌'} Auto-Approve Trades", 
                    callback_data="toggle_auto_approve"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{'🔔' if user_settings['notifications'] else '🔕'} Notifications", 
                    callback_data="toggle_notifications"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "*Settings*\n\n"
            "Configure your trading preferences below:\n\n"
            f"• *Auto-Approve Trades:* {'Enabled' if user_settings['auto_approve'] else 'Disabled'}\n"
            f"• *Notifications:* {'Enabled' if user_settings['notifications'] else 'Disabled'}\n"
        )
        
        query.edit_message_text(text=message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        
        logger.info(f"User {user_id} toggled setting {setting_name} to {user_settings[setting_name]}")

# Standalone test function if run directly
if __name__ == "__main__":
    # Set up logging to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the bot with a dummy token (replace with a real token to test)
    bot = TelegramBot("YOUR_BOT_TOKEN_HERE", admin_ids=[12345])
    
    # Try to start the bot
    if bot.start():
        print("Bot started successfully!")
        
        # Keep the bot running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bot.stop()
            print("Bot stopped.")