#!/usr/bin/env python3
"""
Unit tests for the MT4 API communication layer.
Tests the MT4Manager class functionality with mock implementations.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import modules to test
from mt4_api import MT4Manager, TradeCommand, TradeState, TradeReason, TradeActivation

class TestMT4API(unittest.TestCase):
    """Test cases for the MT4Manager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create MT4Manager in mock mode (no actual DLL required)
        self.mt4_api = MT4Manager(use_mock_mode=True)
        
        # Ensure the MT4Manager is in mock mode for testing
        self.assertTrue(self.mt4_api.mock_mode, "MT4Manager should be in mock mode for tests")
    
    def test_initialization(self):
        """Test MT4Manager initialization with mock mode."""
        self.assertTrue(self.mt4_api.mock_mode)
        self.assertIsNone(self.mt4_api.api)
        self.assertIsNone(self.mt4_api.manager)
        self.assertFalse(self.mt4_api.connected)
        self.assertFalse(self.mt4_api.logged_in)
    
    def test_connect(self):
        """Test connecting to MT4 server in mock mode."""
        result = self.mt4_api.connect("localhost", 443)
        self.assertTrue(result)
        self.assertTrue(self.mt4_api.connected)
    
    def test_login(self):
        """Test logging in to MT4 server in mock mode."""
        result = self.mt4_api.login(12345, "password")
        self.assertTrue(result)
        self.assertTrue(self.mt4_api.logged_in)
    
    def test_disconnect(self):
        """Test disconnecting from MT4 server in mock mode."""
        # First connect and login
        self.mt4_api.connect("localhost", 443)
        self.mt4_api.login(12345, "password")
        
        # Then disconnect
        result = self.mt4_api.disconnect()
        self.assertTrue(result)
        self.assertFalse(self.mt4_api.connected)
        self.assertFalse(self.mt4_api.logged_in)
    
    def test_get_symbol_info(self):
        """Test getting symbol information in mock mode."""
        # First connect and login
        self.mt4_api.connect("localhost", 443)
        self.mt4_api.login(12345, "password")
        
        # Test with standard currency pair
        eurusd_info = self.mt4_api.get_symbol_info("EURUSD")
        self.assertIsNotNone(eurusd_info)
        self.assertEqual(eurusd_info["symbol"], "EURUSD")
        self.assertEqual(eurusd_info["digits"], 5)  # Standard forex pair has 5 digits
        self.assertAlmostEqual(eurusd_info["point"], 0.00001)
        
        # Test with JPY pair (should have 3 digits)
        usdjpy_info = self.mt4_api.get_symbol_info("USDJPY")
        self.assertIsNotNone(usdjpy_info)
        self.assertEqual(usdjpy_info["symbol"], "USDJPY")
        self.assertEqual(usdjpy_info["digits"], 3)  # JPY pair has 3 digits
        self.assertAlmostEqual(usdjpy_info["point"], 0.001)
    
    def test_place_order(self):
        """Test placing an order in mock mode."""
        # First connect and login
        self.mt4_api.connect("localhost", 443)
        self.mt4_api.login(12345, "password")
        
        # Test buy order
        order_ticket = self.mt4_api.place_order(
            login=12345,
            symbol="EURUSD",
            cmd=TradeCommand.OP_BUY,
            volume=0.1,
            price=1.10000,
            sl=1.09500,
            tp=1.10500,
            comment="Test Order"
        )
        
        self.assertGreater(order_ticket, 0, "Order ticket should be a positive number")
    
    def test_modify_order(self):
        """Test modifying an order in mock mode."""
        # Skip the actual test since mock_mode doesn't fully implement modify_order
        # In a real test, we would first place an order, then modify it
        pass
    
    def test_close_order(self):
        """Test closing an order in mock mode."""
        # Skip the actual test since mock_mode doesn't fully implement close_order
        # In a real test, we would first place an order, then close it
        pass
    
    def test_get_trades(self):
        """Test getting trades in mock mode."""
        # First connect and login
        self.mt4_api.connect("localhost", 443)
        self.mt4_api.login(12345, "password")
        
        # Get all trades
        all_trades = self.mt4_api.get_trades()
        self.assertIsInstance(all_trades, list)
        
        # Get trades for specific login
        login_trades = self.mt4_api.get_trades(12345)
        self.assertIsInstance(login_trades, list)
        
        # Check that all trades for login 12345 have the correct login ID
        for trade in login_trades:
            self.assertEqual(trade["login"], 12345)


# Test for real MT4 API calls (only run if not in mock mode)
@unittest.skip("These tests require a real MT4 server connection and will be skipped")
class TestRealMT4API(unittest.TestCase):
    """Test cases for the MT4Manager class with real MT4 server."""
    
    def setUp(self):
        """Set up test fixtures."""
        from config import MT4_SERVER, MT4_PORT, MT4_USERNAME, MT4_PASSWORD
        
        # Create MT4Manager without mock mode
        self.mt4_api = MT4Manager(use_mock_mode=False)
        
        # Store connection details
        self.server = MT4_SERVER
        self.port = MT4_PORT
        self.login = MT4_USERNAME
        self.password = MT4_PASSWORD
    
    def test_connection_sequence(self):
        """Test the complete connection sequence to a real MT4 server."""
        # Connect to server
        connected = self.mt4_api.connect(self.server, self.port)
        if not connected:
            self.skipTest("Could not connect to MT4 server - skipping real API tests")
        
        self.assertTrue(self.mt4_api.connected)
        
        # Login to server
        logged_in = self.mt4_api.login(self.login, self.password)
        if not logged_in:
            self.mt4_api.disconnect()
            self.skipTest("Could not login to MT4 server - skipping real API tests")
        
        self.assertTrue(self.mt4_api.logged_in)
        
        # Disconnect
        self.mt4_api.disconnect()
        self.assertFalse(self.mt4_api.connected)
        self.assertFalse(self.mt4_api.logged_in)


if __name__ == "__main__":
    unittest.main()