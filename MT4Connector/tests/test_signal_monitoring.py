#!/usr/bin/env python3
"""
Unit tests for the Signal Monitoring functionality.
Tests the signal file handling and monitoring capabilities.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import tempfile
import time
import logging
import threading

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import modules to test
from signal_processor import SignalProcessor, SignalFileHandler
from mt4_api import MT4Manager

class TestSignalFileHandler(unittest.TestCase):
    """Test cases for the SignalFileHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_signal_file = os.path.join(self.temp_dir, "test_signals.txt")
        
        # Create a mock signal processor
        self.mock_processor = MagicMock()
        
        # Create the signal file handler
        self.file_handler = SignalFileHandler(self.mock_processor)
        
        # Create an empty signal file
        with open(self.test_signal_file, 'w') as f:
            f.write('[]')
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove test files and directory
        if os.path.exists(self.test_signal_file):
            os.remove(self.test_signal_file)
        os.rmdir(self.temp_dir)
    
    def test_on_modified(self):
        """Test handling file modification events."""
        # Create a mock event
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = self.test_signal_file
        
        # Call the on_modified method
        self.file_handler.on_modified(mock_event)
        
        # Verify the processor's process_signals method was called
        self.mock_processor.process_signals.assert_called_once()
    
    def test_debounce(self):
        """Test the debounce functionality to prevent multiple processing."""
        # Create a mock event
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = self.test_signal_file
        
        # Call on_modified twice in quick succession
        self.file_handler.on_modified(mock_event)
        self.file_handler.on_modified(mock_event)
        
        # Verify process_signals was only called once (due to debounce)
        self.mock_processor.process_signals.assert_called_once()
        
        # Reset the mock
        self.mock_processor.process_signals.reset_mock()
        
        # Change the last_modified time to simulate time passing
        self.file_handler.last_modified = time.time() - 2
        
        # Call on_modified again
        self.file_handler.on_modified(mock_event)
        
        # Verify process_signals was called again
        self.mock_processor.process_signals.assert_called_once()


class TestSignalProcessor(unittest.TestCase):
    """Test cases for the SignalProcessor class."""
    
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
    
    def test_start_file_monitoring(self):
        """Test starting file monitoring."""
        result = self.processor.start_file_monitoring()
        self.assertTrue(result)
        self.assertIsNotNone(self.processor.observer)
        
        # Clean up
        self.processor.stop_file_monitoring()
    
    def test_stop_file_monitoring(self):
        """Test stopping file monitoring."""
        # First start monitoring
        self.processor.start_file_monitoring()
        
        # Then stop it
        result = self.processor.stop_file_monitoring()
        self.assertTrue(result)
        self.assertIsNone(self.processor.observer)
    
    def test_process_signals_empty_file(self):
        """Test processing signals from an empty file."""
        # Process the empty signal file
        processed_count = self.processor.process_signals()
        
        # Should process 0 signals
        self.assertEqual(processed_count, 0)
    
    def test_process_signals_with_content(self):
        """Test processing signals from a file with content."""
        # Create a test signal
        test_signal = {
            "id": "test_signal_123",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.09500,
            "tp": 1.10500,
            "comment": "Test Signal"
        }
        
        # Write the signal to the file
        with open(self.test_signal_file, 'w') as f:
            json.dump([test_signal], f)
        
        # Mock the place_order method to return a ticket number
        self.mock_mt4_api.place_order.return_value = 12345
        
        # Process the signal file
        processed_count = self.processor.process_signals()
        
        # Should process 1 signal
        self.assertEqual(processed_count, 1)
        
        # Verify the MT4 API was called with the correct parameters
        self.mock_mt4_api.place_order.assert_called_once()
        
        # Process again - should not process the same signal twice
        processed_count = self.processor.process_signals()
        self.assertEqual(processed_count, 0)
    
    def test_check_signal_file(self):
        """Test checking the signal file for changes."""
        # Initially, the file is empty
        result = self.processor.check_signal_file()
        self.assertTrue(result)
        
        # Update signal file with a new signal
        test_signal = {
            "id": "test_signal_456",
            "type": "sell",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.10500,
            "tp": 1.09500,
            "comment": "Test Signal"
        }
        
        # Patch process_signals to track calls
        with patch.object(self.processor, 'process_signals') as mock_process:
            # Write the signal to the file
            with open(self.test_signal_file, 'w') as f:
                json.dump([test_signal], f)
            
            # Need to modify the last_check_time to force a check
            self.processor.last_check_time = 0
            
            # Check the signal file
            result = self.processor.check_signal_file()
            self.assertTrue(result)
            
            # Verify process_signals was called
            mock_process.assert_called_once()
    
    def test_execute_buy_signal(self):
        """Test executing a buy signal."""
        # Create a buy signal
        buy_signal = {
            "id": "test_buy_789",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.09500,
            "tp": 1.10500,
            "comment": "Test Buy"
        }
        
        # Mock MT4 API to return a ticket
        self.mock_mt4_api.place_order.return_value = 54321
        
        # Execute the signal
        result = self.processor.execute_signal(buy_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        from mt4_api import TradeCommand
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY,
            volume=0.1,
            price=1.10002,  # Should use ask price for BUY
            sl=1.09500,
            tp=1.10500,
            comment="Test Buy"
        )
    
    def test_execute_sell_signal(self):
        """Test executing a sell signal."""
        # Create a sell signal
        sell_signal = {
            "id": "test_sell_789",
            "type": "sell",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.10500,
            "tp": 1.09500,
            "comment": "Test Sell"
        }
        
        # Mock MT4 API to return a ticket
        self.mock_mt4_api.place_order.return_value = 54321
        
        # Execute the signal
        result = self.processor.execute_signal(sell_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        from mt4_api import TradeCommand
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_SELL,
            volume=0.1,
            price=1.10000,  # Should use bid price for SELL
            sl=1.10500,
            tp=1.09500,
            comment="Test Sell"
        )
    
    def test_execute_pending_order(self):
        """Test executing a pending order signal."""
        # Create a buy limit signal
        buy_limit_signal = {
            "id": "test_buy_limit_789",
            "type": "buy_limit",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "price": 1.09800,  # Target entry price
            "sl": 1.09500,
            "tp": 1.10500,
            "comment": "Test Buy Limit"
        }
        
        # Mock MT4 API to return a ticket
        self.mock_mt4_api.place_order.return_value = 54321
        
        # Execute the signal
        result = self.processor.execute_signal(buy_limit_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        from mt4_api import TradeCommand
        self.mock_mt4_api.place_order.assert_called_with(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY_LIMIT,
            volume=0.1,
            price=1.09800,  # Should use the specified price
            sl=1.09500,
            tp=1.10500,
            comment="Test Buy Limit"
        )
    
    def test_execute_close_order(self):
        """Test executing a close order signal."""
        # Create a close signal
        close_signal = {
            "id": "test_close_789",
            "type": "close",
            "symbol": "EURUSD",
            "login": 12345,
            "ticket": 54321,
            "comment": "Test Close"
        }
        
        # Mock MT4 API to return success
        self.mock_mt4_api.close_order.return_value = True
        
        # Execute the signal
        result = self.processor.execute_signal(close_signal)
        self.assertTrue(result)
        
        # Verify MT4 API was called correctly
        self.mock_mt4_api.close_order.assert_called_with(12345, 54321)
    
    def test_invalid_signal(self):
        """Test handling invalid signals."""
        # Create an invalid signal missing required fields
        invalid_signal = {
            "id": "test_invalid_789",
            "type": "buy",
            # Missing symbol and login
            "volume": 0.1
        }
        
        # Execute the signal - should fail
        result = self.processor.execute_signal(invalid_signal)
        self.assertFalse(result)
    
    def test_unknown_signal_type(self):
        """Test handling unknown signal types."""
        # Create a signal with unknown type
        unknown_signal = {
            "id": "test_unknown_789",
            "type": "unknown_type",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1
        }
        
        # Execute the signal - should fail
        result = self.processor.execute_signal(unknown_signal)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()