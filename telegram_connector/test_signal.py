#!/usr/bin/env python3
"""
Test script for Telegram Connector webhook.
Sends a sample trading signal to verify the connector is working correctly.
"""

import requests
import json
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default webhook URL if not specified
DEFAULT_WEBHOOK_URL = "http://localhost:5001/webhook"

def send_test_signal(webhook_url=None):
    """Send a test trading signal to the webhook endpoint."""
    if not webhook_url:
        webhook_url = os.environ.get('WEBHOOK_URL', DEFAULT_WEBHOOK_URL)
    
    # Create a sample trading signal
    signal = {
        "symbol": "EURUSD",
        "side": "BUY",
        "price": 1.0765,
        "sl": 1.0730,
        "tp1": 1.0800,
        "tp2": 1.0850,
        "tp3": 1.0900,
        "timeframe": "H1",
        "strategy": "SoloTrend X Test",
        "risk": "1%",
        "timestamp": datetime.now().isoformat(),
        "source": "test_script"
    }
    
    try:
        print(f"\n{'='*80}")
        print(f"SENDING TEST SIGNAL TO: {webhook_url}")
        print(f"{'='*80}")
        
        print("\nSignal data:")
        print(json.dumps(signal, indent=2))
        
        # Send the POST request
        response = requests.post(
            webhook_url,
            json=signal,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        # Check the response
        if response.status_code == 200:
            print(f"\n✅ SUCCESS: Signal sent successfully (Status: {response.status_code})")
            print("\nResponse data:")
            try:
                print(json.dumps(response.json(), indent=2))
            except json.JSONDecodeError:
                print(response.text)
        else:
            print(f"\n❌ ERROR: Failed to send signal (Status: {response.status_code})")
            print("\nResponse data:")
            print(response.text)
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ CONNECTION ERROR: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    # Get webhook URL from command line argument if provided
    webhook_url = None
    if len(sys.argv) > 1:
        webhook_url = sys.argv[1]
    
    success = send_test_signal(webhook_url)
    sys.exit(0 if success else 1)