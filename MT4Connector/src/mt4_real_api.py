"""
MT4 Real API Implementation
Wrapper for real MT4 Manager API calls with fallback to mock mode
"""
import os
import sys
import logging
import asyncio
import ctypes
from ctypes import *
import platform
from typing import Dict, Any, Optional, Callable
from enum import IntEnum

# Import mock API as fallback
try:
    from mt4_api import MT4Manager, TradeCommand
    HAS_REAL_API = True
except ImportError:
    HAS_REAL_API = False

# Import mock API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'mt4_connector'))
try:
    from mock_api import MT4MockAPI
except ImportError:
    # Try alternate path
    sys.path.insert(0, os.path.dirname(__file__))
    from mock_api import MT4MockAPI

logger = logging.getLogger(__name__)

# Import pumping mode components
try:
    from mt4_pumping import MT4PumpingMode, PumpingCode
    from mt4_event_dispatcher import EventDispatcher
    from mt4_websocket import MT4WebSocketServer
    HAS_PUMPING = True
except ImportError as e:
    logger.warning(f"Pumping mode components not available: {e}")
    HAS_PUMPING = False

class MT4RealAPI:
    """
    Real MT4 Manager API implementation with mock fallback
    Switches between real and mock based on configuration and availability
    """
    
    def __init__(self, use_mock=None):
        """
        Initialize MT4 API
        
        Args:
            use_mock (bool): Force mock mode. If None, auto-detect based on environment
        """
        # Auto-detect mode if not specified
        if use_mock is None:
            use_mock = os.environ.get('MOCK_MODE', 'True').lower() == 'true'
            
        self.use_mock = use_mock or not HAS_REAL_API
        self.connected = False
        self.manager = None
        self.server_info = {}
        
        # Pumping mode components
        self.pumping_mode = None
        self.event_dispatcher = None
        self.websocket_server = None
        self.pumping_active = False
        self._event_loop = None
        
        if self.use_mock:
            logger.info("Initializing MT4 API in MOCK mode")
            self.mock_api = MT4MockAPI()
        else:
            logger.info("Initializing MT4 API in REAL mode")
            try:
                self._init_real_api()
            except Exception as e:
                logger.error(f"Failed to initialize real API: {e}")
                logger.warning("Falling back to MOCK mode")
                self.use_mock = True
                self.mock_api = MT4MockAPI()
    
    def _init_real_api(self):
        """Initialize the real MT4 Manager API"""
        if not HAS_REAL_API:
            raise ImportError("MT4 Manager API not available")
            
        try:
            self.manager = MT4Manager()
            logger.info("Real MT4 Manager API initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing MT4 Manager: {e}")
            raise
    
    def connect(self, server: str, port: int, login: int, password: str) -> bool:
        """
        Connect to MT4 server
        
        Args:
            server: MT4 server address
            port: Server port (usually 443)
            login: Manager login
            password: Manager password
            
        Returns:
            bool: True if connected successfully
        """
        if self.use_mock:
            return self.mock_api.connect(server, port, login, password)
        
        try:
            # Real MT4 connection
            result = self.manager.Connect(server, port, login, password)
            if result == 0:  # Success
                self.connected = True
                self.server_info = {
                    "server": server,
                    "port": port,
                    "login": login
                }
                logger.info(f"Connected to real MT4 server: {server}:{port}")
                return True
            else:
                logger.error(f"Failed to connect to MT4 server. Error code: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Exception connecting to MT4 server: {e}")
            # Try fallback to mock
            if not self.use_mock:
                logger.warning("Attempting mock mode fallback")
                self.use_mock = True
                self.mock_api = MT4MockAPI()
                return self.mock_api.connect(server, port, login, password)
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from MT4 server"""
        if self.use_mock:
            return self.mock_api.disconnect()
            
        try:
            if self.manager and self.connected:
                self.manager.Disconnect()
                self.connected = False
                logger.info("Disconnected from MT4 server")
                return True
            return False
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False
    
    def execute_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trade
        
        Args:
            trade_data: Dictionary containing trade parameters
            
        Returns:
            dict: Result with status and trade details
        """
        if self.use_mock:
            return self.mock_api.execute_trade(trade_data)
        
        if not self.connected:
            return {
                "status": "error",
                "message": "Not connected to MT4 server"
            }
        
        try:
            # Extract parameters
            symbol = trade_data.get("symbol", "EURUSD")
            cmd = self._get_trade_command(trade_data.get("type", "BUY"))
            volume = int(float(trade_data.get("volume", 0.1)) * 100)  # Convert to cents
            price = float(trade_data.get("price", 0))
            sl = float(trade_data.get("sl", 0))
            tp = float(trade_data.get("tp", 0))
            comment = trade_data.get("comment", "")
            login = int(trade_data.get("login", 0))
            
            # Execute trade
            ticket = self.manager.TradeOpen(
                login, symbol, cmd, volume, price, sl, tp, comment
            )
            
            if ticket > 0:
                logger.info(f"Trade executed successfully. Ticket: {ticket}")
                return {
                    "status": "success",
                    "message": "Trade executed successfully",
                    "data": {
                        "ticket": ticket,
                        "symbol": symbol,
                        "type": trade_data.get("type"),
                        "volume": trade_data.get("volume"),
                        "price": price,
                        "sl": sl,
                        "tp": tp
                    }
                }
            else:
                error_msg = self._get_error_message(ticket)
                logger.error(f"Trade execution failed: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "code": ticket
                }
                
        except Exception as e:
            logger.error(f"Exception executing trade: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def modify_trade(self, ticket: int, sl: float = None, tp: float = None) -> Dict[str, Any]:
        """Modify an existing trade"""
        if self.use_mock:
            return self.mock_api.modify_trade(ticket, sl, tp)
        
        if not self.connected:
            return {
                "status": "error",
                "message": "Not connected to MT4 server"
            }
        
        try:
            # Get current trade info first
            trade_info = self.manager.TradeGet(ticket)
            if not trade_info:
                return {
                    "status": "error",
                    "message": f"Trade {ticket} not found"
                }
            
            # Use existing values if not provided
            new_sl = sl if sl is not None else trade_info.sl
            new_tp = tp if tp is not None else trade_info.tp
            
            # Modify trade
            result = self.manager.TradeModify(ticket, trade_info.price, new_sl, new_tp)
            
            if result == 0:  # Success
                logger.info(f"Trade {ticket} modified successfully")
                return {
                    "status": "success",
                    "message": "Trade modified successfully",
                    "data": {
                        "ticket": ticket,
                        "sl": new_sl,
                        "tp": new_tp
                    }
                }
            else:
                error_msg = self._get_error_message(result)
                logger.error(f"Trade modification failed: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "code": result
                }
                
        except Exception as e:
            logger.error(f"Exception modifying trade: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def close_trade(self, ticket: int) -> Dict[str, Any]:
        """Close an existing trade"""
        if self.use_mock:
            return self.mock_api.close_trade(ticket)
        
        if not self.connected:
            return {
                "status": "error",
                "message": "Not connected to MT4 server"
            }
        
        try:
            # Get current trade info
            trade_info = self.manager.TradeGet(ticket)
            if not trade_info:
                return {
                    "status": "error",
                    "message": f"Trade {ticket} not found"
                }
            
            # Get current price for closing
            price_info = self.manager.SymbolGet(trade_info.symbol)
            close_price = price_info.bid if trade_info.cmd == 0 else price_info.ask  # 0 = BUY
            
            # Close trade
            result = self.manager.TradeClose(ticket, close_price, trade_info.volume)
            
            if result > 0:  # Returns closing ticket
                logger.info(f"Trade {ticket} closed successfully")
                return {
                    "status": "success",
                    "message": "Trade closed successfully",
                    "data": {
                        "ticket": ticket,
                        "close_ticket": result,
                        "close_price": close_price
                    }
                }
            else:
                error_msg = self._get_error_message(result)
                logger.error(f"Trade close failed: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "code": result
                }
                
        except Exception as e:
            logger.error(f"Exception closing trade: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_account_info(self, login: int) -> Dict[str, Any]:
        """Get account information"""
        if self.use_mock:
            return self.mock_api.get_account_info(login)
        
        if not self.connected:
            return {
                "status": "error",
                "message": "Not connected to MT4 server"
            }
        
        try:
            account_info = self.manager.AccountGet(login)
            if account_info:
                return {
                    "status": "success",
                    "data": {
                        "login": account_info.login,
                        "name": account_info.name,
                        "balance": account_info.balance,
                        "equity": account_info.equity,
                        "margin": account_info.margin,
                        "free_margin": account_info.margin_free,
                        "leverage": account_info.leverage
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"Account {login} not found"
                }
                
        except Exception as e:
            logger.error(f"Exception getting account info: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_open_orders(self, login: int = None) -> Dict[str, Any]:
        """Get open orders for an account"""
        if self.use_mock:
            return self.mock_api.get_trades(login, open_only=True) if login else {"status": "success", "data": []}
        
        if not self.connected:
            return {
                "status": "error",
                "message": "Not connected to MT4 server"
            }
        
        try:
            # Get all trades
            trades = self.manager.TradesGet()
            
            # Filter by login if specified
            if login:
                trades = [t for t in trades if t.login == login]
            
            # Convert to dict format
            trades_data = []
            for trade in trades:
                trades_data.append({
                    "ticket": trade.order,
                    "symbol": trade.symbol,
                    "type": self._get_trade_type_name(trade.cmd),
                    "volume": trade.volume / 100.0,  # Convert from cents
                    "open_price": trade.open_price,
                    "open_time": trade.open_time,
                    "sl": trade.sl,
                    "tp": trade.tp,
                    "profit": trade.profit,
                    "comment": trade.comment
                })
            
            return {
                "status": "success",
                "data": trades_data
            }
            
        except Exception as e:
            logger.error(f"Exception getting open orders: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _get_trade_command(self, trade_type: str) -> int:
        """Convert trade type string to MT4 command"""
        trade_map = {
            "BUY": 0,
            "SELL": 1,
            "BUY_LIMIT": 2,
            "SELL_LIMIT": 3,
            "BUY_STOP": 4,
            "SELL_STOP": 5
        }
        return trade_map.get(trade_type.upper(), 0)
    
    def _get_trade_type_name(self, cmd: int) -> str:
        """Convert MT4 command to trade type string"""
        type_map = {
            0: "BUY",
            1: "SELL",
            2: "BUY_LIMIT",
            3: "SELL_LIMIT",
            4: "BUY_STOP",
            5: "SELL_STOP"
        }
        return type_map.get(cmd, "UNKNOWN")
    
    def _get_error_message(self, error_code: int) -> str:
        """Get human-readable error message from MT4 error code"""
        error_messages = {
            -1: "Generic error",
            -2: "Invalid parameters",
            -3: "Server error",
            -4: "Not enough money",
            -5: "Trade not allowed",
            -6: "Market closed",
            -7: "Invalid price",
            -8: "Invalid stops",
            -9: "Trade disabled",
            -10: "Position locked"
        }
        return error_messages.get(error_code, f"Unknown error code: {error_code}")
    
    # Pumping Mode Methods
    async def start_pumping_mode(self, websocket_host: str = 'localhost', 
                                websocket_port: int = 8765) -> bool:
        """
        Start pumping mode for real-time data streaming
        
        Args:
            websocket_host: Host for WebSocket server
            websocket_port: Port for WebSocket server
            
        Returns:
            bool: True if pumping mode started successfully
        """
        if not HAS_PUMPING:
            logger.error("Pumping mode components not available")
            return False
            
        if self.pumping_active:
            logger.warning("Pumping mode already active")
            return True
            
        if not self.connected:
            logger.error("Must be connected to MT4 server to start pumping mode")
            return False
            
        try:
            # Get or create event loop
            try:
                self._event_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
            
            # Initialize components
            self.pumping_mode = MT4PumpingMode(self.manager if not self.use_mock else None)
            self.event_dispatcher = EventDispatcher()
            self.websocket_server = MT4WebSocketServer(websocket_host, websocket_port)
            
            # Register event handlers
            self._register_event_handlers()
            
            # Start pumping
            if self.pumping_mode.start(self._event_loop):
                # Start WebSocket server
                await self.websocket_server.start()
                
                # Start event processing
                asyncio.create_task(self.pumping_mode.process_events())
                
                self.pumping_active = True
                logger.info("Pumping mode started successfully")
                return True
            else:
                logger.error("Failed to start pumping mode")
                return False
                
        except Exception as e:
            logger.error(f"Error starting pumping mode: {e}")
            return False
    
    def stop_pumping_mode(self):
        """Stop pumping mode"""
        if not self.pumping_active:
            return
            
        try:
            if self.pumping_mode:
                self.pumping_mode.stop()
                
            if self.websocket_server:
                asyncio.create_task(self.websocket_server.stop())
                
            self.pumping_active = False
            logger.info("Pumping mode stopped")
            
        except Exception as e:
            logger.error(f"Error stopping pumping mode: {e}")
    
    def _register_event_handlers(self):
        """Register handlers for pumping events"""
        if not self.pumping_mode or not self.event_dispatcher:
            return
            
        # Register pumping mode handlers
        self.pumping_mode.register_handler(
            PumpingCode.UPDATE_BID_ASK,
            self._handle_quote_update
        )
        self.pumping_mode.register_handler(
            PumpingCode.UPDATE_TRADES,
            self._handle_trade_update
        )
        
        # Register dispatcher handlers for WebSocket broadcasting
        self.event_dispatcher.subscribe_all_quotes(
            self._broadcast_quote_to_websocket
        )
        self.event_dispatcher.subscribe_all_trades(
            self._broadcast_trade_to_websocket
        )
    
    async def _handle_quote_update(self, quote_data):
        """Handle quote update from pumping mode"""
        # Dispatch to event dispatcher
        await self.event_dispatcher.dispatch(PumpingCode.UPDATE_BID_ASK, quote_data)
    
    async def _handle_trade_update(self, trade_data):
        """Handle trade update from pumping mode"""
        # Dispatch to event dispatcher
        await self.event_dispatcher.dispatch(PumpingCode.UPDATE_TRADES, trade_data)
    
    async def _broadcast_quote_to_websocket(self, quote_data):
        """Broadcast quote to WebSocket clients"""
        if self.websocket_server:
            await self.websocket_server.broadcast_quote(quote_data)
    
    async def _broadcast_trade_to_websocket(self, trade_data):
        """Broadcast trade to WebSocket clients"""
        if self.websocket_server:
            await self.websocket_server.broadcast_trade(trade_data, trade_data.login)
    
    def subscribe_quotes(self, symbol: str, callback: Callable):
        """Subscribe to quote updates for a symbol"""
        if self.event_dispatcher:
            self.event_dispatcher.subscribe_quotes(symbol, callback)
    
    def subscribe_trades(self, login: int, callback: Callable):
        """Subscribe to trade updates for a login"""
        if self.event_dispatcher:
            self.event_dispatcher.subscribe_trades(login, callback)
    
    def get_pumping_stats(self) -> Dict[str, Any]:
        """Get statistics from pumping mode"""
        stats = {}
        
        if self.pumping_mode:
            stats['pumping'] = self.pumping_mode.get_stats()
            
        if self.event_dispatcher:
            stats['dispatcher'] = self.event_dispatcher.get_stats()
            
        if self.websocket_server:
            stats['websocket'] = self.websocket_server.get_stats()
            
        return stats

# Create a singleton instance
_mt4_real_api = None

def get_mt4_api(use_mock=None):
    """Get or create MT4 API instance"""
    global _mt4_real_api
    if _mt4_real_api is None:
        _mt4_real_api = MT4RealAPI(use_mock)
    return _mt4_real_api