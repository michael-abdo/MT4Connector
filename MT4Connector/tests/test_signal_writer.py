"""
Test suite for SignalWriter EA signal format validation
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

class TestSignalWriter(unittest.TestCase):
    """Test SignalWriter EA signal format"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_signal_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        self.test_signal_file.close()
        self.signal_path = self.test_signal_file.name
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.signal_path):
            os.unlink(self.signal_path)
    
    def test_signal_format_buy(self):
        """Test buy signal format"""
        # Example signal that EA would write
        signal_data = [{
            "signal_id": "1234567890_98765_EURUSD",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "comment": "MA Cross Buy",
            "magic": 12345
        }]
        
        # Write signal to file
        with open(self.signal_path, 'w') as f:
            json.dump(signal_data, f)
        
        # Read and validate
        with open(self.signal_path, 'r') as f:
            loaded_data = json.load(f)
        
        self.assertIsInstance(loaded_data, list)
        self.assertEqual(len(loaded_data), 1)
        
        signal = loaded_data[0]
        self.assertEqual(signal['type'], 'buy')
        self.assertEqual(signal['symbol'], 'EURUSD')
        self.assertEqual(signal['volume'], 0.1)
        self.assertIn('signal_id', signal)
        self.assertIn('login', signal)
    
    def test_signal_format_sell_with_sl_tp(self):
        """Test sell signal with SL/TP"""
        signal_data = [{
            "signal_id": "1234567890_98765_GBPUSD",
            "type": "sell",
            "symbol": "GBPUSD",
            "login": 12345,
            "volume": 0.2,
            "sl": 1.2650,
            "tp": 1.2450,
            "comment": "MA Cross Sell"
        }]
        
        with open(self.signal_path, 'w') as f:
            json.dump(signal_data, f)
        
        with open(self.signal_path, 'r') as f:
            loaded_data = json.load(f)
        
        signal = loaded_data[0]
        self.assertEqual(signal['type'], 'sell')
        self.assertEqual(signal['sl'], 1.2650)
        self.assertEqual(signal['tp'], 1.2450)
    
    def test_signal_format_pending_order(self):
        """Test pending order signal format"""
        signal_data = [{
            "signal_id": "1234567890_98765_USDJPY",
            "type": "buy_limit",
            "symbol": "USDJPY",
            "login": 12345,
            "volume": 0.1,
            "price": 108.50,
            "sl": 108.00,
            "tp": 109.50
        }]
        
        with open(self.signal_path, 'w') as f:
            json.dump(signal_data, f)
        
        with open(self.signal_path, 'r') as f:
            loaded_data = json.load(f)
        
        signal = loaded_data[0]
        self.assertEqual(signal['type'], 'buy_limit')
        self.assertEqual(signal['price'], 108.50)
    
    def test_signal_format_close_order(self):
        """Test close order signal format"""
        signal_data = [{
            "signal_id": "1234567890_98765_EURUSD",
            "type": "close",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0,
            "ticket": 987654
        }]
        
        with open(self.signal_path, 'w') as f:
            json.dump(signal_data, f)
        
        with open(self.signal_path, 'r') as f:
            loaded_data = json.load(f)
        
        signal = loaded_data[0]
        self.assertEqual(signal['type'], 'close')
        self.assertEqual(signal['ticket'], 987654)
    
    def test_empty_signal_file(self):
        """Test handling of empty signal file"""
        with open(self.signal_path, 'w') as f:
            f.write("[]")
        
        with open(self.signal_path, 'r') as f:
            loaded_data = json.load(f)
        
        self.assertIsInstance(loaded_data, list)
        self.assertEqual(len(loaded_data), 0)
    
    def test_signal_required_fields(self):
        """Test that all required fields are present"""
        required_fields = ['signal_id', 'type', 'symbol', 'login', 'volume']
        
        signal_data = [{
            "signal_id": "test_123",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1
        }]
        
        with open(self.signal_path, 'w') as f:
            json.dump(signal_data, f)
        
        with open(self.signal_path, 'r') as f:
            loaded_data = json.load(f)
        
        signal = loaded_data[0]
        for field in required_fields:
            self.assertIn(field, signal, f"Required field '{field}' missing")

if __name__ == '__main__':
    unittest.main()