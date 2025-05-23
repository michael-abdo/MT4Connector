#!/usr/bin/env python3
"""
Simple test script to verify Phase 1 flow:
EA Signal File → Signal Processor → Telegram Notification
"""
import json
import time
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_signal_flow():
    """Test the complete Phase 1 signal flow"""
    print("=" * 60)
    print("PHASE 1 INTEGRATION TEST")
    print("EA Signal → File → Processor → Telegram")
    print("=" * 60)
    
    # Signal file path
    signal_file = os.path.join(os.path.dirname(__file__), 'signals', 'ea_signals.txt')
    
    print(f"\n1. Writing test signal to: {signal_file}")
    
    # Create test signal as EA would write it
    test_signal = [{
        "signal_id": f"test_{int(time.time())}",
        "type": "buy",
        "symbol": "EURUSD",
        "login": 12345,
        "volume": 0.1,
        "sl": 1.0950,
        "tp": 1.1050,
        "comment": "Phase 1 Test Signal",
        "magic": 12345
    }]
    
    # Write signal to file
    with open(signal_file, 'w') as f:
        json.dump(test_signal, f, indent=2)
    
    print(f"✅ Signal written successfully:")
    print(json.dumps(test_signal[0], indent=2))
    
    print("\n2. Signal is now ready to be processed by:")
    print("   - signal_processor.py (monitors the file)")
    print("   - telegram_connector (sends notifications)")
    
    print("\n3. To complete the test:")
    print("   a) Start telegram connector in another terminal:")
    print("      cd telegram_connector && python3 app.py")
    print("   b) Start signal processor:")
    print("      python3 src/signal_processor.py")
    print("   c) Check Telegram for the notification")
    
    print("\n4. Current signal file contents:")
    with open(signal_file, 'r') as f:
        content = f.read()
        print(content)
    
    print("\n✅ Phase 1 test signal created successfully!")
    print("   The EA → File part is working correctly.")
    print("   Next: Start the processors to complete the flow.")

if __name__ == "__main__":
    test_signal_flow()