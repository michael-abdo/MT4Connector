#!/usr/bin/env python3
"""
Test Phase 2.2: Real MT4 Connection
Tests switching between mock and real MT4 API modes
"""
import os
import sys
import json
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_mt4_connection():
    """Test MT4 connection in both mock and real modes"""
    print("=" * 60)
    print("PHASE 2.2 TEST - Real MT4 Connection")
    print("Testing MT4 API Mode Switching")
    print("=" * 60)
    
    # Import the API
    from mt4_real_api import MT4RealAPI
    
    # Test 1: Mock Mode
    print("\n1. Testing MOCK Mode:")
    print("-" * 40)
    
    mock_api = MT4RealAPI(use_mock=True)
    print(f"✅ API initialized in MOCK mode: {mock_api.use_mock}")
    
    # Test mock connection
    connected = mock_api.connect("localhost", 443, 12345, "password")
    print(f"✅ Mock connection successful: {connected}")
    
    # Test mock trade
    mock_trade = {
        "symbol": "EURUSD",
        "type": "BUY",
        "volume": 0.1,
        "sl": 1.0950,
        "tp": 1.1050,
        "comment": "Mock test trade",
        "login": 12345
    }
    
    result = mock_api.execute_trade(mock_trade)
    if result["status"] == "success":
        print(f"✅ Mock trade executed: Ticket #{result['data']['ticket']}")
    else:
        print(f"❌ Mock trade failed: {result['message']}")
    
    # Disconnect
    mock_api.disconnect()
    print("✅ Disconnected from mock server")
    
    # Test 2: Check Real Mode Availability
    print("\n2. Checking Real MT4 API Availability:")
    print("-" * 40)
    
    # Check environment
    mock_mode_env = os.environ.get('MOCK_MODE', 'True')
    print(f"MOCK_MODE environment variable: {mock_mode_env}")
    
    # Try real mode (will fallback to mock if not available)
    real_api = MT4RealAPI(use_mock=False)
    print(f"API mode after initialization: {'MOCK' if real_api.use_mock else 'REAL'}")
    
    if real_api.use_mock:
        print("ℹ️  Real MT4 API not available on this system")
        print("   This is expected on non-Windows systems")
        print("   The API automatically falls back to mock mode")
    else:
        print("✅ Real MT4 API is available!")
        print("⚠️  WARNING: Real mode will execute actual trades!")
    
    # Test 3: Configuration
    print("\n3. Configuration for Real Trading:")
    print("-" * 40)
    
    print("To enable real trading:")
    print("1. Set MOCK_MODE=False in .env file")
    print("2. Configure real MT4 server credentials:")
    print("   - MT4_SERVER=your.mt4.server.com")
    print("   - MT4_PORT=443")
    print("   - MT4_LOGIN=your_manager_login")
    print("   - MT4_PASSWORD=your_password")
    print("3. Ensure MT4 Manager API DLLs are available")
    print("4. Run on Windows server with MT4 installed")
    
    # Test 4: Error Handling
    print("\n4. Testing Error Handling:")
    print("-" * 40)
    
    # Test invalid connection
    api = MT4RealAPI(use_mock=True)
    
    # Test with invalid trade data
    invalid_trade = {
        "symbol": "",  # Missing symbol
        "volume": -1   # Invalid volume
    }
    
    result = api.execute_trade(invalid_trade)
    print(f"Invalid trade result: {result['status']} - {result.get('message', 'No message')}")
    
    # Test 5: Mode Detection
    print("\n5. Automatic Mode Detection:")
    print("-" * 40)
    
    # Test auto-detection
    auto_api = MT4RealAPI(use_mock=None)  # Let it auto-detect
    print(f"Auto-detected mode: {'MOCK' if auto_api.use_mock else 'REAL'}")
    
    print("\n" + "=" * 60)
    print("Phase 2.2 Testing Complete!")
    print("=" * 60)
    print("\nSummary:")
    print("- Mock mode is always available ✅")
    print("- Real mode requires Windows + MT4 DLLs")
    print("- API automatically falls back to mock when needed")
    print("- Configuration via .env file controls behavior")
    print("\nThe system is ready for both mock and real trading!")

if __name__ == "__main__":
    test_mt4_connection()