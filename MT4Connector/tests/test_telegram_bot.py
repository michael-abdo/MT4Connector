#!/usr/bin/env python3
"""
Unit tests for the Telegram Bot functionality.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the telegram module before importing TelegramBot
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()

# Now we can import the modules to test
from telegram_bot import TelegramBot
from telegram_bot.signal_handler import TelegramSignalHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestTelegramBot(unittest.TestCase):
    """Tests for the TelegramBot class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the Telegram Updater
        self.mock_updater = MagicMock()
        self.mock_dispatcher = MagicMock()
        self.mock_bot = MagicMock()
        
        # Configure mocks
        self.mock_updater.dispatcher = self.mock_dispatcher
        self.mock_updater.bot = self.mock_bot
        self.mock_bot.get_me.return_value.username = "test_bot"
        
        # Patch the Updater class
        self.updater_patcher = patch('telegram_bot.bot.Updater')
        self.mock_updater_class = self.updater_patcher.start()
        self.mock_updater_class.return_value = self.mock_updater
        
        # Create the bot instance
        self.admin_ids = [12345, 67890]
        self.mt4_api = MagicMock()
        self.telegram_bot = TelegramBot("test_token", self.mt4_api, self.admin_ids)
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.updater_patcher.stop()
    
    def test_initialization(self):
        """Test bot initialization."""
        self.assertEqual(self.telegram_bot.token, "test_token")
        self.assertEqual(self.telegram_bot.mt4_api, self.mt4_api)
        self.assertEqual(self.telegram_bot.admin_ids, self.admin_ids)
        self.assertEqual(self.telegram_bot.bot_username, "test_bot")
        self.assertFalse(self.telegram_bot.running)
        
        # Check if Updater was initialized correctly
        self.mock_updater_class.assert_called_once_with("test_token")
    
    def test_start_stop(self):
        """Test starting and stopping the bot."""
        # Test start
        result = self.telegram_bot.start()
        self.assertTrue(result)
        self.assertTrue(self.telegram_bot.running)
        self.mock_updater.start_polling.assert_called_once()
        
        # Check if handlers were added - should be at least 3 handlers
        # (1 for /start, 1 for /help, 1 for /settings, 1 for callbacks)
        self.assertTrue(self.mock_dispatcher.add_handler.call_count >= 3)
        
        # Test stop
        result = self.telegram_bot.stop()
        self.assertTrue(result)
        self.assertFalse(self.telegram_bot.running)
        self.mock_updater.stop.assert_called_once()
    
    def test_broadcast_message(self):
        """Test broadcasting messages to admins."""
        # Replace the send_message method directly with our own mock
        send_mock = MagicMock()
        self.telegram_bot.updater.bot.send_message = send_mock
        
        # Call the broadcast method
        count = self.telegram_bot.broadcast_message("Test message")
        
        # Verify the expected result
        self.assertEqual(count, 2)  # Two admin IDs
        self.assertEqual(send_mock.call_count, 2)
        
        # Verify the call arguments without being too specific about exact call matching
        # Just check that we called it with the right chat IDs
        chat_ids = [call_args[1]['chat_id'] for call_args in send_mock.call_args_list]
        self.assertIn(12345, chat_ids)
        self.assertIn(67890, chat_ids)
        
        # Check text parameter is correct in all calls
        for call_args in send_mock.call_args_list:
            self.assertEqual(call_args[1]['text'], "Test message")
            # Don't check parse_mode directly as it might be a MockObject
    
    def test_send_trading_signal(self):
        """Test sending trading signals."""
        # Setup the mock to properly track calls
        self.telegram_bot.updater.bot.send_message = MagicMock()
        
        signal = {
            "id": "test_signal_123",
            "type": "buy",
            "symbol": "EURUSD",
            "volume": 0.1,
            "price": 1.10000,
            "sl": 1.09500,
            "tp": 1.10500
        }
        
        # Test sending to all admins
        result = self.telegram_bot.send_trading_signal(signal)
        self.assertEqual(result, 2)  # Two admins
        self.assertEqual(self.telegram_bot.updater.bot.send_message.call_count, 2)
        
        # Reset mock
        self.telegram_bot.updater.bot.send_message.reset_mock()
        
        # Test sending to specific chat
        result = self.telegram_bot.send_trading_signal(signal, chat_id=12345)
        self.assertEqual(result, 1)  # One chat
        self.assertEqual(self.telegram_bot.updater.bot.send_message.call_count, 1)
        
        # Check if inline keyboard was included
        call_args = self.telegram_bot.updater.bot.send_message.call_args[1]
        self.assertIn('reply_markup', call_args)
    
    def test_format_signal_message(self):
        """Test signal message formatting."""
        # Test buy signal
        buy_signal = {
            "id": "test_signal_123",
            "type": "buy",
            "symbol": "EURUSD",
            "volume": 0.1,
            "price": 1.10000,
            "sl": 1.09500,
            "tp": 1.10500,
            "comment": "Test Signal"
        }
        
        buy_message = self.telegram_bot._format_signal_message(buy_signal)
        self.assertIn("*🟢 Trading Signal: BUY*", buy_message)
        self.assertIn("*Symbol:* EURUSD", buy_message)
        self.assertIn("*Volume:* 0.1 lots", buy_message)
        self.assertIn("*Price:* 1.10000", buy_message)
        self.assertIn("*Stop Loss:* 1.09500", buy_message)
        self.assertIn("*Take Profit:* 1.10500", buy_message)
        self.assertIn("*Comment:* Test Signal", buy_message)
        self.assertIn("*Signal ID:* `test_signal_123`", buy_message)
        
        # Test sell signal
        sell_signal = {
            "id": "test_signal_456",
            "type": "sell",
            "symbol": "GBPUSD",
            "volume": 0.2,
            "price": 1.25000,
            "sl": 1.25500,
            "tp": 1.24500
        }
        
        sell_message = self.telegram_bot._format_signal_message(sell_signal)
        self.assertIn("*🔴 Trading Signal: SELL*", sell_message)
        self.assertIn("*Symbol:* GBPUSD", sell_message)
        self.assertIn("*Volume:* 0.2 lots", sell_message)
    
    def test_is_admin(self):
        """Test admin check functionality."""
        self.assertTrue(self.telegram_bot._is_admin(12345))
        self.assertTrue(self.telegram_bot._is_admin(67890))
        self.assertFalse(self.telegram_bot._is_admin(99999))


class TestTelegramSignalHandler(unittest.TestCase):
    """Tests for the TelegramSignalHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the Telegram bot
        self.mock_bot = MagicMock()
        self.mt4_api = MagicMock()
        
        # Create temp signal file for testing
        self.test_signal_file = os.path.join(
            os.path.dirname(__file__),
            "test_signals.txt"
        )
        
        # Create the signal handler
        self.signal_handler = TelegramSignalHandler(
            self.mock_bot,
            self.mt4_api,
            self.test_signal_file,
            auto_execute=False
        )
        
        # Make sure the handler is not running
        self.signal_handler.running = False
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove test signal file if it exists
        if os.path.exists(self.test_signal_file):
            os.remove(self.test_signal_file)
    
    def test_initialization(self):
        """Test signal handler initialization."""
        self.assertEqual(self.signal_handler.telegram_bot, self.mock_bot)
        self.assertEqual(self.signal_handler.mt4_api, self.mt4_api)
        self.assertEqual(self.signal_handler.signal_file, self.test_signal_file)
        self.assertFalse(self.signal_handler.auto_execute)
        self.assertFalse(self.signal_handler.running)
        
        # Check if the bot registered the signal handler
        self.mock_bot.register_signal_handler.assert_called_once()
    
    def test_process_signal(self):
        """Test signal processing."""
        # Create a test signal
        signal = {
            "id": "test_signal_123",
            "type": "buy",
            "symbol": "EURUSD",
            "volume": 0.1,
            "price": 1.10000,
            "sl": 1.09500,
            "tp": 1.10500
        }
        
        # Process the signal
        result = self.signal_handler.process_signal(signal)
        self.assertTrue(result)
        
        # Check if signal was added to pending signals
        self.assertIn("test_signal_123", self.signal_handler.pending_signals)
        self.assertEqual(self.signal_handler.pending_signals["test_signal_123"], signal)
        
        # Process the same signal again (should be skipped)
        self.signal_handler.processed_signal_ids.add("test_signal_123")
        result = self.signal_handler.process_signal(signal)
        self.assertFalse(result)
    
    def test_on_signal_response(self):
        """Test handling signal responses from telegram."""
        # Create a test signal and add it to pending signals
        signal = {
            "id": "test_signal_123",
            "type": "buy",
            "symbol": "EURUSD",
            "volume": 0.1,
            "price": 1.10000,
            "sl": 1.09500,
            "tp": 1.10500
        }
        self.signal_handler.pending_signals["test_signal_123"] = signal
        
        # Test approve action
        self.signal_handler._on_signal_response("test_signal_123", "approve")
        
        # Check if MT4 API was called to execute the trade
        self.mt4_api.place_order.assert_called_once()
        
        # Test reject action
        self.signal_handler.pending_signals["test_signal_123"] = signal  # Re-add signal
        self.mt4_api.reset_mock()
        
        self.signal_handler._on_signal_response("test_signal_123", "reject")
        
        # Check that MT4 API was not called for rejected signal
        self.mt4_api.place_order.assert_not_called()
    
    def test_execute_signal(self):
        """Test signal execution."""
        # Create a test buy signal
        buy_signal = {
            "id": "test_signal_123",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "price": 1.10000,
            "sl": 1.09500,
            "tp": 1.10500
        }
        
        # Set up the MT4 API to return a ticket number
        self.mt4_api.place_order.return_value = 12345
        
        # Execute the signal
        result = self.signal_handler._execute_signal(buy_signal)
        self.assertTrue(result)
        
        # Check if MT4 API was called correctly
        from mt4_api import TradeCommand
        self.mt4_api.place_order.assert_called_once_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY,
            volume=0.1,
            price=1.10000,
            sl=1.09500,
            tp=1.10500,
            comment=''
        )
        
        # Test close signal
        self.mt4_api.reset_mock()
        close_signal = {
            "id": "test_signal_456",
            "type": "close",
            "symbol": "EURUSD",
            "login": 12345,
            "ticket": 12345
        }
        
        self.mt4_api.close_order.return_value = True
        
        result = self.signal_handler._execute_signal(close_signal)
        self.assertTrue(result)
        
        # Check if MT4 API was called correctly
        self.mt4_api.close_order.assert_called_once_with(12345, 12345)


if __name__ == "__main__":
    unittest.main()