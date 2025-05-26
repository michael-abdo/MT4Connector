"""
MT4 Pumping Mode Implementation
Handles real-time data streaming from MT4 Manager API
"""

import ctypes
import asyncio
import threading
import logging
import time
from enum import IntEnum
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import weakref

logger = logging.getLogger(__name__)

# Pumping event codes from MT4 Manager API
class PumpingCode(IntEnum):
    """MT4 Manager API pumping event codes"""
    START_PUMPING = 0
    UPDATE_SYMBOLS = 1
    UPDATE_GROUPS = 2
    UPDATE_USERS = 3
    UPDATE_ONLINE = 4
    UPDATE_BID_ASK = 5
    UPDATE_NEWS = 6
    UPDATE_NEWS_BODY = 7
    UPDATE_MAIL = 8
    UPDATE_TRADES = 9
    UPDATE_REQUESTS = 10
    UPDATE_PLUGINS = 11
    UPDATE_ACTIVATION = 12
    UPDATE_MARGINCALL = 13
    STOP_PUMPING = 14
    PING = 15
    UPDATE_NEWS_NEW = 16

# Define callback function type for ctypes
# Windows calling convention
if hasattr(ctypes, 'WINFUNCTYPE'):
    PUMP_FUNC = ctypes.WINFUNCTYPE(
        None,  # return type
        ctypes.c_int,     # code
        ctypes.c_int,     # type
        ctypes.c_void_p,  # data
        ctypes.c_void_p   # param
    )
else:
    # For non-Windows platforms (for testing)
    PUMP_FUNC = ctypes.CFUNCTYPE(
        None,  # return type
        ctypes.c_int,     # code
        ctypes.c_int,     # type
        ctypes.c_void_p,  # data
        ctypes.c_void_p   # param
    )

@dataclass
class QuoteData:
    """Real-time quote data"""
    symbol: str
    bid: float
    ask: float
    spread: float
    time: int
    server_time: datetime
    
@dataclass
class TradeData:
    """Trade update data"""
    order: int
    login: int
    symbol: str
    cmd: int
    volume: float
    open_price: float
    close_price: float
    sl: float
    tp: float
    profit: float
    state: str
    
class MT4PumpingMode:
    """Handles MT4 Manager API pumping mode for real-time data"""
    
    def __init__(self, mt4_manager):
        self.mt4_manager = mt4_manager
        self.pumping_active = False
        self.event_queue: Optional[asyncio.Queue] = None
        self.handlers: Dict[int, List[Callable]] = {}
        self.callback_ref = None  # Keep reference to prevent GC
        self._lock = threading.Lock()
        self._worker_thread = None
        self._stop_event = threading.Event()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'errors': 0,
            'start_time': None,
            'last_event_time': None
        }
        
    def _pumping_callback(self, code: int, type_: int, data: int, param: int):
        """C++ callback function called by MT4 Manager API"""
        try:
            with self._lock:
                self.stats['events_received'] += 1
                self.stats['last_event_time'] = time.time()
                
                # Handle control events synchronously
                if code == PumpingCode.START_PUMPING:
                    logger.info("Pumping mode started successfully")
                    self.pumping_active = True
                    return
                elif code == PumpingCode.STOP_PUMPING:
                    logger.info("Pumping mode stopped")
                    self.pumping_active = False
                    return
                elif code == PumpingCode.PING:
                    logger.debug("Received ping from MT4 server")
                    return
                
                # Convert data pointer based on event code
                event_data = self._convert_data(code, data)
                
                # Put event in queue for async processing
                if self.loop and self.event_queue:
                    asyncio.run_coroutine_threadsafe(
                        self.event_queue.put((code, event_data)),
                        self.loop
                    )
                
        except Exception as e:
            logger.error(f"Error in pumping callback: {e}")
            self.stats['errors'] += 1
    
    def _convert_data(self, code: int, data_ptr: int) -> Optional[Any]:
        """Convert C++ data pointer to Python object based on event code"""
        if data_ptr == 0:
            return None
            
        try:
            if code == PumpingCode.UPDATE_BID_ASK:
                # Import SymbolInfo from mt4_api
                from mt4_api import SymbolInfo
                
                # Convert to SymbolInfo structure
                symbol_info = ctypes.cast(data_ptr, ctypes.POINTER(SymbolInfo)).contents
                
                return QuoteData(
                    symbol=symbol_info.symbol.decode('utf-8').rstrip('\x00'),
                    bid=symbol_info.bid,
                    ask=symbol_info.ask,
                    spread=round((symbol_info.ask - symbol_info.bid) * 
                               (10 ** symbol_info.digits), 1),
                    time=symbol_info.time,
                    server_time=datetime.fromtimestamp(symbol_info.time)
                )
                
            elif code == PumpingCode.UPDATE_TRADES:
                # Import TradeRecord from mt4_api
                from mt4_api import TradeRecord, TradeState
                
                # Convert to TradeRecord structure
                trade = ctypes.cast(data_ptr, ctypes.POINTER(TradeRecord)).contents
                
                # Map trade state
                state_map = {
                    TradeState.TS_OPEN_NORMAL: "open",
                    TradeState.TS_CLOSED_NORMAL: "closed",
                    TradeState.TS_CLOSED_PART: "partial_close",
                    TradeState.TS_DELETED: "deleted"
                }
                
                return TradeData(
                    order=trade.order,
                    login=trade.login,
                    symbol=trade.symbol.decode('utf-8').rstrip('\x00'),
                    cmd=trade.cmd,
                    volume=trade.volume / 100.0,  # Convert to lots
                    open_price=trade.open_price,
                    close_price=trade.close_price,
                    sl=trade.sl,
                    tp=trade.tp,
                    profit=trade.profit,
                    state=state_map.get(trade.state, "unknown")
                )
                
            elif code == PumpingCode.UPDATE_USERS:
                # Import UserRecord from mt4_api
                from mt4_api import UserRecord
                
                # Convert to UserRecord structure
                user = ctypes.cast(data_ptr, ctypes.POINTER(UserRecord)).contents
                
                return {
                    'login': user.login,
                    'balance': user.balance,
                    'credit': user.credit,
                    'group': user.group.decode('utf-8').rstrip('\x00'),
                    'leverage': user.leverage
                }
                
            # Add more conversions as needed
            
        except Exception as e:
            logger.error(f"Error converting data for code {code}: {e}")
            
        return None
    
    def start(self, event_loop: asyncio.AbstractEventLoop) -> bool:
        """Start pumping mode"""
        if self.pumping_active:
            logger.warning("Pumping mode already active")
            return True
            
        if not self.mt4_manager or not self.mt4_manager.logged_in:
            logger.error("MT4 Manager not connected or logged in")
            return False
            
        try:
            # Store event loop reference
            self.loop = event_loop
            self.event_queue = asyncio.Queue()
            
            # Create callback function
            self.callback_ref = PUMP_FUNC(self._pumping_callback)
            
            # Call PumpingSwitch on MT4 Manager
            # This is a placeholder - actual implementation depends on the API
            if hasattr(self.mt4_manager.api, 'PumpingSwitch'):
                result = self.mt4_manager.api.PumpingSwitch(
                    self.mt4_manager.manager,
                    self.callback_ref,
                    0,  # flags
                    None  # param
                )
                
                if result == 0:  # Assuming 0 is success
                    self.stats['start_time'] = time.time()
                    logger.info("Pumping mode initialization successful")
                    return True
                else:
                    logger.error(f"Failed to start pumping mode: {result}")
                    return False
            else:
                # Mock mode or API doesn't have PumpingSwitch
                logger.warning("PumpingSwitch not available, using mock mode")
                self.pumping_active = True
                self.stats['start_time'] = time.time()
                # Start mock data generator
                asyncio.create_task(self._generate_mock_data())
                return True
                
        except Exception as e:
            logger.error(f"Error starting pumping mode: {e}")
            return False
    
    def stop(self):
        """Stop pumping mode"""
        if not self.pumping_active:
            return
            
        try:
            self.pumping_active = False
            self._stop_event.set()
            
            # Call MT4 API to stop pumping
            if hasattr(self.mt4_manager.api, 'PumpingSwitch') and self.mt4_manager.manager:
                self.mt4_manager.api.PumpingSwitch(
                    self.mt4_manager.manager,
                    None,  # NULL callback to stop
                    0,
                    None
                )
                
            logger.info("Pumping mode stopped")
            
        except Exception as e:
            logger.error(f"Error stopping pumping mode: {e}")
    
    def register_handler(self, event_code: int, handler: Callable):
        """Register a handler for a specific event code"""
        if event_code not in self.handlers:
            self.handlers[event_code] = []
        self.handlers[event_code].append(handler)
        logger.debug(f"Registered handler for event code {event_code}")
    
    async def process_events(self):
        """Process events from the queue"""
        logger.info("Starting event processing")
        
        while self.pumping_active:
            try:
                # Get event with timeout
                code, data = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                self.stats['events_processed'] += 1
                
                # Call registered handlers
                if code in self.handlers:
                    for handler in self.handlers[code]:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(data)
                            else:
                                handler(data)
                        except Exception as e:
                            logger.error(f"Error in event handler: {e}")
                            self.stats['errors'] += 1
                            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing events: {e}")
                self.stats['errors'] += 1
        
        logger.info("Event processing stopped")
    
    async def _generate_mock_data(self):
        """Generate mock pumping data for testing"""
        import random
        
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']
        base_prices = {
            'EURUSD': 1.0850,
            'GBPUSD': 1.2650,
            'USDJPY': 148.50,
            'USDCHF': 0.8950,
            'AUDUSD': 0.6550
        }
        
        logger.info("Starting mock data generator")
        
        while self.pumping_active:
            try:
                # Generate random quote updates
                for symbol in symbols:
                    if random.random() < 0.3:  # 30% chance to update each symbol
                        base = base_prices[symbol]
                        spread = 0.0002 if 'JPY' not in symbol else 0.02
                        
                        # Random walk
                        change = random.uniform(-0.0005, 0.0005)
                        base_prices[symbol] = base + change
                        
                        quote = QuoteData(
                            symbol=symbol,
                            bid=base_prices[symbol],
                            ask=base_prices[symbol] + spread,
                            spread=spread * 10000 if 'JPY' not in symbol else spread * 100,
                            time=int(time.time()),
                            server_time=datetime.now()
                        )
                        
                        await self.event_queue.put((PumpingCode.UPDATE_BID_ASK, quote))
                
                # Sleep to simulate realistic update frequency
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in mock data generator: {e}")
                
        logger.info("Mock data generator stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pumping statistics"""
        stats = self.stats.copy()
        if stats['start_time']:
            stats['uptime_seconds'] = time.time() - stats['start_time']
        return stats