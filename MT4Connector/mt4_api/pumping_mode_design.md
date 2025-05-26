# MT4 Pumping Mode Implementation Design

## Overview

Pumping mode is the MT4 Manager API's mechanism for receiving real-time updates from the MT4 server. This includes price quotes, trade executions, account updates, and other events. This design document outlines how to integrate pumping mode into the existing Python-based MT4 wrapper.

## Architecture

### 1. Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                         MT4 Server                          │
└──────────────────┬──────────────────────────────────────────┘
                   │ Real-time Data Stream
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              MT4 Manager API (C++ DLL)                      │
│  - PumpingSwitch()                                          │
│  - Callback Registration                                    │
└──────────────────┬──────────────────────────────────────────┘
                   │ C++ Callbacks
                   ▼
┌─────────────────────────────────────────────────────────────┐
│           Python-C++ Bridge (ctypes)                        │
│  - Callback Wrapper                                         │
│  - Data Structure Conversion                                │
│  - Thread Safety                                            │
└──────────────────┬──────────────────────────────────────────┘
                   │ Python Events
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Event Dispatcher (Python)                      │
│  - Event Queue                                              │
│  - Handler Registration                                     │
│  - Async Processing                                         │
└────────┬──────────────────────┬──────────────────┬─────────┘
         │                      │                    │
         ▼                      ▼                    ▼
┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│ Quote Handler  │   │ Trade Handler  │   │ Event Handler  │
│ - Price Cache  │   │ - Execution    │   │ - News/Mail    │
│ - Subscribers  │   │ - Monitoring   │   │ - Account      │
└────────────────┘   └────────────────┘   └────────────────┘
         │                      │                    │
         └──────────────────────┴────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Server                         │
│  - Real-time client updates                                │
│  - Subscription management                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2. Implementation Strategy

#### Phase 1: C++ to Python Bridge
1. Define ctypes callback function types
2. Implement thread-safe callback wrapper
3. Handle data structure marshalling

#### Phase 2: Event System
1. Create event queue with asyncio
2. Implement event dispatcher
3. Add handler registration system

#### Phase 3: Data Handlers
1. Quote handler with caching
2. Trade execution handler
3. Account update handler

#### Phase 4: WebSocket Distribution
1. WebSocket server integration
2. Client subscription management
3. Selective data streaming

## Detailed Implementation

### 1. Pumping Mode Initialization

```python
# mt4_pumping.py
import ctypes
import asyncio
import threading
from enum import IntEnum
from typing import Callable, Dict, List, Any
import weakref

class PumpingCode(IntEnum):
    """Pumping event codes from MT4 Manager API"""
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
PUMP_FUNC = ctypes.WINFUNCTYPE(
    None,  # return type
    ctypes.c_int,     # code
    ctypes.c_int,     # type
    ctypes.c_void_p,  # data
    ctypes.c_void_p   # param
)

class MT4PumpingMode:
    """Handles MT4 Manager API pumping mode for real-time data"""
    
    def __init__(self, mt4_manager):
        self.mt4_manager = mt4_manager
        self.pumping_active = False
        self.event_queue = asyncio.Queue()
        self.handlers = {}
        self.callback_ref = None  # Keep reference to prevent GC
        self._lock = threading.Lock()
        self._worker_thread = None
        self._stop_event = threading.Event()
        
    def _pumping_callback(self, code: int, type_: int, data: int, param: int):
        """C++ callback function called by MT4 Manager API"""
        try:
            with self._lock:
                # Convert data pointer based on event code
                event_data = self._convert_data(code, data)
                
                # Put event in queue for async processing
                asyncio.run_coroutine_threadsafe(
                    self.event_queue.put((code, event_data)),
                    self.loop
                )
                
        except Exception as e:
            logger.error(f"Error in pumping callback: {e}")
    
    def _convert_data(self, code: int, data_ptr: int) -> Any:
        """Convert C++ data pointer to Python object based on event code"""
        if data_ptr == 0:
            return None
            
        if code == PumpingCode.UPDATE_BID_ASK:
            # Convert to SymbolInfo structure
            symbol_info = ctypes.cast(data_ptr, ctypes.POINTER(SymbolInfo)).contents
            return {
                'symbol': symbol_info.symbol.decode('utf-8'),
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'time': symbol_info.time
            }
        elif code == PumpingCode.UPDATE_TRADES:
            # Convert to TradeRecord structure
            trade = ctypes.cast(data_ptr, ctypes.POINTER(TradeRecord)).contents
            return {
                'order': trade.order,
                'login': trade.login,
                'symbol': trade.symbol.decode('utf-8'),
                'cmd': trade.cmd,
                'volume': trade.volume,
                'open_price': trade.open_price,
                'sl': trade.sl,
                'tp': trade.tp,
                'close_price': trade.close_price,
                'profit': trade.profit
            }
        # Add more conversions as needed
        
        return None
```

### 2. Event Handler System

```python
# mt4_event_handler.py
import asyncio
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
import time

@dataclass
class QuoteData:
    """Real-time quote data"""
    symbol: str
    bid: float
    ask: float
    time: int
    spread: float
    
class EventDispatcher:
    """Dispatches pumping events to registered handlers"""
    
    def __init__(self):
        self.handlers: Dict[int, List[Callable]] = {}
        self.quote_cache: Dict[str, QuoteData] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        
    def register_handler(self, event_code: int, handler: Callable):
        """Register a handler for a specific event code"""
        if event_code not in self.handlers:
            self.handlers[event_code] = []
        self.handlers[event_code].append(handler)
        
    def subscribe_quotes(self, symbol: str, callback: Callable):
        """Subscribe to quote updates for a specific symbol"""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
        
    async def dispatch(self, event_code: int, data: Any):
        """Dispatch event to all registered handlers"""
        if event_code in self.handlers:
            for handler in self.handlers[event_code]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
                    
        # Special handling for quotes
        if event_code == PumpingCode.UPDATE_BID_ASK and data:
            await self._handle_quote_update(data)
    
    async def _handle_quote_update(self, data: Dict):
        """Handle quote updates with caching and distribution"""
        symbol = data['symbol']
        quote = QuoteData(
            symbol=symbol,
            bid=data['bid'],
            ask=data['ask'],
            time=data['time'],
            spread=round((data['ask'] - data['bid']) * 10000, 1)  # Assuming 5 digits
        )
        
        # Update cache
        self.quote_cache[symbol] = quote
        
        # Notify subscribers
        if symbol in self.subscribers:
            for callback in self.subscribers[symbol]:
                try:
                    await callback(quote)
                except Exception as e:
                    logger.error(f"Error notifying quote subscriber: {e}")
```

### 3. WebSocket Integration

```python
# mt4_websocket.py
import asyncio
import json
import websockets
from typing import Set, Dict
import logging

logger = logging.getLogger(__name__)

class MT4WebSocketServer:
    """WebSocket server for real-time MT4 data distribution"""
    
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_subscriptions: Dict[websockets.WebSocketServerProtocol, Set[str]] = {}
        
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        self.client_subscriptions[websocket] = set()
        logger.info(f"Client {websocket.remote_address} connected")
        
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        self.client_subscriptions.pop(websocket, None)
        logger.info(f"Client {websocket.remote_address} disconnected")
        
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
            
    async def process_message(self, websocket, message):
        """Process client message"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'subscribe':
                symbols = data.get('symbols', [])
                self.client_subscriptions[websocket].update(symbols)
                await websocket.send(json.dumps({
                    'type': 'subscription',
                    'status': 'success',
                    'symbols': list(self.client_subscriptions[websocket])
                }))
                
            elif action == 'unsubscribe':
                symbols = data.get('symbols', [])
                self.client_subscriptions[websocket].difference_update(symbols)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def broadcast_quote(self, quote: QuoteData):
        """Broadcast quote update to subscribed clients"""
        message = json.dumps({
            'type': 'quote',
            'data': {
                'symbol': quote.symbol,
                'bid': quote.bid,
                'ask': quote.ask,
                'spread': quote.spread,
                'time': quote.time
            }
        })
        
        # Send to all clients subscribed to this symbol
        tasks = []
        for client, subscriptions in self.client_subscriptions.items():
            if quote.symbol in subscriptions:
                tasks.append(client.send(message))
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        await websockets.serve(self.handle_client, self.host, self.port)
```

### 4. Integration with Existing System

```python
# mt4_real_api.py (additions)

class MT4RealAPI:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pumping_mode = None
        self.event_dispatcher = None
        self.websocket_server = None
        
    async def start_pumping_mode(self):
        """Start pumping mode for real-time data"""
        if self.mock_mode:
            logger.info("MOCK MODE: Simulating pumping mode")
            return True
            
        if not self.mt4_manager.logged_in:
            logger.error("Must be logged in to start pumping mode")
            return False
            
        # Initialize components
        self.pumping_mode = MT4PumpingMode(self.mt4_manager)
        self.event_dispatcher = EventDispatcher()
        self.websocket_server = MT4WebSocketServer()
        
        # Register handlers
        self.event_dispatcher.register_handler(
            PumpingCode.UPDATE_BID_ASK,
            self._handle_quote_update
        )
        self.event_dispatcher.register_handler(
            PumpingCode.UPDATE_TRADES,
            self._handle_trade_update
        )
        
        # Start pumping
        success = self.pumping_mode.start()
        if success:
            # Start WebSocket server
            await self.websocket_server.start()
            
            # Start event processing
            asyncio.create_task(self._process_events())
            
        return success
    
    async def _process_events(self):
        """Process events from pumping mode"""
        while self.pumping_mode.pumping_active:
            try:
                code, data = await asyncio.wait_for(
                    self.pumping_mode.event_queue.get(),
                    timeout=1.0
                )
                await self.event_dispatcher.dispatch(code, data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _handle_quote_update(self, quote_data):
        """Handle quote update from pumping mode"""
        # Broadcast to WebSocket clients
        if self.websocket_server:
            await self.websocket_server.broadcast_quote(quote_data)
```

## Security Considerations

1. **Authentication**: WebSocket connections must be authenticated
2. **Rate Limiting**: Implement rate limiting for quote updates
3. **Data Filtering**: Only send data that clients are authorized to see
4. **TLS/SSL**: Use secure WebSocket connections in production

## Performance Optimization

1. **Quote Throttling**: Limit quote updates per symbol (e.g., max 10/second)
2. **Batching**: Batch multiple updates before sending to clients
3. **Compression**: Use WebSocket compression for large data transfers
4. **Caching**: Cache static data to reduce API calls

## Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test full data flow from MT4 to WebSocket
3. **Load Tests**: Verify system can handle high-frequency updates
4. **Mock Mode**: Implement mock pumping for testing without MT4

## Deployment Considerations

1. **Monitoring**: Add metrics for pumping performance
2. **Logging**: Comprehensive logging for debugging
3. **Graceful Shutdown**: Properly close connections on shutdown
4. **Reconnection**: Automatic reconnection on connection loss

## Next Steps

1. Implement basic pumping mode bridge
2. Add WebSocket server
3. Create example client application
4. Add monitoring and metrics
5. Performance testing and optimization