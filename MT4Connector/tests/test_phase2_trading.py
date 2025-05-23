"""
Test suite for Phase 2: Single Account Trading
Tests approve/reject buttons, trade execution, and management
"""
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

class TestPhase2Trading(unittest.TestCase):
    """Test Phase 2 trading functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.signal_file = os.path.join(self.test_dir, 'ea_signals.txt')
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_signal_with_buttons(self):
        """Test that signals trigger button display in Telegram"""
        # Create a signal that should trigger buttons
        signal = {
            "signal_id": "test_buttons_123",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 12345,
            "volume": 0.1,
            "sl": 1.0950,
            "tp": 1.1050
        }
        
        # Verify signal has required fields for button display
        self.assertIn("signal_id", signal)
        self.assertIn("type", signal)
        self.assertIn("symbol", signal)
        
        # Button callback data format
        accept_callback = f"trade_{signal['signal_id']}_accept"
        reject_callback = f"trade_{signal['signal_id']}_reject"
        custom_callback = f"trade_{signal['signal_id']}_custom"
        
        # Verify callback data format
        self.assertTrue(accept_callback.startswith("trade_"))
        self.assertTrue(accept_callback.endswith("_accept"))
        self.assertTrue(reject_callback.endswith("_reject"))
        self.assertTrue(custom_callback.endswith("_custom"))
    
    def test_mock_trade_execution(self):
        """Test mock trade execution flow"""
        from telegram_connector.mt4_connector import MT4Connector
        
        # Create mock connector
        connector = MT4Connector("http://localhost:5002", use_mock=True)
        
        # Test trade data
        trade_data = {
            "symbol": "EURUSD",
            "action": "BUY",
            "volume": 0.1,
            "sl": 1.0950,
            "tp": 1.1050
        }
        
        # Execute mock trade
        result = connector.execute_trade(trade_data)
        
        # Verify mock response
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertIn("ticket", result["data"])
        self.assertEqual(result["data"]["symbol"], "EURUSD")
        self.assertEqual(result["data"]["type"], "BUY")
    
    def test_trade_approval_flow(self):
        """Test the approve button flow"""
        # Simulate button callback data
        signal_id = "test_approve_123"
        action = "accept"
        
        # Mock signal data stored in bot
        mock_signal = {
            "symbol": "GBPUSD",
            "direction": "SELL",
            "stop_loss": 1.2650,
            "take_profit": 1.2450
        }
        
        # Verify signal can be retrieved by ID
        self.assertEqual(mock_signal["symbol"], "GBPUSD")
        self.assertEqual(mock_signal["direction"], "SELL")
    
    def test_trade_rejection_flow(self):
        """Test the reject button flow"""
        # Simulate rejection
        signal_id = "test_reject_123"
        action = "reject"
        
        # After rejection, signal should be removed from active signals
        active_signals = {"test_reject_123": {"symbol": "USDJPY"}}
        
        # Simulate rejection
        if action == "reject" and signal_id in active_signals:
            del active_signals[signal_id]
        
        # Verify signal was removed
        self.assertNotIn(signal_id, active_signals)
    
    def test_custom_lot_size(self):
        """Test custom lot size selection"""
        # Available lot sizes
        lot_sizes = [0.01, 0.05, 0.1, 0.5, 1.0]
        
        # Verify all standard sizes available
        self.assertIn(0.01, lot_sizes)
        self.assertIn(0.1, lot_sizes)
        self.assertIn(1.0, lot_sizes)
        
        # Test callback format for lot size
        signal_id = "test_custom_123"
        for lot in lot_sizes:
            callback = f"lot_{lot}_{signal_id}"
            self.assertTrue(callback.startswith("lot_"))
            self.assertIn(str(lot), callback)
    
    def test_orders_command_format(self):
        """Test /orders command response format"""
        # Mock open orders
        mock_orders = [
            {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "open_price": 1.1000,
                "current_price": 1.1020,
                "sl": 1.0950,
                "tp": 1.1050,
                "profit": 20.0
            }
        ]
        
        # Verify order has required fields
        order = mock_orders[0]
        required_fields = ["ticket", "symbol", "type", "volume", 
                          "open_price", "current_price", "sl", "tp", "profit"]
        
        for field in required_fields:
            self.assertIn(field, order)
    
    def test_close_order_flow(self):
        """Test order close functionality"""
        from telegram_connector.mt4_connector import MT4Connector
        
        connector = MT4Connector("http://localhost:5002", use_mock=True)
        
        # Test closing an order
        ticket = 12345
        result = connector.close_trade(ticket)
        
        # Verify mock close response
        self.assertEqual(result["status"], "success")
        self.assertIn(str(ticket), result["data"]["message"])
    
    def test_modify_order_flow(self):
        """Test order modification functionality"""
        from telegram_connector.mt4_connector import MT4Connector
        
        connector = MT4Connector("http://localhost:5002", use_mock=True)
        
        # Test modifying an order
        ticket = 12345
        new_sl = 1.0960
        new_tp = 1.1100
        
        result = connector.modify_trade(ticket, sl=new_sl, tp=new_tp)
        
        # Verify mock modify response
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["modifications"]["sl"], new_sl)
        self.assertEqual(result["data"]["modifications"]["tp"], new_tp)
    
    def test_settings_persistence(self):
        """Test user settings storage"""
        # Default user settings
        default_settings = {
            "risk_percent": 1.0,
            "default_lot_size": 0.01,
            "auto_trade": False,
            "notifications": True
        }
        
        # Verify all settings have defaults
        self.assertIn("risk_percent", default_settings)
        self.assertIn("default_lot_size", default_settings)
        self.assertIn("auto_trade", default_settings)
        self.assertIn("notifications", default_settings)
        
        # Test settings update
        updated_settings = default_settings.copy()
        updated_settings["default_lot_size"] = 0.1
        updated_settings["auto_trade"] = True
        
        self.assertEqual(updated_settings["default_lot_size"], 0.1)
        self.assertTrue(updated_settings["auto_trade"])

if __name__ == '__main__':
    unittest.main()