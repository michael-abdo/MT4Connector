#!/usr/bin/env python3
"""
Run tests with proper environment configuration loaded from .env.test
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Colors for output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

def main():
    print(f"{YELLOW}Loading test environment configuration...{NC}")
    
    # Load environment from .env.test
    env_file = Path(__file__).parent / '.env.test'
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"{GREEN}Loaded environment from .env.test{NC}")
    else:
        print(f"{RED}Warning: .env.test not found!{NC}")
    
    # Set critical environment variables explicitly
    os.environ['MOCK_MODE'] = 'True'
    os.environ['PYTHONPATH'] = f"{Path.cwd()}/MT4Connector/src:{Path.cwd()}/telegram_connector"
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['MT4_SERVER'] = 'localhost'
    os.environ['MT4_PORT'] = '443'
    
    # Print loaded configuration
    print(f"{GREEN}Environment variables set:{NC}")
    print(f"  MOCK_MODE={os.environ.get('MOCK_MODE')}")
    print(f"  PYTHONPATH={os.environ.get('PYTHONPATH')}")
    print(f"  DATABASE_URL={os.environ.get('DATABASE_URL')}")
    print(f"  MT4_SERVER={os.environ.get('MT4_SERVER')}")
    print(f"  MT4_PORT={os.environ.get('MT4_PORT')}")
    
    # Test files to run
    test_files = [
        'MT4Connector/tests/test_config.py',
        'MT4Connector/tests/test_integration.py',
        'MT4Connector/tests/test_telegram_bot.py',
        'MT4Connector/tests/test_mt4_real_api.py',
        'MT4Connector/tests/test_signal_writer.py'
    ]
    
    # Run pytest
    print(f"\n{YELLOW}Running tests...{NC}")
    cmd = [sys.executable, '-m', 'pytest'] + test_files + ['-v', '--tb=short']
    
    result = subprocess.run(cmd, env=os.environ)
    
    # Summary
    if result.returncode == 0:
        print(f"\n{GREEN}All tests passed!{NC}")
    else:
        print(f"\n{RED}Some tests failed. Exit code: {result.returncode}{NC}")
    
    return result.returncode

if __name__ == '__main__':
    sys.exit(main())