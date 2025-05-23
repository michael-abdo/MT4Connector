"""
Pytest configuration file to fix import paths
"""

import os
import sys

# Add the src directory to Python path for all tests
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

# This will automatically be loaded by pytest and fix imports for all tests