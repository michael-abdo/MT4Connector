#!/usr/bin/env python3
"""
Unit tests for different types of trade signals in the MT4 Connector.
Tests the processing of various trade signal formats (market orders, pending orders, etc.)
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import tempfile
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import modules to test
from signal_processor import SignalProcessor
from mt4_api import MT4Manager, TradeCommand

class TestTradeSignals(unittest.TestCase):
    """Test cases for different types of trade signals."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_signal_file = os.path.join(self.temp_dir, "test_signals.txt")
        
        # Patch the EA_SIGNAL_FILE value in config
        self.signal_file_patcher = patch('signal_processor.EA_SIGNAL_FILE', self.test_signal_file)
        self.signal_file_patcher.start()
        
        # Create mock MT4 API
        self.mock_mt4_api = MagicMock()
        self.mock_mt4_api.get_symbol_info.return_value = {
            "symbol": "EURUSD",
            "digits": 5,
            "point": 0.00001,
            "bid": 1.10000,
            "ask": 1.10002
        }
        
        # Create mock DX API
        self.mock_dx_api = MagicMock()
        
        # Create the signal processor
        self.processor = SignalProcessor(self.mock_mt4_api, self.mock_dx_api)
        
        # Initialize with a connected state for testing
        self.processor.connected = True
        
        # Configure MT4 API methods to return success
        self.mock_mt4_api.place_order.return_value = 12345
        self.mock_mt4_api.modify_order.return_value = True
        self.mock_mt4_api.close_order.return_value = True
        
        # Create an empty signal file
        with open(self.test_signal_file, 'w') as f:
            f.write('[]')
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop file monitoring if active
        if self.processor.observer:
            self.processor.stop_file_monitoring()
        
        # Remove test files and directory
        if os.path.exists(self.test_signal_file):
            os.remove(self.test_signal_file)
        os.rmdir(self.temp_dir)
        
        # Stop the signal_file_patcher
        self.signal_file_patcher.stop()
    
    def test_market_buy_signal(self):
        """Test processing a market buy signal."""
        # Create a market buy signal
        buy_signal = {
            "id": "test_buy_123",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.09500,
            "tp": 1.10500,
            "comment": "Market Buy Test"
        }
        
        # Execute the signal
        result = self.processor.execute_signal(buy_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY,
            volume=0.1,
            price=1.10002,  # Should use ask price for BUY
            sl=1.09500,
            tp=1.10500,
            comment="Market Buy Test"
        )
    
    def test_market_sell_signal(self):
        """Test processing a market sell signal."""
        # Create a market sell signal
        sell_signal = {
            "id": "test_sell_123",
            "type": "sell",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.10500,
            "tp": 1.09500,
            "comment": "Market Sell Test"
        }
        
        # Execute the signal
        result = self.processor.execute_signal(sell_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_SELL,
            volume=0.1,
            price=1.10000,  # Should use bid price for SELL
            sl=1.10500,
            tp=1.09500,
            comment="Market Sell Test"
        )
    
    def test_buy_limit_signal(self):
        """Test processing a buy limit signal."""
        # Create a buy limit signal
        buy_limit_signal = {
            "id": "test_buy_limit_123",
            "type": "buy_limit",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "price": 1.09800,  # Entry price below current price
            "sl": 1.09500,
            "tp": 1.10500,
            "comment": "Buy Limit Test"
        }
        
        # Execute the signal
        result = self.processor.execute_signal(buy_limit_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY_LIMIT,
            volume=0.1,
            price=1.09800,
            sl=1.09500,
            tp=1.10500,
            comment="Buy Limit Test"
        )
    
    def test_sell_limit_signal(self):
        """Test processing a sell limit signal."""
        # Create a sell limit signal
        sell_limit_signal = {
            "id": "test_sell_limit_123",
            "type": "sell_limit",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "price": 1.10200,  # Entry price above current price
            "sl": 1.10500,
            "tp": 1.09500,
            "comment": "Sell Limit Test"
        }
        
        # Execute the signal
        result = self.processor.execute_signal(sell_limit_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_SELL_LIMIT,
            volume=0.1,
            price=1.10200,
            sl=1.10500,
            tp=1.09500,
            comment="Sell Limit Test"
        )
    
    def test_buy_stop_signal(self):
        """Test processing a buy stop signal."""
        # Create a buy stop signal
        buy_stop_signal = {
            "id": "test_buy_stop_123",
            "type": "buy_stop",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "price": 1.10200,  # Entry price above current price
            "sl": 1.09900,
            "tp": 1.10500,
            "comment": "Buy Stop Test"
        }
        
        # Execute the signal
        result = self.processor.execute_signal(buy_stop_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY_STOP,
            volume=0.1,
            price=1.10200,
            sl=1.09900,
            tp=1.10500,
            comment="Buy Stop Test"
        )
    
    def test_sell_stop_signal(self):
        """Test processing a sell stop signal."""
        # Create a sell stop signal
        sell_stop_signal = {
            "id": "test_sell_stop_123",
            "type": "sell_stop",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "price": 1.09800,  # Entry price below current price
            "sl": 1.10100,
            "tp": 1.09500,
            "comment": "Sell Stop Test"
        }
        
        # Execute the signal
        result = self.processor.execute_signal(sell_stop_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_SELL_STOP,
            volume=0.1,
            price=1.09800,
            sl=1.10100,
            tp=1.09500,
            comment="Sell Stop Test"
        )
    
    def test_close_order_signal(self):
        """Test processing a close order signal."""
        # Create a close order signal
        close_signal = {
            "id": "test_close_123",
            "type": "close",
            "symbol": "EURUSD",
            "login": 12345,
            "ticket": 54321,
            "comment": "Close Order Test"
        }
        
        # Execute the signal
        result = self.processor.execute_signal(close_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.close_order.assert_called_with(12345, 54321)
    
    def test_process_multiple_signals(self):
        """Test processing multiple signals at once."""
        # Create multiple signals
        signals = [
            {
                "id": "test_multi_1",
                "type": "buy",
                "symbol": "EURUSD",
                "login": 12345,
                "volume": 0.1,
                "sl": 1.09500,
                "tp": 1.10500
            },
            {
                "id": "test_multi_2",
                "type": "sell",
                "symbol": "GBPUSD",
                "login": 12345,
                "volume": 0.2,
                "sl": 1.31000,
                "tp": 1.29000
            }
        ]
        
        # Write signals to the file
        with open(self.test_signal_file, 'w') as f:
            json.dump(signals, f)
        
        # Update symbol info mock for GBPUSD
        symbol_info_side_effect = lambda symbol: {
            "EURUSD": {
                "symbol": "EURUSD",
                "digits": 5,
                "point": 0.00001,
                "bid": 1.10000,
                "ask": 1.10002
            },
            "GBPUSD": {
                "symbol": "GBPUSD",
                "digits": 5,
                "point": 0.00001,
                "bid": 1.30000,
                "ask": 1.30002
            }
        }[symbol]
        
        self.mock_mt4_api.get_symbol_info.side_effect = symbol_info_side_effect
        
        # Process all signals
        processed_count = self.processor.process_signals()
        
        # Should process 2 signals
        self.assertEqual(processed_count, 2)
        
        # Verify MT4 API was called twice for place_order
        self.assertEqual(self.mock_mt4_api.place_order.call_count, 2)
    
    def test_signal_with_minimum_fields(self):
        """Test processing a signal with only required fields."""
        # Create a minimal signal
        minimal_signal = {
            "id": "test_minimal",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345
        }
        
        # Execute the signal
        result = self.processor.execute_signal(minimal_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called with default values
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY,
            volume=0.1,  # Default volume
            price=1.10002,
            sl=0,  # No stop loss
            tp=0,  # No take profit
            comment=''  # Empty comment
        )
    
    def test_signal_with_invalid_symbol(self):
        """Test handling a signal with an invalid symbol."""
        # Create a signal with invalid symbol
        invalid_symbol_signal = {
            "id": "test_invalid_symbol",
            "type": "buy",
            "symbol": "INVALID",
            "login": 12345,
            "volume": 0.1
        }
        
        # Mock get_symbol_info to return None for invalid symbol
        self.mock_mt4_api.get_symbol_info.return_value = None
        
        # Execute the signal - should fail
        result = self.processor.execute_signal(invalid_symbol_signal)
        self.assertFalse(result)
        
        # Verify place_order was not called
        self.mock_mt4_api.place_order.assert_not_called()


if __name__ == "__main__":
    unittest.main()