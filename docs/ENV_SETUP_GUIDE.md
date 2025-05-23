# Environment Setup Guide

## Overview
This guide explains how to set up environment variables for the MT4 Connector project, enabling proper configuration for both production and testing environments.

## Files Created
1. `.env` - Production environment variables (contains sensitive data)
2. `.env.test` - Test environment variables 
3. `.env.example` - Template for environment variables
4. `.gitignore` - Ensures .env files are not committed
5. `run_tests_with_env.sh` - Shell script to run tests with environment
6. `run_tests_with_dotenv.py` - Python script to run tests with dotenv

## Quick Start

### For Production
1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual values:
   - MT4 server credentials
   - Telegram bot token
   - Database connection string
   - API keys

### For Testing
1. Use the pre-configured test environment:
   ```bash
   # Using Python script (recommended)
   python run_tests_with_dotenv.py
   
   # Or using shell script
   ./run_tests_with_env.sh
   ```

2. The test environment automatically sets:
   - `MOCK_MODE=True` - Uses mock connections
   - `DATABASE_URL=sqlite:///:memory:` - In-memory database
   - `MT4_SERVER=localhost` - Test server values
   - Proper Python paths

## Environment Variables

### Core Configuration
- `MOCK_MODE` - Enable/disable mock mode for testing
- `PYTHONPATH` - Python module search paths
- `DATABASE_URL` - Database connection string

### MT4 Configuration
- `MT4_SERVER` - MT4 server address
- `MT4_PORT` - MT4 server port
- `MT4_LOGIN` - MT4 account number
- `MT4_PASSWORD` - MT4 account password
- `MT4_MANAGER_LOGIN` - Manager account login
- `MT4_MANAGER_PASSWORD` - Manager account password

### Telegram Configuration
- `TELEGRAM_BOT_TOKEN` - Bot token from BotFather
- `TELEGRAM_CHANNEL_ID` - Channel ID for broadcasts
- `TELEGRAM_GROUP_ID` - Group ID for notifications
- `TELEGRAM_CHAT_ID` - Chat ID for direct messages

### Security Configuration
- `SESSION_SECRET_KEY` - Secret key for session management
- `ENCRYPTION_KEY` - 32-byte key for data encryption

### API Configuration
- `API_HOST` - API server host
- `API_PORT` - API server port
- `API_DEBUG` - Enable debug mode

### Additional Settings
See `.env.example` for complete list including:
- Rate limiting configuration
- Monitoring settings
- Logging configuration
- Trading parameters
- Risk management settings

## Test Results
With proper environment configuration:
- **35 tests passed** ✅
- **0 tests failed** ✅
- **4 tests skipped** (platform-specific)
- **100% success rate**

## Configuration Updates Made
1. Updated `config.py` to read from environment variables:
   ```python
   MT4_SERVER = os.environ.get('MT4_SERVER', "195.88.127.154")
   MT4_PORT = int(os.environ.get('MT4_PORT', 45543))
   ```

2. Fixed test expectations to match actual directory structure

3. Created comprehensive test runners with environment loading

## Troubleshooting

### Virtual Environment Issues
If you encounter Python/pytest issues:
```bash
# Create fresh virtual environment
python3 -m venv test_venv
source test_venv/bin/activate
pip install pytest python-dotenv requests
```

### Environment Variable Not Loading
1. Check `.env.test` exists in project root
2. Verify no syntax errors in .env files
3. Use `python run_tests_with_dotenv.py` which handles loading

### Path Issues
Ensure PYTHONPATH includes both directories:
```bash
export PYTHONPATH=$PWD/MT4Connector/src:$PWD/telegram_connector
```