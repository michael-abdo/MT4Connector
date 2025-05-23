#!/usr/bin/env python3
"""
Run all tests for the MT4 Connector
This script discovers and runs all tests in the tests directory
"""

import os
import sys
import unittest
import argparse
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestRunner")

def run_all_tests(verbose=False):
    """
    Run all test cases in the tests directory
    
    Args:
        verbose (bool): If True, show detailed test results
        
    Returns:
        int: Number of failures
    """
    start_time = time.time()
    logger.info("Starting MT4 Connector test suite")
    
    # Get the tests directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    test_suite = loader.discover(test_dir, pattern="test_*.py")
    
    # Create a test runner
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    
    # Run the tests
    result = runner.run(test_suite)
    
    # Calculate and print metrics
    elapsed_time = time.time() - start_time
    success_count = result.testsRun - len(result.failures) - len(result.errors)
    
    logger.info("Test suite complete in %.2f seconds", elapsed_time)
    logger.info("Tests run: %d, Successes: %d, Failures: %d, Errors: %d", 
                result.testsRun, success_count, len(result.failures), len(result.errors))
    
    # Print individual failures and errors if any
    if result.failures or result.errors:
        if result.failures:
            logger.error("Failures:")
            for i, (test_case, traceback) in enumerate(result.failures, 1):
                logger.error("  %d. %s", i, test_case)
                if verbose:
                    logger.error("     %s", traceback)
                    
        if result.errors:
            logger.error("Errors:")
            for i, (test_case, traceback) in enumerate(result.errors, 1):
                logger.error("  %d. %s", i, test_case)
                if verbose:
                    logger.error("     %s", traceback)
    
    return len(result.failures) + len(result.errors)

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="Run MT4 Connector test suite")
    parser.add_argument('-v', '--verbose', action='store_true', help="Show detailed test output")
    parser.add_argument('-m', '--module', help="Run tests for a specific module only")
    args = parser.parse_args()
    
    # Run the test suite
    failures = run_all_tests(args.verbose)
    
    # Exit with number of failures as exit code
    return failures

if __name__ == "__main__":
    sys.exit(main())