#!/usr/bin/env python3
"""
Unit tests for error handling and recovery scenarios in the MT4 Connector.
Tests how the application handles various error conditions.
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import modules to test
from signal_processor import SignalProcessor
from mt4_api import MT4Manager, TradeCommand

class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling and recovery scenarios."""
    
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
    
    def test_connection_failure(self):
        """Test handling of connection failure."""
        # Create new processor with clean state
        processor = SignalProcessor(self.mock_mt4_api, self.mock_dx_api)
        
        # Make connect method return False to simulate connection failure
        self.mock_mt4_api.connect.return_value = False
        
        # Try to connect
        result = processor.connect("localhost", 443, 12345, "password")
        
        # Should return False
        self.assertFalse(result)
        self.assertFalse(processor.connected)
    
    def test_login_failure(self):
        """Test handling of login failure."""
        # Create new processor with clean state
        processor = SignalProcessor(self.mock_mt4_api, self.mock_dx_api)
        
        # Make connect method succeed but login method fail
        self.mock_mt4_api.connect.return_value = True
        self.mock_mt4_api.login.return_value = False
        
        # Try to connect
        result = processor.connect("localhost", 443, 12345, "password")
        
        # Should return False
        self.assertFalse(result)
        self.assertFalse(processor.connected)
        
        # Should disconnect after login failure
        self.mock_mt4_api.disconnect.assert_called_once()
    
    def test_disconnect_failure(self):
        """Test handling of disconnect failure."""
        # Create new processor with clean state
        processor = SignalProcessor(self.mock_mt4_api, self.mock_dx_api)
        
        # Successfully connect
        self.mock_mt4_api.connect.return_value = True
        self.mock_mt4_api.login.return_value = True
        processor.connect("localhost", 443, 12345, "password")
        
        # Make disconnect method fail
        self.mock_mt4_api.disconnect.return_value = False
        
        # Try to disconnect
        result = processor.disconnect()
        
        # Should return False
        self.assertFalse(result)
        # Should still mark itself as disconnected for safety
        self.assertFalse(processor.connected)
    
    def test_invalid_json_in_signal_file(self):
        """Test handling of invalid JSON in signal file."""
        # Write invalid JSON to the file
        with open(self.test_signal_file, 'w') as f:
            f.write('{"invalid": "json"')  # Missing closing brace
        
        # Process signals - should handle error gracefully
        processed_count = self.processor.process_signals()
        
        # Should process 0 signals due to error
        self.assertEqual(processed_count, 0)
        
        # Place order should not be called
        self.mock_mt4_api.place_order.assert_not_called()
    
    def test_missing_signal_file(self):
        """Test handling of missing signal file."""
        # Remove the signal file
        os.remove(self.test_signal_file)
        
        # Process signals - should handle error gracefully
        with patch('signal_processor.logger') as mock_logger:
            result = self.processor.check_signal_file()
            
            # Should return False due to missing file
            self.assertFalse(result)
            
            # Should log a warning
            mock_logger.warning.assert_called_once()
    
    def test_place_order_failure(self):
        """Test handling of failure when placing an order."""
        # Create a test signal
        test_signal = {
            "id": "test_failure_123",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.09500,
            "tp": 1.10500,
            "comment": "Test Signal"
        }
        
        # Make place_order method return 0 to simulate failure
        self.mock_mt4_api.place_order.return_value = 0
        
        # Execute the signal
        with patch('signal_processor.logger') as mock_logger:
            result = self.processor.execute_signal(test_signal)
            
            # Should return False due to place_order failure
            self.assertFalse(result)
            
            # Should log an error
            mock_logger.error.assert_called_once()
    
    def test_unknown_signal_type(self):
        """Test handling of unknown signal type."""
        # Create a signal with unknown type
        unknown_signal = {
            "id": "test_unknown_123",
            "type": "unknown_type",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1
        }
        
        # Execute the signal
        with patch('signal_processor.logger') as mock_logger:
            result = self.processor.execute_signal(unknown_signal)
            
            # Should return False due to unknown type
            self.assertFalse(result)
            
            # Should log an error
            mock_logger.error.assert_called_once()
    
    def test_reconnection_attempt(self):
        """Test reconnection attempt after server disconnection."""
        # Mock reconnect functionality in MT4Manager
        reconnect_mock = MagicMock()
        
        # Create a test scenario where connection is lost
        with patch.object(self.mock_mt4_api, 'connect', return_value=True) as connect_mock, \
             patch.object(self.mock_mt4_api, 'login', return_value=True) as login_mock:
            
            # First connection attempt
            self.processor.connect("localhost", 443, 12345, "password")
            self.assertTrue(self.processor.connected)
            connect_mock.assert_called_once()
            login_mock.assert_called_once()
            
            # Manually set connected to False to simulate disconnect
            self.processor.connected = False
            
            # Pretend signal file was updated
            with open(self.test_signal_file, 'w') as f:
                json.dump([{"id": "test", "type": "buy", "symbol": "EURUSD", "login": 12345, "volume": 0.1}], f)
            
            # Process signals method should detect not connected state
            processed_count = self.processor.process_signals()
            
            # Should process 0 signals due to not being connected
            self.assertEqual(processed_count, 0)
    
    def test_get_symbol_info_failure(self):
        """Test handling of failure to get symbol information."""
        # Create a test signal
        test_signal = {
            "id": "test_symbol_failure",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1
        }
        
        # Make get_symbol_info return None to simulate failure
        self.mock_mt4_api.get_symbol_info.return_value = None
        
        # Execute the signal
        with patch('signal_processor.logger') as mock_logger:
            result = self.processor.execute_signal(test_signal)
            
            # Should return False due to get_symbol_info failure
            self.assertFalse(result)
            
            # Should log an error
            mock_logger.error.assert_called_once()
    
    def test_observer_error_handling(self):
        """Test handling of errors in file observer."""
        # Patch Observer to raise exception on start
        with patch('signal_processor.Observer') as mock_observer_class:
            mock_observer = MagicMock()
            mock_observer.start.side_effect = Exception("Test exception")
            mock_observer_class.return_value = mock_observer
            
            # Try to start file monitoring - should return False due to exception
            with patch('signal_processor.logger') as mock_logger:
                result = self.processor.start_file_monitoring()
                
                # Should return False due to exception
                self.assertFalse(result)
                
                # Should log an error
                mock_logger.error.assert_called_once()
    
    def test_stop_observer_error_handling(self):
        """Test handling of errors when stopping file observer."""
        # Start file monitoring
        self.processor.start_file_monitoring()
        
        # Patch observer methods to raise exception
        self.processor.observer.stop = MagicMock(side_effect=Exception("Test exception"))
        
        # Try to stop file monitoring - should handle error
        with patch('signal_processor.logger') as mock_logger:
            result = self.processor.stop_file_monitoring()
            
            # Should return False due to exception
            self.assertFalse(result)
            
            # Should log an error
            mock_logger.error.assert_called_once()
    
    def test_run_error_handling(self):
        """Test handling of errors in main run loop."""
        # Make check_signal_file raise exception first time, then work normally
        side_effects = [Exception("Test exception"), True]
        
        # Set up the processor to be properly connected
        self.processor.connected = True
        
        # Patch to simulate keyboard interrupt after some time
        with patch.object(self.processor, 'check_signal_file', side_effect=side_effects), \
             patch('signal_processor.time.sleep', side_effect=KeyboardInterrupt), \
             patch('signal_processor.logger') as mock_logger:
            
            # Run the main loop - should catch exceptions and keyboard interrupt
            self.processor.run()
            
            # Should log the error
            mock_logger.error.assert_called_once()
            
            # Should disconnect on exit
            self.assertFalse(self.processor.connected)
    
    def test_invalid_signal_parameters(self):
        """Test handling of invalid signal parameters."""
        # Create signals with various missing parameters
        invalid_signals = [
            # Missing symbol
            {"id": "missing_symbol", "type": "buy", "login": 12345, "volume": 0.1},
            # Missing login
            {"id": "missing_login", "type": "buy", "symbol": "EURUSD", "volume": 0.1},
            # Missing type
            {"id": "missing_type", "symbol": "EURUSD", "login": 12345, "volume": 0.1},
            # Missing id
            {"type": "buy", "symbol": "EURUSD", "login": 12345, "volume": 0.1}
        ]
        
        # Test each invalid signal
        for signal in invalid_signals:
            with patch('signal_processor.logger') as mock_logger:
                # Execute the signal
                result = self.processor.execute_signal(signal)
                
                # Should return False due to invalid parameters
                self.assertFalse(result)
                
                # Should log an error
                mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()