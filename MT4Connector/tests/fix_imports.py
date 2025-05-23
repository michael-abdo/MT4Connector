#!/usr/bin/env python3
"""
Fix import paths in test files
"""

import os
import sys

# Add the src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

# Now all imports will work correctly
print(f"Added {src_path} to Python path")