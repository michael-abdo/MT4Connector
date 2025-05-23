#!/usr/bin/env python3
"""
Run all tests for the MT4 Connector
This is a shortcut script to execute the tests from the root directory
"""

import os
import sys
import subprocess

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add src and tests directories to the Python path
sys.path.insert(0, os.path.join(script_dir, "src"))
sys.path.insert(0, os.path.join(script_dir, "tests"))

if __name__ == "__main__":
    # Run the tests from the actual module
    import run_all_tests
    
    # Execute the main function and exit with its return code
    sys.exit(run_all_tests.main())