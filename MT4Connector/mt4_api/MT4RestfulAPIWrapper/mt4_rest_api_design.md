# MT4ManagerAPI REST Architecture Design

## Overview

This document outlines a RESTful API design that wraps the MT4ManagerAPI, providing a modern web interface to interact with MetaTrader 4 servers.

## Core Design Principles

1. **Resource-oriented architecture**: All MT4 entities (accounts, trades, symbols) are modeled as resources
2. **Stateless communication**: Each request contains all necessary information
3. **Standard HTTP methods**: Using GET, POST, PUT, DELETE appropriately
4. **JSON payloads**: For both requests and responses
5. **Authentication**: Token-based authentication system
6. **Error handling**: Consistent error response format

## Authentication

```
POST /api/auth/login
```
- Request: `{ "username": "manager", "password": "secret" }`
- Response: `{ "token": "jwt-token-here", "expires_in": 3600 }`

## API Endpoints

### Accounts

#### Get All Accounts
```
GET /api/accounts
```
- Response: List of account objects

#### Get Account Details
```
GET /api/accounts/{login}
```
- Response: Detailed account information

#### Update Account
```
PUT /api/accounts/{login}
```
- Request: Account properties to update
- Response: Updated account object

### Trades

#### Get All Trades
```
GET /api/trades
```
- Query params: `login`, `symbol`, `from_date`, `to_date`, etc.
- Response: List of trade objects

#### Get Trade Details
```
GET /api/trades/{ticket}
```
- Response: Detailed trade information

#### Place New Order
```
POST /api/trades
```
- Request:
```json
{
  "login": 12345,
  "symbol": "EURUSD",
  "type": "buy",
  "volume": 0.1,
  "price": 1.1050,
  "sl": 1.0950,
  "tp": 1.1150,
  "comment": "API order"
}
```
- Response: Created trade object with ticket number

#### Modify Order
```
PUT /api/trades/{ticket}
```
- Request: Properties to modify (price, sl, tp)
- Response: Updated trade object

#### Close Order
```
DELETE /api/trades/{ticket}
```
- Query params: `volume` (optional, partial close)
- Response: Closure confirmation

### Symbols

#### Get All Symbols
```
GET /api/symbols
```
- Response: List of available symbols

#### Get Symbol Details
```
GET /api/symbols/{symbol}
```
- Response: Detailed symbol information including current price

### Market Data

#### Get Price History
```
GET /api/history/{symbol}
```
- Query params: `timeframe`, `from`, `to`, `count`
- Response: OHLC price data

#### Get Tick Data
```
GET /api/ticks/{symbol}
```
- Query params: `from`, `to`, `count`
- Response: Tick-by-tick price data

### Server Management

#### Get Server Status
```
GET /api/server/status
```
- Response: Server information and status

#### Server Configuration
```
GET /api/server/config
```
- Response: Server configuration settings

## Response Format

### Success Response
```json
{
  "status": "success",
  "data": { ... }
}
```

### Error Response
```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "Human readable error message"
}
```

## Implementation Notes

1. **Connection Pool**: Maintain a pool of MT4Manager connections for better performance
2. **Middleware**: 
   - Authentication middleware to validate tokens
   - Error handling middleware to format exceptions
3. **Rate Limiting**: Implement rate limiting to protect the API
4. **Logging**: Comprehensive logging of requests and MT4 operations
5. **Mock Mode**: Support a mock mode for testing without a live MT4 server

## Technology Stack Recommendations

1. **Backend Framework**:
   - Node.js with Express
   - Python with Flask/FastAPI
   - Java with Spring Boot
   
2. **Authentication**:
   - JWT tokens
   - OAuth2 for third-party integration
   
3. **Documentation**:
   - OpenAPI/Swagger for API documentation
   
4. **Deployment**:
   - Docker containers
   - Kubernetes for orchestration

## Sample Implementation (Python/Flask)

```python
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from mt4_api import MT4Manager

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'
jwt = JWTManager(app)

# Connection pool
mt4_connections = {}

@app.route('/api/auth/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    # Validate credentials
    if username == 'manager' and password == 'secret':
        access_token = create_access_token(identity=username)
        return jsonify(token=access_token, expires_in=3600)
    
    return jsonify(status='error', message='Invalid credentials'), 401

@app.route('/api/accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    mt4 = get_mt4_connection()
    accounts = mt4.get_users()
    return jsonify(status='success', data=accounts)

@app.route('/api/trades', methods=['POST'])
@jwt_required()
def place_order():
    data = request.json
    mt4 = get_mt4_connection()
    
    # Map type string to TradeCommand enum
    cmd_map = {'buy': 0, 'sell': 1, 'buylimit': 2, 'selllimit': 3, 'buystop': 4, 'sellstop': 5}
    cmd = cmd_map.get(data['type'].lower())
    
    ticket = mt4.place_order(
        login=data['login'],
        symbol=data['symbol'],
        cmd=cmd,
        volume=data['volume'],
        price=data['price'],
        sl=data.get('sl', 0),
        tp=data.get('tp', 0),
        comment=data.get('comment', '')
    )
    
    if ticket > 0:
        return jsonify(status='success', data={'ticket': ticket})
    
    return jsonify(status='error', message='Failed to place order'), 400

def get_mt4_connection():
    # Simplified connection management
    if 'default' not in mt4_connections:
        mt4 = MT4Manager()
        mt4.connect('mt4server.example.com', 443)
        mt4.login(1234, 'manager_password')
        mt4_connections['default'] = mt4
    
    return mt4_connections['default']

if __name__ == '__main__':
    app.run(debug=True)
```