# Telegram Connector

This module connects the MT4 API with Telegram for trade signal notifications.

## Overview

The Telegram Connector serves as a bridge between the SoloTrend X trading system and Telegram, allowing users to receive trading signals and execute trades via a Telegram bot interface. 

This implementation has been enhanced with robust validation, clear error handling, and proper authentication to ensure reliable operation.

## Configuration

Create a `.env` file in the project root with the following required variables:

```
# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCDefGHIJklmnOPQRSTuvwxyz
ALLOWED_USER_IDS=123456789,987654321

# MT4 API Configuration
MT4_API_URL=http://localhost:5002/api/v1

# Application Settings
FLASK_PORT=5001
FLASK_DEBUG=False
MOCK_MODE=False
```

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from BotFather | `123456789:ABCDefGHIJklmnOPQRSTuvwxyz` |
| `ALLOWED_USER_IDS` | Comma-separated list of Telegram user IDs allowed to use the bot | `123456789,987654321` |
| `MT4_API_URL` | URL to your MT4 API service | `http://localhost:5002/api/v1` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_USER_IDS` | Comma-separated list of admin user IDs | Empty (no admins) |
| `FLASK_PORT` | Port for the webhook server | `5001` |
| `FLASK_DEBUG` | Enable Flask debug mode | `False` |
| `MOCK_MODE` | Run in mock mode without actual trading | `False` |

## Running the Connector

From the project root directory:

```bash
python telegram_connector/run.py
```

## Health Checking

The connector includes a health check endpoint at `/health` that returns the status of the Telegram bot and MT4 API connections:

```bash
curl http://localhost:5001/health
```

Response will look like:

```json
{
  "status": "ok",
  "service": "telegram_connector",
  "mock_mode": false,
  "components": {
    "telegram": "ok",
    "mt4_api": "ok"
  },
  "config_validation": {
    "result": "passed"
  }
}
```

## Testing

You can test the signal handler with the provided test script:

```bash
python telegram_connector/test_signal.py
```

This will send a sample signal to the webhook endpoint to verify it's working correctly.

## Architecture

- **app.py**: Flask application setup and configuration
- **bot.py**: Telegram bot implementation
- **signal_handler.py**: Processes trading signals and sends them to Telegram
- **mt4_connector.py**: Communicates with the MT4 API
- **routes.py**: Defines HTTP routes for webhooks
- **run.py**: Entry point for running the connector

## Error Handling

The connector includes robust error handling:

1. Configuration errors are caught early with clear messages
2. Telegram token validation ensures proper authentication
3. Health check endpoints allow monitoring of component status
4. All errors are logged with detailed information

## Integration

This connector is designed to be part of the larger SoloTrend X trading system. It receives signals from various sources via webhooks and forwards them to users via Telegram.