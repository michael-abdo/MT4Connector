"""
MT4 Manager API REST Interface

This module implements a Flask-based REST API that directly integrates
with the MT4 Manager API DLL using the MT4Manager wrapper class.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.security import check_password_hash
import jwt

# Import the MT4Manager class
from mt4_api import MT4Manager, TradeCommand

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mt4_rest_api.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configuration
class Config:
    MT4_SERVER = os.environ.get('MT4_SERVER', 'localhost')
    MT4_PORT = int(os.environ.get('MT4_PORT', '443'))
    MT4_LOGIN = int(os.environ.get('MT4_LOGIN', '0'))
    MT4_PASSWORD = os.environ.get('MT4_PASSWORD', '')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'develop-secret-key-change-in-production')
    TOKEN_EXPIRY = int(os.environ.get('TOKEN_EXPIRY', '3600'))  # 1 hour
    USE_MOCK_MODE = os.environ.get('USE_MOCK_MODE', 'False').lower() == 'true'
    API_ADMIN_USERNAME = os.environ.get('API_ADMIN_USERNAME', 'admin')
    API_ADMIN_PASSWORD = os.environ.get('API_ADMIN_PASSWORD', 'password')

# Flask application
app = Flask(__name__)
CORS(app)

# Connection pool
# In a production environment, this should be replaced with a proper connection pool manager
mt4_connections = {}
connection_last_used = {}
CONNECTION_TIMEOUT = 300  # 5 minutes

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if not token:
            return jsonify({'status': 'error', 'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            g.user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'status': 'error', 'message': 'Token has expired!'}), 401
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return jsonify({'status': 'error', 'message': 'Token is invalid!'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# MT4 Connection management
def get_mt4_connection():
    """
    Gets or creates an MT4Manager connection.
    Implements a simple connection pooling mechanism.
    """
    # Clean up old connections
    current_time = time.time()
    stale_connections = []
    for conn_id, last_used in connection_last_used.items():
        if current_time - last_used > CONNECTION_TIMEOUT:
            stale_connections.append(conn_id)
    
    for conn_id in stale_connections:
        if conn_id in mt4_connections:
            logger.info(f"Closing stale connection: {conn_id}")
            try:
                mt4_connections[conn_id].disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            del mt4_connections[conn_id]
            del connection_last_used[conn_id]
    
    # Use "default" connection id for now
    # In a multi-tenant application, this could be user-specific
    conn_id = "default"
    
    # Create new connection if needed
    if conn_id not in mt4_connections:
        logger.info(f"Creating new MT4 connection to {Config.MT4_SERVER}:{Config.MT4_PORT}")
        mt4 = MT4Manager(use_mock_mode=Config.USE_MOCK_MODE)
        
        # Connect and login
        if not mt4.connect(Config.MT4_SERVER, Config.MT4_PORT):
            raise Exception(f"Failed to connect to MT4 server {Config.MT4_SERVER}:{Config.MT4_PORT}")
        
        if not mt4.login(Config.MT4_LOGIN, Config.MT4_PASSWORD):
            raise Exception(f"Failed to login to MT4 server with login {Config.MT4_LOGIN}")
        
        mt4_connections[conn_id] = mt4
    
    # Update last used timestamp
    connection_last_used[conn_id] = time.time()
    
    return mt4_connections[conn_id]

# Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    auth = request.json
    
    if not auth or not auth.get('username') or not auth.get('password'):
        return jsonify({'status': 'error', 'message': 'Missing username or password'}), 400
    
    # For simplicity, using a single admin user defined in config
    # In production, should use a database with hashed passwords
    if auth.get('username') != Config.API_ADMIN_USERNAME or auth.get('password') != Config.API_ADMIN_PASSWORD:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
    
    # Generate token
    expiry = datetime.utcnow() + timedelta(seconds=Config.TOKEN_EXPIRY)
    token = jwt.encode(
        {
            'username': auth.get('username'),
            'exp': expiry
        }, 
        Config.SECRET_KEY
    )
    
    return jsonify({
        'status': 'success',
        'data': {
            'token': token,
            'expires_in': Config.TOKEN_EXPIRY
        }
    })

@app.route('/api/server/status', methods=['GET'])
@token_required
def server_status():
    """Get MT4 server status"""
    try:
        mt4 = get_mt4_connection()
        
        # For now, just return connected status
        # Could be extended with more MT4 server information
        return jsonify({
            'status': 'success',
            'data': {
                'connected': mt4.connected,
                'logged_in': mt4.logged_in,
                'server': Config.MT4_SERVER,
                'port': Config.MT4_PORT,
                'using_mock_mode': mt4.mock_mode
            }
        })
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/accounts', methods=['GET'])
@token_required
def get_accounts():
    """Get all user accounts"""
    try:
        mt4 = get_mt4_connection()
        users = mt4.get_users()
        
        return jsonify({
            'status': 'success',
            'data': users
        })
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/accounts/<int:login>', methods=['GET'])
@token_required
def get_account(login):
    """Get user account details"""
    try:
        mt4 = get_mt4_connection()
        user = mt4.get_user_by_login(login)
        
        if user is None:
            return jsonify({'status': 'error', 'message': f'Account {login} not found'}), 404
        
        return jsonify({
            'status': 'success',
            'data': user
        })
    except Exception as e:
        logger.error(f"Error getting account {login}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/symbols', methods=['GET'])
@token_required
def get_symbols():
    """Get all available symbols"""
    try:
        mt4 = get_mt4_connection()
        symbols = mt4.get_symbols()
        
        return jsonify({
            'status': 'success',
            'data': symbols
        })
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/symbols/<symbol>', methods=['GET'])
@token_required
def get_symbol(symbol):
    """Get symbol details"""
    try:
        mt4 = get_mt4_connection()
        symbol_info = mt4.get_symbol_info(symbol)
        
        if symbol_info is None:
            return jsonify({'status': 'error', 'message': f'Symbol {symbol} not found'}), 404
        
        return jsonify({
            'status': 'success',
            'data': symbol_info
        })
    except Exception as e:
        logger.error(f"Error getting symbol {symbol}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/trades', methods=['GET'])
@token_required
def get_trades():
    """Get trades with optional filtering"""
    try:
        mt4 = get_mt4_connection()
        
        # Get query parameters
        login = request.args.get('login', default=0, type=int)
        
        trades = mt4.get_trades(login)
        
        return jsonify({
            'status': 'success',
            'data': trades
        })
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/trades/<int:ticket>', methods=['GET'])
@token_required
def get_trade(ticket):
    """Get trade details by ticket number"""
    try:
        mt4 = get_mt4_connection()
        
        # Get all trades (could be optimized in production)
        trades = mt4.get_trades()
        
        # Find trade with matching ticket
        trade = next((t for t in trades if t['order'] == ticket), None)
        
        if trade is None:
            return jsonify({'status': 'error', 'message': f'Trade {ticket} not found'}), 404
        
        return jsonify({
            'status': 'success',
            'data': trade
        })
    except Exception as e:
        logger.error(f"Error getting trade {ticket}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/trades', methods=['POST'])
@token_required
def place_order():
    """Place a new trade order"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['login', 'symbol', 'type', 'volume', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400
        
        mt4 = get_mt4_connection()
        
        # Map order type string to TradeCommand enum
        type_map = {
            'buy': TradeCommand.OP_BUY,
            'sell': TradeCommand.OP_SELL,
            'buylimit': TradeCommand.OP_BUY_LIMIT,
            'selllimit': TradeCommand.OP_SELL_LIMIT,
            'buystop': TradeCommand.OP_BUY_STOP,
            'sellstop': TradeCommand.OP_SELL_STOP,
        }
        
        order_type = data['type'].lower()
        if order_type not in type_map:
            return jsonify({'status': 'error', 'message': f'Invalid order type: {order_type}'}), 400
        
        cmd = type_map[order_type]
        
        # Place the order
        ticket = mt4.place_order(
            login=data['login'],
            symbol=data['symbol'],
            cmd=cmd,
            volume=float(data['volume']),
            price=float(data['price']),
            sl=float(data.get('sl', 0)),
            tp=float(data.get('tp', 0)),
            comment=data.get('comment', '')
        )
        
        if ticket == 0:
            return jsonify({'status': 'error', 'message': 'Failed to place order'}), 400
        
        return jsonify({
            'status': 'success',
            'data': {
                'ticket': ticket,
                'message': f'Order placed successfully with ticket {ticket}'
            }
        })
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/trades/<int:ticket>', methods=['PUT'])
@token_required
def modify_order(ticket):
    """Modify an existing trade order"""
    try:
        data = request.json
        
        # Validate at least one modification field is present
        if not any(k in data for k in ['price', 'sl', 'tp']):
            return jsonify({'status': 'error', 'message': 'Missing modification parameters'}), 400
        
        # Get login from data or find it from the ticket
        login = data.get('login')
        if not login:
            mt4 = get_mt4_connection()
            trades = mt4.get_trades()
            trade = next((t for t in trades if t['order'] == ticket), None)
            
            if not trade:
                return jsonify({'status': 'error', 'message': f'Trade {ticket} not found'}), 404
            
            login = trade['login']
        
        mt4 = get_mt4_connection()
        
        # Modify the order
        success = mt4.modify_order(
            login=login,
            order=ticket,
            price=float(data['price']) if 'price' in data else None,
            sl=float(data['sl']) if 'sl' in data else None,
            tp=float(data['tp']) if 'tp' in data else None
        )
        
        if not success:
            return jsonify({'status': 'error', 'message': f'Failed to modify order {ticket}'}), 400
        
        return jsonify({
            'status': 'success',
            'data': {
                'ticket': ticket,
                'message': f'Order {ticket} modified successfully'
            }
        })
    except Exception as e:
        logger.error(f"Error modifying order {ticket}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/trades/<int:ticket>', methods=['DELETE'])
@token_required
def close_order(ticket):
    """Close an existing trade order"""
    try:
        # Get volume from query params for partial close
        volume = request.args.get('volume', default=0, type=float)
        
        # Get login (either from query params or find by ticket)
        login = request.args.get('login', default=0, type=int)
        if login == 0:
            mt4 = get_mt4_connection()
            trades = mt4.get_trades()
            trade = next((t for t in trades if t['order'] == ticket), None)
            
            if not trade:
                return jsonify({'status': 'error', 'message': f'Trade {ticket} not found'}), 404
            
            login = trade['login']
        
        mt4 = get_mt4_connection()
        
        # Close the order
        success = mt4.close_order(
            login=login,
            order=ticket,
            lots=volume
        )
        
        if not success:
            return jsonify({'status': 'error', 'message': f'Failed to close order {ticket}'}), 400
        
        return jsonify({
            'status': 'success',
            'data': {
                'ticket': ticket,
                'message': f'Order {ticket} closed successfully'
            }
        })
    except Exception as e:
        logger.error(f"Error closing order {ticket}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check endpoint that doesn't require authentication"""
    return jsonify({
        'status': 'success',
        'data': {
            'service': 'MT4 REST API',
            'time': datetime.utcnow().isoformat(),
            'healthy': True
        }
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # In production, use a proper WSGI server like gunicorn
    app.run(host='0.0.0.0', port=port, debug=False)