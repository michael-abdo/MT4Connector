"""
MT4 API Server

This module provides a REST API for the MT4 Manager API implementation.
It allows other components to interact with MT4 (mock or real) over HTTP.
"""

import os
import sys
import logging
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'MT4Connector', 'src'))

# Import the real API wrapper
try:
    from mt4_real_api import get_mt4_api
    mt4_api = get_mt4_api()
except ImportError:
    # Fallback to mock API
    from .mock_api import mt4_api

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mt4_api_server")

# Create Flask app
app = Flask(__name__)

@app.route('/api/status', methods=['GET'])
def status():
    """Get API status"""
    return jsonify({
        "status": "success",
        "message": "MT4 Mock API Server is running",
        "connected": mt4_api.connected,
        "server_info": mt4_api.server_info
    })

@app.route('/api/connect', methods=['POST'])
def connect():
    """Connect to MT4 server"""
    data = request.json
    server = data.get('server', 'localhost')
    port = int(data.get('port', 443))
    login = int(data.get('login', 12345))
    password = data.get('password', 'password')
    
    result = mt4_api.connect(server, port, login, password)
    
    return jsonify({
        "status": "success" if result else "error",
        "message": "Connected to MT4 server" if result else "Failed to connect to MT4 server",
        "connected": mt4_api.connected
    })

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from MT4 server"""
    result = mt4_api.disconnect()
    
    return jsonify({
        "status": "success" if result else "error",
        "message": "Disconnected from MT4 server" if result else "Failed to disconnect from MT4 server",
        "connected": mt4_api.connected
    })

@app.route('/api/trade', methods=['POST'])
def execute_trade():
    """Execute a trade"""
    data = request.json
    logger.info(f"Received trade request: {data}")
    
    result = mt4_api.execute_trade(data)
    
    return jsonify(result)

@app.route('/api/trade/<int:ticket>', methods=['GET'])
def get_trade(ticket):
    """Get trade details"""
    result = mt4_api.get_trade_by_ticket(ticket)
    
    return jsonify(result)

@app.route('/api/trade/<int:ticket>/modify', methods=['POST'])
def modify_trade(ticket):
    """Modify a trade"""
    data = request.json
    sl = data.get('sl')
    tp = data.get('tp')
    
    result = mt4_api.modify_trade(ticket, sl, tp)
    
    return jsonify(result)

@app.route('/api/trade/<int:ticket>/close', methods=['POST'])
def close_trade(ticket):
    """Close a trade"""
    result = mt4_api.close_trade(ticket)
    
    return jsonify(result)

@app.route('/api/account/<int:login>', methods=['GET'])
def get_account(login):
    """Get account information"""
    result = mt4_api.get_account_info(login)
    
    return jsonify(result)

@app.route('/api/account/<int:login>/trades', methods=['GET'])
def get_trades(login):
    """Get account trades"""
    open_only = request.args.get('open_only', 'true').lower() == 'true'
    
    result = mt4_api.get_trades(login, open_only)
    
    return jsonify(result)

@app.route('/api/price/<symbol>', methods=['GET'])
def get_price(symbol):
    """Get current price for a symbol"""
    result = mt4_api.get_price(symbol)
    
    return jsonify(result)

if __name__ == '__main__':
    # Auto-connect to MT4 server
    mt4_api.connect("localhost", 443, 12345, "password")
    
    # Get port from environment or use default
    port = int(os.environ.get('MT4_API_PORT', 5003))
    
    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=True)