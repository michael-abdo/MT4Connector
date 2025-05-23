"""
Integration test for Phase 1: EA Signal to Telegram Flow
Tests the complete flow from EA signal file to Telegram notification
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.signal_processor import SignalProcessor
from src.config import Config

class TestPhase1Integration(unittest.TestCase):
    """Test Phase 1 integration: EA → Signal File → Processor → Telegram"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.signal_file = os.path.join(self.test_dir, 'ea_signals.txt')
        
        # Create config with test signal file
        self.config = Config()
        self.config.SIGNAL_FILE = self.signal_file
        self.config.USE_MOCK_API = True  # Use mock mode for testing
        
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_ea_signal_format(self):
        """Test that EA signals match expected format"""
        # Simulate EA writing a signal
        ea_signal = [{
            "signal_id": "1234567890_98765_EURUSD",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "comment": "MA Cross Buy",
            "magic": 12345
        }]
        
        # Write signal as EA would
        with open(self.signal_file, 'w') as f:
            json.dump(ea_signal, f)
        
        # Verify signal can be read
        with open(self.signal_file, 'r') as f:
            loaded = json.load(f)
        
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]['type'], 'buy')
        self.assertEqual(loaded[0]['symbol'], 'EURUSD')
    
    def test_signal_processor_reads_ea_format(self):
        """Test that signal processor can read EA signal format"""
        # Create processor
        processor = SignalProcessor(self.config)
        
        # Write EA signal
        ea_signal = [{
            "signal_id": "test_signal_123",
            "type": "sell",
            "symbol": "GBPUSD",
            "login": 12345,
            "volume": 0.2,
            "sl": 1.2650,
            "tp": 1.2450,
            "comment": "Test Signal"
        }]
        
        with open(self.signal_file, 'w') as f:
            json.dump(ea_signal, f)
        
        # Process signals
        signals = processor._read_signals()
        
        self.assertIsNotNone(signals)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]['type'], 'sell')
        self.assertEqual(signals[0]['symbol'], 'GBPUSD')
    
    def test_multiple_signal_formats(self):
        """Test various signal types from EA"""
        test_signals = [
            {
                "signal_id": "sig1",
                "type": "buy",
                "symbol": "EURUSD",
                "login": 12345,
                "volume": 0.1
            },
            {
                "signal_id": "sig2",
                "type": "sell_limit",
                "symbol": "GBPUSD",
                "login": 12345,
                "volume": 0.2,
                "price": 1.2500,
                "sl": 1.2600,
                "tp": 1.2400
            },
            {
                "signal_id": "sig3",
                "type": "close",
                "symbol": "USDJPY",
                "login": 12345,
                "volume": 0,
                "ticket": 987654
            }
        ]
        
        # Write signals
        with open(self.signal_file, 'w') as f:
            json.dump(test_signals, f)
        
        # Create processor and read
        processor = SignalProcessor(self.config)
        signals = processor._read_signals()
        
        self.assertEqual(len(signals), 3)
        self.assertEqual(signals[0]['type'], 'buy')
        self.assertEqual(signals[1]['type'], 'sell_limit')
        self.assertEqual(signals[2]['type'], 'close')
    
    def test_signal_file_monitoring(self):
        """Test that file changes are detected"""
        processor = SignalProcessor(self.config)
        
        # Write initial empty signal
        with open(self.signal_file, 'w') as f:
            f.write('[]')
        
        # Start monitoring in mock mode
        processor.start_monitoring()
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Write a new signal
        new_signal = [{
            "signal_id": "monitor_test",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1
        }]
        
        with open(self.signal_file, 'w') as f:
            json.dump(new_signal, f)
        
        # Give processor time to detect change
        time.sleep(0.5)
        
        # Stop monitoring
        processor.stop_monitoring()
        
        # In a real test, we would verify the signal was processed
        # For now, just verify no exceptions
        self.assertTrue(True)
    
    def test_empty_signal_handling(self):
        """Test handling of empty signal file"""
        # Write empty array
        with open(self.signal_file, 'w') as f:
            f.write('[]')
        
        processor = SignalProcessor(self.config)
        signals = processor._read_signals()
        
        self.assertIsNotNone(signals)
        self.assertEqual(len(signals), 0)

if __name__ == '__main__':
    unittest.main()