# MT4 Connector Telegram Bot

A Telegram bot integration for the MT4 Dynamic Trailing connector that allows you to receive, approve, and manage trading signals from your mobile device.

## Features

- **Interactive Trading Signals**: Receive real-time trading signals with detailed information
- **Approve/Reject Trades**: Make trading decisions directly from your Telegram chat
- **Modify Orders**: Adjust trade parameters before execution
- **Trade Confirmations**: Get notifications when trades are executed
- **User Authentication**: Only authorized users can interact with the bot
- **Settings Management**: Configure your trading preferences

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a chat with BotFather and send the command `/newbot`
3. Follow the instructions to name your bot and get a username
4. BotFather will provide a token like `123456789:ABCdefGhIJKlmnOPQRstUVwxYZ`
5. Copy this token - you'll need it for configuration

### 2. Configure MT4 Connector

1. Open `config.py` in the MT4 Connector directory
2. Update the Telegram bot settings:

```python
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TOKEN_HERE"  # Add your bot token from BotFather
TELEGRAM_ADMIN_IDS = [12345678]  # Add your Telegram user ID(s)
TELEGRAM_NOTIFICATIONS = True  # Enable or disable notifications
```

### 3. Finding Your Telegram User ID

1. Start a chat with `@userinfobot` on Telegram
2. The bot will respond with your user ID
3. Add this ID to the `TELEGRAM_ADMIN_IDS` list in `config.py`

## Usage

### Starting the Bot

Run the connector with Telegram bot integration:

```bash
python run_with_telegram.py
```

### Bot Commands

The following commands are available in the Telegram chat:

- `/start` - Start the bot and show welcome message
- `/help` - Show help information about the bot
- `/settings` - Configure your trading preferences

### Trading Signal Flow

1. When a trading signal is detected from your EA, the bot sends you a notification with details
2. You can choose to:
   - **Approve** the trade: The bot will execute it through the MT4 API
   - **Reject** the trade: The signal will be discarded
   - **Modify** the trade: Adjust parameters like volume, stop loss, or take profit
3. After approving, you'll receive a confirmation when the trade is executed

### Auto-Approval

You can enable auto-approval in the settings to execute trades automatically without manual confirmation. This is useful for fully automated trading strategies.

## Testing

Use the included test script to generate sample trading signals:

```bash
# Generate a random trading signal
python generate_test_signal.py

# Generate a specific signal type
python generate_test_signal.py --type buy --symbol EURUSD --volume 0.1

# Generate multiple signals at once
python generate_test_signal.py --batch 3
```

## Troubleshooting

- **Bot Not Responding**: Check that the bot token is correct and the bot is running
- **Not Receiving Messages**: Make sure your user ID is in the `TELEGRAM_ADMIN_IDS` list
- **Failed to Start Bot**: Check for error messages in the console logs
- **Trades Not Executing**: Verify that the MT4 connection is working correctly

## Security Notes

- Keep your bot token private - anyone with the token can control your bot
- Only add trusted user IDs to the `TELEGRAM_ADMIN_IDS` list
- The bot can execute real trades with real money - use caution
- Consider running in test mode initially by using mock mode