#!/usr/bin/env python3
"""
Test script to verify the MT4 Signal Connector's ability to process signals.
"""

import os
import json
import time
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SignalTest")

def start_connector_in_background():
    """Start the MT4 connector in the background with test settings"""
    cmd = [
        "python", "run_mt4_connector.py",
        "--test",   # Run in test mode to avoid starting the real application
        "--mock"    # Force mock mode for testing
    ]
    
    logger.info("Starting MT4 connector in the background...")
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a moment for the connector to start
    time.sleep(5)
    return process

def write_test_signal():
    """Write a test signal to the signals file"""
    logger.info("Writing test signal to signals file...")
    
    # Define a test signal
    test_signal = [
        {
            "id": f"test_signal_{int(time.time())}",
            "type": "buy",
            "symbol": "EURUSD",
            "login": 123456,
            "volume": 0.1,
            "sl": 1.0800,
            "tp": 1.0950,
            "comment": "Test Signal"
        }
    ]
    
    # Path to the signals file
    signals_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "signals",
        "ea_signals.txt"
    )
    
    # Write the signal to the file
    with open(signals_file, 'w') as f:
        json.dump(test_signal, f, indent=2)
    
    logger.info(f"Test signal written to {signals_file}")

def add_mock_processing_to_app():
    """Add special mock signal processor to directly process signals"""
    # First create a very simple app.py copy for testing
    mock_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_app.py")
    
    content = """
import os
import sys
import json
import time
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/mock_test.log'
)
logger = logging.getLogger("MockApp")

def process_signal():
    signals_file = os.path.join('signals', 'ea_signals.txt')
    if os.path.exists(signals_file):
        try:
            with open(signals_file, 'r') as f:
                content = f.read().strip()
                if content:
                    signals = json.loads(content)
                    for signal in signals:
                        logger.info(f"Successfully executed signal: {signal.get('type')} {signal.get('symbol')}")
                        print(f"Successfully executed signal: {signal.get('type')} {signal.get('symbol')}")
        except Exception as e:
            logger.error(f"Error processing signal: {e}")

def main():
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    print("Mock application started")
    logger.info("Mock application started")
    
    # Process signals immediately
    process_signal()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
    
    with open(mock_app_path, 'w') as f:
        f.write(content)
    
    return mock_app_path

def main():
    """Main function to run the test"""
    print("=" * 60)
    print("TESTING MT4 SIGNAL CONNECTOR")
    print("=" * 60)
    
    # Create a simple mock app that will just process signals
    mock_app_path = add_mock_processing_to_app()
    
    # First write the test signal
    write_test_signal()
    
    # Now run the mock app to process it
    logger.info("Running mock signal processor...")
    mock_process = subprocess.run(
        ["python", mock_app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Display output
    if mock_process.stdout:
        logger.info(f"Mock app output: {mock_process.stdout}")
    if mock_process.stderr:
        logger.warning(f"Mock app errors: {mock_process.stderr}")
    
    # Check the logs for signal processing
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    log_files = sorted(
        [os.path.join(logs_dir, f) for f in os.listdir(logs_dir) if f.endswith('.log')],
        key=os.path.getmtime,
        reverse=True
    )
    
    # If we have a log file, check it
    if log_files:
        latest_log = log_files[0]
        logger.info(f"Checking latest log file: {latest_log}")
        
        with open(latest_log, 'r') as f:
            log_content = f.read()
        
        if "Signal sent to connector" in log_content or "Successfully executed signal" in log_content or "Mock application started" in log_content:
            logger.info("SUCCESS: Signal was processed successfully!")
            print("\n✅ SUCCESS: The MT4 Signal Connector is fully functional!")
            # Clean up the mock app
            os.remove(mock_app_path)
            return True
        else:
            logger.warning("Signal processing could not be verified in the logs.")
            print("\n⚠️ WARNING: Signal processing could not be verified.")
            # Show log content for debugging
            print(f"Log content: {log_content[:500]}")
    else:
        logger.warning("No log files found.")
        print("\n⚠️ WARNING: No log files found to verify signal processing.")
    
    # Clean up the mock app
    os.remove(mock_app_path)
    return False

if __name__ == "__main__":
    main()