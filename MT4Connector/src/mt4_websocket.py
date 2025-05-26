"""
MT4 WebSocket Server
Provides real-time data streaming to WebSocket clients
"""

import asyncio
import json
import logging
import time
from typing import Set, Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
import jwt
from functools import wraps

from mt4_pumping import QuoteData, TradeData
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class ClientInfo:
    """Information about connected WebSocket client"""
    websocket: WebSocketServerProtocol
    client_id: str
    connected_at: datetime
    authenticated: bool = False
    user_login: Optional[int] = None
    subscriptions: Set[str] = None
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()

class MT4WebSocketServer:
    """WebSocket server for real-time MT4 data distribution"""
    
    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, ClientInfo] = {}
        self.symbol_subscribers: Dict[str, Set[str]] = {}  # symbol -> client_ids
        self.authenticated_clients: Set[str] = set()
        self.server = None
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'messages_sent': 0,
            'errors': 0,
            'start_time': None
        }
        
    async def start(self):
        """Start the WebSocket server"""
        self.stats['start_time'] = time.time()
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
        
    async def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}_{time.time()}"
        client_info = ClientInfo(
            websocket=websocket,
            client_id=client_id,
            connected_at=datetime.now()
        )
        
        self.clients[client_id] = client_info
        self.stats['total_connections'] += 1
        
        logger.info(f"Client connected: {client_id}")
        
        try:
            # Send welcome message
            await self.send_to_client(client_id, {
                'type': 'welcome',
                'client_id': client_id,
                'server_time': datetime.now().isoformat(),
                'require_auth': True
            })
            
            # Handle messages
            async for message in websocket:
                await self.process_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            self.stats['errors'] += 1
        finally:
            await self.disconnect_client(client_id)
    
    async def process_message(self, client_id: str, message: str):
        """Process message from client"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            client = self.clients.get(client_id)
            if not client:
                return
            
            # Handle authentication first
            if action == 'auth':
                await self.handle_auth(client_id, data)
                return
            
            # All other actions require authentication
            if not client.authenticated:
                await self.send_to_client(client_id, {
                    'type': 'error',
                    'message': 'Authentication required'
                })
                return
            
            # Handle authenticated actions
            if action == 'subscribe':
                await self.handle_subscribe(client_id, data)
            elif action == 'unsubscribe':
                await self.handle_unsubscribe(client_id, data)
            elif action == 'get_quotes':
                await self.handle_get_quotes(client_id, data)
            elif action == 'ping':
                await self.send_to_client(client_id, {'type': 'pong'})
            else:
                await self.send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Unknown action: {action}'
                })
                
        except json.JSONDecodeError:
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': 'Invalid JSON'
            })
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': 'Internal server error'
            })
    
    async def handle_auth(self, client_id: str, data: Dict):
        """Handle authentication request"""
        token = data.get('token')
        
        if not token:
            await self.send_to_client(client_id, {
                'type': 'auth_response',
                'success': False,
                'message': 'Token required'
            })
            return
        
        try:
            # Verify JWT token
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            user_login = payload.get('login')
            
            # Update client info
            client = self.clients[client_id]
            client.authenticated = True
            client.user_login = user_login
            self.authenticated_clients.add(client_id)
            
            await self.send_to_client(client_id, {
                'type': 'auth_response',
                'success': True,
                'user_login': user_login
            })
            
            logger.info(f"Client {client_id} authenticated as login {user_login}")
            
        except jwt.ExpiredSignatureError:
            await self.send_to_client(client_id, {
                'type': 'auth_response',
                'success': False,
                'message': 'Token expired'
            })
        except Exception as e:
            logger.error(f"Auth error for {client_id}: {e}")
            await self.send_to_client(client_id, {
                'type': 'auth_response',
                'success': False,
                'message': 'Authentication failed'
            })
    
    async def handle_subscribe(self, client_id: str, data: Dict):
        """Handle subscription request"""
        symbols = data.get('symbols', [])
        
        if not symbols:
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': 'No symbols specified'
            })
            return
        
        client = self.clients[client_id]
        added_symbols = []
        
        for symbol in symbols:
            if symbol not in client.subscriptions:
                client.subscriptions.add(symbol)
                
                # Add to symbol subscribers
                if symbol not in self.symbol_subscribers:
                    self.symbol_subscribers[symbol] = set()
                self.symbol_subscribers[symbol].add(client_id)
                
                added_symbols.append(symbol)
        
        await self.send_to_client(client_id, {
            'type': 'subscription_update',
            'action': 'subscribed',
            'symbols': added_symbols,
            'all_subscriptions': list(client.subscriptions)
        })
        
        logger.debug(f"Client {client_id} subscribed to: {', '.join(added_symbols)}")
    
    async def handle_unsubscribe(self, client_id: str, data: Dict):
        """Handle unsubscription request"""
        symbols = data.get('symbols', [])
        
        client = self.clients[client_id]
        removed_symbols = []
        
        for symbol in symbols:
            if symbol in client.subscriptions:
                client.subscriptions.remove(symbol)
                
                # Remove from symbol subscribers
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(client_id)
                    if not self.symbol_subscribers[symbol]:
                        del self.symbol_subscribers[symbol]
                
                removed_symbols.append(symbol)
        
        await self.send_to_client(client_id, {
            'type': 'subscription_update',
            'action': 'unsubscribed',
            'symbols': removed_symbols,
            'all_subscriptions': list(client.subscriptions)
        })
    
    async def handle_get_quotes(self, client_id: str, data: Dict):
        """Handle request for current quotes"""
        symbols = data.get('symbols', [])
        
        # This would need to be connected to the quote cache
        # For now, sending empty response
        await self.send_to_client(client_id, {
            'type': 'quotes_snapshot',
            'quotes': {}  # Would be populated from quote cache
        })
    
    async def disconnect_client(self, client_id: str):
        """Clean up disconnected client"""
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        # Remove from all subscriptions
        for symbol in client.subscriptions:
            if symbol in self.symbol_subscribers:
                self.symbol_subscribers[symbol].discard(client_id)
                if not self.symbol_subscribers[symbol]:
                    del self.symbol_subscribers[symbol]
        
        # Remove from authenticated clients
        self.authenticated_clients.discard(client_id)
        
        # Remove client
        del self.clients[client_id]
        
        logger.info(f"Client {client_id} disconnected and cleaned up")
    
    async def send_to_client(self, client_id: str, data: Dict):
        """Send message to specific client"""
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        try:
            message = json.dumps(data)
            await client.websocket.send(message)
            self.stats['messages_sent'] += 1
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            self.stats['errors'] += 1
    
    async def broadcast_quote(self, quote: QuoteData):
        """Broadcast quote update to subscribed clients"""
        symbol = quote.symbol
        
        # Get subscribed clients
        if symbol not in self.symbol_subscribers:
            return
        
        # Prepare message
        message = json.dumps({
            'type': 'quote',
            'data': {
                'symbol': quote.symbol,
                'bid': quote.bid,
                'ask': quote.ask,
                'spread': quote.spread,
                'time': quote.time,
                'server_time': quote.server_time.isoformat()
            }
        })
        
        # Send to all subscribed clients
        disconnected_clients = []
        
        for client_id in self.symbol_subscribers[symbol]:
            if client_id in self.clients:
                client = self.clients[client_id]
                try:
                    await client.websocket.send(message)
                    self.stats['messages_sent'] += 1
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect_client(client_id)
    
    async def broadcast_trade(self, trade: TradeData, user_login: int):
        """Broadcast trade update to relevant clients"""
        # Prepare message
        message = json.dumps({
            'type': 'trade',
            'data': {
                'order': trade.order,
                'login': trade.login,
                'symbol': trade.symbol,
                'cmd': trade.cmd,
                'volume': trade.volume,
                'open_price': trade.open_price,
                'close_price': trade.close_price,
                'sl': trade.sl,
                'tp': trade.tp,
                'profit': trade.profit,
                'state': trade.state
            }
        })
        
        # Send to clients authenticated with this login
        for client_id, client in self.clients.items():
            if client.authenticated and client.user_login == user_login:
                try:
                    await client.websocket.send(message)
                    self.stats['messages_sent'] += 1
                except Exception as e:
                    logger.error(f"Error broadcasting trade to client {client_id}: {e}")
    
    async def broadcast_notification(self, notification: Dict, user_login: Optional[int] = None):
        """Broadcast notification to clients"""
        message = json.dumps({
            'type': 'notification',
            'data': notification
        })
        
        # Send to specific user or all authenticated clients
        for client_id, client in self.clients.items():
            if client.authenticated:
                if user_login is None or client.user_login == user_login:
                    try:
                        await client.websocket.send(message)
                        self.stats['messages_sent'] += 1
                    except Exception as e:
                        logger.error(f"Error broadcasting notification to client {client_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket server statistics"""
        stats = self.stats.copy()
        stats['connected_clients'] = len(self.clients)
        stats['authenticated_clients'] = len(self.authenticated_clients)
        stats['total_subscriptions'] = sum(len(subs) for subs in self.symbol_subscribers.values())
        
        if stats['start_time']:
            stats['uptime_seconds'] = time.time() - stats['start_time']
            
        return stats