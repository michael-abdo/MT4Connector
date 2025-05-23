#!/bin/bash
# Script to run tests with proper environment configuration

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up test environment...${NC}"

# Export environment variables from .env.test
export $(grep -v '^#' .env.test | xargs)

# Additional explicit exports for critical test variables
export MOCK_MODE=True
export PYTHONPATH=$PWD/MT4Connector/src:$PWD/telegram_connector
export DATABASE_URL=sqlite:///:memory:
export MT4_SERVER=localhost
export MT4_PORT=443

echo -e "${GREEN}Environment variables loaded:${NC}"
echo "  MOCK_MODE=$MOCK_MODE"
echo "  PYTHONPATH=$PYTHONPATH"
echo "  DATABASE_URL=$DATABASE_URL"
echo "  MT4_SERVER=$MT4_SERVER"
echo "  MT4_PORT=$MT4_PORT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Run tests with proper configuration
echo -e "${YELLOW}Running tests...${NC}"
pytest MT4Connector/tests/test_config.py \
       MT4Connector/tests/test_integration.py \
       MT4Connector/tests/test_telegram_bot.py \
       MT4Connector/tests/test_mt4_real_api.py \
       MT4Connector/tests/test_signal_writer.py \
       -v --tb=short

# Store exit code
TEST_EXIT_CODE=$?

# Summary
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed. Exit code: $TEST_EXIT_CODE${NC}"
fi

exit $TEST_EXIT_CODE