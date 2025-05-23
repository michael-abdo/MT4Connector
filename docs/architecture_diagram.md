# ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────┐
│                    SIGNAL SOURCES                       │
├────────────────────────────┬────────────────────────────┤
│ TRADINGVIEW INDICATOR      │ MT4 DYNAMIC TRAILING STOP  │
│ (External Platform)        │ (Running in MT4)           │
│                            │                            │
│ ┌────────────────────┐     │ ┌────────────────────┐     │
│ │   SOLOTREND X      │     │ │  DYNAMIC TRAILING  │     │
│ │    INDICATOR       │     │ │      STOP EA       │     │
│ └─────────┬──────────┘     │ └──────────┬─────────┘     │
│           │                │            │               │
│           └────────────────┼────────────┘               │
│                            │                            │
│                BOTH USE HTTP WEBHOOKS                   │
│                            │                            │
└────────────────────────────┼────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────┐
│             WINDOWS SERVER                │
│                (AZURE)                    │
├───────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐   │
│ │             WEBHOOK API             │   │
│ │   (UNIFIED SIGNAL ENTRY POINT)      │   │
│ └───────────────────┬─────────────────┘   │
│                     │                     │
│                     ▼                     │
│ ┌─────────────────────────────────────┐   │    ┌─────────────────────┐
│ │        TELEGRAM CONNECTOR           │◄──────►│   CLIENT DEVICES    │
│ │     (NOTIFICATION & EXECUTION)      │   │    │                     │
│ └───────────────────┬─────────────────┘   │    │ ┌─────────────────┐ │
│                     │                     │    │ │    TELEGRAM     │ │
│                     │                     │    │ │     CLIENT      │ │
│                     │                     │    │ │                 │ │
│                     │                     │    │ └─────────────────┘ │
│                     ▼                     │    │                     │
│ ┌─────────────────────────────────────┐   │    │ ┌─────────────────┐ │
│ │       MT4 MANAGER API               │   │    │ │  MT4 TRADING    │ │
│ │      (RESTFUL WRAPPER)              │   │    │ │  CLIENT (OPT)   │ │
│ └───────────────────┬─────────────────┘   │    │ │                 │ │
│                     │                     │    │ └─────────────────┘ │
│                     ▼                     │    └─────────────────────┘
│ ┌─────────────────────────────────────┐   │
│ │           MT4 TERMINAL              │   │
│ │                                     │   │
│ └───────────────────┬─────────────────┘   │
└─────────────────────┼─────────────────────┘
                      │
                      ▼
┌────────────────────────┐              
│      BROKER            │              
│    TRADE SERVER        │                      
│                        │              
└────────────────────────┘              
```

## INTERACTIVE DATA FLOW

1. **Signal Generation**:
   - Both TradingView and Dynamic Trailing Stop EA send signals via webhooks
   - Signals arrive at the Webhook API entry point

2. **User Notification & Decision Flow**:
   - Webhook API → Telegram Connector → Telegram Client (signal notification)
   - Telegram Client → Telegram Connector (user accepts/rejects trade)

3. **Trade Execution Flow** (after user confirmation):
   - Telegram Connector → MT4 Manager API (RESTful) → MT4 Terminal → Broker

4. **Status Reporting Flow**:
   - MT4 Terminal → MT4 Manager API → Telegram Connector → Telegram Client
   - MT4 Terminal → MT4 Trading Client (optional direct monitoring)

## TELEGRAM INTEGRATION BENEFITS

1. Human verification and approval of all trading signals
2. Interactive trading parameters (stop loss, take profit, trade size)
3. Real-time status updates and notifications
4. Easy command interface for managing existing positions
5. Accessible from any device with Telegram installed

## COMPONENTS DESCRIPTION

- **TradingView Indicator**: External platform generating entry signals via webhooks
- **Dynamic Trailing Stop EA**: Sends exit signals via webhooks
- **Webhook API**: Single unified entry point for all trading signals
- **Telegram Connector**: Processes signals, sends notifications, receives commands
- **MT4 Manager API (RESTful)**: Wrapper around DLL files providing HTTP access to MT4
- **MT4 Terminal**: The MetaTrader 4 client application running on the server
- **Telegram Client**: Mobile/desktop app for receiving signals and sending commands
- **MT4 Trading Client**: Optional direct interface to monitor trading (not required)
- **Broker Trade Server**: External server processing actual market orders

## USER INTERACTION WORKFLOW

1. Signal is received and sent to user's Telegram
2. User sees signal details (currency pair, direction, entry price, etc.)
3. User can tap buttons to:
   - Execute trade (with pre-configured parameters)
   - Modify parameters (lot size, stop loss, take profit)
   - Ignore signal
4. User receives confirmation when trade is executed
5. User receives updates on trade status (filled, closed, etc.)
6. User can send commands to close or modify existing trades

## PREREQUISITES & SETUP REQUIREMENTS

### 1. HARDWARE/INFRASTRUCTURE
- Azure Windows Server VM (minimum 2 cores, 4GB RAM recommended)
- Static IP address for webhook endpoint accessibility
- Port 80/443 opened for webhook traffic
- Stable internet connection with low latency to broker

### 2. SOFTWARE REQUIREMENTS
- Windows Server 2019 or newer
- MetaTrader 4 Terminal (latest version)
- MT4 Manager API files (mtmanapi.dll, mtmanapi64.dll, MT4ManagerAPI.h)
- Python 3.7+ for webhook and Telegram integration
- Web server (like Nginx or built-in Python HTTP server)
- SSL certificate for secure webhook communications

### 3. ACCOUNT REQUIREMENTS
- Broker MT4 account with API trading enabled
- Telegram Bot API token (from BotFather)
- TradingView Pro account (for custom alerts with webhooks)

### 4. DEVELOPMENT REQUIREMENTS
- RESTful API wrapper for MT4 Manager API (custom code)
- Telegram Bot implementation (custom code)
- Webhook endpoint implementation (custom code)
- Dynamic Trailing Stop EA modified for webhook communications

### 5. CONFIGURATION REQUIREMENTS
- API credentials securely stored
- Webhook URL configured in TradingView alerts
- Webhook URL configured in Dynamic Trailing Stop EA
- Telegram Bot registered and connected to user chat(s)
- MT4 Manager API login credentials configured

### 6. INSTALLATION SEQUENCE
a. Provision Azure Windows Server
b. Install MT4 Terminal and connect to broker
c. Install MT4 Manager API files
d. Deploy RESTful API wrapper
e. Set up webhook listener and Telegram connector
f. Install modified Dynamic Trailing Stop EA
g. Configure TradingView webhook alerts
h. Test end-to-end signal flow with sample alerts


### 1. Signal Sources

- **TradingView Indicator (External Platform)**
  - Not directly in the codebase, as it runs on TradingView's platform
- **MT4 Dynamic Trailing Stop EA (Running in MT4)**
  - `Dynamic Trailing Stop.mq4.m` - The EA code for MT4
  - `MT4Connector/examples/SimpleConnectorEA.mq4` - Example EA for integration

### 2. Windows Server (Azure) Components

- **Webhook API (Unified Signal Entry Point)**
  - `telegram/src/mt4_integration/mt4_connector.py` - Handles webhook connections
  - `MT4Connector/app.py` - Main application running webhook listener
- **Telegram Connector (Notification & Execution)**
  - `telegram/` directory - Contains the Telegram bot implementation
  - `telegram/src/telegram_bot/bot.py` - Main Telegram bot code
  - `telegram/main.py` - Entry point for Telegram service
  - `telegram/config/config.py` - Configuration for Telegram integration
- **MT4 Manager API (RESTful Wrapper)**
  - `MT4ManagerAPI/` directory - Contains MT4 Manager API files and examples
  - `MT4Connector/mt4_api.py` - Python wrapper for MT4 Manager API
  - `MT4Connector/mt4_api/` - Contains DLL files (mtmanapi.dll, mtmanapi64.dll)
  - `MT4RestfulAPIWrapper.zip` - ZIP file containing RESTful API wrapper
- **MT4 Terminal**
  - Not directly in the codebase as this would be installed on Azure
  - `MT4Test/` - Contains setup scripts for MT4 on AWS/Azure

### 3. Infrastructure Setup & Deployment

- **Server Setup**
  - `MT4Test/scripts/` - Contains scripts for setting up Windows Server
  - `MT4Test/scripts/aws_mt4_setup.py` - AWS setup script
  - `MT4Test/scripts/setup_mt4_windows.ps1` - Windows setup script
- **Connector Setup**
  - `MT4Connector/START_CONNECTOR.bat` - Windows startup script
  - `MT4Connector/START_CONNECTOR.sh` - Linux/Mac startup script
  - `MT4Connector/setup.bat` and `setup.sh` - Setup scripts
- **Signal Processing**
  - `MT4Connector/signal_processor.py` - Processes trading signals
  - `MT4Connector/signals/` - Directory for signal files
  - `telegram/src/mt4_integration/mt4_connector.py` - Connects signals to Telegram
- **Architecture Documentation**
  - `architecture_diagram.md` - Main architecture diagram
  - `documents/SOLOTREND X DYNAMIC TRAILING FEATURE.pdf` - Feature documentation

This mapping shows how the project implements the multi-component architecture described in the diagram, connecting signal sources through a webhook API to Telegram and MT4 for trade execution.