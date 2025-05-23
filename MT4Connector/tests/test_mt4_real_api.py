"""
Test suite for MT4 Real API wrapper
Tests both mock and real mode functionality
"""
import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mt4_real_api import MT4RealAPI, get_mt4_api

class TestMT4RealAPI(unittest.TestCase):
    """Test MT4 Real API implementation"""
    
    def setUp(self):
        """Set up test environment"""
        # Force mock mode for testing
        os.environ['MOCK_MODE'] = 'True'
    
    def test_mock_mode_initialization(self):
        """Test initialization in mock mode"""
        api = MT4RealAPI(use_mock=True)
        self.assertTrue(api.use_mock)
        self.assertIsNotNone(api.mock_api)
        self.assertFalse(api.connected)
    
    def test_auto_mode_detection(self):
        """Test automatic mode detection"""
        # With MOCK_MODE=True
        os.environ['MOCK_MODE'] = 'True'
        api = MT4RealAPI(use_mock=None)
        self.assertTrue(api.use_mock)
        
        # With MOCK_MODE=False (will still use mock on non-Windows)
        os.environ['MOCK_MODE'] = 'False'
        api2 = MT4RealAPI(use_mock=None)
        # On non-Windows, it should still use mock
        self.assertTrue(api2.use_mock)
    
    def test_mock_connection(self):
        """Test connection in mock mode"""
        api = MT4RealAPI(use_mock=True)
        
        # Test connection
        result = api.connect("localhost", 443, 12345, "password")
        self.assertTrue(result)
        self.assertTrue(api.mock_api.connected)
    
    def test_mock_trade_execution(self):
        """Test trade execution in mock mode"""
        api = MT4RealAPI(use_mock=True)
        api.connect("localhost", 443, 12345, "password")
        
        # Test trade
        trade_data = {
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 0.1,
            "sl": 1.0950,
            "tp": 1.1050,
            "login": 12345
        }
        
        result = api.execute_trade(trade_data)
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertIn("ticket", result["data"])
    
    def test_mock_trade_modification(self):
        """Test trade modification in mock mode"""
        api = MT4RealAPI(use_mock=True)
        api.connect("localhost", 443, 12345, "password")
        
        # Create a trade first
        trade_data = {
            "symbol": "GBPUSD",
            "type": "SELL",
            "volume": 0.2,
            "login": 12345
        }
        
        trade_result = api.execute_trade(trade_data)
        ticket = trade_result["data"]["ticket"]
        
        # Modify the trade
        modify_result = api.modify_trade(ticket, sl=1.2650, tp=1.2450)
        self.assertEqual(modify_result["status"], "success")
        self.assertEqual(modify_result["data"]["sl"], 1.2650)
        self.assertEqual(modify_result["data"]["tp"], 1.2450)
    
    def test_mock_trade_close(self):
        """Test trade closing in mock mode"""
        api = MT4RealAPI(use_mock=True)
        api.connect("localhost", 443, 12345, "password")
        
        # Create a trade
        trade_data = {
            "symbol": "USDJPY",
            "type": "BUY",
            "volume": 0.1,
            "login": 12345
        }
        
        trade_result = api.execute_trade(trade_data)
        ticket = trade_result["data"]["ticket"]
        
        # Close the trade
        close_result = api.close_trade(ticket)
        self.assertEqual(close_result["status"], "success")
    
    def test_get_account_info(self):
        """Test getting account information"""
        api = MT4RealAPI(use_mock=True)
        api.connect("localhost", 443, 12345, "password")
        
        # Get account info
        result = api.get_account_info(12345)
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertEqual(result["data"]["login"], 12345)
    
    def test_get_open_orders(self):
        """Test getting open orders"""
        api = MT4RealAPI(use_mock=True)
        api.connect("localhost", 443, 12345, "password")
        
        # Get orders
        result = api.get_open_orders(12345)
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertIsInstance(result["data"], list)
    
    def test_error_handling_not_connected(self):
        """Test error handling when not connected"""
        api = MT4RealAPI(use_mock=True)
        
        # Try to execute trade without connection
        trade_data = {"symbol": "EURUSD", "type": "BUY", "volume": 0.1}
        result = api.execute_trade(trade_data)
        
        self.assertEqual(result["status"], "error")
        self.assertIn("not connected", result["message"].lower())
    
    def test_trade_command_conversion(self):
        """Test trade type to command conversion"""
        api = MT4RealAPI(use_mock=True)
        
        # Test conversions
        self.assertEqual(api._get_trade_command("BUY"), 0)
        self.assertEqual(api._get_trade_command("SELL"), 1)
        self.assertEqual(api._get_trade_command("BUY_LIMIT"), 2)
        self.assertEqual(api._get_trade_command("SELL_LIMIT"), 3)
        self.assertEqual(api._get_trade_command("BUY_STOP"), 4)
        self.assertEqual(api._get_trade_command("SELL_STOP"), 5)
    
    def test_trade_type_name_conversion(self):
        """Test command to trade type conversion"""
        api = MT4RealAPI(use_mock=True)
        
        # Test conversions
        self.assertEqual(api._get_trade_type_name(0), "BUY")
        self.assertEqual(api._get_trade_type_name(1), "SELL")
        self.assertEqual(api._get_trade_type_name(2), "BUY_LIMIT")
        self.assertEqual(api._get_trade_type_name(3), "SELL_LIMIT")
        self.assertEqual(api._get_trade_type_name(4), "BUY_STOP")
        self.assertEqual(api._get_trade_type_name(5), "SELL_STOP")
        self.assertEqual(api._get_trade_type_name(99), "UNKNOWN")
    
    def test_error_message_translation(self):
        """Test error code to message translation"""
        api = MT4RealAPI(use_mock=True)
        
        # Test error messages
        self.assertIn("money", api._get_error_message(-4).lower())
        self.assertIn("closed", api._get_error_message(-6).lower())
        self.assertIn("price", api._get_error_message(-7).lower())
        self.assertIn("unknown", api._get_error_message(-999).lower())
    
    def test_singleton_pattern(self):
        """Test get_mt4_api returns same instance"""
        api1 = get_mt4_api(use_mock=True)
        api2 = get_mt4_api(use_mock=True)
        
        self.assertIs(api1, api2)

if __name__ == '__main__':
    unittest.main()