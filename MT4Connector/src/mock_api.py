"""
Mock MT4 API for testing without real MT4 connection
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import random

logger = logging.getLogger(__name__)


class MT4MockAPI:
    """Mock implementation of MT4 API for testing"""
    
    def __init__(self):
        self.connected = False  # Use 'connected' instead of 'is_connected'
        self.mock_orders = {}
        self.next_ticket = 100000
        logger.info("MT4MockAPI initialized")
    
    def connect(self, server: str, port: int, login: int, password: str) -> bool:
        """Simulate connection to MT4 server"""
        logger.info(f"Mock connecting to {server}:{port} with login {login}")
        self.connected = True
        return True
    
    def disconnect(self) -> bool:
        """Simulate disconnection from MT4 server"""
        logger.info("Mock disconnecting from MT4")
        self.connected = False
        return True
    
    def is_connected_to_server(self) -> bool:
        """Check if connected to server"""
        return self.connected
    
    def get_account_info(self, login: Optional[int] = None) -> Dict[str, Any]:
        """Get mock account information"""
        if not self.connected:
            raise Exception("Not connected to server")
        
        return {
            "status": "success",
            "data": {
                "login": login or 12345,
                "balance": 10000.0,
                "equity": 10000.0,
                "margin": 0.0,
                "free_margin": 10000.0,
                "currency": "USD",
                "leverage": 100,
                "name": "Mock Account",
                "server": "Mock-Server"
            }
        }
    
    def execute_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a mock trade from trade data dictionary"""
        if not self.connected:
            return {
                "status": "error",
                "message": "Not connected to server"
            }
        
        # Extract parameters from trade_data
        symbol = trade_data.get("symbol", "EURUSD")
        operation = self._get_operation_from_type(trade_data.get("type", "BUY"))
        volume = trade_data.get("volume", 0.01)
        price = trade_data.get("price", 0)
        slippage = trade_data.get("slippage", 3)
        stoploss = trade_data.get("stoploss", 0)
        takeprofit = trade_data.get("takeprofit", 0)
        comment = trade_data.get("comment", "")
        magic = trade_data.get("magic", 0)
        
        ticket = self.next_ticket
        self.next_ticket += 1
        
        # Simulate market price
        if price == 0:
            price = 1.1000 + random.uniform(-0.0050, 0.0050)
        
        order = {
            "ticket": ticket,
            "symbol": symbol,
            "operation": operation,
            "volume": volume,
            "price": price,
            "stoploss": stoploss,
            "takeprofit": takeprofit,
            "comment": comment,
            "magic": magic,
            "open_time": datetime.now().isoformat(),
            "profit": 0.0
        }
        
        self.mock_orders[ticket] = order
        logger.info(f"Mock trade executed: {order}")
        
        return {
            "status": "success",
            "data": {
                "ticket": ticket,
                "success": True,
                "order": order
            }
        }
    
    def get_open_orders(self, login: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of open orders"""
        if not self.connected:
            raise Exception("Not connected to server")
        
        return list(self.mock_orders.values())
    
    def get_trades(self, login: Optional[int] = None, open_only: bool = True) -> Dict[str, Any]:
        """Get trades for account"""
        if not self.connected:
            raise Exception("Not connected to server")
        
        trades = list(self.mock_orders.values()) if open_only else []
        return {"status": "success", "data": trades}
    
    def close_order(self, ticket: int) -> Dict[str, Any]:
        """Close a mock order"""
        if not self.connected:
            raise Exception("Not connected to server")
        
        if ticket in self.mock_orders:
            del self.mock_orders[ticket]
            logger.info(f"Mock order {ticket} closed")
            return {"status": "success", "message": f"Order {ticket} closed"}
        return {"status": "error", "message": f"Order {ticket} not found"}
    
    def modify_order(self, ticket: int, stoploss: float = None, 
                    takeprofit: float = None) -> Dict[str, Any]:
        """Modify a mock order"""
        if not self.connected:
            raise Exception("Not connected to server")
        
        if ticket in self.mock_orders:
            if stoploss is not None:
                self.mock_orders[ticket]["stoploss"] = stoploss
            if takeprofit is not None:
                self.mock_orders[ticket]["takeprofit"] = takeprofit
            logger.info(f"Mock order {ticket} modified")
            return {"status": "success", "message": f"Order {ticket} modified"}
        return {"status": "error", "message": f"Order {ticket} not found"}
    
    def close_trade(self, ticket: int) -> Dict[str, Any]:
        """Alias for close_order for compatibility"""
        return self.close_order(ticket)
    
    def modify_trade(self, ticket: int, sl: float = None, tp: float = None) -> Dict[str, Any]:
        """Alias for modify_order for compatibility"""
        result = self.modify_order(ticket, sl, tp)
        if result["status"] == "success" and ticket in self.mock_orders:
            # Add data field with the modified values
            result["data"] = {
                "ticket": ticket,
                "sl": self.mock_orders[ticket]["stoploss"],
                "tp": self.mock_orders[ticket]["takeprofit"]
            }
        return result
    
    def _get_operation_from_type(self, trade_type: str) -> int:
        """Convert trade type string to operation code"""
        type_map = {
            "BUY": 0,
            "SELL": 1,
            "BUY_LIMIT": 2,
            "SELL_LIMIT": 3,
            "BUY_STOP": 4,
            "SELL_STOP": 5
        }
        return type_map.get(trade_type.upper(), 0)