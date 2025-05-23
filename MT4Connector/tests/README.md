# MT4Connector Test Suite

This directory contains comprehensive tests for the MT4Connector project, covering all major components of the system.

## Running Tests

Run all tests with the root test runner:

```bash
python run_all_tests.py
```

For verbose output:

```bash
python run_all_tests.py -v
```

To run a specific test module:

```bash
python run_all_tests.py -m test_mt4_api
```

## Test Structure

### Core Components Tests

- `test_mt4_api.py`: Tests for the MT4 Manager API wrapper
- `test_signal_monitoring.py`: Tests for signal file monitoring and processing
- `test_config.py`: Tests for the configuration system
- `test_dx_integration.py`: Tests for CloudTrader DX API integration

### Signal Processing Tests

- `test_trade_signals.py`: Tests for different types of trade signals (market, pending, etc.)
- `test_error_handling.py`: Tests for error handling and recovery scenarios

### Telegram Integration Tests

- `test_telegram_bot.py`: Unit tests for the TelegramBot and TelegramSignalHandler classes
- `test_integration.py`: Integration tests for Telegram bot with MT4 connector

## Testing Approach

### Mock Mode Testing

Most tests run in "mock mode" which simulates the MT4 API behaviors without requiring an actual MT4 server connection. This allows for reliable, reproducible testing without external dependencies.

### Test Coverage

The test suite aims to cover:
- Core functionality of each component
- Error handling and edge cases
- Integration between components
- Various types of trade signals
- Recovery from failures

### Test Dependencies

Tests use the Python `unittest` module and mocking features to simulate the behavior of external dependencies:
- `unittest.mock` for mocking objects and functions
- `patch` for temporarily replacing functionality
- Temporary files and directories for isolating file operations

## Adding New Tests

When adding new functionality:

1. Create a corresponding test file in this directory
2. Make sure the test filename starts with `test_`
3. The test runner will automatically discover and run the new tests
4. Ensure tests cover both the "happy path" and error scenarios
5. Run all tests after making changes to verify nothing is broken
6. Maintain isolation between tests using proper setup and teardown

## Test Conventions

- Each test class should inherit from `unittest.TestCase`
- Use `setUp` and `tearDown` methods for test fixtures
- Test method names should be descriptive and start with `test_`
- Mock external dependencies to ensure tests are self-contained
- Use assertions to verify expected behavior
- Include docstrings that explain what each test is verifying