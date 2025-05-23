#!/usr/bin/env python3
"""
Integration tests for the MT4 Connector with Telegram integration.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import tempfile
import logging
import time

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the telegram module before importing anything that depends on it
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()
sys.modules['telegram.Update'] = MagicMock()
sys.modules['telegram.ParseMode'] = MagicMock()
sys.modules['telegram.InlineKeyboardButton'] = MagicMock()
sys.modules['telegram.InlineKeyboardMarkup'] = MagicMock()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestTelegramIntegration(unittest.TestCase):
    """Integration tests for Telegram bot with MT4 connector."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temp directory for signal files
        self.temp_dir = tempfile.mkdtemp()
        self.signal_file = os.path.join(self.temp_dir, "test_signals.txt")
        
        # Patch config values for testing
        self.config_patcher = patch.dict('config.__dict__', {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_ADMIN_IDS': [12345, 67890],
            'EA_SIGNAL_FILE': self.signal_file,
            'AUTO_EXECUTE_SIGNALS': False
        })
        self.config_patcher.start()
        
        # Mock MT4 API
        self.mt4_api_patcher = patch('mt4_api.MT4Manager')
        self.mock_mt4_manager = self.mt4_api_patcher.start()
        self.mock_mt4_api = MagicMock()
        self.mock_mt4_manager.return_value = self.mock_mt4_api
        
        # Mock Telegram Updater
        self.updater_patcher = patch('telegram_bot.bot.Updater')
        self.mock_updater_class = self.updater_patcher.start()
        self.mock_updater = MagicMock()
        self.mock_dispatcher = MagicMock()
        self.mock_bot = MagicMock()
        
        # Configure mocks
        self.mock_updater.dispatcher = self.mock_dispatcher
        self.mock_updater.bot = self.mock_bot
        self.mock_bot.get_me.return_value.username = "test_bot"
        self.mock_updater_class.return_value = self.mock_updater
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.config_patcher.stop()
        self.mt4_api_patcher.stop()
        self.updater_patcher.stop()
        
        # Clean up temp directory
        if os.path.exists(self.signal_file):
            os.remove(self.signal_file)
        os.rmdir(self.temp_dir)
    
    def test_signal_flow(self):
        """Test the full signal flow from file to Telegram to MT4."""
        # Import the modules
        from telegram_bot import TelegramBot
        from telegram_bot.signal_handler import TelegramSignalHandler
        from mt4_api import TradeCommand
        
        # Set up the mock updater bot to track calls
        bot_mock = MagicMock()
        self.mock_updater.bot = bot_mock
        
        # Create the bot and signal handler
        bot = TelegramBot("test_token", self.mock_mt4_api, [12345, 67890])
        
        # Replace the send_message method with a mock to track calls
        bot.updater.bot.send_message = MagicMock()
        
        # Configure mock MT4 API behavior
        self.mock_mt4_api.place_order = MagicMock(return_value=12345)
        
        # Create signal handler and store test signal in pending signals directly
        signal_handler = TelegramSignalHandler(
            bot,
            self.mock_mt4_api,
            self.signal_file,
            auto_execute=False
        )
        
        # Start the bot and signal handler
        bot.start()
        signal_handler.start()
        
        try:
            # Create a test signal
            test_signal = {
                "id": "test_signal_123",
                "type": "buy",
                "symbol": "EURUSD",
                "login": 12345,
                "volume": 0.1,
                "price": 1.10000,
                "sl": 1.09500,
                "tp": 1.10500,
                "comment": "Test Signal"
            }
            
            # Add signal directly to pending signals
            signal_handler.pending_signals["test_signal_123"] = test_signal
            
            # Write signal to file
            with open(self.signal_file, 'w') as f:
                json.dump(test_signal, f, indent=2)
            
            # Simulate signal processing directly
            signal_handler._handle_signal(test_signal)
            
            # Verify send_trading_signal was called (by checking if send_message was called)
            self.assertTrue(bot.updater.bot.send_message.called)
            
            # Manually execute signal (simulate approval)
            result = signal_handler._execute_signal(test_signal)
            self.assertTrue(result)
            
            # Verify MT4 API was called with correct parameters
            self.mock_mt4_api.place_order.assert_called_with(
                login=12345,
                symbol="EURUSD",
                cmd=TradeCommand.OP_BUY,
                volume=0.1,
                price=1.10000,
                sl=1.09500,
                tp=1.10500,
                comment="Test Signal"
            )
            
        finally:
            # Stop the bot and signal handler
            signal_handler.stop()
            bot.stop()
    
    def test_run_with_telegram(self):
        """Test the run_with_telegram entry point (partial test)."""
        # Patch the main components
        with patch('telegram_bot.TelegramBot') as mock_bot_class, \
             patch('telegram_bot.signal_handler.TelegramSignalHandler') as mock_handler_class:
            
            # Configure mocks
            mock_bot = MagicMock()
            mock_bot.start.return_value = True
            mock_bot.bot_username = "test_bot"
            mock_bot_class.return_value = mock_bot
            
            mock_handler = MagicMock()
            mock_handler.start.return_value = True
            mock_handler_class.return_value = mock_handler
            
            # Patch the main loop to avoid hanging
            with patch('time.sleep', side_effect=KeyboardInterrupt):
                # Import the run_with_telegram module
                from run_with_telegram import run_telegram_bot
                
                # Run with arguments to skip dependency checks
                result = run_telegram_bot()
                
                # Check the result
                self.assertEqual(result, 0)
                
                # Check if the components were initialized and started
                mock_bot_class.assert_called_once()
                mock_handler_class.assert_called_once()
                mock_bot.start.assert_called_once()
                mock_handler.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()