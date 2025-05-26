"""
MT4 Event Dispatcher
Handles distribution of pumping events to registered handlers and subscribers
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Set, Optional
from dataclasses import dataclass
from collections import defaultdict
import time
from datetime import datetime

from mt4_pumping import QuoteData, TradeData, PumpingCode

logger = logging.getLogger(__name__)

class EventDispatcher:
    """Dispatches pumping events to registered handlers"""
    
    def __init__(self):
        # Event handlers by event code
        self.handlers: Dict[int, List[Callable]] = defaultdict(list)
        
        # Quote subscribers by symbol
        self.quote_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Trade subscribers by login
        self.trade_subscribers: Dict[int, List[Callable]] = defaultdict(list)
        
        # Global subscribers (receive all events of a type)
        self.global_subscribers: Dict[int, List[Callable]] = defaultdict(list)
        
        # Quote cache for latest prices
        self.quote_cache: Dict[str, QuoteData] = {}
        
        # Trade cache by order ID
        self.trade_cache: Dict[int, TradeData] = {}
        
        # Statistics
        self.stats = {
            'events_dispatched': 0,
            'quotes_processed': 0,
            'trades_processed': 0,
            'errors': 0
        }
        
    def register_handler(self, event_code: int, handler: Callable) -> None:
        """Register a handler for a specific event code"""
        self.handlers[event_code].append(handler)
        logger.debug(f"Registered handler for event code {event_code}")
        
    def unregister_handler(self, event_code: int, handler: Callable) -> None:
        """Unregister a handler"""
        if event_code in self.handlers and handler in self.handlers[event_code]:
            self.handlers[event_code].remove(handler)
            
    def subscribe_quotes(self, symbol: str, callback: Callable) -> None:
        """Subscribe to quote updates for a specific symbol"""
        self.quote_subscribers[symbol].append(callback)
        logger.debug(f"Subscribed to quotes for {symbol}")
        
    def unsubscribe_quotes(self, symbol: str, callback: Callable) -> None:
        """Unsubscribe from quote updates"""
        if symbol in self.quote_subscribers and callback in self.quote_subscribers[symbol]:
            self.quote_subscribers[symbol].remove(callback)
            
    def subscribe_all_quotes(self, callback: Callable) -> None:
        """Subscribe to all quote updates"""
        self.global_subscribers[PumpingCode.UPDATE_BID_ASK].append(callback)
        
    def subscribe_trades(self, login: int, callback: Callable) -> None:
        """Subscribe to trade updates for a specific login"""
        self.trade_subscribers[login].append(callback)
        logger.debug(f"Subscribed to trades for login {login}")
        
    def subscribe_all_trades(self, callback: Callable) -> None:
        """Subscribe to all trade updates"""
        self.global_subscribers[PumpingCode.UPDATE_TRADES].append(callback)
        
    async def dispatch(self, event_code: int, data: Any) -> None:
        """Dispatch event to all registered handlers"""
        self.stats['events_dispatched'] += 1
        
        try:
            # Call registered handlers for this event code
            if event_code in self.handlers:
                await self._call_handlers(self.handlers[event_code], data)
                
            # Call global subscribers
            if event_code in self.global_subscribers:
                await self._call_handlers(self.global_subscribers[event_code], data)
                
            # Special handling for specific event types
            if event_code == PumpingCode.UPDATE_BID_ASK and isinstance(data, QuoteData):
                await self._handle_quote_update(data)
            elif event_code == PumpingCode.UPDATE_TRADES and isinstance(data, TradeData):
                await self._handle_trade_update(data)
                
        except Exception as e:
            logger.error(f"Error dispatching event {event_code}: {e}")
            self.stats['errors'] += 1
    
    async def _call_handlers(self, handlers: List[Callable], data: Any) -> None:
        """Call a list of handlers with the given data"""
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    # Run sync handlers in executor to avoid blocking
                    await asyncio.get_event_loop().run_in_executor(
                        None, handler, data
                    )
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
                self.stats['errors'] += 1
    
    async def _handle_quote_update(self, quote: QuoteData) -> None:
        """Handle quote updates with caching and distribution"""
        self.stats['quotes_processed'] += 1
        
        # Update cache
        self.quote_cache[quote.symbol] = quote
        
        # Notify symbol-specific subscribers
        if quote.symbol in self.quote_subscribers:
            await self._call_handlers(
                self.quote_subscribers[quote.symbol], 
                quote
            )
            
        logger.debug(f"Quote update: {quote.symbol} Bid: {quote.bid} Ask: {quote.ask}")
    
    async def _handle_trade_update(self, trade: TradeData) -> None:
        """Handle trade updates with caching and distribution"""
        self.stats['trades_processed'] += 1
        
        # Update cache
        self.trade_cache[trade.order] = trade
        
        # Notify login-specific subscribers
        if trade.login in self.trade_subscribers:
            await self._call_handlers(
                self.trade_subscribers[trade.login], 
                trade
            )
            
        logger.info(f"Trade update: Order #{trade.order} {trade.symbol} {trade.state}")
    
    def get_latest_quote(self, symbol: str) -> Optional[QuoteData]:
        """Get the latest cached quote for a symbol"""
        return self.quote_cache.get(symbol)
    
    def get_all_quotes(self) -> Dict[str, QuoteData]:
        """Get all cached quotes"""
        return self.quote_cache.copy()
    
    def get_trade(self, order_id: int) -> Optional[TradeData]:
        """Get a cached trade by order ID"""
        return self.trade_cache.get(order_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dispatcher statistics"""
        stats = self.stats.copy()
        stats['cached_quotes'] = len(self.quote_cache)
        stats['cached_trades'] = len(self.trade_cache)
        stats['quote_subscribers'] = sum(len(subs) for subs in self.quote_subscribers.values())
        stats['trade_subscribers'] = sum(len(subs) for subs in self.trade_subscribers.values())
        return stats


class QuoteAggregator:
    """Aggregates and manages quote data with throttling"""
    
    def __init__(self, max_updates_per_second: int = 10):
        self.max_updates_per_second = max_updates_per_second
        self.last_update_time: Dict[str, float] = {}
        self.pending_updates: Dict[str, QuoteData] = {}
        self.update_callbacks: List[Callable] = []
        
    def add_quote(self, quote: QuoteData) -> bool:
        """Add a quote, returns True if it should be broadcast"""
        current_time = time.time()
        last_time = self.last_update_time.get(quote.symbol, 0)
        
        # Check if we're within rate limit
        if current_time - last_time < 1.0 / self.max_updates_per_second:
            # Store as pending
            self.pending_updates[quote.symbol] = quote
            return False
        else:
            # Update immediately
            self.last_update_time[quote.symbol] = current_time
            self.pending_updates.pop(quote.symbol, None)
            return True
    
    async def process_pending(self):
        """Process pending quote updates"""
        while True:
            try:
                current_time = time.time()
                
                for symbol, quote in list(self.pending_updates.items()):
                    last_time = self.last_update_time.get(symbol, 0)
                    
                    if current_time - last_time >= 1.0 / self.max_updates_per_second:
                        # Send the update
                        self.last_update_time[symbol] = current_time
                        del self.pending_updates[symbol]
                        
                        # Notify callbacks
                        for callback in self.update_callbacks:
                            await callback(quote)
                
                # Small delay to avoid busy loop
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error processing pending quotes: {e}")


class TradeMonitor:
    """Monitors trade lifecycle and generates alerts"""
    
    def __init__(self):
        self.monitored_trades: Dict[int, TradeData] = {}
        self.alert_callbacks: List[Callable] = []
        
    async def on_trade_update(self, trade: TradeData):
        """Handle trade update and check for alerts"""
        order_id = trade.order
        
        # Check if this is a new trade
        if order_id not in self.monitored_trades:
            await self._alert("new_trade", trade, f"New trade opened: {trade.symbol}")
            
        else:
            old_trade = self.monitored_trades[order_id]
            
            # Check for state changes
            if old_trade.state != trade.state:
                if trade.state == "closed":
                    await self._alert("trade_closed", trade, 
                                    f"Trade closed: {trade.symbol} P/L: {trade.profit}")
                elif trade.state == "deleted":
                    await self._alert("trade_deleted", trade, 
                                    f"Trade deleted: {trade.symbol}")
                    
            # Check for modification
            elif (old_trade.sl != trade.sl or old_trade.tp != trade.tp):
                await self._alert("trade_modified", trade,
                                f"Trade modified: SL={trade.sl} TP={trade.tp}")
        
        # Update monitored trade
        self.monitored_trades[order_id] = trade
    
    async def _alert(self, alert_type: str, trade: TradeData, message: str):
        """Send alert to registered callbacks"""
        alert_data = {
            'type': alert_type,
            'trade': trade,
            'message': message,
            'timestamp': datetime.now()
        }
        
        for callback in self.alert_callbacks:
            try:
                await callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """Register a callback for trade alerts"""
        self.alert_callbacks.append(callback)