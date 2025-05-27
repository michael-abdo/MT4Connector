# MT4 Dynamic Trailing

Connect your MetaTrader 4 Expert Advisors to MT4 Manager API with minimal code changes.

> **Note**: This is the MT4 Connector component of the SoloDex platform. For complete setup including database, authentication, and monitoring features, see the [main README](../README.md).

## Table of Contents
- [What is MT4 Dynamic Trailing?](#what-is-mt4-dynamic-trailing)
- [Quick Start](#quick-start)
- [EA Integration](#ea-integration)
- [Telegram Bot Integration](#telegram-bot-integration)
- [Troubleshooting](#troubleshooting)
- [Technical Reference](#technical-reference)

## What is MT4 Dynamic Trailing?

The MT4 Dynamic Trailing connector is a tool that enables your Expert Advisors to execute trades automatically through the MT4 Manager API using a simple file-based communication method.

### Key Features
- **One-Click Setup**: Simple installation and configuration
- **Minimal EA Changes**: Add just one function to your EA code
- **Cross-Platform**: Works on Windows, Mac, and Linux
- **Automatic Order Management**: Place, modify, and close trades
- **Full Signal Support**: Market orders, pending orders, and position management
- **Telegram Integration**: Control trades from your mobile device

## Quick Start

### Windows Users
1. Double-click `START_CONNECTOR.bat` in the root directory
2. Follow the on-screen prompts to enter your MT4 server details

### Mac/Linux Users
1. Open a terminal in the project directory
2. Run `./START_CONNECTOR.sh` (you may need to make it executable with `chmod +x START_CONNECTOR.sh`)
3. Follow the on-screen prompts

### What Happens Behind the Scenes
The connector will:
1. Check and install required dependencies
2. Create necessary directories and files
3. Guide you through MT4 connection setup
4. Connect to your MT4 server
5. Start monitoring for trading signals

## Installation Directory Information

**Important**: The MT4 Connector does **NOT** need to be installed in any specific directory. It works independently of your MT4 terminal installation.

### How It Works:
- **MT4 Manager API**: Connects directly to the MT4 server over the network (e.g., 195.88.127.154:45543)
- **No MT4 Terminal Required**: Uses manager credentials to authenticate directly with the broker's server
- **File-Based Communication**: Your EA writes signals to a JSON file that the connector monitors

### Directory Structure:
```
C:\Any\Directory\You\Want\MT4Connector\
├── mt4_api\
│   ├── mtmanapi.dll        (Required - MT4 Manager API)
│   └── mtmanapi64.dll      (Required - 64-bit version)
├── signals\
│   └── ea_signals.txt      (EA writes signals here)
├── src\
│   └── (connector code)
└── START_WINDOWS.bat
```

### Example Setup:
- **MT4 Terminal**: `C:\Program Files (x86)\MetaTrader 4\`
- **MT4 Connector**: `C:\MT4Connector\` (or any location you prefer)
- **EA Signal File**: Update your EA to write to the connector's signals directory

The connector acts as a bridge between your EA and the MT4 server, using the Manager API for direct server communication.

## Telegram Bot Integration

The MT4 Connector includes a Telegram bot that allows you to receive trading signals and manage trades from your mobile device.

### Setting Up the Telegram Bot

1. Create a new bot using BotFather in Telegram:
   - Open Telegram and search for `@BotFather`
   - Send the command `/newbot` and follow the instructions
   - Copy the API token provided by BotFather

2. Configure the bot in MT4 Connector:
   - Open `src/config.py` in the MT4 Connector directory
   - Set your bot token: `TELEGRAM_BOT_TOKEN = "YOUR_TOKEN_HERE"`
   - Add your Telegram user ID: `TELEGRAM_ADMIN_IDS = [YOUR_USER_ID]`
   - To find your user ID, chat with `@userinfobot` in Telegram

3. Run the Telegram bot:
   ```
   python src/run_with_telegram.py
   ```

### Using the Telegram Bot

- **Receive Trading Signals**: Get real-time notifications about new trading signals from your EAs
- **Approve/Reject Trades**: Make trading decisions directly from Telegram
- **Modify Orders**: Adjust parameters like volume, stop loss, or take profit
- **Settings Management**: Configure auto-approval and notification preferences

### Bot Commands

- `/start` - Start the bot and show welcome message
- `/help` - Show help information
- `/settings` - Configure your trading preferences

For more details, see the [Telegram Bot README](telegram_bot/README.md).

## EA Integration

### Basic Integration

1. Copy this function to your Expert Advisor:

```cpp
void SendSignalToConnector(string type, string symbol, double volume, 
                          double stoploss = 0, double takeprofit = 0, 
                          string comment = "", int magic = 0, double price = 0, 
                          int ticket = 0) {
   // Create a unique ID for this signal
   string signal_id = IntegerToString(TimeCurrent()) + "_" + DoubleToString(volume, 2) + "_" + symbol;
   
   // Open the signal file - UPDATE THIS PATH to match your installation!
   int file = FileOpen("C:\\MT4_Dynamic_Trailing\\signals\\ea_signals.txt", FILE_WRITE|FILE_TXT);
   
   if(file != INVALID_HANDLE) {
      // Create JSON with required fields
      string json = "{\"signal_id\":\"" + signal_id + "\",\"type\":\"" + type + 
                    "\",\"symbol\":\"" + symbol + "\",\"volume\":" + DoubleToString(volume, 2) + 
                    ",\"login\":\"" + IntegerToString(AccountNumber()) + "\"";
      
      // Add optional fields if provided
      if(stoploss > 0) json += ",\"stoploss\":" + DoubleToString(stoploss, 5);
      if(takeprofit > 0) json += ",\"takeprofit\":" + DoubleToString(takeprofit, 5);
      if(comment != "") json += ",\"comment\":\"" + comment + "\"";
      if(magic > 0) json += ",\"magic\":" + IntegerToString(magic);
      if(price > 0) json += ",\"price\":" + DoubleToString(price, 5);
      if(ticket > 0) json += ",\"ticket\":" + IntegerToString(ticket);
      
      json += "}";
      
      // Write the JSON to the file
      FileWriteString(file, json);
      FileClose(file);
      Print("Signal sent to connector: ", json);
   } else {
      Print("Error opening signal file!");
   }
}
```

2. Update the signal file path in the `FileOpen()` function to match your installation directory:
   - Windows: `"C:\\MT4_Dynamic_Trailing\\signals\\ea_signals.txt"`
   - Mac/Linux: `"Z:/path/to/MT4_Dynamic_Trailing/signals/ea_signals.txt"`

### Using the Function

#### Market Orders
```cpp
// Buy 0.1 lot of EURUSD
SendSignalToConnector("buy", "EURUSD", 0.1);

// Sell 0.05 lots of GBPUSD with SL and TP
SendSignalToConnector("sell", "GBPUSD", 0.05, 1.3050, 1.2850);
```

#### Pending Orders
```cpp
// Buy limit 0.1 lot of EURUSD at 1.1800
SendSignalToConnector("buy_limit", "EURUSD", 0.1, 0, 0, "", 0, 1.1800);

// Sell stop 0.2 lots of USDJPY at 109.50 with comment and magic number
SendSignalToConnector("sell_stop", "USDJPY", 0.2, 110.50, 108.50, "MA Cross", 12345, 109.50);
```

#### Position Management
```cpp
// Close position with ticket #123456
SendSignalToConnector("close", "EURUSD", 0.0, 0, 0, "", 0, 0, 123456);

// Modify SL and TP on position #123456
SendSignalToConnector("modify", "EURUSD", 0.0, 1.1850, 1.1950, "", 0, 0, 123456);
```

### Supported Signal Types

| Signal Type | Description | Required Parameters |
|-------------|-------------|---------------------|
| `buy` | Market buy order | symbol, volume, login |
| `sell` | Market sell order | symbol, volume, login |
| `buy_limit` | Buy limit pending order | symbol, volume, login, price |
| `sell_limit` | Sell limit pending order | symbol, volume, login, price |
| `buy_stop` | Buy stop pending order | symbol, volume, login, price |
| `sell_stop` | Sell stop pending order | symbol, volume, login, price |
| `close` | Close an open position | symbol, login, ticket |
| `modify` | Modify an existing order | symbol, login, ticket, (+ parameters to modify) |

## Troubleshooting

### Common Issues

#### Application Won't Start
- Ensure Python 3.6+ is installed and added to your PATH
- Try running the script as Administrator
- Check the logs folder for error messages

#### DLL Loading Failures
- Run the application as Administrator
- Check if your antivirus has quarantined the DLL files
- Add an exception in your antivirus for the MT4_Dynamic_Trailing folder
- Ensure you have the Microsoft Visual C++ Redistributable installed

#### Connection Issues
- Double-check your MT4 server address, port, username, and password
- Ensure your MT4 server allows API access
- Check if your firewall is blocking the connection

#### Signal File Problems
- Verify the EA is writing to the correct signal file location
- Ensure the signal file format matches the expected JSON format
- Check logs for any parsing errors

#### EA Integration Issues
- Update the signal file path in the EA to match your installation directory
- Use double backslashes in file paths in MQL4 code
- Ensure MT4 has permission to write to the signals directory

### Checking Logs
1. Navigate to the `logs` folder in your MT4_Dynamic_Trailing directory
2. Look for the most recent log file
3. Open it with any text editor to see detailed error messages

### Testing MT4 API Connection
To test only the MT4 API connection:
1. Open a command prompt in the MT4_Dynamic_Trailing directory
2. Run: `python -c "from src.mt4_api import MT4API; api = MT4API(); print(api.connect('your_server', port, 'username', 'password'))"`

## System Requirements
- Python 3.6 or higher
- MetaTrader 4 with Manager API access
- Internet connection to your MT4 server

## Project Structure

```
MT4Connector/
├── .gitignore               # Git ignore file
├── README.md                # This documentation file
├── START_CONNECTOR.bat      # Windows one-click starter script
├── START_CONNECTOR.command  # macOS one-click starter script
├── START_CONNECTOR.sh       # Linux one-click starter script
├── requirements.txt         # Python dependencies
├── run_all_tests.py         # Main test runner script
├── setup.bat                # Windows setup script
├── setup.sh                 # Linux/macOS setup script
├── start.bat                # Windows startup script
├── start.sh                 # Linux/macOS startup script
├── examples/                # Example MT4 EA files
│   └── SimpleConnectorEA.mq4  # Simple example EA
├── logs/                    # Log files directory
├── mt4_api/                 # MT4 Manager API files
│   ├── MT4Manager.h         # MT4 Manager API header
│   ├── MT4ManagerAPI.h      # MT4 Manager API header
│   ├── mtmanapi.dll         # MT4 Manager API DLL (32-bit)
│   └── mtmanapi64.dll       # MT4 Manager API DLL (64-bit)
├── signals/                 # Signal files directory
│   ├── ea_signals.txt       # Signal file monitored by the connector
│   └── ea_signals_example.txt # Example signal file
├── src/                     # Source code
│   ├── app.py               # Main application
│   ├── config.py            # Configuration module
│   ├── dx_integration.py    # Trading platform integration
│   ├── mt4_api.py           # MT4 API wrapper
│   ├── run_mt4_connector.py # MT4 connector runner
│   ├── run_with_telegram.py # Telegram bot integration
│   ├── signal_processor.py  # Signal processing logic
│   └── utils/               # Utility modules
│       ├── debug_signal.py  # Signal debugging utility
│       └── generate_test_signal.py # Test signal generator
├── telegram_bot/            # Telegram bot functionality
│   ├── README.md            # Telegram bot documentation
│   ├── bot.py               # Telegram bot implementation
│   └── signal_handler.py    # Signal handling for Telegram
└── tests/                   # Test suite
    ├── README.md            # Testing documentation
    ├── run_all_tests.py     # Test runner implementation
    ├── test_config.py       # Config module tests
    ├── test_dx_integration.py # Integration tests
    ├── test_error_handling.py # Error handling tests
    ├── test_integration.py  # Integration tests
    ├── test_mt4_api.py      # MT4 API tests
    ├── test_signal_monitoring.py # Signal monitoring tests
    ├── test_signal_processing.py # Signal processing tests
    ├── test_telegram_bot.py # Telegram bot tests
    └── test_trade_signals.py # Trade signal tests
```

## Technical Reference

### Signal File Format
The connector processes trading signals in JSON format with these required fields:
- `signal_id`: A unique identifier for the signal
- `type`: The order type (buy, sell, etc.)
- `symbol`: The trading instrument symbol
- `volume`: Trading volume/lot size
- `login`: Your MT4 account number

Optional fields:
- `stoploss`: Stop loss price level
- `takeprofit`: Take profit price level
- `comment`: Order comment
- `magic`: Magic number for the order
- `price`: Price for pending orders
- `ticket`: Ticket number for modify/close operations

### Best Practices
1. Generate unique signal IDs to prevent duplicate execution
2. Always check if the file opened successfully
3. Use `Print()` to log when signals are sent
4. Avoid sending too many signals in a short time
5. Check logs if orders aren't being executed
6. Always test in a demo account first

## Support
If you encounter issues:
1. Check the Troubleshooting section above
2. Examine the log files in the `logs` directory
3. Contact support with details about your issue

## License
This software is provided "as is" and is intended for educational and trading purposes only. Use at your own risk.