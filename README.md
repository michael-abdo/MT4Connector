# SoloDex - MT4 Trading Automation Platform

A comprehensive trading automation platform that connects MetaTrader 4 to modern APIs with enterprise-grade features including PostgreSQL database, session management, rate limiting, health monitoring, and Telegram integration.

## 🚀 Quick Start

### Prerequisites
- Python 3.6+
- PostgreSQL (optional - SQLite used for testing)
- MT4 Manager API access
- Telegram Bot Token (for notifications)

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd solodex

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Key configurations to update:
- `MT4_SERVER` - Your MT4 server address
- `MT4_PORT` - MT4 server port (usually 443)
- `MT4_LOGIN` - Your MT4 account number
- `MT4_PASSWORD` - Your MT4 password
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `DATABASE_URL` - PostgreSQL connection string

### 3. Run the Platform

#### Option 1: Quick Start (All-in-One)
```bash
# Windows
MT4Connector/START_CONNECTOR.bat

# Mac/Linux
./MT4Connector/START_CONNECTOR.sh
```

#### Option 2: Component by Component
```bash
# Start MT4 Connector
python MT4Connector/src/run_mt4_connector.py

# Start Telegram Bot (in new terminal)
python telegram_connector/app.py

# Start Health Monitor (in new terminal)
python telegram_connector/health_server.py
```

## 🎯 Features

### Phase 1-4 Features (Completed)
- ✅ **EA Signal Processing** - File-based signal monitoring
- ✅ **Mock Trading Mode** - Test without real MT4 connection
- ✅ **Real MT4 Integration** - Full Manager API support
- ✅ **Telegram Bot** - Mobile trading interface
- ✅ **Multi-Account Support** - Manage multiple MT4 accounts
- ✅ **User Authentication** - Secure access control

### Phase 5 Features (Production Ready)
- ✅ **PostgreSQL Database** - Enterprise-grade data persistence
- ✅ **Encrypted Credentials** - Fernet encryption for sensitive data
- ✅ **Session Management** - Secure API sessions with tokens
- ✅ **Rate Limiting** - Configurable API rate limits
- ✅ **Health Monitoring** - Prometheus-compatible metrics
- ✅ **Auto-Reconnection** - Automatic recovery with exponential backoff
- ✅ **Trade Logging** - Comprehensive audit trail
- ✅ **100% Test Coverage** - Full test suite with environment configuration

## 📁 Project Structure

```
solodex/
├── .env                     # Environment configuration (create from .env.example)
├── .env.example            # Example environment file
├── .env.test               # Test environment configuration
├── .gitignore              # Git ignore rules
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── setup.sh               # Main setup script
│
├── docs/                   # Documentation
│   ├── architecture_diagram.md
│   ├── claude.md          # Development roadmap
│   ├── DEV_SETUP_GUIDE.md
│   ├── ENV_SETUP_GUIDE.md
│   ├── FIXING_TESTS_SUMMARY.md
│   ├── TEST_REPORT.md
│   └── phases/            # Phase-specific docs
│       ├── PHASE1_README.md
│       ├── PHASE2_README.md
│       └── PHASE3_README.md
│
├── scripts/               # Utility scripts
│   ├── run.py
│   ├── run_tests_with_dotenv.py
│   └── run_tests_with_env.sh
│
├── MT4Connector/          # Core MT4 integration
│   ├── README.md
│   ├── START_CONNECTOR.bat/command/sh
│   ├── requirements.txt
│   ├── src/               
│   │   ├── config.py      # Configuration (reads from .env)
│   │   ├── mock_api.py    # Mock API for testing
│   │   ├── mt4_api.py     # MT4 Manager API wrapper
│   │   ├── mt4_real_api.py
│   │   ├── signal_processor.py
│   │   └── run_mt4_connector.py
│   ├── tests/             # Comprehensive test suite
│   ├── mt4_api/           # MT4 DLLs and headers
│   └── signals/           # EA signal files
│
├── telegram_connector/    # Production-ready Telegram bot
│   ├── app.py            # Main Flask application
│   ├── routes.py         # API endpoints with auth
│   ├── database.py       # Database interface
│   ├── database_postgres.py # PostgreSQL implementation
│   ├── database_sqlite.py  # SQLite for testing
│   ├── session_manager.py  # Session management
│   ├── rate_limiter.py    # API rate limiting
│   ├── health_monitor.py   # Health check system
│   ├── reconnection_manager.py # Auto-reconnection
│   └── trade_logger.py     # Trade execution logging
│
├── data/                  # Runtime data
│   └── logs/             # Log files
│
├── signals/              # Global signal files
└── logs/                 # Application logs
```

## 🧪 Testing

### Run All Tests (100% Pass Rate)
```bash
# Using the test runner (recommended)
python scripts/run_tests_with_dotenv.py

# Or manually with environment
export MOCK_MODE=True
export DATABASE_URL=sqlite:///:memory:
pytest -v
```

### Test Coverage
- **35 tests passed** ✅
- **0 tests failed** ✅  
- **4 tests skipped** (platform-specific)
- **100% success rate**

## 🔧 Configuration

### Environment Variables

See `.env.example` for full list. Key variables:

#### MT4 Configuration
```bash
MT4_SERVER=your.mt4.server.com
MT4_PORT=443
MT4_LOGIN=your_account_number
MT4_PASSWORD=your_password
```

#### Database Configuration
```bash
# Production (PostgreSQL)
DATABASE_URL=postgresql://user:pass@localhost:5432/solodex

# Testing (SQLite)
DATABASE_URL=sqlite:///:memory:
```

#### Security Configuration
```bash
SESSION_SECRET_KEY=generate_secure_key_here
ENCRYPTION_KEY=32_byte_encryption_key_here!!!
```

#### Rate Limiting
```bash
RATE_LIMIT_TIER=standard  # strict (10/min), standard (60/min), relaxed (300/min)
```

## 📱 Telegram Bot Setup

1. **Create Bot**
   ```
   1. Message @BotFather on Telegram
   2. Send /newbot
   3. Follow instructions
   4. Copy the token
   ```

2. **Configure**
   ```bash
   # In .env file
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id
   ```

3. **Find Your Chat ID**
   ```
   1. Message @userinfobot
   2. It will reply with your ID
   ```

4. **Run Bot**
   ```bash
   python telegram_connector/app.py
   ```

## 🛡️ Security Features

- **Encrypted Storage**: All credentials encrypted with Fernet
- **Session Tokens**: Secure API authentication
- **Rate Limiting**: Prevent API abuse
- **Input Validation**: Comprehensive request validation
- **Audit Trail**: Complete trade execution logging

## 📊 Monitoring

### Health Check Endpoints
- `GET /health` - Basic health status
- `GET /health/detailed` - Detailed component status
- `GET /metrics` - Prometheus-compatible metrics

### Monitor Components
- Database connectivity
- MT4 connection status
- Telegram bot availability
- System resources
- Recent trade activity

## 🚨 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
export PYTHONPATH=$PWD/MT4Connector/src:$PWD/telegram_connector
```

**2. Database Connection Failed**
```bash
# For testing, use SQLite
export DATABASE_URL=sqlite:///:memory:
```

**3. MT4 Connection Issues**
```bash
# Enable mock mode for testing
export MOCK_MODE=True
```

**4. Permission Denied**
```bash
chmod +x START_CONNECTOR.sh
chmod +x run_tests_with_dotenv.py
```

### Checking Logs
```bash
# MT4 Connector logs
tail -f MT4Connector/logs/mt4_connector_*.log

# Telegram connector logs
tail -f telegram_connector.log

# Trade execution logs
tail -f logs/trades_*.log
```

## 🔄 Development Workflow

1. **Make Changes**
2. **Run Tests**
   ```bash
   python run_tests_with_dotenv.py
   ```
3. **Check Logs**
4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

## 📈 API Endpoints

### Authentication
- `POST /api/auth/login` - Login with credentials
- `POST /api/auth/logout` - Logout and invalidate session
- `GET /api/auth/me` - Get current user info

### Trading
- `POST /webhook` - Receive trading signals
- `GET /api/signals` - List recent signals
- `POST /api/trades` - Execute trade
- `GET /api/trades/{id}` - Get trade details

### Monitoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /api/stats` - Trading statistics

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`python run_tests_with_dotenv.py`)
4. Commit changes (`git commit -m 'feat: add amazing feature'`)
5. Push branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

- Check [ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md) for environment setup
- Review logs in `logs/` directory
- Check [Troubleshooting](#-troubleshooting) section
- Open an issue for bugs or feature requests

---

Built with ❤️ for automated trading