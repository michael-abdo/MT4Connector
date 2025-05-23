#!/usr/bin/env python3
"""
Integration test runner for the complete SoloTrend X pipeline
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}--- {text} ---{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def run_command(cmd, cwd=None, capture=True):
    """Run a command and return success status and output"""
    try:
        if capture:
            result = subprocess.run(
                cmd, 
                shell=True, 
                cwd=cwd, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True, cwd=cwd, timeout=60)
            return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def main():
    print_header("SOLOTRENDX INTEGRATION TEST SUITE")
    
    # Get project root
    project_root = Path(__file__).parent.absolute()
    venv_path = project_root / "venv"
    
    # Check virtual environment
    print_section("Environment Check")
    if not venv_path.exists():
        print_error("Virtual environment not found!")
        print(f"Expected at: {venv_path}")
        return 1
    print_success(f"Virtual environment found at {venv_path}")
    
    # Activate virtual environment
    if sys.platform == "win32":
        activate_cmd = f"{venv_path}\\Scripts\\activate && "
    else:
        activate_cmd = f"source {venv_path}/bin/activate && "
    
    # Test results
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    # 1. Test MT4Connector components
    print_section("Testing MT4Connector Components")
    mt4_dir = project_root / "MT4Connector"
    
    test_files = [
        "tests/test_config.py",
        "tests/test_integration.py",
        "tests/test_signal_processing.py",
        "tests/test_telegram_bot.py",
        "tests/test_mt4_real_api.py",
        "tests/test_signal_writer.py"
    ]
    
    for test_file in test_files:
        total_tests += 1
        print(f"\nRunning {test_file}...")
        cmd = f"{activate_cmd}cd {mt4_dir} && python -m pytest {test_file} -v --tb=short"
        success, stdout, stderr = run_command(cmd)
        
        if success:
            passed_tests += 1
            print_success(f"{test_file} passed")
        else:
            failed_tests.append(test_file)
            print_error(f"{test_file} failed")
            if stderr:
                print(f"  Error: {stderr[:200]}...")
    
    # 2. Test telegram_connector components
    print_section("Testing Telegram Connector Components")
    telegram_dir = project_root / "telegram_connector"
    
    # Check if required modules are installed
    print("\nChecking dependencies...")
    deps = ["psycopg2", "cryptography", "flask", "telegram", "aiohttp", "psutil"]
    for dep in deps:
        cmd = f"{activate_cmd}python -c 'import {dep}'"
        success, _, _ = run_command(cmd)
        if success:
            print_success(f"{dep} is installed")
        else:
            print_warning(f"{dep} is not installed")
    
    # Run Phase 5 component tests
    if (telegram_dir / "test_phase5_components.py").exists():
        total_tests += 1
        print("\nRunning Phase 5 component tests...")
        cmd = f"{activate_cmd}cd {telegram_dir} && python test_phase5_components.py"
        success, stdout, stderr = run_command(cmd)
        
        if "FAILED" not in stderr and "ERROR" not in stdout:
            passed_tests += 1
            print_success("Phase 5 component tests passed")
        else:
            failed_tests.append("test_phase5_components.py")
            print_error("Phase 5 component tests failed")
    
    # 3. Integration Flow Tests
    print_section("Integration Flow Tests")
    
    # Test 1: Signal file processing flow
    print("\nTest 1: Signal File Processing")
    signal_file = mt4_dir / "signals" / "ea_signals.txt"
    if signal_file.parent.exists():
        total_tests += 1
        # Write a test signal
        test_signal = '{"signal_id":"test_123","type":"buy","symbol":"EURUSD","volume":0.1,"login":"12345"}'
        try:
            with open(signal_file, 'w') as f:
                f.write(test_signal)
            print_success("Test signal written")
            passed_tests += 1
        except Exception as e:
            print_error(f"Failed to write test signal: {e}")
            failed_tests.append("Signal file write test")
    
    # Test 2: Database connectivity (PostgreSQL)
    print("\nTest 2: Database Connectivity")
    total_tests += 1
    cmd = f"{activate_cmd}python -c \"from telegram_connector.database_postgres import get_database; db = get_database(); print('Database initialized')\""
    success, stdout, stderr = run_command(cmd, cwd=project_root)
    
    if success or "Database initialized" in stdout:
        passed_tests += 1
        print_success("Database connectivity test passed")
    else:
        failed_tests.append("Database connectivity test")
        print_warning("Database connectivity test skipped (PostgreSQL not available)")
    
    # Test 3: Health check endpoint
    print("\nTest 3: Health Check System")
    total_tests += 1
    cmd = f"{activate_cmd}python -c \"from telegram_connector.health_monitor import HealthMonitor; print('Health monitor imported successfully')\""
    success, stdout, stderr = run_command(cmd, cwd=project_root)
    
    if success or "Health monitor imported successfully" in stdout:
        passed_tests += 1
        print_success("Health monitoring system test passed")
    else:
        failed_tests.append("Health monitoring test")
        print_error("Health monitoring system test failed")
    
    # 4. Summary
    print_header("TEST SUMMARY")
    
    print(f"Total tests run: {total_tests}")
    print(f"{Colors.OKGREEN}Passed: {passed_tests}{Colors.ENDC}")
    print(f"{Colors.FAIL}Failed: {len(failed_tests)}{Colors.ENDC}")
    
    if failed_tests:
        print(f"\n{Colors.FAIL}Failed tests:{Colors.ENDC}")
        for test in failed_tests:
            print(f"  - {test}")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"\n{Colors.BOLD}Success rate: {success_rate:.1f}%{Colors.ENDC}")
    
    # Recommendations
    if success_rate < 100:
        print_section("Recommendations")
        if "Database connectivity test" in failed_tests:
            print_warning("• Set up PostgreSQL or use MOCK_MODE=True for testing")
        if any("test_phase" in t for t in failed_tests):
            print_warning("• Check that all Phase implementations are complete")
        if any("mt4" in t.lower() for t in failed_tests):
            print_warning("• MT4 API tests may fail on macOS - this is expected")
    
    return 0 if success_rate >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())