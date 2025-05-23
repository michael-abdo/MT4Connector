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
        "*Account Management:*\n"
        "/register - Create your account\n"
        "/login - Manage MT4 accounts\n"
        "/accounts - View all your accounts\n"
        "/dashboard - Multi-account dashboard\n\n"
        "*Trading:*\n"
        "/status - Check MT4 connection status\n"
        "/settings - Configure trading settings\n"
        "/orders - View and manage open orders\n"
        "/cancel - Cancel current operation\n\n"
        "*Statistics:*\n"
        "/stats - View trading statistics\n\n"
        "*Other:*\n"
        "/start - Welcome message\n"
        "/help - Show this help message\n\n"
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
    """Configure per-account trading settings."""
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
    
    # Get user's accounts
    accounts = db.get_user_accounts(user_id)
    if not accounts:
        await update.message.reply_text(
            "❌ You need to add an MT4 account first!\n\n"
            "Use /login to add your MT4 account."
        )
        return
    
    # If user has multiple accounts, show account selector
    if len(accounts) > 1:
        keyboard = []
        for acc in accounts:
            if acc['is_active']:
                btn_text = f"⚙️ {acc['account_name']}" if acc.get('account_name') else f"⚙️ Account {acc['account_number']}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"settings_account_{acc['account_number']}")])
        
        await update.message.reply_text(
            "⚙️ *Select Account for Settings*\n\n"
            "Choose which account to configure:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        # Single account, show settings directly
        account = accounts[0]
        await show_account_settings(update, context, account['account_number'])

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

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage MT4 accounts."""
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
    
    # Get command arguments
    args = context.args
    
    if not args:
        # Show account list
        accounts = db.get_user_accounts(user_id)
        
        if not accounts:
            await update.message.reply_text(
                "📭 You don't have any MT4 accounts configured.\n\n"
                "To add an account:\n"
                "/login add <account_number> <server> <password> <name>\n\n"
                "Example:\n"
                "/login add 12345 demo.mt4.com:443 mypass123 Demo Account"
            )
        else:
            # Format account list
            message = "📊 *Your MT4 Accounts*\n\n"
            
            for acc in accounts:
                default = "✅" if acc['is_default'] else "⚪"
                message += (
                    f"{default} *{acc['account_name']}*\n"
                    f"   Account: {acc['account_number']}\n"
                    f"   Server: {acc['server']}\n\n"
                )
            
            message += (
                "Commands:\n"
                "/login switch <account_number> - Switch account\n"
                "/login add <number> <server> <pass> <name> - Add account\n"
                "/login remove <account_number> - Remove account"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
    
    elif args[0] == "add":
        # Add new account
        if len(args) < 5:
            await update.message.reply_text(
                "❌ Invalid format.\n\n"
                "Usage: /login add <account_number> <server> <password> <name>\n"
                "Example: /login add 12345 demo.mt4.com:443 mypass123 Demo Account"
            )
            return
        
        try:
            account_number = int(args[1])
            server = args[2]
            password = args[3]
            account_name = " ".join(args[4:])
            
            # Check if first account (make it default)
            accounts = db.get_user_accounts(user_id)
            is_default = len(accounts) == 0
            
            # Add account
            success = db.add_mt4_account(
                telegram_id=user_id,
                account_number=account_number,
                account_name=account_name,
                server=server,
                password=password,
                is_default=is_default
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ Account {account_name} added successfully!\n"
                    f"Account number: {account_number}\n"
                    f"{'This is now your default account.' if is_default else ''}"
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to add account. It may already exist."
                )
                
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid account number. Must be numeric."
            )
    
    elif args[0] == "switch":
        # Switch default account
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Please specify account number.\n"
                "Usage: /login switch <account_number>"
            )
            return
        
        try:
            account_number = int(args[1])
            
            # Check if user owns this account
            accounts = db.get_user_accounts(user_id)
            if not any(acc['account_number'] == account_number for acc in accounts):
                await update.message.reply_text(
                    "❌ Account not found. Use /login to see your accounts."
                )
                return
            
            # Set as default
            success = db.set_default_account(user_id, account_number)
            
            if success:
                await update.message.reply_text(
                    f"✅ Switched to account {account_number}"
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to switch account."
                )
                
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid account number."
            )
    
    elif args[0] == "remove":
        # Remove account
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Please specify account number.\n"
                "Usage: /login remove <account_number>"
            )
            return
        
        try:
            account_number = int(args[1])
            
            # Remove account
            success = db.remove_account(user_id, account_number)
            
            if success:
                await update.message.reply_text(
                    f"✅ Account {account_number} removed."
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to remove account."
                )
                
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid account number."
            )
    
    else:
        await update.message.reply_text(
            "❌ Unknown command. Use /login to see available options."
        )

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show multi-account trading dashboard."""
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
    
    # Get user's accounts
    accounts = db.get_user_accounts(user_id)
    if not accounts:
        await update.message.reply_text(
            "❌ You don't have any MT4 accounts yet.\n"
            "Use /login to add your first account."
        )
        return
    
    # Build dashboard message
    message = "📊 *Multi-Account Trading Dashboard*\n"
    message += "━" * 30 + "\n\n"
    
    total_trades = 0
    total_profit = 0.0
    
    for acc in accounts:
        if not acc['is_active']:
            continue
            
        # Get account settings
        settings = db.get_account_settings(acc['account_number'])
        
        # Get account statistics (from signal history)
        stats = db.get_account_stats(acc['account_number'])
        
        # Account header
        account_name = acc['account_name'] if acc.get('account_name') else f"Account {acc['account_number']}"
        is_default = "⭐ " if acc['is_default'] else ""
        
        message += f"{is_default}*{account_name}*\n"
        message += f"├ Server: {acc['server']}\n"
        message += f"├ Account: {acc['account_number']}\n"
        message += f"├ Lot Size: {settings['default_lot_size']}\n"
        message += f"├ Risk: {settings['risk_percent']}%\n"
        message += f"├ Auto-Trade: {'✅' if settings['auto_trade'] else '❌'}\n"
        
        # Add stats if available
        if stats:
            executed = stats.get('executed_trades', 0)
            win_rate = stats.get('win_rate', 0)
            net_profit = stats.get('net_profit', 0)
            
            message += f"├ Trades: {executed}\n"
            message += f"├ Win Rate: {win_rate:.1f}%\n"
            message += f"└ P&L: ${net_profit:.2f}\n"
            
            total_trades += executed
            total_profit += net_profit
        else:
            message += f"└ No trades yet\n"
        
        message += "\n"
    
    # Add summary
    message += "━" * 30 + "\n"
    message += f"*Summary*\n"
    message += f"Total Accounts: {len([a for a in accounts if a['is_active']])}\n"
    message += f"Total Trades: {total_trades}\n"
    message += f"Total P&L: ${total_profit:.2f}\n"
    
    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Account", callback_data="login_add"),
            InlineKeyboardButton("🔄 Switch Account", callback_data="login_switch")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu"),
            InlineKeyboardButton("📈 Performance", callback_data="performance_menu")
        ]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show account dashboard."""
    user_id = update.effective_user.id
    
    # Initialize database if needed
    global db
    if db is None:
        db = get_database()
    
    # Get user accounts
    accounts = db.get_user_accounts(user_id)
    
    if not accounts:
        await update.message.reply_text(
            "📭 No accounts configured.\n"
            "Use /login add to add an account."
        )
        return
    
    # Create inline keyboard for account selection
    keyboard = []
    
    for acc in accounts:
        btn_text = f"{'✅' if acc['is_default'] else '⚪'} {acc['account_name']} ({acc['account_number']})"
        callback_data = f"account_select_{acc['account_number']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("➕ Add New Account", callback_data="account_add")])
    
    await update.message.reply_text(
        "🏦 *Account Dashboard*\n\n"
        "Select an account to view details:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

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
    
    elif callback_data.startswith("signal_"):
        # Handle signal account selection
        parts = callback_data.split("_")
        if len(parts) >= 4 and parts[2] == "account":
            signal_id = parts[1]
            account_number = int(parts[3])
            await handle_signal_with_account(update, context, signal_id, account_number)
    
    elif callback_data.startswith("settings_account_"):
        # Handle settings account selection
        account_number = int(callback_data.replace("settings_account_", ""))
        await show_account_settings(update, context, account_number)

async def show_account_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, account_number: int) -> None:
    """Show settings for a specific account."""
    db = get_database()
    
    # Get account info
    accounts = db.get_user_accounts(update.effective_user.id)
    account = next((acc for acc in accounts if acc['account_number'] == account_number), None)
    
    if not account:
        await update.message.reply_text("❌ Account not found.")
        return
    
    # Get account settings
    settings = db.get_account_settings(account_number)
    
    # Store current account in context for settings updates
    if "current_settings_account" not in context.user_data:
        context.user_data["current_settings_account"] = {}
    context.user_data["current_settings_account"] = account_number
    
    # Create settings keyboard
    keyboard = [
        [InlineKeyboardButton(f"Risk: {settings['risk_percent']}%", callback_data="settings_risk")],
        [InlineKeyboardButton(f"Lot Size: {settings['default_lot_size']}", callback_data="settings_lot")],
        [InlineKeyboardButton(f"Auto-Trade: {'On' if settings['auto_trade'] else 'Off'}", callback_data="settings_auto")],
        [InlineKeyboardButton(f"Notifications: {'On' if settings['notifications'] else 'Off'}", callback_data="settings_notify")],
        [InlineKeyboardButton(f"Max Daily Trades: {settings['max_daily_trades']}", callback_data="settings_max_trades")],
        [InlineKeyboardButton("💾 Save Settings", callback_data="settings_save")]
    ]
    
    account_display = f"{account['account_name']}" if account.get('account_name') else f"Account {account_number}"
    
    message = (
        f"⚙️ *Settings for {account_display}*\n\n"
        f"Server: {account['server']}\n"
        f"Configure your trading preferences:"
    )
    
    # Check if this is from a callback or a regular message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def handle_signal_with_account(update: Update, context: ContextTypes.DEFAULT_TYPE, signal_id: str, account_number: int) -> None:
    """Handle signal after account selection."""
    query = update.callback_query
    await query.answer()
    
    # Get the signal from bot_data
    signals = context.bot_data.get("active_signals", {})
    if signal_id not in signals:
        await query.edit_message_text("⚠️ This signal has expired or is no longer valid.")
        return
    
    signal = signals[signal_id]
    
    # Store the selected account for this signal
    if "selected_accounts" not in context.bot_data:
        context.bot_data["selected_accounts"] = {}
    context.bot_data["selected_accounts"][signal_id] = account_number
    
    # Show trade options with the selected account
    keyboard = [
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"trade_{signal_id}_accept"),
            InlineKeyboardButton("❌ Reject", callback_data=f"trade_{signal_id}_reject")
        ],
        [InlineKeyboardButton("⚙️ Custom", callback_data=f"trade_{signal_id}_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update message to show selected account
    db = get_database()
    account_info = db.get_user_accounts(update.effective_user.id)
    selected_account = next((acc for acc in account_info if acc['account_number'] == account_number), None)
    
    account_display = f"{selected_account['account_name']}" if selected_account and selected_account.get('account_name') else f"Account {account_number}"
    
    current_text = query.message.text
    updated_text = f"{current_text}\n\n📍 Selected Account: {account_display}"
    
    await query.edit_message_text(
        text=updated_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

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
        
        # Get user's selected account for this signal or default
        db = get_database()
        selected_accounts = context.bot_data.get("selected_accounts", {})
        account_number = selected_accounts.get(signal_id)
        
        if not account_number:
            # No account selected for this signal, use default
            account_number = db.get_default_account(int(user_id))
            if not account_number:
                # Check if user has any accounts
                accounts = db.get_user_accounts(int(user_id))
                if not accounts:
                    await query.edit_message_text(
                        "❌ You need to add an MT4 account first!\n\n"
                        "Use /login to add your MT4 account."
                    )
                    return
                # Use first account if no default set
                account_number = accounts[0]['account_number']
        
        # Get account credentials
        credentials = db.get_account_credentials(account_number)
        if not credentials:
            await query.edit_message_text(
                "❌ Unable to retrieve account credentials.\n"
                "Please re-add your account using /login."
            )
            return
        
        # Get per-account settings
        account_settings = db.get_account_settings(account_number)
        lot_size = account_settings.get('default_lot_size', 0.01)
        
        # Prepare trade request
        trade_request = {
            "symbol": signal.get("symbol"),
            "direction": signal.get("direction", "BUY"),
            "volume": lot_size,
            "sl": signal.get("stop_loss"),
            "tp": signal.get("take_profit"),
            "account": account_number,
            "server": credentials['server'],
            "password": credentials['password']
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
                    'mt4_account': account_number,
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
                
                # Get account info for display
                account_info = db.get_user_accounts(int(user_id))
                selected_account = next((acc for acc in account_info if acc['account_number'] == account_number), None)
                account_display = f"{selected_account['account_name']}" if selected_account and selected_account.get('account_name') else f"Account {account_number}"
                
                await query.edit_message_text(
                    f"✅ Trade executed successfully!\n\n"
                    f"Account: {account_display}\n"
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
        application.add_handler(CommandHandler("login", login_command))
        application.add_handler(CommandHandler("accounts", accounts_command))
        application.add_handler(CommandHandler("dashboard", dashboard_command))
        
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