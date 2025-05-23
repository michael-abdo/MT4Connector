#!/usr/bin/env python3
"""
Test Signal Generator for MT4 Connector
Generates sample trading signals for testing the MT4 Connector and Telegram bot.
"""

import os
import json
import time
import argparse
import random
from datetime import datetime

# Default signal file path
SIGNALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals")
EA_SIGNAL_FILE = os.path.join(SIGNALS_DIR, "ea_signals.txt")

def generate_signal_id():
    """Generate a unique signal ID"""
    timestamp = int(time.time())
    random_part = random.randint(1000, 9999)
    return f"signal_{timestamp}_{random_part}"

def generate_buy_signal(symbol="EURUSD", volume=0.1, login=12345):
    """Generate a buy signal"""
    # Generate price based on symbol
    base_price = 1.10000 if "JPY" not in symbol else 110.000
    price = round(base_price + random.uniform(-0.01, 0.01), 5)
    
    # Generate SL and TP
    sl = round(price - (0.005 if "JPY" not in symbol else 0.5), 5)
    tp = round(price + (0.01 if "JPY" not in symbol else 1.0), 5)
    
    return {
        "id": generate_signal_id(),
        "type": "buy",
        "symbol": symbol,
        "login": login,
        "volume": volume,
        "sl": sl,
        "tp": tp,
        "comment": "Test Buy Signal",
        "price": price
    }

def generate_sell_signal(symbol="EURUSD", volume=0.1, login=12345):
    """Generate a sell signal"""
    # Generate price based on symbol
    base_price = 1.10000 if "JPY" not in symbol else 110.000
    price = round(base_price + random.uniform(-0.01, 0.01), 5)
    
    # Generate SL and TP
    sl = round(price + (0.005 if "JPY" not in symbol else 0.5), 5)
    tp = round(price - (0.01 if "JPY" not in symbol else 1.0), 5)
    
    return {
        "id": generate_signal_id(),
        "type": "sell",
        "symbol": symbol,
        "login": login,
        "volume": volume,
        "sl": sl,
        "tp": tp,
        "comment": "Test Sell Signal",
        "price": price
    }

def generate_pending_signal(signal_type, symbol="EURUSD", volume=0.1, login=12345):
    """Generate a pending order signal"""
    # Generate price based on symbol and type
    base_price = 1.10000 if "JPY" not in symbol else 110.000
    
    # Offset price based on order type
    if signal_type == "buy_limit":
        price = round(base_price - random.uniform(0.002, 0.005), 5)
        sl = round(price - (0.005 if "JPY" not in symbol else 0.5), 5)
        tp = round(price + (0.01 if "JPY" not in symbol else 1.0), 5)
    elif signal_type == "sell_limit":
        price = round(base_price + random.uniform(0.002, 0.005), 5)
        sl = round(price + (0.005 if "JPY" not in symbol else 0.5), 5)
        tp = round(price - (0.01 if "JPY" not in symbol else 1.0), 5)
    elif signal_type == "buy_stop":
        price = round(base_price + random.uniform(0.002, 0.005), 5)
        sl = round(price - (0.005 if "JPY" not in symbol else 0.5), 5)
        tp = round(price + (0.01 if "JPY" not in symbol else 1.0), 5)
    elif signal_type == "sell_stop":
        price = round(base_price - random.uniform(0.002, 0.005), 5)
        sl = round(price + (0.005 if "JPY" not in symbol else 0.5), 5)
        tp = round(price - (0.01 if "JPY" not in symbol else 1.0), 5)
    
    return {
        "id": generate_signal_id(),
        "type": signal_type,
        "symbol": symbol,
        "login": login,
        "volume": volume,
        "price": price,
        "sl": sl,
        "tp": tp,
        "comment": f"Test {signal_type.replace('_', ' ').title()} Signal"
    }

def generate_close_signal(ticket=12345, symbol="EURUSD", login=12345):
    """Generate a close signal"""
    return {
        "id": generate_signal_id(),
        "type": "close",
        "symbol": symbol,
        "login": login,
        "ticket": ticket,
        "comment": "Test Close Signal"
    }

def write_signal_to_file(signal, file_path=EA_SIGNAL_FILE):
    """Write a signal to the signal file"""
    # Make sure the signals directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write signal to file as array format
    with open(file_path, 'w') as f:
        json.dump([signal], f, indent=2)
    
    print(f"✅ Signal written to {file_path}:")
    print(json.dumps([signal], indent=2))
    
def write_signals_to_file(signals, file_path=EA_SIGNAL_FILE):
    """Write multiple signals to the signal file"""
    # Make sure the signals directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write signals to file (array format)
    with open(file_path, 'w') as f:
        json.dump(signals, f, indent=2)
    
    print(f"✅ {len(signals)} signals written to {file_path}:")
    print(json.dumps(signals, indent=2))

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate test signals for MT4 Connector")
    parser.add_argument("--type", choices=["buy", "sell", "buy_limit", "sell_limit", "buy_stop", "sell_stop", "close", "random"], 
                        default="random", help="Type of signal to generate")
    parser.add_argument("--symbol", default="EURUSD", help="Trading symbol")
    parser.add_argument("--volume", type=float, default=0.1, help="Trade volume in lots")
    parser.add_argument("--login", type=int, default=12345, help="MT4 account login")
    parser.add_argument("--ticket", type=int, default=12345, help="Ticket number for close signals")
    parser.add_argument("--file", default=EA_SIGNAL_FILE, help="Path to signal file")
    parser.add_argument("--batch", type=int, default=1, help="Number of signals to generate")
    
    args = parser.parse_args()
    
    # Generate signals
    signals = []
    
    for i in range(args.batch):
        if args.type == "random":
            # Choose a random signal type
            signal_type = random.choice(["buy", "sell", "buy_limit", "sell_limit", "buy_stop", "sell_stop", "close"])
        else:
            signal_type = args.type
        
        # Generate the selected signal type
        if signal_type == "buy":
            signal = generate_buy_signal(args.symbol, args.volume, args.login)
        elif signal_type == "sell":
            signal = generate_sell_signal(args.symbol, args.volume, args.login)
        elif signal_type in ["buy_limit", "sell_limit", "buy_stop", "sell_stop"]:
            signal = generate_pending_signal(signal_type, args.symbol, args.volume, args.login)
        elif signal_type == "close":
            signal = generate_close_signal(args.ticket, args.symbol, args.login)
        
        signals.append(signal)
    
    # Write to file
    if args.batch == 1:
        write_signal_to_file(signals[0], args.file)
    else:
        write_signals_to_file(signals, args.file)

if __name__ == "__main__":
    main()