#!/usr/bin/env python3
"""
Test Phase 2.1: Mock Trading with Approve/Reject Buttons
Tests that signals sent to Telegram include interactive buttons
"""
import json
import time
import os
import sys

def test_phase2_buttons():
    """Test Phase 2.1 - Mock trading with approve/reject buttons"""
    print("=" * 60)
    print("PHASE 2.1 TEST - Mock Trading with Buttons")
    print("EA Signal → Telegram with Approve/Reject Buttons")
    print("=" * 60)
    
    # Signal file path
    signal_file = os.path.join("MT4Connector", "signals", "ea_signals.txt")
    
    print(f"\n1. Writing test signal to: {signal_file}")
    
    # Create test signal
    test_signal = [{
        "signal_id": f"phase2_test_{int(time.time())}",
        "type": "buy",
        "symbol": "EURUSD",
        "login": 12345,
        "volume": 0.1,
        "sl": 1.0950,
        "tp": 1.1050,
        "comment": "Phase 2 Button Test",
        "magic": 12345
    }]
    
    # Write signal to file
    with open(signal_file, 'w') as f:
        json.dump(test_signal, f, indent=2)
    
    print(f"✅ Signal written successfully")
    
    print("\n2. Expected Telegram Message Format:")
    print("┌─────────────────────────────────┐")
    print("│ 🔔 SIGNAL: EURUSD BUY           │")
    print("│ 💰 Price: Market                │")
    print("│ 📊 Volume: 0.1                  │")
    print("│ 🛑 Stop Loss: 1.0950           │")
    print("│ 🎯 Take Profit: 1.1050         │")
    print("│                                 │")
    print("│ [✅ Accept] [❌ Reject]         │")
    print("│      [⚙️ Custom]                │")
    print("└─────────────────────────────────┘")
    
    print("\n3. Button Functionality (Mock Mode):")
    print("   ✅ Accept - Executes trade with default settings")
    print("   ❌ Reject - Dismisses the signal")
    print("   ⚙️ Custom - Shows lot size options")
    
    print("\n4. To test the buttons:")
    print("   a) Ensure telegram_connector is running:")
    print("      cd telegram_connector && python3 app.py")
    print("   ")
    print("   b) Check your Telegram bot for the signal")
    print("   ")
    print("   c) Click the buttons to test functionality")
    print("   ")
    print("   d) Verify mock trades are executed")
    
    print("\n5. What to verify:")
    print("   - Signal appears with interactive buttons")
    print("   - Clicking 'Accept' shows trade execution message")
    print("   - Clicking 'Reject' dismisses the signal")
    print("   - Mock mode shows simulated ticket numbers")
    
    print("\n✅ Phase 2.1 test signal created!")
    print("   The system already has button functionality built-in.")
    print("   Just need to verify it works with our signals.")

if __name__ == "__main__":
    test_phase2_buttons()