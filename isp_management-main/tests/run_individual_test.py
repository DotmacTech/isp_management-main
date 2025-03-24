#!/usr/bin/env python
"""
Script to run individual tests with proper mocking of dependencies
"""
import os
import sys
import pytest
import importlib.util
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock problematic modules
sys.modules['modules.reseller.api'] = MagicMock()
sys.modules['modules.reseller.api.endpoints'] = MagicMock()
sys.modules['modules.reseller.api.schemas'] = MagicMock()
sys.modules['modules.auth.api'] = MagicMock()
sys.modules['modules.auth.api.endpoints'] = MagicMock()
sys.modules['modules.auth.api.schemas'] = MagicMock()

# Run the tests
if __name__ == "__main__":
    # Set any environment variables needed for testing
    os.environ["TESTING"] = "1"
    
    if len(sys.argv) < 2:
        print("Usage: python run_individual_test.py <test_file_path>")
        sys.exit(1)
    
    test_file = sys.argv[1]
    
    # Run the tests with specific markers if provided
    args = [
        "-xvs",  # Show test output immediately, be verbose, and stop on first failure
        test_file,  # Test file
        "--disable-warnings"  # Disable warnings
    ]
    
    # Add any additional arguments from command line
    if len(sys.argv) > 2:
        args.extend(sys.argv[2:])
    
    # Run pytest with the arguments
    exit_code = pytest.main(args)
    
    # Exit with the pytest exit code
    sys.exit(exit_code)
