"""
DX Integration module.
This module provides functionality to connect to CloudTrader DX APIs.
"""

import json
import logging
import requests
from datetime import datetime
import sys
from pathlib import Path

# Add the parent directory to sys.path if not already there
src_dir = Path(__file__).parent
root_dir = src_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Define default API URLs if they're not in config
DX_API_URL = "https://api.dx.com/v1"
DX_ADMIN_API_URL = "https://api.dx.com/admin/v1"

try:
    # Try to import from config, but don't fail if not found
    from config import DX_API_URL, DX_ADMIN_API_URL
except (ImportError, ModuleNotFoundError):
    try:
        from src.config import DX_API_URL, DX_ADMIN_API_URL
    except (ImportError, AttributeError):
        # Use the defaults defined above
        pass

# Set up logging
logger = logging.getLogger(__name__)

class DXIntegration:
    """
    CloudTrader DX API Integration class.
    Handles API requests to DX endpoints.
    """
    
    def __init__(self, api_key=None, api_secret=None):
        """
        Initialize the DX Integration.
        
        Args:
            api_key (str, optional): API Key for authentication
            api_secret (str, optional): API Secret for authentication
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Set API credentials if provided
        if api_key and api_secret:
            self.set_auth_credentials(api_key, api_secret)
    
    def set_auth_credentials(self, api_key, api_secret):
        """
        Set the API authentication credentials.
        
        Args:
            api_key (str): API Key
            api_secret (str): API Secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.session.headers.update({
            'X-API-Key': api_key,
            'X-API-Secret': api_secret
        })
    
    def get_market_data(self, symbol):
        """
        Get market data for a specific symbol.
        
        Args:
            symbol (str): Symbol name
            
        Returns:
            dict: Market data
        """
        endpoint = f"{DX_API_URL}/market/data/{symbol}"
        
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved market data for {symbol}: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol, timeframe, start_time, end_time=None):
        """
        Get historical market data for a specific symbol and timeframe.
        
        Args:
            symbol (str): Symbol name
            timeframe (str): Timeframe (e.g., "M1", "H1", "D1")
            start_time (int/datetime): Start time (UNIX timestamp or datetime)
            end_time (int/datetime, optional): End time (UNIX timestamp or datetime)
            
        Returns:
            list: Historical market data
        """
        # Convert datetime to UNIX timestamp if needed
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp())
        
        if end_time and isinstance(end_time, datetime):
            end_time = int(end_time.timestamp())
        
        # Prepare query parameters
        params = {
            'symbol': symbol,
            'timeframe': timeframe,
            'from': start_time
        }
        
        if end_time:
            params['to'] = end_time
        
        endpoint = f"{DX_API_URL}/market/history"
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved historical data for {symbol} ({timeframe}): {len(data)} records")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting historical data for {symbol} ({timeframe}): {e}")
            return []
    
    def get_account_info(self, account_id):
        """
        Get account information.
        
        Args:
            account_id (int): Account ID
            
        Returns:
            dict: Account information
        """
        endpoint = f"{DX_API_URL}/account/{account_id}"
        
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved account information for {account_id}: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting account information for {account_id}: {e}")
            return None
    
    def get_positions(self, account_id):
        """
        Get open positions for an account.
        
        Args:
            account_id (int): Account ID
            
        Returns:
            list: Open positions
        """
        endpoint = f"{DX_API_URL}/account/{account_id}/positions"
        
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved positions for {account_id}: {len(data)} positions")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting positions for {account_id}: {e}")
            return []
    
    def get_orders(self, account_id):
        """
        Get pending orders for an account.
        
        Args:
            account_id (int): Account ID
            
        Returns:
            list: Pending orders
        """
        endpoint = f"{DX_API_URL}/account/{account_id}/orders"
        
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved orders for {account_id}: {len(data)} orders")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting orders for {account_id}: {e}")
            return []
    
    def get_history(self, account_id, start_time, end_time=None):
        """
        Get trade history for an account.
        
        Args:
            account_id (int): Account ID
            start_time (int/datetime): Start time (UNIX timestamp or datetime)
            end_time (int/datetime, optional): End time (UNIX timestamp or datetime)
            
        Returns:
            list: Trade history
        """
        # Convert datetime to UNIX timestamp if needed
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp())
        
        if end_time and isinstance(end_time, datetime):
            end_time = int(end_time.timestamp())
        
        # Prepare query parameters
        params = {
            'from': start_time
        }
        
        if end_time:
            params['to'] = end_time
        
        endpoint = f"{DX_API_URL}/account/{account_id}/history"
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved history for {account_id}: {len(data)} records")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting history for {account_id}: {e}")
            return []
    
    def place_order(self, account_id, symbol, direction, volume, order_type="MARKET", price=None, sl=None, tp=None):
        """
        Place a new order.
        
        Args:
            account_id (int): Account ID
            symbol (str): Symbol name
            direction (str): Order direction ("BUY" or "SELL")
            volume (float): Order volume in lots
            order_type (str, optional): Order type ("MARKET", "LIMIT", "STOP")
            price (float, optional): Order price (required for LIMIT and STOP orders)
            sl (float, optional): Stop Loss level
            tp (float, optional): Take Profit level
            
        Returns:
            dict: Order result
        """
        # Prepare order data
        order_data = {
            'symbol': symbol,
            'direction': direction,
            'volume': volume,
            'type': order_type
        }
        
        if price is not None and order_type in ["LIMIT", "STOP"]:
            order_data['price'] = price
        
        if sl is not None:
            order_data['sl'] = sl
        
        if tp is not None:
            order_data['tp'] = tp
        
        endpoint = f"{DX_API_URL}/account/{account_id}/order"
        
        try:
            response = self.session.post(endpoint, json=order_data)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Placed order for {account_id} ({symbol} {direction}): {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error placing order for {account_id} ({symbol} {direction}): {e}")
            return None
    
    def modify_order(self, account_id, order_id, price=None, sl=None, tp=None):
        """
        Modify an existing order.
        
        Args:
            account_id (int): Account ID
            order_id (int): Order ID
            price (float, optional): New price for pending orders
            sl (float, optional): New Stop Loss level
            tp (float, optional): New Take Profit level
            
        Returns:
            dict: Modification result
        """
        # Prepare modification data
        mod_data = {}
        
        if price is not None:
            mod_data['price'] = price
        
        if sl is not None:
            mod_data['sl'] = sl
        
        if tp is not None:
            mod_data['tp'] = tp
        
        if not mod_data:
            logger.warning(f"No modification parameters provided for order {order_id}")
            return None
        
        endpoint = f"{DX_API_URL}/account/{account_id}/order/{order_id}"
        
        try:
            response = self.session.put(endpoint, json=mod_data)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Modified order {order_id} for {account_id}: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error modifying order {order_id} for {account_id}: {e}")
            return None
    
    def close_order(self, account_id, order_id, volume=None):
        """
        Close an existing order.
        
        Args:
            account_id (int): Account ID
            order_id (int): Order ID
            volume (float, optional): Volume to close (partial close if provided)
            
        Returns:
            dict: Closure result
        """
        # Prepare closure data
        close_data = {}
        
        if volume is not None:
            close_data['volume'] = volume
        
        endpoint = f"{DX_API_URL}/account/{account_id}/order/{order_id}/close"
        
        try:
            response = self.session.post(endpoint, json=close_data)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Closed order {order_id} for {account_id}: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error closing order {order_id} for {account_id}: {e}")
            return None
    
    def admin_get_users(self):
        """
        Admin API: Get all users.
        
        Returns:
            list: User records
        """
        endpoint = f"{DX_ADMIN_API_URL}/users"
        
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved users: {len(data)} users")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def admin_get_accounts(self, user_id=None):
        """
        Admin API: Get accounts.
        
        Args:
            user_id (int, optional): User ID to filter accounts
            
        Returns:
            list: Account records
        """
        endpoint = f"{DX_ADMIN_API_URL}/accounts"
        
        # Add user_id filter if provided
        params = {}
        if user_id:
            params['user_id'] = user_id
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved accounts: {len(data)} accounts")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting accounts: {e}")
            return []
    
    def admin_get_account_stats(self, account_id):
        """
        Admin API: Get account statistics.
        
        Args:
            account_id (int): Account ID
            
        Returns:
            dict: Account statistics
        """
        endpoint = f"{DX_ADMIN_API_URL}/account/{account_id}/stats"
        
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved account statistics for {account_id}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting account statistics for {account_id}: {e}")
            return None