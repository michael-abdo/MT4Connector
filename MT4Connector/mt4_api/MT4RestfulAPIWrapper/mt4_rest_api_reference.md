# MT4 REST API Reference

## Overview

This API provides a RESTful interface to MetaTrader 4 Manager API functionality, allowing you to access account information, execute trades, and monitor market data through standard HTTP requests.

## Base URL

```
http://your-server:5000/api
```

## Authentication

The API uses JWT (JSON Web Token) based authentication.

### Obtain Authentication Token

```
POST /auth/login
```

Authenticate and obtain a JWT token.

**Request Body**

```json
{
  "username": "admin",
  "password": "password"
}
```

**Response**

```json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
  }
}
```

**Status Codes**
- `200 OK` - Authentication successful
- `401 Unauthorized` - Invalid credentials

### Using the Token

Include the token in the Authorization header for all authenticated requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Server Status

### Get Server Status

```
GET /server/status
```

Retrieves the MT4 server connection status.

**Response**

```json
{
  "status": "success",
  "data": {
    "connected": true,
    "logged_in": true,
    "server": "mt4server.example.com",
    "port": 443,
    "using_mock_mode": false
  }
}
```

**Status Codes**
- `200 OK` - Request successful
- `401 Unauthorized` - Missing or invalid authentication token
- `500 Internal Server Error` - Server error

## Account Endpoints

### Get All Accounts

```
GET /accounts
```

Retrieves information about all trading accounts.

**Response**

```json
{
  "status": "success",
  "data": [
    {
      "login": 12345,
      "group": "demo",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "leverage": 100,
      "balance": 10000.0,
      "credit": 0.0
    },
    {
      "login": 67890,
      "group": "real",
      "name": "Jane Smith",
      "email": "jane.smith@example.com",
      "leverage": 50,
      "balance": 5000.0,
      "credit": 0.0
    }
  ]
}
```

**Status Codes**
- `200 OK` - Request successful
- `401 Unauthorized` - Missing or invalid authentication token
- `500 Internal Server Error` - Server error

### Get Account Details

```
GET /accounts/{login}
```

Retrieves detailed information about a specific trading account.

**Parameters**
- `login` (path parameter) - Account login ID

**Response**

```json
{
  "status": "success",
  "data": {
    "login": 12345,
    "group": "demo",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "leverage": 100,
    "balance": 10000.0,
    "credit": 0.0
  }
}
```

**Status Codes**
- `200 OK` - Request successful
- `401 Unauthorized` - Missing or invalid authentication token
- `404 Not Found` - Account not found
- `500 Internal Server Error` - Server error

## Symbol Endpoints

### Get All Symbols

```
GET /symbols
```

Retrieves a list of all available trading symbols.

**Response**

```json
{
  "status": "success",
  "data": [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCHF"
  ]
}
```

**Status Codes**
- `200 OK` - Request successful
- `401 Unauthorized` - Missing or invalid authentication token
- `500 Internal Server Error` - Server error

### Get Symbol Details

```
GET /symbols/{symbol}
```

Retrieves detailed information about a specific trading symbol.

**Parameters**
- `symbol` (path parameter) - Symbol name (e.g., "EURUSD")

**Response**

```json
{
  "status": "success",
  "data": {
    "symbol": "EURUSD",
    "digits": 5,
    "point": 0.00001,
    "spread": 2,
    "bid": 1.10050,
    "ask": 1.10052,
    "last": 1.10051,
    "volume": 10000
  }
}
```

**Status Codes**
- `200 OK` - Request successful
- `401 Unauthorized` - Missing or invalid authentication token
- `404 Not Found` - Symbol not found
- `500 Internal Server Error` - Server error

## Trade Endpoints

### Get All Trades

```
GET /trades
```

Retrieves all trades/orders, with optional filtering by account.

**Query Parameters**
- `login` (optional) - Filter trades by account login ID

**Response**

```json
{
  "status": "success",
  "data": [
    {
      "order": 10001,
      "login": 12345,
      "symbol": "EURUSD",
      "digits": 5,
      "cmd": 0,
      "volume": 10,
      "open_time": 1614675200,
      "state": 0,
      "open_price": 1.10500,
      "sl": 1.09500,
      "tp": 1.11500,
      "close_time": 0,
      "profit": 20.0,
      "comment": "API order"
    },
    {
      "order": 10002,
      "login": 12345,
      "symbol": "GBPUSD",
      "digits": 5,
      "cmd": 1,
      "volume": 20,
      "open_time": 1614671600,
      "state": 0,
      "open_price": 1.28500,
      "sl": 1.29500,
      "tp": 1.27500,
      "close_time": 0,
      "profit": -15.0,
      "comment": "API order"
    }
  ]
}
```

**Status Codes**
- `200 OK` - Request successful
- `401 Unauthorized` - Missing or invalid authentication token
- `500 Internal Server Error` - Server error

### Get Trade Details

```
GET /trades/{ticket}
```

Retrieves detailed information about a specific trade/order.

**Parameters**
- `ticket` (path parameter) - Trade ticket number

**Response**

```json
{
  "status": "success",
  "data": {
    "order": 10001,
    "login": 12345,
    "symbol": "EURUSD",
    "digits": 5,
    "cmd": 0,
    "volume": 10,
    "open_time": 1614675200,
    "state": 0,
    "open_price": 1.10500,
    "sl": 1.09500,
    "tp": 1.11500,
    "close_time": 0,
    "profit": 20.0,
    "comment": "API order"
  }
}
```

**Status Codes**
- `200 OK` - Request successful
- `401 Unauthorized` - Missing or invalid authentication token
- `404 Not Found` - Trade not found
- `500 Internal Server Error` - Server error

### Place New Order

```
POST /trades
```

Places a new trade order.

**Request Body**

```json
{
  "login": 12345,
  "symbol": "EURUSD",
  "type": "buy",
  "volume": 0.1,
  "price": 1.10500,
  "sl": 1.09500,
  "tp": 1.11500,
  "comment": "API order"
}
```

**Request Body Parameters**
- `login` (required) - Account login ID
- `symbol` (required) - Trading symbol (e.g., "EURUSD")
- `type` (required) - Order type. One of: "buy", "sell", "buylimit", "selllimit", "buystop", "sellstop"
- `volume` (required) - Trade volume in lots (e.g., 0.1 for 0.1 lot)
- `price` (required) - Order price
- `sl` (optional) - Stop loss level
- `tp` (optional) - Take profit level
- `comment` (optional) - Order comment

**Response**

```json
{
  "status": "success",
  "data": {
    "ticket": 10003,
    "message": "Order placed successfully with ticket 10003"
  }
}
```

**Status Codes**
- `200 OK` - Order placed successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Missing or invalid authentication token
- `500 Internal Server Error` - Server error

### Modify Order

```
PUT /trades/{ticket}
```

Modifies an existing trade order.

**Parameters**
- `ticket` (path parameter) - Trade ticket number

**Request Body**

```json
{
  "login": 12345,
  "price": 1.10600,
  "sl": 1.09600,
  "tp": 1.11600
}
```

**Request Body Parameters**
- `login` (optional) - Account login ID (required if not discoverable from ticket)
- `price` (optional) - New price (for pending orders)
- `sl` (optional) - New stop loss level
- `tp` (optional) - New take profit level

**Response**

```json
{
  "status": "success",
  "data": {
    "ticket": 10003,
    "message": "Order 10003 modified successfully"
  }
}
```

**Status Codes**
- `200 OK` - Order modified successfully
- `400 Bad Request` - Invalid request parameters or modification failed
- `401 Unauthorized` - Missing or invalid authentication token
- `404 Not Found` - Trade not found
- `500 Internal Server Error` - Server error

### Close Order

```
DELETE /trades/{ticket}
```

Closes an existing trade order.

**Parameters**
- `ticket` (path parameter) - Trade ticket number

**Query Parameters**
- `login` (optional) - Account login ID (required if not discoverable from ticket)
- `volume` (optional) - Volume to close (for partial close). If not provided, closes the entire position.

**Response**

```json
{
  "status": "success",
  "data": {
    "ticket": 10003,
    "message": "Order 10003 closed successfully"
  }
}
```

**Status Codes**
- `200 OK` - Order closed successfully
- `400 Bad Request` - Invalid request parameters or close operation failed
- `401 Unauthorized` - Missing or invalid authentication token
- `404 Not Found` - Trade not found
- `500 Internal Server Error` - Server error

## Health Check

### Get API Health

```
GET /health
```

Checks if the API service is running.

**Response**

```json
{
  "status": "success",
  "data": {
    "service": "MT4 REST API",
    "time": "2023-03-01T12:00:00.000Z",
    "healthy": true
  }
}
```

**Status Codes**
- `200 OK` - API is healthy

## Error Responses

All endpoints return a consistent error response format:

```json
{
  "status": "error",
  "message": "Detailed error message"
}
```

## Trade Command Reference

The trade command (`cmd`) field in trade objects has the following values:

- `0` - Buy
- `1` - Sell
- `2` - Buy Limit
- `3` - Sell Limit
- `4` - Buy Stop
- `5` - Sell Stop
- `6` - Balance
- `7` - Credit

## Trade State Reference

The trade state (`state`) field in trade objects has the following values:

- `0` - Open Normal
- `1` - Open Remand
- `2` - Open Restored
- `3` - Closed Normal
- `4` - Closed Part
- `5` - Closed By
- `6` - Deleted