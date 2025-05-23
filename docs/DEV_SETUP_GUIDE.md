# SoloTrend X Development Setup Guide

This guide provides detailed, step-by-step instructions for setting up a local development environment for the SoloTrend X trading system on macOS, without requiring a real MT4 terminal or live trading connections.

## Project Overview

The SoloTrend X system consists of these key components:

1. **Webhook API** - Receives signals from TradingView and EA
2. **Telegram Bot** - User interface for signal notification and trade execution
3. **MT4 API Mock** - Simulated MT4 Manager API for development
4. **MT4Connector** - Signal processor (will run in mock mode)

## Development Plan

### Phase 1: Environment Setup

1. **Create mock MT4 API**
2. **Configure Telegram bot**
3. **Implement webhook server**
4. **Connect components together**

### Phase 2: Feature Implementation

1. **Complete MT4 connector integration**
2. **Enhance Telegram UI**
3. **Add signal processing logic**
4. **Implement testing tools**

## Step-by-Step Setup Instructions

### Step 1: Create a Mock MT4 API Environment

```bash
# Create directory structure
mkdir -p ~/solotrendx_dev/mt4_mock_api
```

The MT4Connector already has a mock mode (line 42 in app.py). We'll use this as the backend instead of connecting to a real MT4 server.

### Step 2: Set Up Telegram Bot

1. **Create a Telegram bot with BotFather**:
   - Open Telegram and search for @BotFather
   - Send `/newbot` command and follow instructions
   - Write down the bot token provided

2. **Create .env file for the Telegram component**:
   ```bash
   cd ~/Desktop/upwork/3\\)\ current\ projects/solotrendx_021891146667638771828/telegram
   touch .env
   ```

3. **Add your bot token to the .env file**:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id
   FLASK_PORT=5001
   FLASK_DEBUG=True
   ```

### Step 3: Implement the MT4 Connector for Telegram

1. **Update the mt4_connector.py file**:
   ```bash
   cd ~/Desktop/upwork/3\\)\ current\ projects/solotrendx_021891146667638771828/telegram/src/mt4_integration
   ```

2. **Create/edit mt4_connector.py with this implementation**:
   ```python
   # mt4_connector.py
   import logging
   import json
   import requests
   import os
   import time
   
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   class MT4Connector:
       def __init__(self, use_mock=True):
           self.use_mock = use_mock
           self.mock_api_url = "http://localhost:5002/api/trade"  # Mock API endpoint
           self.api_url = os.environ.get("MT4_API_URL", "http://localhost:5002/api/trade")
           logger.info(f"MT4Connector initialized with {'mock' if use_mock else 'live'} mode")
   
       def send_trade(self, signal_data):
           """Send trade signal to MT4 platform"""
           logger.info(f"Sending trade signal to MT4: {signal_data}")
           
           if self.use_mock:
               # Simulate successful trade execution
               time.sleep(1)  # Simulate network delay
               return {"status": "success", "message": "Trade executed (MOCK)", "ticket": 12345}
           
           try:
               # Real implementation would use the API
               response = requests.post(
                   self.api_url,
                   json=signal_data,
                   headers={"Content-Type": "application/json"}
               )
               return response.json()
           except Exception as e:
               logger.error(f"Error executing trade: {e}")
               return {"status": "error", "message": str(e)}
               
   # Create a singleton instance
   mt4_api = MT4Connector(use_mock=True)
   
   def send_trade(signal_data):
       """Wrapper function for the MT4 API"""
       return mt4_api.send_trade(signal_data)
   ```

### Step 4: Create a Webhook API Server

1. **Create a unified webhook API server directory**:
   ```bash
   mkdir -p ~/solotrendx_dev/webhook_api
   cd ~/solotrendx_dev/webhook_api
   touch webhook_server.py
   ```

2. **Implement the webhook server code**:
   ```python
   # webhook_server.py
   from flask import Flask, request, jsonify
   import requests
   import json
   import logging
   import os
   
   app = Flask(__name__)
   logging.basicConfig(level=logging.INFO)
   
   # Configure these with your actual Telegram webhook URL
   TELEGRAM_WEBHOOK_URL = "http://localhost:5001/webhook"
   
   @app.route('/webhook/tradingview', methods=['POST'])
   def tradingview_webhook():
       """Handle TradingView signals"""
       data = request.json
       logging.info(f"Received TradingView signal: {data}")
       
       # Forward to Telegram bot
       try:
           response = requests.post(TELEGRAM_WEBHOOK_URL, json=data)
           return jsonify({"status": "success", "message": "Signal forwarded to Telegram"})
       except Exception as e:
           logging.error(f"Error forwarding signal: {e}")
           return jsonify({"status": "error", "message": str(e)}), 500
   
   @app.route('/webhook/ea', methods=['POST'])
   def ea_webhook():
       """Handle MT4 EA signals"""
       data = request.json
       logging.info(f"Received EA signal: {data}")
       
       # Forward to Telegram bot
       try:
           response = requests.post(TELEGRAM_WEBHOOK_URL, json=data)
           return jsonify({"status": "success", "message": "Signal forwarded to Telegram"})
       except Exception as e:
           logging.error(f"Error forwarding signal: {e}")
           return jsonify({"status": "error", "message": str(e)}), 500
   
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5002, debug=True)
   ```

### Step 5: Set Up MT4 Manager API Mock Server

1. **Create a mock REST API for the MT4 Manager API**:
   ```bash
   mkdir -p ~/solotrendx_dev/mt4_rest_api
   cd ~/solotrendx_dev/mt4_rest_api
   touch mt4_rest_server.py
   ```

2. **Implement the REST API server code**:
   ```python
   # mt4_rest_server.py
   from flask import Flask, request, jsonify
   import logging
   import time
   import random
   
   app = Flask(__name__)
   logging.basicConfig(level=logging.INFO)
   
   @app.route('/api/trade', methods=['POST'])
   def execute_trade():
       """Mock MT4 trade execution"""
       data = request.json
       logging.info(f"Processing trade: {data}")
       
       # Simulate processing time
       time.sleep(0.5)
       
       # Generate fake ticket number
       ticket = random.randint(10000, 99999)
       
       return jsonify({
           "status": "success",
           "message": "Trade executed successfully",
           "data": {
               "ticket": ticket,
               "symbol": data.get("symbol", "EURUSD"),
               "type": data.get("side", "BUY"),
               "price": data.get("price", 1.1234),
               "volume": data.get("volume", 0.1),
               "sl": data.get("sl", 0),
               "tp": data.get("tp", 0)
           }
       })
   
   @app.route('/api/status', methods=['GET'])
   def server_status():
       """Check server status"""
       return jsonify({"status": "ok", "mode": "mock"})
   
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5003, debug=True)
   ```

### Step 6: Create a Launch Script

1. **Create a unified launch script**:
   ```bash
   cd ~/Desktop/upwork/3\\)\ current\ projects/solotrendx_021891146667638771828
   touch start_dev_environment.sh
   chmod +x start_dev_environment.sh
   ```

2. **Add the launch commands to the script**:
   ```bash
   #!/bin/bash
   
   # Start all components in separate terminal windows
   
   # 1. MT4 REST API Mock Server
   osascript -e 'tell app "Terminal" to do script "cd ~/solotrendx_dev/mt4_rest_api && python mt4_rest_server.py"'
   
   # 2. Webhook API Server
   osascript -e 'tell app "Terminal" to do script "cd ~/solotrendx_dev/webhook_api && python webhook_server.py"'
   
   # 3. MT4Connector in mock mode
   osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/MT4Connector && python app.py --mock"'
   
   # 4. Telegram Bot
   osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/telegram && python main.py"'
   
   echo "Development environment started!"
   echo "- Webhook API: http://localhost:5002/webhook/tradingview"
   echo "- MT4 REST API: http://localhost:5003/api/trade"
   echo "- MT4Connector: Running in mock mode"
   echo "- Telegram Bot: Check your Telegram for the bot"
   ```

### Step 7: Create Test Signal Generator

1. **Create a script to generate test signals**:
   ```bash
   mkdir -p ~/solotrendx_dev/test_tools
   cd ~/solotrendx_dev/test_tools
   touch generate_signal.py
   ```

2. **Implement the signal generator code**:
   ```python
   # generate_signal.py
   import requests
   import json
   import argparse
   import random
   
   def generate_tradingview_signal(direction="BUY"):
       """Generate a sample TradingView signal"""
       symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
       symbol = random.choice(symbols)
       price = round(random.uniform(1.0, 1.5), 4)
       
       return {
           "symbol": symbol,
           "side": direction,
           "price": price,
           "sl": round(price * 0.99, 4) if direction == "BUY" else round(price * 1.01, 4),
           "tp1": round(price * 1.01, 4) if direction == "BUY" else round(price * 0.99, 4),
           "tp2": round(price * 1.02, 4) if direction == "BUY" else round(price * 0.98, 4),
           "tp3": round(price * 1.03, 4) if direction == "BUY" else round(price * 0.97, 4),
           "currentTimeframe": "H1",
           "strategy": "SOLOTREND X",
           "risk": "1%",
           "expiration": "2h"
       }
   
   def send_signal(webhook_url, signal_type="tradingview", direction="BUY"):
       """Send a test signal to the webhook"""
       endpoint = f"{webhook_url}/{signal_type}"
       
       if signal_type == "tradingview":
           data = generate_tradingview_signal(direction)
       else:
           # EA signal format
           data = generate_tradingview_signal(direction)
           data["type"] = "signal"
       
       print(f"Sending {direction} signal to {endpoint}:")
       print(json.dumps(data, indent=2))
       
       try:
           response = requests.post(endpoint, json=data)
           print(f"Response: {response.status_code}")
           print(response.json())
       except Exception as e:
           print(f"Error: {e}")
   
   if __name__ == "__main__":
       parser = argparse.ArgumentParser(description="Generate and send test trading signals")
       parser.add_argument("--url", default="http://localhost:5002/webhook", help="Webhook URL")
       parser.add_argument("--type", default="tradingview", choices=["tradingview", "ea"], help="Signal type")
       parser.add_argument("--direction", default="BUY", choices=["BUY", "SELL"], help="Trade direction")
       
       args = parser.parse_args()
       send_signal(args.url, args.type, args.direction)
   ```

### Step 8: Update the Telegram main.py to Use MT4 Connector

Modify the `execute_order` function in `telegram/main.py` to use our new MT4 connector:

```python
async def execute_order(user_params, order_details, update):
    print("Executing order...")
    
    # Import our MT4 connector implementation
    from src.mt4_integration.mt4_connector import send_trade
    
    # Prepare trade data
    trade_data = {
        "symbol": user_params.get('asset', 'EURUSD'),
        "type": "BUY" if user_params.get('trade_type', 'Standard').lower() == "standard" else "SELL",
        "volume": float(user_params.get('amount', 1)),
        "sl": 0,  # Would be calculated in real implementation
        "tp": 0   # Would be calculated in real implementation
    }
    
    # Send the trade to MT4
    result = send_trade(trade_data)
    
    if result.get("status") == "success":
        await update.message.reply_text(
            f"✅ Trade executed successfully!\n\n"
            f"Ticket: {result.get('ticket', 'N/A')}\n"
            f"Details: {order_details}"
        )
    else:
        await update.message.reply_text(
            f"❌ Trade execution failed!\n\n"
            f"Error: {result.get('message', 'Unknown error')}"
        )
    
    return CHOOSING
```

### Step 9: Create Requirements File

```bash
cd ~/Desktop/upwork/3\\)\ current\ projects/solotrendx_021891146667638771828
touch requirements.txt
```

Add the following to requirements.txt:
```
flask==3.1.0
python-telegram-bot==20.0a6
python-dotenv==1.0.1
requests==2.32.3
```

## Testing the Environment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Development Environment

```bash
./start_dev_environment.sh
```

### 3. Testing with Sample Signals

```bash
cd ~/solotrendx_dev/test_tools
python generate_signal.py --direction BUY
```

### 4. Expected Results

1. You should see logs in your webhook server showing the received signal
2. The signal should be forwarded to the Telegram bot
3. Your Telegram bot should send you a notification with the signal details
4. You can click buttons in Telegram to execute a mock trade
5. The system should report a successful (mock) trade execution

## Development Roadmap

Now that you have a working development environment, here are the next steps to enhance the system:

1. **Improve Signal Processing**: Add more sophisticated signal parsing and validation
2. **Enhance Telegram UI**: Add more features to the Telegram interface
3. **Add Authentication**: Implement proper authentication for API endpoints
4. **Implement User Management**: Add support for multiple users
5. **Develop Testing Framework**: Create automated tests for each component

## Troubleshooting

### Telegram Bot Not Responding
- Check that your bot token is correct
- Ensure you've started a conversation with your bot
- Verify the Telegram bot process is running

### Webhook Not Receiving Signals
- Check that the webhook server is running on the correct port
- Ensure your firewall allows connections to the port
- Test with curl: `curl -X POST http://localhost:5002/webhook/tradingview -H "Content-Type: application/json" -d '{"symbol":"EURUSD","side":"BUY"}'`

### MT4 Connector Issues
- Verify the mock MT4 API server is running
- Check the logs for any connection errors
- Ensure the correct URLs are configured

## Conclusion

By following this guide, you've set up a complete local development environment for the SoloTrend X trading system without needing a real MT4 terminal. This environment lets you develop and test all components of the system while simulating the behavior of the MT4 platform.