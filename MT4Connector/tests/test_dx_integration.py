#!/usr/bin/env python3
"""
Unit tests for the DX Integration module.
Tests the CloudTrader DX API integration functionality.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import logging
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import modules to test
from dx_integration import DXIntegration

class TestDXIntegration(unittest.TestCase):
    """Test cases for the DX Integration module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create new patchers for every test to avoid interference
        self.session_patcher = patch('dx_integration.requests.Session')
        self.dx_api_url_patcher = patch('dx_integration.DX_API_URL', 'https://mock-api.example.com/dxweb')
        self.dx_admin_api_url_patcher = patch('dx_integration.DX_ADMIN_API_URL', 'https://mock-api.example.com/dxsca-web')
        
        # Start all patchers
        self.mock_session_class = self.session_patcher.start()
        self.dx_api_url_patcher.start()
        self.dx_admin_api_url_patcher.start()
        
        # Configure session mock
        self.mock_session = MagicMock()
        self.mock_session.headers = MagicMock()
        self.mock_session_class.return_value = self.mock_session
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop all patchers
        self.session_patcher.stop()
        self.dx_api_url_patcher.stop()
        self.dx_admin_api_url_patcher.stop()
    
    def test_initialization(self):
        """Test DX Integration initialization."""
        # Create a new instance with default params
        dx_api = DXIntegration()
        
        # Test default initialization
        self.assertIsNone(dx_api.api_key)
        self.assertIsNone(dx_api.api_secret)
        self.assertEqual(dx_api.session, self.mock_session)
        
        # Verify session headers were set
        self.mock_session.headers.update.assert_called_once()
    
    def test_initialization_with_credentials(self):
        """Test DX Integration initialization with API credentials."""
        # Create a new instance with credentials
        dx_api = DXIntegration("test_api_key", "test_api_secret")
        
        # Verify credentials were set
        self.assertEqual(dx_api.api_key, "test_api_key")
        self.assertEqual(dx_api.api_secret, "test_api_secret")
        
        # Verify headers were set with content type and credentials
        # First call sets content type and accept headers
        self.mock_session.headers.update.assert_any_call({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Second call sets API credentials
        self.mock_session.headers.update.assert_any_call({
            'X-API-Key': 'test_api_key',
            'X-API-Secret': 'test_api_secret'
        })
        
        # Should have exactly two calls
        self.assertEqual(self.mock_session.headers.update.call_count, 2)
    
    def test_set_auth_credentials(self):
        """Test setting authentication credentials."""
        # Create instance without credentials
        dx_api = DXIntegration()
        
        # Reset mock call history
        self.mock_session.headers.update.reset_mock()
        
        # Set credentials
        dx_api.set_auth_credentials("new_api_key", "new_api_secret")
        
        # Verify credentials were set
        self.assertEqual(dx_api.api_key, "new_api_key")
        self.assertEqual(dx_api.api_secret, "new_api_secret")
        
        # Verify session headers were updated
        self.mock_session.headers.update.assert_called_once_with({
            'X-API-Key': "new_api_key",
            'X-API-Secret': "new_api_secret"
        })
    
    def test_get_market_data(self):
        """Test getting market data."""
        # Create instance
        dx_api = DXIntegration()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "symbol": "EURUSD",
            "bid": 1.10000,
            "ask": 1.10002,
            "time": 1615000000
        }
        mock_response.raise_for_status = MagicMock()
        self.mock_session.get.return_value = mock_response
        
        # Call the method
        result = dx_api.get_market_data("EURUSD")
        
        # Verify result
        self.assertEqual(result, mock_response.json.return_value)
        
        # Verify session.get was called with the correct endpoint
        self.mock_session.get.assert_called_with("https://mock-api.example.com/dxweb/market/data/EURUSD")
    
    def test_get_market_data_error(self):
        """Test error handling when getting market data."""
        # Create instance
        dx_api = DXIntegration()
        
        # Mock response to raise exception
        self.mock_session.get.side_effect = Exception("Test error")
        
        # Call the method - should handle error and return None
        with patch('dx_integration.logger') as mock_logger:
            result = dx_api.get_market_data("EURUSD")
            
            # Should return None on error
            self.assertIsNone(result)
            
            # Should log an error
            mock_logger.error.assert_called_once()
    
    def test_get_historical_data(self):
        """Test getting historical market data."""
        # Create instance
        dx_api = DXIntegration()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"time": 1615000000, "open": 1.10000, "high": 1.10100, "low": 1.09900, "close": 1.10050, "volume": 100},
            {"time": 1615001000, "open": 1.10050, "high": 1.10150, "low": 1.10000, "close": 1.10100, "volume": 120}
        ]
        mock_response.raise_for_status = MagicMock()
        self.mock_session.get.return_value = mock_response
        
        # Call the method with UNIX timestamp
        result = dx_api.get_historical_data("EURUSD", "H1", 1615000000, 1615010000)
        
        # Verify result
        self.assertEqual(result, mock_response.json.return_value)
        
        # Verify session.get was called with the correct endpoint and params
        self.mock_session.get.assert_called_with(
            "https://mock-api.example.com/dxweb/market/history",
            params={
                'symbol': "EURUSD",
                'timeframe': "H1",
                'from': 1615000000,
                'to': 1615010000
            }
        )
        
        # Reset mock
        self.mock_session.get.reset_mock()
        
        # Call the method with datetime objects
        start_time = datetime.fromtimestamp(1615000000)
        end_time = datetime.fromtimestamp(1615010000)
        result = dx_api.get_historical_data("EURUSD", "H1", start_time, end_time)
        
        # Verify session.get was called with the correct endpoint and params
        self.mock_session.get.assert_called_with(
            "https://mock-api.example.com/dxweb/market/history",
            params={
                'symbol': "EURUSD",
                'timeframe': "H1",
                'from': 1615000000,
                'to': 1615010000
            }
        )
    
    def test_get_account_info(self):
        """Test getting account information."""
        # Create instance
        dx_api = DXIntegration()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "login": 12345,
            "balance": 10000.0,
            "equity": 10050.0,
            "margin": 500.0,
            "margin_level": 2010.0
        }
        mock_response.raise_for_status = MagicMock()
        self.mock_session.get.return_value = mock_response
        
        # Call the method
        result = dx_api.get_account_info(12345)
        
        # Verify result
        self.assertEqual(result, mock_response.json.return_value)
        
        # Verify session.get was called with the correct endpoint
        self.mock_session.get.assert_called_with("https://mock-api.example.com/dxweb/account/12345")
    
    def test_get_positions(self):
        """Test getting positions for an account."""
        # Create instance
        dx_api = DXIntegration()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "ticket": 54321,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "open_price": 1.10000,
                "open_time": 1615000000,
                "sl": 1.09500,
                "tp": 1.10500,
                "profit": 25.0
            },
            {
                "ticket": 54322,
                "symbol": "GBPUSD",
                "type": "SELL",
                "volume": 0.2,
                "open_price": 1.30000,
                "open_time": 1615001000,
                "sl": 1.30500,
                "tp": 1.29500,
                "profit": -15.0
            }
        ]
        mock_response.raise_for_status = MagicMock()
        self.mock_session.get.return_value = mock_response
        
        # Call the method
        result = dx_api.get_positions(12345)
        
        # Verify result
        self.assertEqual(result, mock_response.json.return_value)
        
        # Verify session.get was called with the correct endpoint
        self.mock_session.get.assert_called_with("https://mock-api.example.com/dxweb/account/12345/positions")
    
    def test_place_order(self):
        """Test placing an order."""
        # Create instance
        dx_api = DXIntegration()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ticket": 54323,
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 0.1,
            "price": 1.10000,
            "sl": 1.09500,
            "tp": 1.10500,
            "time": 1615000000
        }
        mock_response.raise_for_status = MagicMock()
        self.mock_session.post.return_value = mock_response
        
        # Call the method
        result = dx_api.place_order(
            account_id=12345,
            symbol="EURUSD",
            direction="BUY",
            volume=0.1,
            order_type="MARKET",
            price=None,
            sl=1.09500,
            tp=1.10500
        )
        
        # Verify result
        self.assertEqual(result, mock_response.json.return_value)
        
        # Verify session.post was called with the correct endpoint and data
        self.mock_session.post.assert_called_with(
            "https://mock-api.example.com/dxweb/account/12345/order",
            json={
                'symbol': "EURUSD",
                'direction': "BUY",
                'volume': 0.1,
                'type': "MARKET",
                'sl': 1.09500,
                'tp': 1.10500
            }
        )
    
    def test_admin_get_users(self):
        """Test getting all users (admin API)."""
        # Create instance
        dx_api = DXIntegration()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "email": "user1@example.com",
                "name": "User One",
                "status": "ACTIVE"
            },
            {
                "id": 2,
                "email": "user2@example.com",
                "name": "User Two",
                "status": "INACTIVE"
            }
        ]
        mock_response.raise_for_status = MagicMock()
        self.mock_session.get.return_value = mock_response
        
        # Call the method
        result = dx_api.admin_get_users()
        
        # Verify result
        self.assertEqual(result, mock_response.json.return_value)
        
        # Verify session.get was called with the correct endpoint
        self.mock_session.get.assert_called_with("https://mock-api.example.com/dxsca-web/users")


if __name__ == "__main__":
    unittest.main()