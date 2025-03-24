#!/usr/bin/env python
"""
Script to run tests for the reseller module
"""
import os
import sys
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Run the tests
if __name__ == "__main__":
    # Run tests with HATEOAS support and proper error handling
    print("Running reseller module tests...")
    
    # Set any environment variables needed for testing
    os.environ["TESTING"] = "1"
    
    # Run the tests with specific markers if provided
    args = [
        "-xvs",  # Show test output immediately, be verbose, and stop on first failure
        "tests/reseller/",  # Test directory
        "--disable-warnings"  # Disable warnings
    ]
    
    # Add any additional arguments from command line
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    # Run pytest with the arguments
    exit_code = pytest.main(args)
    
    # Exit with the pytest exit code
    sys.exit(exit_code)
