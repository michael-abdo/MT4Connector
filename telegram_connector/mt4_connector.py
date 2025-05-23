#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MT4 Connector for Telegram Connector in SoloTrend X trading system.
Handles communication with the MT4 REST API.
"""

import os
import logging
import json
import requests
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

class MT4Connector:
    """Connects to MT4 REST API for trade execution and management"""
    
    def __init__(self, api_url=None, use_mock=None):
        """
        Initialize the MT4 Connector
        
        Args:
            api_url (str): Base URL for the MT4 REST API
            use_mock (bool): Whether to use mock mode (simulated trades)
        """
        # Set API URL from parameter or environment
        self.api_url = api_url or os.environ.get('MT4_API_URL', 'http://localhost:5002/api')
        
        # Determine mock mode from parameter or environment
        if use_mock is None:
            mock_env = os.environ.get('MOCK_MODE', 'True')
            self.use_mock = mock_env.lower() == 'true'
        else:
            self.use_mock = use_mock
        
        # Log connection details
        logger.info(f"MT4Connector initialized with API URL: {self.api_url}")
        logger.info(f"MT4Connector using mock mode: {self.use_mock}")
        
        # Track connection status
        self.connected = False
        self.last_error = None
        
        # Check connection on initialization
        self.check_connection()
    
    def check_connection(self):
        """
        Check connection to MT4 REST API
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Try to connect to health endpoint
            health_url = f"{self.api_url}/health"
            logger.info(f"Checking MT4 connection: {health_url}")
            
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.connected = True
                    self.last_error = None
                    logger.info("MT4 connection successful")
                    return True
            
            # Connection failed
            self.connected = False
            self.last_error = f"API returned status code: {response.status_code}"
            logger.warning(f"MT4 connection failed: {self.last_error}")
            return False
            
        except requests.RequestException as e:
            # Request exception (connection error, timeout, etc.)
            self.connected = False
            self.last_error = str(e)
            logger.warning(f"MT4 connection error: {e}")
            return False
    
    def execute_trade(self, trade_data):
        """
        Execute a trade via MT4 REST API
        
        Args:
            trade_data (dict): The trade data to send, including:
                - symbol: Trading symbol
                - direction: BUY or SELL
                - volume: Lot size
                - sl: Stop loss (optional)
                - tp: Take profit (optional)
                - account: MT4 account number
                - server: MT4 server
                - password: MT4 password
            
        Returns:
            dict: API response or error details
        """
        if not trade_data.get('symbol'):
            return {
                "status": "error",
                "message": "Symbol is required"
            }
        
        # Extract account credentials
        account = trade_data.get('account')
        server = trade_data.get('server')
        password = trade_data.get('password')
        
        # For real API, we'll need to login with these credentials
        # For now, we'll pass them along with the trade request
        
        # Check connection
        if not self.connected and not self.check_connection():
            # If we're in mock mode, we can simulate a successful trade
            if self.use_mock:
                logger.info(f"Using mock mode to simulate trade: {trade_data}")
                return self._simulate_trade(trade_data)
            
            # Real mode but can't connect
            return {
                "status": "error",
                "message": f"MT4 API connection error: {self.last_error}"
            }
        
        # Prepare the endpoint URL
        trades_url = f"{self.api_url}/trades"
        
        try:
            logger.info(f"Sending trade to MT4 API: {trade_data}")
            
            # In mock mode, simulate a trade without calling the API
            if self.use_mock:
                return self._simulate_trade(trade_data)
            
            # Execute the trade via REST API
            response = requests.post(
                trades_url,
                json=trade_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Process the response
            if response.status_code in (200, 201):
                result = response.json()
                logger.info(f"Trade executed successfully: {result}")
                return result
            else:
                logger.error(f"Error executing trade: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"MT4 API error: {response.status_code} - {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                "status": "error",
                "message": f"MT4 API request error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
    
    def _simulate_trade(self, trade_data):
        """
        Simulate a trade for mock mode
        
        Args:
            trade_data (dict): The trade data
            
        Returns:
            dict: Simulated API response
        """
        # Generate a random ticket number
        import random
        ticket = random.randint(10000, 99999)
        
        # Get the symbol and action from the trade data
        symbol = trade_data.get("symbol", "EURUSD")
        # Check various field names that might contain the action
        action = None
        for field in ["action", "side", "type", "cmd"]:
            if field in trade_data:
                action = trade_data[field]
                break
        
        if not action:
            action = "BUY"  # Default to BUY if no action specified
        
        # Normalize the action name
        if isinstance(action, str):
            action = action.upper()
        
        # Simulated response
        return {
            "status": "success",
            "data": {
                "ticket": ticket,
                "message": f"Trade executed successfully (MOCK) with ticket {ticket}",
                "symbol": symbol,
                "type": action,
                "volume": trade_data.get("volume", 0.1),
                "price": trade_data.get("price", 1.1234),
                "sl": trade_data.get("sl", 0),
                "tp": trade_data.get("tp", 0),
                "comment": trade_data.get("comment", "MOCK_TRADE"),
                "open_time": datetime.now().isoformat(),
                "account": trade_data.get("account", "MOCK_ACCOUNT")
            }
        }
    
    def close_trade(self, ticket, volume=None):
        """
        Close an open trade
        
        Args:
            ticket (int): The ticket number of the trade to close
            volume (float, optional): Volume to close (partial close if less than original)
            
        Returns:
            dict: API response or error details
        """
        if not self.connected and not self.check_connection():
            if self.use_mock:
                logger.info(f"Using mock mode to simulate closing trade: {ticket}")
                return {
                    "status": "success",
                    "data": {
                        "message": f"Trade {ticket} closed successfully (MOCK)"
                    }
                }
            
            return {
                "status": "error",
                "message": f"MT4 API connection error: {self.last_error}"
            }
        
        # Prepare the endpoint URL
        close_url = f"{self.api_url}/trades/{ticket}"
        
        try:
            logger.info(f"Closing trade {ticket} with volume {volume}")
            
            # In mock mode, simulate closing a trade
            if self.use_mock:
                return {
                    "status": "success",
                    "data": {
                        "message": f"Trade {ticket} closed successfully (MOCK)"
                    }
                }
            
            # Build query parameters
            params = {}
            if volume is not None:
                params["volume"] = volume
            
            # Send DELETE request to close the trade
            response = requests.delete(
                close_url,
                params=params,
                timeout=10
            )
            
            # Process the response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Trade closed successfully: {result}")
                return result
            else:
                logger.error(f"Error closing trade: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"MT4 API error: {response.status_code} - {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                "status": "error",
                "message": f"MT4 API request error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
    
    def modify_trade(self, ticket, sl=None, tp=None):
        """
        Modify an open trade
        
        Args:
            ticket (int): The ticket number of the trade to modify
            sl (float, optional): New stop loss level
            tp (float, optional): New take profit level
            
        Returns:
            dict: API response or error details
        """
        if not self.connected and not self.check_connection():
            if self.use_mock:
                logger.info(f"Using mock mode to simulate modifying trade: {ticket}")
                return {
                    "status": "success",
                    "data": {
                        "message": f"Trade {ticket} modified successfully (MOCK)"
                    }
                }
            
            return {
                "status": "error",
                "message": f"MT4 API connection error: {self.last_error}"
            }
        
        # Prepare the endpoint URL
        modify_url = f"{self.api_url}/trades/{ticket}"
        
        # Prepare modification data
        modify_data = {}
        if sl is not None:
            modify_data["sl"] = sl
        if tp is not None:
            modify_data["tp"] = tp
        
        if not modify_data:
            return {
                "status": "error",
                "message": "No modifications specified"
            }
        
        try:
            logger.info(f"Modifying trade {ticket}: {modify_data}")
            
            # In mock mode, simulate modifying a trade
            if self.use_mock:
                return {
                    "status": "success",
                    "data": {
                        "message": f"Trade {ticket} modified successfully (MOCK)",
                        "modifications": modify_data
                    }
                }
            
            # Send PUT request to modify the trade
            response = requests.put(
                modify_url,
                json=modify_data,
                timeout=10
            )
            
            # Process the response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Trade modified successfully: {result}")
                return result
            else:
                logger.error(f"Error modifying trade: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"MT4 API error: {response.status_code} - {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                "status": "error",
                "message": f"MT4 API request error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }