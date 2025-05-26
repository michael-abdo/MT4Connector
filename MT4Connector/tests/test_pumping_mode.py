"""
Test MT4 Pumping Mode Implementation
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mt4_pumping import MT4PumpingMode, PumpingCode, QuoteData, TradeData
from mt4_event_dispatcher import EventDispatcher, QuoteAggregator, TradeMonitor
from mt4_websocket import MT4WebSocketServer, ClientInfo


class TestMT4PumpingMode:
    """Test MT4 pumping mode functionality"""
    
    @pytest.fixture
    def pumping_mode(self):
        """Create pumping mode instance"""
        mock_manager = Mock()
        return MT4PumpingMode(mock_manager)
    
    def test_initialization(self, pumping_mode):
        """Test pumping mode initialization"""
        assert pumping_mode.pumping_active is False
        assert pumping_mode.event_queue is None
        assert len(pumping_mode.handlers) == 0
        assert pumping_mode.stats['events_received'] == 0
    
    @pytest.mark.asyncio
    async def test_start_pumping(self, pumping_mode):
        """Test starting pumping mode"""
        loop = asyncio.get_event_loop()
        
        # Mock the API call
        pumping_mode.mt4_manager = Mock()
        pumping_mode.mt4_manager.logged_in = True
        
        # Start pumping in mock mode
        result = pumping_mode.start(loop)
        assert result is True
        assert pumping_mode.pumping_active is True
        assert pumping_mode.event_queue is not None
        assert pumping_mode.stats['start_time'] is not None
        
        # Stop pumping
        pumping_mode.stop()
        assert pumping_mode.pumping_active is False
    
    def test_register_handler(self, pumping_mode):
        """Test handler registration"""
        handler = Mock()
        pumping_mode.register_handler(PumpingCode.UPDATE_BID_ASK, handler)
        
        assert PumpingCode.UPDATE_BID_ASK in pumping_mode.handlers
        assert handler in pumping_mode.handlers[PumpingCode.UPDATE_BID_ASK]
    
    @pytest.mark.asyncio
    async def test_event_processing(self, pumping_mode):
        """Test event processing"""
        loop = asyncio.get_event_loop()
        pumping_mode.event_queue = asyncio.Queue()
        pumping_mode.pumping_active = True
        
        # Register a handler
        handler_called = False
        async def test_handler(data):
            nonlocal handler_called
            handler_called = True
            assert data.symbol == "EURUSD"
        
        pumping_mode.handlers[PumpingCode.UPDATE_BID_ASK] = [test_handler]
        
        # Create test quote
        quote = QuoteData(
            symbol="EURUSD",
            bid=1.0850,
            ask=1.0852,
            spread=2.0,
            time=int(time.time()),
            server_time=datetime.now()
        )
        
        # Add event to queue
        await pumping_mode.event_queue.put((PumpingCode.UPDATE_BID_ASK, quote))
        
        # Process one event
        pumping_mode.pumping_active = False  # Stop after one event
        await pumping_mode.process_events()
        
        assert handler_called is True
        assert pumping_mode.stats['events_processed'] == 1


class TestEventDispatcher:
    """Test event dispatcher functionality"""
    
    @pytest.fixture
    def dispatcher(self):
        """Create event dispatcher instance"""
        return EventDispatcher()
    
    def test_initialization(self, dispatcher):
        """Test dispatcher initialization"""
        assert len(dispatcher.handlers) == 0
        assert len(dispatcher.quote_subscribers) == 0
        assert len(dispatcher.trade_subscribers) == 0
        assert dispatcher.stats['events_dispatched'] == 0
    
    def test_register_handler(self, dispatcher):
        """Test handler registration"""
        handler = Mock()
        dispatcher.register_handler(PumpingCode.UPDATE_BID_ASK, handler)
        
        assert handler in dispatcher.handlers[PumpingCode.UPDATE_BID_ASK]
    
    def test_subscribe_quotes(self, dispatcher):
        """Test quote subscription"""
        callback = Mock()
        dispatcher.subscribe_quotes("EURUSD", callback)
        
        assert callback in dispatcher.quote_subscribers["EURUSD"]
    
    @pytest.mark.asyncio
    async def test_dispatch_quote(self, dispatcher):
        """Test quote dispatching"""
        callback = Mock()
        dispatcher.subscribe_quotes("EURUSD", callback)
        
        quote = QuoteData(
            symbol="EURUSD",
            bid=1.0850,
            ask=1.0852,
            spread=2.0,
            time=int(time.time()),
            server_time=datetime.now()
        )
        
        await dispatcher.dispatch(PumpingCode.UPDATE_BID_ASK, quote)
        
        # Check stats
        assert dispatcher.stats['events_dispatched'] == 1
        assert dispatcher.stats['quotes_processed'] == 1
        
        # Check cache
        cached_quote = dispatcher.get_latest_quote("EURUSD")
        assert cached_quote is not None
        assert cached_quote.bid == 1.0850
    
    @pytest.mark.asyncio
    async def test_dispatch_trade(self, dispatcher):
        """Test trade dispatching"""
        callback = Mock()
        dispatcher.subscribe_trades(12345, callback)
        
        trade = TradeData(
            order=1001,
            login=12345,
            symbol="EURUSD",
            cmd=0,
            volume=0.1,
            open_price=1.0850,
            close_price=0,
            sl=1.0800,
            tp=1.0900,
            profit=0,
            state="open"
        )
        
        await dispatcher.dispatch(PumpingCode.UPDATE_TRADES, trade)
        
        # Check stats
        assert dispatcher.stats['trades_processed'] == 1
        
        # Check cache
        cached_trade = dispatcher.get_trade(1001)
        assert cached_trade is not None
        assert cached_trade.symbol == "EURUSD"


class TestQuoteAggregator:
    """Test quote aggregator functionality"""
    
    @pytest.fixture
    def aggregator(self):
        """Create quote aggregator instance"""
        return QuoteAggregator(max_updates_per_second=2)
    
    def test_rate_limiting(self, aggregator):
        """Test quote rate limiting"""
        quote1 = QuoteData(
            symbol="EURUSD",
            bid=1.0850,
            ask=1.0852,
            spread=2.0,
            time=int(time.time()),
            server_time=datetime.now()
        )
        
        # First quote should be allowed
        assert aggregator.add_quote(quote1) is True
        
        # Immediate second quote should be throttled
        quote2 = QuoteData(
            symbol="EURUSD",
            bid=1.0851,
            ask=1.0853,
            spread=2.0,
            time=int(time.time()),
            server_time=datetime.now()
        )
        assert aggregator.add_quote(quote2) is False
        
        # Check pending
        assert "EURUSD" in aggregator.pending_updates


class TestWebSocketServer:
    """Test WebSocket server functionality"""
    
    @pytest.fixture
    def ws_server(self):
        """Create WebSocket server instance"""
        return MT4WebSocketServer('localhost', 8765)
    
    def test_initialization(self, ws_server):
        """Test server initialization"""
        assert ws_server.host == 'localhost'
        assert ws_server.port == 8765
        assert len(ws_server.clients) == 0
        assert ws_server.stats['total_connections'] == 0
    
    @pytest.mark.asyncio
    async def test_client_registration(self, ws_server):
        """Test client registration"""
        # Mock WebSocket
        mock_ws = Mock()
        mock_ws.remote_address = ('127.0.0.1', 12345)
        
        await ws_server.register_client(mock_ws)
        
        # Check client is registered
        assert len(ws_server.clients) == 1
        client_id = list(ws_server.clients.keys())[0]
        client = ws_server.clients[client_id]
        
        assert client.websocket == mock_ws
        assert client.authenticated is False
        assert len(client.subscriptions) == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_quote(self, ws_server):
        """Test quote broadcasting"""
        # Add a mock client
        mock_ws = Mock()
        mock_ws.send = MagicMock(return_value=asyncio.Future())
        mock_ws.send.return_value.set_result(None)
        
        client_id = "test_client"
        client = ClientInfo(
            websocket=mock_ws,
            client_id=client_id,
            connected_at=datetime.now(),
            authenticated=True,
            subscriptions={"EURUSD"}
        )
        ws_server.clients[client_id] = client
        ws_server.symbol_subscribers["EURUSD"] = {client_id}
        
        # Broadcast quote
        quote = QuoteData(
            symbol="EURUSD",
            bid=1.0850,
            ask=1.0852,
            spread=2.0,
            time=int(time.time()),
            server_time=datetime.now()
        )
        
        await ws_server.broadcast_quote(quote)
        
        # Check message was sent
        mock_ws.send.assert_called_once()
        sent_data = mock_ws.send.call_args[0][0]
        
        # Verify JSON structure
        import json
        message = json.loads(sent_data)
        assert message['type'] == 'quote'
        assert message['data']['symbol'] == 'EURUSD'
        assert message['data']['bid'] == 1.0850


@pytest.mark.asyncio
async def test_integration():
    """Test integration of all components"""
    # Create components
    mock_manager = Mock()
    mock_manager.logged_in = True
    
    pumping_mode = MT4PumpingMode(mock_manager)
    dispatcher = EventDispatcher()
    ws_server = MT4WebSocketServer()
    
    # Connect components
    quotes_received = []
    
    async def quote_handler(quote):
        quotes_received.append(quote)
    
    # Register handlers
    pumping_mode.register_handler(PumpingCode.UPDATE_BID_ASK, 
                                 lambda data: asyncio.create_task(dispatcher.dispatch(PumpingCode.UPDATE_BID_ASK, data)))
    dispatcher.subscribe_all_quotes(quote_handler)
    
    # Start pumping
    loop = asyncio.get_event_loop()
    pumping_mode.start(loop)
    
    # Wait for mock data
    await asyncio.sleep(0.5)
    
    # Stop pumping
    pumping_mode.stop()
    
    # Verify quotes were received
    assert len(quotes_received) > 0
    assert all(isinstance(q, QuoteData) for q in quotes_received)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])