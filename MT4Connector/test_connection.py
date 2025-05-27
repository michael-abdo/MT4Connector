#!/usr/bin/env python3
"""
Test MT4 connection with provided credentials
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mt4_real_api import get_mt4_api
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_connection():
    """Test MT4 connection"""
    # Connection details
    server = "195.88.127.154"
    port = 45543
    login = 66
    password = "iybe8ba"
    
    logger.info(f"Testing connection to MT4 server: {server}:{port}")
    logger.info(f"Login: {login}")
    
    # Get API instance
    api = get_mt4_api()
    
    # Try to connect
    logger.info("Attempting to connect...")
    result = api.connect(server, port, login, password)
    
    if result:
        logger.info("✓ Successfully connected to MT4 server!")
        
        # Get account info
        account_info = api.get_account_info(login)
        if account_info['status'] == 'success':
            data = account_info['data']
            logger.info(f"✓ Account Info Retrieved:")
            logger.info(f"  - Name: {data.get('name', 'N/A')}")
            logger.info(f"  - Balance: {data.get('balance', 0)}")
            logger.info(f"  - Leverage: {data.get('leverage', 0)}")
        else:
            logger.error(f"Failed to get account info: {account_info.get('message')}")
        
        # Get open orders
        orders = api.get_open_orders(login)
        if orders['status'] == 'success':
            logger.info(f"✓ Open Orders: {len(orders['data'])}")
        
        # Disconnect
        api.disconnect()
        logger.info("✓ Disconnected successfully")
        
    else:
        logger.error("✗ Failed to connect to MT4 server")
        logger.error("This could be due to:")
        logger.error("  - Incorrect server address or port")
        logger.error("  - Invalid login credentials")
        logger.error("  - MT4 Manager API DLL not available")
        logger.error("  - Running in MOCK mode")

if __name__ == "__main__":
    test_connection()