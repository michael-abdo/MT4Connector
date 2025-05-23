"""
MT4 Manager API Python wrapper.
This module provides functionality to connect to MT4 servers and manage orders.
"""

import os
import time
import ctypes
import logging
from ctypes import (
    CDLL, POINTER, Structure, Union, 
    c_int, c_uint, c_char, c_long, c_ulong, c_longlong, c_ulonglong, 
    c_double, c_void_p, c_char_p, c_wchar_p, c_bool, byref
)
from datetime import datetime
from enum import IntEnum, auto
import platform

from config import (
    MT4_MANAGER_API_DLL, MT4_MANAGER_API_VERSION, 
    MT4_TRADE_TRANSACTION_MAX_RETRIES, MT4_TRADE_TRANSACTION_RETRY_DELAY
)

# Set up logging
logger = logging.getLogger(__name__)

# Define MT4 Manager API constants
class TradeCommand(IntEnum):
    OP_BUY = 0
    OP_SELL = 1
    OP_BUY_LIMIT = 2
    OP_SELL_LIMIT = 3
    OP_BUY_STOP = 4
    OP_SELL_STOP = 5
    OP_BALANCE = 6
    OP_CREDIT = 7

class TradeState(IntEnum):
    TS_OPEN_NORMAL = 0
    TS_OPEN_REMAND = 1
    TS_OPEN_RESTORED = 2
    TS_CLOSED_NORMAL = 3
    TS_CLOSED_PART = 4
    TS_CLOSED_BY = 5
    TS_DELETED = 6

class TradeReason(IntEnum):
    TR_CLIENT = 0
    TR_EXPERT = 1
    TR_DEALER = 2
    TR_SIGNAL = 3
    TR_GATEWAY = 4
    TR_MOBILE = 5
    TR_WEB = 6
    TR_API = 7

class TradeActivation(IntEnum):
    ACTIVATION_NONE = 0
    ACTIVATION_SL = 1
    ACTIVATION_TP = 2
    ACTIVATION_PENDING = 3
    ACTIVATION_STOPOUT = 4
    ACTIVATION_ROLLBACK = 5

# Define MT4 Manager API structures
MAX_PATH = 260
COMPANY_MAX_LEN = 128
SYMBOL_LEN = 12
ACCOUNT_NAME_MAX_LEN = 28
ACCOUNT_ADDRESS_MAX_LEN = 96
ACCOUNT_PHONE_MAX_LEN = 32
ACCOUNT_EMAIL_MAX_LEN = 48
ACCOUNT_COMMENT_MAX_LEN = 64
DATE_TIME_FORMAT_LENGTH = 20

class TradeRecord(Structure):
    _fields_ = [
        ("order", c_int),        # Order ticket
        ("login", c_int),        # Client login
        ("symbol", c_char * SYMBOL_LEN),  # Symbol
        ("digits", c_int),       # Digits
        ("cmd", c_int),          # Operation type (TradeCommand)
        ("volume", c_int),       # Volume
        ("open_time", c_int),    # Open time
        ("state", c_int),        # State (TradeState)
        ("open_price", c_double),  # Open price
        ("sl", c_double),        # Stop Loss
        ("tp", c_double),        # Take Profit
        ("close_time", c_int),   # Close time
        ("value_date", c_int),   # Value date
        ("expiration", c_int),   # Expiration
        ("reason", c_int),       # Trade reason (TradeReason)
        ("conv_rate1", c_double),  # Conversion rate from profit currency to group currency
        ("conv_rate2", c_double),  # Conversion rate from group currency to deposit currency
        ("commission", c_double),  # Commission
        ("commission_agent", c_double),  # Agent commission
        ("storage", c_double),   # Storage
        ("close_price", c_double),  # Close price
        ("profit", c_double),    # Profit
        ("taxes", c_double),     # Taxes
        ("magic", c_int),        # Expert magic number
        ("comment", c_char * ACCOUNT_COMMENT_MAX_LEN),  # Comment
        ("activation", c_int),   # Order activation state (TradeActivation)
        ("margin_rate", c_double),  # Margin rate
        ("timestamp", c_int),    # Timestamp
        ("reserved", c_int * 4)  # Reserved
    ]

class UserRecord(Structure):
    _fields_ = [
        ("login", c_int),        # Login
        ("group", c_char * 16),  # Group
        ("password", c_char * 16),  # Password
        ("name", c_char * ACCOUNT_NAME_MAX_LEN),  # Name
        ("email", c_char * ACCOUNT_EMAIL_MAX_LEN),  # Email
        ("country", c_char * 32),  # Country
        ("city", c_char * 32),   # City
        ("address", c_char * ACCOUNT_ADDRESS_MAX_LEN),  # Address
        ("phone", c_char * ACCOUNT_PHONE_MAX_LEN),  # Phone
        ("state", c_char * 32),  # State
        ("zipcode", c_char * 16),  # Zip code
        ("id", c_char * 32),     # ID
        ("status", c_char * 16), # Status
        ("comment", c_char * ACCOUNT_COMMENT_MAX_LEN),  # Comment
        ("timestamp", c_int),    # Timestamp
        ("last_access", c_int),  # Last access time
        ("leverage", c_int),     # Leverage
        ("agent_account", c_int),  # Agent account
        ("balance", c_double),   # Balance
        ("credit", c_double),    # Credit
        ("interestrate", c_double),  # Interest rate
        ("taxes", c_double),     # Taxes
        ("send_reports", c_int), # Send reports
        ("mqid", c_uint),        # MQ ID
        ("user_color", c_uint),  # User color
        ("api_data", c_char * 16),  # API data
        ("password_investor", c_char * 16),  # Investor password
        ("password_phone", c_char * 32),  # Phone password
        # ... Add more fields as needed
    ]

class SymbolInfo(Structure):
    _fields_ = [
        ("symbol", c_char * SYMBOL_LEN),  # Symbol name
        ("digits", c_int),       # Digits
        ("count", c_int),        # Count
        ("visible", c_int),      # Visibility
        ("type", c_int),         # Symbol type
        ("point", c_double),     # Point size
        ("spread", c_int),       # Spread
        ("spread_balance", c_int),  # Spread balance
        ("direction", c_int),    # Direction
        ("updateflag", c_int),   # Update flag
        ("bid", c_double),       # Current bid
        ("bidhigh", c_double),   # Bid high
        ("bidlow", c_double),    # Bid low
        ("ask", c_double),       # Current ask
        ("askhigh", c_double),   # Ask high
        ("asklow", c_double),    # Ask low
        ("last", c_double),      # Last price
        ("lasthigh", c_double),  # Last high
        ("lastlow", c_double),   # Last low
        ("volume", c_longlong),  # Volume
        ("volumehigh", c_longlong),  # Volume high
        ("volumelow", c_longlong),   # Volume low
        ("time", c_int),         # Time
        ("digits_currency", c_int),  # Currency digits
        # ... Add more fields as needed
    ]

class TradeTransInfo(Structure):
    _fields_ = [
        ("type", c_int),         # Transaction type (e.g., OP_BUY, OP_SELL)
        ("flags", c_int),        # Trade transaction flags
        ("order", c_int),        # Order ticket
        ("volume", c_int),       # Trade volume
        ("price", c_double),     # Trade price
        ("sl", c_double),        # Stop loss level
        ("tp", c_double),        # Take profit level
        ("symbol", c_char * SYMBOL_LEN),  # Trade symbol
        ("comment", c_char * ACCOUNT_COMMENT_MAX_LEN),  # Trade comment
        ("expiration", c_int),   # Order expiration time
        ("crc", c_int),          # Checksum
        # ... Add more fields as needed
    ]

class MT4Manager:
    """
    Python wrapper for the MT4 Manager API.
    Handles connection to MT4 servers and trade operations.
    """
    
    def __init__(self, use_mock_mode=False):
        """
        Initialize the MT4Manager wrapper.
        
        Args:
            use_mock_mode (bool): If True, uses mock implementation when DLL is not available
        """
        self.api = None
        self.manager = None
        self.connected = False
        self.logged_in = False
        self.mock_mode = False
        
        # Load the MT4 Manager API DLL
        try:
            if not os.path.exists(MT4_MANAGER_API_DLL):
                if use_mock_mode:
                    logger.warning(f"MT4 Manager API DLL not found at {MT4_MANAGER_API_DLL}")
                    logger.warning("Running in MOCK MODE - no actual trades will be executed!")
                    self.mock_mode = True
                    return
                else:
                    raise FileNotFoundError(f"MT4 Manager API DLL not found at {MT4_MANAGER_API_DLL}")
            
            self.api = CDLL(MT4_MANAGER_API_DLL)
            if not self.api:
                if use_mock_mode:
                    logger.warning("Failed to load MT4 Manager API DLL")
                    logger.warning("Running in MOCK MODE - no actual trades will be executed!")
                    self.mock_mode = True
                    return
                else:
                    raise RuntimeError("Failed to load MT4 Manager API DLL")
            
            logger.info(f"Successfully loaded MT4 Manager API DLL from {MT4_MANAGER_API_DLL}")
        except Exception as e:
            if use_mock_mode:
                logger.warning(f"Error loading MT4 Manager API DLL: {e}")
                logger.warning("Running in MOCK MODE - no actual trades will be executed!")
                self.mock_mode = True
            else:
                logger.error(f"Error loading MT4 Manager API DLL: {e}")
                raise
    
    def connect(self, server, port):
        """
        Connect to the MT4 server.
        
        Args:
            server (str): Server IP address
            port (int): Server port
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        # Handle mock mode
        if self.mock_mode:
            logger.info(f"MOCK MODE: Simulating connection to MT4 server {server}:{port}")
            self.connected = True
            return True
            
        # Real implementation for when API is available
        if not self.api:
            logger.error("MT4 Manager API not initialized")
            return False
        
        try:
            # Create MT4 manager factory
            if hasattr(self.api, 'ManagerFactory'):
                factory_func = self.api.ManagerFactory
            else:
                factory_func = self.api.MtManagerFactory
                
            factory_func.restype = c_void_p
            factory = factory_func()
            
            if not factory:
                logger.error("Failed to create MT4 Manager factory")
                return False
            
            # Create MT4 manager interface
            if hasattr(self.api, 'ManagerCreate'):
                create_func = self.api.ManagerCreate
            else:
                create_func = self.api.MtManagerCreate
                
            create_func.restype = c_void_p
            create_func.argtypes = [c_void_p, c_int]
            self.manager = create_func(factory, MT4_MANAGER_API_VERSION)
            
            if not self.manager:
                logger.error("Failed to create MT4 Manager interface")
                return False
            
            # Connect to the server
            connect_func = None
            if hasattr(self.api, 'ManagerConnect'):
                connect_func = self.api.ManagerConnect
            else:
                # Find the connect function in the manager interface
                # This is a bit more complex and depends on the exact API structure
                pass
            
            if connect_func:
                connect_func.restype = c_int
                connect_func.argtypes = [c_void_p, c_char_p, c_int]
                server_bytes = server.encode('utf-8')
                result = connect_func(self.manager, c_char_p(server_bytes), port)
                
                if result == 0:
                    self.connected = True
                    logger.info(f"Successfully connected to MT4 server {server}:{port}")
                    return True
                else:
                    logger.error(f"Failed to connect to MT4 server {server}:{port}, error code: {result}")
                    return False
            else:
                logger.error("Connect function not found in MT4 Manager API")
                return False
        except Exception as e:
            logger.error(f"Error connecting to MT4 server: {e}")
            return False
    
    def login(self, login, password):
        """
        Login to the MT4 server.
        
        Args:
            login (int): Login ID
            password (str): Password
            
        Returns:
            bool: True if login successful, False otherwise
        """
        # Handle mock mode
        if self.mock_mode:
            logger.info(f"MOCK MODE: Simulating login to MT4 server with login {login}")
            self.logged_in = True
            return True
            
        # Real implementation for when API is available
        if not self.connected or not self.manager:
            logger.error("Not connected to MT4 server")
            return False
        
        try:
            # Login to the server
            login_func = None
            if hasattr(self.api, 'ManagerLogin'):
                login_func = self.api.ManagerLogin
            else:
                # Find the login function in the manager interface
                pass
            
            if login_func:
                login_func.restype = c_int
                login_func.argtypes = [c_void_p, c_int, c_char_p]
                password_bytes = password.encode('utf-8')
                result = login_func(self.manager, login, c_char_p(password_bytes))
                
                if result == 0:
                    self.logged_in = True
                    logger.info(f"Successfully logged in to MT4 server with login {login}")
                    return True
                else:
                    logger.error(f"Failed to login to MT4 server, error code: {result}")
                    return False
            else:
                logger.error("Login function not found in MT4 Manager API")
                return False
        except Exception as e:
            logger.error(f"Error logging in to MT4 server: {e}")
            return False
    
    def disconnect(self):
        """
        Disconnect from the MT4 server.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        # Handle mock mode
        if self.mock_mode:
            logger.info("MOCK MODE: Simulating disconnection from MT4 server")
            self.connected = False
            self.logged_in = False
            return True
            
        # Real implementation for when API is available
        if not self.connected or not self.manager:
            return True  # Already disconnected
        
        try:
            # Disconnect from the server
            disconnect_func = None
            if hasattr(self.api, 'ManagerDisconnect'):
                disconnect_func = self.api.ManagerDisconnect
            else:
                # Find the disconnect function in the manager interface
                pass
            
            if disconnect_func:
                disconnect_func.restype = c_int
                disconnect_func.argtypes = [c_void_p]
                result = disconnect_func(self.manager)
                
                if result == 0:
                    self.connected = False
                    self.logged_in = False
                    logger.info("Successfully disconnected from MT4 server")
                    return True
                else:
                    logger.error(f"Failed to disconnect from MT4 server, error code: {result}")
                    return False
            else:
                logger.error("Disconnect function not found in MT4 Manager API")
                return False
        except Exception as e:
            logger.error(f"Error disconnecting from MT4 server: {e}")
            return False
        finally:
            # Cleanup
            if self.api and hasattr(self.api, 'ManagerRelease') and self.manager:
                release_func = self.api.ManagerRelease
                release_func.argtypes = [c_void_p]
                release_func(self.manager)
            self.manager = None
    
    def get_symbols(self):
        """
        Get the list of available symbols.
        
        Returns:
            list: List of symbol names
        """
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return []
        
        try:
            # Get symbols information
            symbols_func = None
            if hasattr(self.api, 'ManagerSymbolsGetAll'):
                symbols_func = self.api.ManagerSymbolsGetAll
            else:
                # Find the symbols function in the manager interface
                pass
            
            if symbols_func:
                symbols_func.restype = c_int
                symbols_func.argtypes = [c_void_p, POINTER(c_void_p)]
                
                symbols_ptr = c_void_p()
                result = symbols_func(self.manager, byref(symbols_ptr))
                
                if result > 0 and symbols_ptr.value:
                    symbols = []
                    for i in range(result):
                        # Extract symbol name from the symbols array
                        symbol_info = SymbolInfo.from_address(symbols_ptr.value + i * ctypes.sizeof(SymbolInfo))
                        symbol_name = symbol_info.symbol.decode('utf-8').strip('\0')
                        symbols.append(symbol_name)
                    
                    # Free the symbols memory
                    free_func = self.api.ManagerMemFree
                    free_func.argtypes = [c_void_p]
                    free_func(symbols_ptr)
                    
                    return symbols
                else:
                    logger.error(f"Failed to get symbols, error code: {result}")
                    return []
            else:
                logger.error("Symbols function not found in MT4 Manager API")
                return []
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []
    
    def get_symbol_info(self, symbol):
        """
        Get information for a specific symbol.
        
        Args:
            symbol (str): Symbol name
            
        Returns:
            dict: Symbol information
        """
        # Handle mock mode
        if self.mock_mode:
            logger.info(f"MOCK MODE: Simulating get_symbol_info for {symbol}")
            # Return mock symbol data
            mock_info = {
                "symbol": symbol,
                "digits": 5 if "JPY" not in symbol else 3,
                "point": 0.00001 if "JPY" not in symbol else 0.001,
                "spread": 2,
                "bid": 1.10000 if "JPY" not in symbol else 110.000,
                "ask": 1.10002 if "JPY" not in symbol else 110.002,
                "last": 1.10001 if "JPY" not in symbol else 110.001,
                "volume": 10000
            }
            return mock_info
            
        # Real implementation for when API is available
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return None
        
        try:
            # Get symbol information
            symbol_func = None
            if hasattr(self.api, 'ManagerSymbolInfoGet'):
                symbol_func = self.api.ManagerSymbolInfoGet
            else:
                # Find the symbol info function in the manager interface
                pass
            
            if symbol_func:
                symbol_func.restype = c_int
                symbol_func.argtypes = [c_void_p, c_char_p, POINTER(SymbolInfo)]
                
                symbol_info = SymbolInfo()
                symbol_bytes = symbol.encode('utf-8')
                result = symbol_func(self.manager, c_char_p(symbol_bytes), byref(symbol_info))
                
                if result == 0:
                    # Convert the symbol_info to a dictionary
                    info = {
                        "symbol": symbol_info.symbol.decode('utf-8').strip('\0'),
                        "digits": symbol_info.digits,
                        "point": symbol_info.point,
                        "spread": symbol_info.spread,
                        "bid": symbol_info.bid,
                        "ask": symbol_info.ask,
                        "last": symbol_info.last,
                        "volume": symbol_info.volume
                    }
                    return info
                else:
                    logger.error(f"Failed to get symbol info for {symbol}, error code: {result}")
                    return None
            else:
                logger.error("Symbol info function not found in MT4 Manager API")
                return None
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_trades(self, login=0):
        """
        Get trades for a specific login or all trades.
        
        Args:
            login (int, optional): Client login ID. If 0, gets all trades.
            
        Returns:
            list: List of trade records
        """
        # Handle mock mode
        if self.mock_mode:
            logger.info(f"MOCK MODE: Simulating get_trades for login {login}")
            # Return mock trades data
            import time
            import random
            
            # Current timestamp
            current_time = int(time.time())
            
            # Generate some mock trades
            mock_trades = []
            
            # Only return trades for requested login or all trades if login=0
            if login == 0 or login == 12345:
                mock_trades.extend([
                    {
                        "order": 10001,
                        "login": 12345,
                        "symbol": "EURUSD",
                        "digits": 5,
                        "cmd": TradeCommand.OP_BUY,
                        "volume": 10,  # 0.1 lot
                        "open_time": current_time - 3600,  # 1 hour ago
                        "state": 0,
                        "open_price": 1.1050,
                        "sl": 1.0950,
                        "tp": 1.1150,
                        "close_time": 0,
                        "profit": 20.0,
                        "comment": "Mock Trade"
                    },
                    {
                        "order": 10002,
                        "login": 12345,
                        "symbol": "GBPUSD",
                        "digits": 5,
                        "cmd": TradeCommand.OP_SELL,
                        "volume": 20,  # 0.2 lot
                        "open_time": current_time - 7200,  # 2 hours ago
                        "state": 0,
                        "open_price": 1.2850,
                        "sl": 1.2950,
                        "tp": 1.2750,
                        "close_time": 0,
                        "profit": -15.0,
                        "comment": "Mock Trade"
                    }
                ])
            
            # Add another login if requensted
            if login == 0 or login == 67890:
                mock_trades.append({
                    "order": 20001,
                    "login": 67890,
                    "symbol": "USDJPY",
                    "digits": 3,
                    "cmd": TradeCommand.OP_BUY,
                    "volume": 50,  # 0.5 lot
                    "open_time": current_time - 10800,  # 3 hours ago
                    "state": 0,
                    "open_price": 109.500,
                    "sl": 109.000,
                    "tp": 110.000,
                    "close_time": 0,
                    "profit": 35.0,
                    "comment": "Mock Trade"
                })
            
            return mock_trades
            
        # Real implementation for when API is available
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return []
        
        try:
            # Get trades
            trades_func = None
            if login > 0 and hasattr(self.api, 'ManagerTradesGetByLogin'):
                trades_func = self.api.ManagerTradesGetByLogin
                trades_func.argtypes = [c_void_p, c_int, POINTER(c_void_p)]
            elif hasattr(self.api, 'ManagerTradesRequest'):
                trades_func = self.api.ManagerTradesRequest
                trades_func.argtypes = [c_void_p, POINTER(c_void_p)]
            else:
                # Find the trades function in the manager interface
                pass
            
            if trades_func:
                trades_func.restype = c_int
                
                trades_ptr = c_void_p()
                if login > 0:
                    result = trades_func(self.manager, login, byref(trades_ptr))
                else:
                    result = trades_func(self.manager, byref(trades_ptr))
                
                if result > 0 and trades_ptr.value:
                    trades = []
                    for i in range(result):
                        # Extract trade record from the trades array
                        trade_record = TradeRecord.from_address(trades_ptr.value + i * ctypes.sizeof(TradeRecord))
                        
                        # Convert the trade_record to a dictionary
                        trade = {
                            "order": trade_record.order,
                            "login": trade_record.login,
                            "symbol": trade_record.symbol.decode('utf-8').strip('\0'),
                            "digits": trade_record.digits,
                            "cmd": trade_record.cmd,
                            "volume": trade_record.volume,
                            "open_time": trade_record.open_time,
                            "state": trade_record.state,
                            "open_price": trade_record.open_price,
                            "sl": trade_record.sl,
                            "tp": trade_record.tp,
                            "close_time": trade_record.close_time,
                            "profit": trade_record.profit,
                            "comment": trade_record.comment.decode('utf-8').strip('\0')
                        }
                        trades.append(trade)
                    
                    # Free the trades memory
                    free_func = self.api.ManagerMemFree
                    free_func.argtypes = [c_void_p]
                    free_func(trades_ptr)
                    
                    return trades
                else:
                    logger.error(f"Failed to get trades, error code: {result}")
                    return []
            else:
                logger.error("Trades function not found in MT4 Manager API")
                return []
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_users(self):
        """
        Get all users.
        
        Returns:
            list: List of user records
        """
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return []
        
        try:
            # Get users
            users_func = None
            if hasattr(self.api, 'ManagerUsersRequest'):
                users_func = self.api.ManagerUsersRequest
            else:
                # Find the users function in the manager interface
                pass
            
            if users_func:
                users_func.restype = c_int
                users_func.argtypes = [c_void_p, POINTER(c_void_p)]
                
                users_ptr = c_void_p()
                result = users_func(self.manager, byref(users_ptr))
                
                if result > 0 and users_ptr.value:
                    users = []
                    for i in range(result):
                        # Extract user record from the users array
                        user_record = UserRecord.from_address(users_ptr.value + i * ctypes.sizeof(UserRecord))
                        
                        # Convert the user_record to a dictionary
                        user = {
                            "login": user_record.login,
                            "group": user_record.group.decode('utf-8').strip('\0'),
                            "name": user_record.name.decode('utf-8').strip('\0'),
                            "email": user_record.email.decode('utf-8').strip('\0'),
                            "leverage": user_record.leverage,
                            "balance": user_record.balance,
                            "credit": user_record.credit
                        }
                        users.append(user)
                    
                    # Free the users memory
                    free_func = self.api.ManagerMemFree
                    free_func.argtypes = [c_void_p]
                    free_func(users_ptr)
                    
                    return users
                else:
                    logger.error(f"Failed to get users, error code: {result}")
                    return []
            else:
                logger.error("Users function not found in MT4 Manager API")
                return []
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def get_user_by_login(self, login):
        """
        Get user record by login.
        
        Args:
            login (int): User login ID
            
        Returns:
            dict: User record
        """
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return None
        
        try:
            # Get user
            user_func = None
            if hasattr(self.api, 'ManagerUserRecordGet'):
                user_func = self.api.ManagerUserRecordGet
            else:
                # Find the user function in the manager interface
                pass
            
            if user_func:
                user_func.restype = c_int
                user_func.argtypes = [c_void_p, c_int, POINTER(UserRecord)]
                
                user_record = UserRecord()
                result = user_func(self.manager, login, byref(user_record))
                
                if result == 0:
                    # Convert the user_record to a dictionary
                    user = {
                        "login": user_record.login,
                        "group": user_record.group.decode('utf-8').strip('\0'),
                        "name": user_record.name.decode('utf-8').strip('\0'),
                        "email": user_record.email.decode('utf-8').strip('\0'),
                        "leverage": user_record.leverage,
                        "balance": user_record.balance,
                        "credit": user_record.credit
                    }
                    return user
                else:
                    logger.error(f"Failed to get user by login {login}, error code: {result}")
                    return None
            else:
                logger.error("User record function not found in MT4 Manager API")
                return None
        except Exception as e:
            logger.error(f"Error getting user by login {login}: {e}")
            return None
    
    def place_order(self, login, symbol, cmd, volume, price, sl=0, tp=0, comment=""):
        """
        Place a new trade order.
        
        Args:
            login (int): Client login ID
            symbol (str): Symbol name
            cmd (int): Trade command (TradeCommand)
            volume (float): Trade volume in lots
            price (float): Trade price
            sl (float, optional): Stop loss level
            tp (float, optional): Take profit level
            comment (str, optional): Trade comment
            
        Returns:
            int: Order ticket number if successful, 0 otherwise
        """
        # Handle mock mode
        if self.mock_mode:
            logger.info(f"MOCK MODE: Simulating placing order - {symbol} {cmd} {volume} lots @ {price}")
            # Generate a random order ticket between 10000-99999
            import random
            ticket = random.randint(10000, 99999)
            logger.info(f"MOCK MODE: Order placed successfully with ticket: {ticket}")
            return ticket
            
        # Real implementation for when API is available
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return 0
        
        try:
            # Prepare trade transaction
            trans_info = TradeTransInfo()
            trans_info.type = cmd
            trans_info.flags = 0
            trans_info.order = 0  # Will be set by server
            trans_info.volume = int(volume * 100)  # Convert to MT4 format (0.1 lot = 10)
            trans_info.price = price
            trans_info.sl = sl
            trans_info.tp = tp
            symbol_bytes = symbol.encode('utf-8')
            for i, b in enumerate(symbol_bytes[:SYMBOL_LEN-1]):
                trans_info.symbol[i] = b
            comment_bytes = comment.encode('utf-8')
            for i, b in enumerate(comment_bytes[:ACCOUNT_COMMENT_MAX_LEN-1]):
                trans_info.comment[i] = b
            
            # Execute trade
            trade_func = None
            if hasattr(self.api, 'ManagerTradeTransaction'):
                trade_func = self.api.ManagerTradeTransaction
            else:
                # Find the trade function in the manager interface
                pass
            
            if trade_func:
                trade_func.restype = c_int
                trade_func.argtypes = [c_void_p, c_int, POINTER(TradeTransInfo)]
                
                # Try the transaction with retries
                retries = 0
                while retries < MT4_TRADE_TRANSACTION_MAX_RETRIES:
                    result = trade_func(self.manager, login, byref(trans_info))
                    if result > 0:
                        logger.info(f"Successfully placed order: {result}")
                        return result
                    else:
                        retries += 1
                        if retries < MT4_TRADE_TRANSACTION_MAX_RETRIES:
                            logger.warning(f"Retrying trade transaction, attempt {retries+1}/{MT4_TRADE_TRANSACTION_MAX_RETRIES}")
                            time.sleep(MT4_TRADE_TRANSACTION_RETRY_DELAY)
                        else:
                            logger.error(f"Failed to place order after {MT4_TRADE_TRANSACTION_MAX_RETRIES} attempts, error code: {result}")
                            return 0
            else:
                logger.error("Trade transaction function not found in MT4 Manager API")
                return 0
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return 0
    
    def modify_order(self, login, order, price=None, sl=None, tp=None):
        """
        Modify an existing trade order.
        
        Args:
            login (int): Client login ID
            order (int): Order ticket
            price (float, optional): New price for pending orders
            sl (float, optional): New stop loss level
            tp (float, optional): New take profit level
            
        Returns:
            bool: True if modification successful, False otherwise
        """
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return False
        
        try:
            # Get the current order first
            trades = self.get_trades(login)
            current_order = None
            for trade in trades:
                if trade["order"] == order:
                    current_order = trade
                    break
            
            if not current_order:
                logger.error(f"Order {order} not found for login {login}")
                return False
            
            # Prepare trade transaction for modification
            trans_info = TradeTransInfo()
            trans_info.type = current_order["cmd"]
            trans_info.flags = 0
            trans_info.order = order
            trans_info.volume = current_order["volume"]
            
            # Use current values if not provided
            trans_info.price = price if price is not None else current_order["open_price"]
            trans_info.sl = sl if sl is not None else current_order["sl"]
            trans_info.tp = tp if tp is not None else current_order["tp"]
            
            symbol_bytes = current_order["symbol"].encode('utf-8')
            for i, b in enumerate(symbol_bytes[:SYMBOL_LEN-1]):
                trans_info.symbol[i] = b
            
            # Execute trade modification
            trade_func = None
            if hasattr(self.api, 'ManagerTradeTransaction'):
                trade_func = self.api.ManagerTradeTransaction
            else:
                # Find the trade function in the manager interface
                pass
            
            if trade_func:
                trade_func.restype = c_int
                trade_func.argtypes = [c_void_p, c_int, POINTER(TradeTransInfo)]
                
                # Try the transaction with retries
                retries = 0
                while retries < MT4_TRADE_TRANSACTION_MAX_RETRIES:
                    result = trade_func(self.manager, login, byref(trans_info))
                    if result > 0:
                        logger.info(f"Successfully modified order {order}")
                        return True
                    else:
                        retries += 1
                        if retries < MT4_TRADE_TRANSACTION_MAX_RETRIES:
                            logger.warning(f"Retrying trade modification, attempt {retries+1}/{MT4_TRADE_TRANSACTION_MAX_RETRIES}")
                            time.sleep(MT4_TRADE_TRANSACTION_RETRY_DELAY)
                        else:
                            logger.error(f"Failed to modify order {order} after {MT4_TRADE_TRANSACTION_MAX_RETRIES} attempts, error code: {result}")
                            return False
            else:
                logger.error("Trade transaction function not found in MT4 Manager API")
                return False
        except Exception as e:
            logger.error(f"Error modifying order {order}: {e}")
            return False
    
    def close_order(self, login, order, lots=0):
        """
        Close an existing trade order.
        
        Args:
            login (int): Client login ID
            order (int): Order ticket
            lots (float, optional): Volume to close. If 0, closes the entire position.
            
        Returns:
            bool: True if closure successful, False otherwise
        """
        if not self.logged_in or not self.manager:
            logger.error("Not logged in to MT4 server")
            return False
        
        try:
            # Get the current order first
            trades = self.get_trades(login)
            current_order = None
            for trade in trades:
                if trade["order"] == order:
                    current_order = trade
                    break
            
            if not current_order:
                logger.error(f"Order {order} not found for login {login}")
                return False
            
            # Get the current price for the symbol
            symbol_info = self.get_symbol_info(current_order["symbol"])
            if not symbol_info:
                logger.error(f"Failed to get symbol info for {current_order['symbol']}")
                return False
            
            # Determine close price based on order type
            close_price = 0
            if current_order["cmd"] == TradeCommand.OP_BUY:
                close_price = symbol_info["bid"]
            elif current_order["cmd"] == TradeCommand.OP_SELL:
                close_price = symbol_info["ask"]
            
            # Prepare trade transaction for closure
            trans_info = TradeTransInfo()
            trans_info.type = (TradeCommand.OP_SELL if current_order["cmd"] == TradeCommand.OP_BUY else TradeCommand.OP_BUY)
            trans_info.flags = 0
            trans_info.order = order
            
            # Use provided volume or current volume
            close_volume = int(lots * 100) if lots > 0 else current_order["volume"]
            trans_info.volume = close_volume
            
            trans_info.price = close_price
            trans_info.sl = 0
            trans_info.tp = 0
            
            symbol_bytes = current_order["symbol"].encode('utf-8')
            for i, b in enumerate(symbol_bytes[:SYMBOL_LEN-1]):
                trans_info.symbol[i] = b
            
            # Execute trade closure
            trade_func = None
            if hasattr(self.api, 'ManagerTradeTransaction'):
                trade_func = self.api.ManagerTradeTransaction
            else:
                # Find the trade function in the manager interface
                pass
            
            if trade_func:
                trade_func.restype = c_int
                trade_func.argtypes = [c_void_p, c_int, POINTER(TradeTransInfo)]
                
                # Try the transaction with retries
                retries = 0
                while retries < MT4_TRADE_TRANSACTION_MAX_RETRIES:
                    result = trade_func(self.manager, login, byref(trans_info))
                    if result > 0:
                        logger.info(f"Successfully closed order {order}")
                        return True
                    else:
                        retries += 1
                        if retries < MT4_TRADE_TRANSACTION_MAX_RETRIES:
                            logger.warning(f"Retrying trade closure, attempt {retries+1}/{MT4_TRADE_TRANSACTION_MAX_RETRIES}")
                            time.sleep(MT4_TRADE_TRANSACTION_RETRY_DELAY)
                        else:
                            logger.error(f"Failed to close order {order} after {MT4_TRADE_TRANSACTION_MAX_RETRIES} attempts, error code: {result}")
                            return False
            else:
                logger.error("Trade transaction function not found in MT4 Manager API")
                return False
        except Exception as e:
            logger.error(f"Error closing order {order}: {e}")
            return False