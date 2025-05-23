#!/usr/bin/env python3
"""
Debug Signal Generator for MT4 Connector
Creates signals with debugging information to diagnose issues.
"""

import os
import json
import time
import random
import datetime

# Default signal file path
SIGNALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals")
EA_SIGNAL_FILE = os.path.join(SIGNALS_DIR, "ea_signals.txt")

def generate_signal():
    """Generate a debug test signal"""
    timestamp = int(time.time())
    random_part = random.randint(1000, 9999)
    
    signal = {
        "id": f"debug_signal_{timestamp}_{random_part}",
        "type": "buy",
        "symbol": "EURUSD",
        "login": 12345,
        "volume": 0.1,
        "sl": 1.09000,
        "tp": 1.11000,
        "comment": f"Debug Test Signal {datetime.datetime.now()}",
        "price": 1.10000,
        "debug_timestamp": timestamp
    }
    
    return signal

def write_signal():
    """Write a debug signal to the file"""
    signal = generate_signal()
    
    # Make sure the signals directory exists
    os.makedirs(os.path.dirname(EA_SIGNAL_FILE), exist_ok=True)
    
    # Write signal to file as array format
    with open(EA_SIGNAL_FILE, 'w') as f:
        json.dump([signal], f, indent=2)
    
    print(f"✅ Debug signal written to {EA_SIGNAL_FILE}:")
    print(json.dumps([signal], indent=2))
    
    # Wait a moment to let file system events propagate
    time.sleep(1)
    
    # Read the file back to verify
    print("\nVerifying file contents:")
    try:
        with open(EA_SIGNAL_FILE, 'r') as f:
            content = f.read()
            print(content)
            
            # Try parsing the JSON
            try:
                parsed = json.loads(content)
                print("\nJSON parsing successful")
                print(f"Signal count: {len(parsed)}")
            except json.JSONDecodeError as e:
                print(f"\nJSON parsing error: {e}")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    write_signal()