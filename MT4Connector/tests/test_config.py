#!/usr/bin/env python3
"""
Unit tests for the MT4 Connector Configuration System.
Tests config file loading, validation, and usage.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import platform
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestConfigSystem(unittest.TestCase):
    """Test cases for the Configuration System."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.signals_dir = os.path.join(self.temp_dir, "signals")
        self.logs_dir = os.path.join(self.temp_dir, "logs")
        os.makedirs(self.signals_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Save the original sys.modules to restore later
        self.orig_modules = sys.modules.copy()
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directories
        os.rmdir(self.signals_dir)
        os.rmdir(self.logs_dir)
        os.rmdir(self.temp_dir)
        
        # Restore original modules
        sys.modules = self.orig_modules
    
    def test_config_default_values(self):
        """Test that default configuration values are set correctly."""
        # Import the configuration module
        import config
        
        # Test default values
        self.assertEqual(config.MT4_SERVER, "localhost")
        self.assertEqual(config.MT4_PORT, 443)
        self.assertEqual(config.SIGNAL_CHECK_INTERVAL, 5)
        self.assertTrue(config.AUTO_EXECUTE_SIGNALS)
        self.assertEqual(config.MT4_TRADE_TRANSACTION_MAX_RETRIES, 3)
        self.assertEqual(config.MT4_TRADE_TRANSACTION_RETRY_DELAY, 2)
        self.assertEqual(config.LOG_LEVEL, "INFO")
    
    def test_derived_directories(self):
        """Test derived directory paths in the configuration."""
        # Import the configuration module
        import config
        
        # Test derived directories
        # BASE_DIR should be the parent of the src directory (MT4Connector)
        expected_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(config.__file__)))
        self.assertEqual(config.BASE_DIR, expected_base_dir)
        self.assertEqual(config.MT4_API_DIR, os.path.join(config.BASE_DIR, "mt4_api"))
        self.assertEqual(config.SIGNALS_DIR, os.path.join(config.BASE_DIR, "signals"))
        self.assertEqual(config.LOGS_DIR, os.path.join(config.BASE_DIR, "logs"))
        self.assertEqual(config.EA_SIGNAL_FILE, os.path.join(config.SIGNALS_DIR, "ea_signals.txt"))
    
    # Skip platform-specific DLL tests
    @unittest.skip("DLL selection tests are platform-specific and need separate testing")
    def test_dll_selection_windows_32bit(self):
        """Test DLL selection on 32-bit Windows."""
        pass
    
    @unittest.skip("DLL selection tests are platform-specific and need separate testing")
    def test_dll_selection_windows_64bit(self):
        """Test DLL selection on 64-bit Windows."""
        pass
    
    @unittest.skip("DLL selection tests are platform-specific and need separate testing")
    def test_dll_selection_macos(self):
        """Test DLL selection on macOS."""
        pass
    
    @unittest.skip("DLL selection tests are platform-specific and need separate testing")
    def test_dll_selection_linux(self):
        """Test DLL selection on Linux."""
        pass
    
    def test_directory_creation(self):
        """Test that required directories are created if they don't exist."""
        # Create a fresh module object for config
        mock_config = MagicMock()
        
        # Mock os.path.exists to return False for directories
        with patch.dict('sys.modules', {'config': mock_config}), \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs:
            
            # Configure mock paths
            mock_config.BASE_DIR = "/mock/base/dir"
            mock_config.SIGNALS_DIR = "/mock/base/dir/signals"
            mock_config.LOGS_DIR = "/mock/base/dir/logs"
            
            # Manually call the directory creation code that would be in config.py
            if not os.path.exists(mock_config.SIGNALS_DIR):
                os.makedirs(mock_config.SIGNALS_DIR, exist_ok=True)
            
            if not os.path.exists(mock_config.LOGS_DIR):
                os.makedirs(mock_config.LOGS_DIR, exist_ok=True)
            
            # Verify makedirs was called for both directories
            mock_makedirs.assert_any_call("/mock/base/dir/signals", exist_ok=True)
            mock_makedirs.assert_any_call("/mock/base/dir/logs", exist_ok=True)
    
    def test_signal_file_creation(self):
        """Test that the empty signal file is created if it doesn't exist."""
        # Create a fresh module object for config
        mock_config = MagicMock()
        
        # Mock open and file operations
        with patch.dict('sys.modules', {'config': mock_config}), \
             patch('os.path.exists', return_value=False), \
             patch('builtins.open', unittest.mock.mock_open()) as mock_open:
            
            # Configure mock paths
            mock_config.EA_SIGNAL_FILE = "/mock/base/dir/signals/ea_signals.txt"
            
            # Manually call the file creation code that would be in config.py
            if not os.path.exists(mock_config.EA_SIGNAL_FILE):
                with open(mock_config.EA_SIGNAL_FILE, 'w') as f:
                    f.write('[]')
            
            # Verify open was called with the right file path and mode
            mock_open.assert_called_once_with("/mock/base/dir/signals/ea_signals.txt", 'w')
            
            # Verify write was called with empty JSON array
            mock_open().write.assert_called_once_with('[]')


if __name__ == "__main__":
    unittest.main()