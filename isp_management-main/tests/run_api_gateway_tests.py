#!/usr/bin/env python
"""
Test runner for API Gateway tests.

This script runs all tests for the API Gateway module and generates a coverage report.
"""

import os
import sys
import pytest


def run_tests():
    """Run API Gateway tests with coverage reporting."""
    print("Running API Gateway tests...")
    
    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    
    # Set up test arguments
    test_args = [
        "tests/backend_core/api_gateway",  # Test directory
        "-v",                              # Verbose output
        "--cov=backend_core/api_gateway",  # Coverage for API Gateway module
        "--cov-report=term",               # Terminal coverage report
        "--cov-report=html:coverage/api_gateway",  # HTML coverage report
    ]
    
    # Run tests
    result = pytest.main(test_args)
    
    return result


if __name__ == "__main__":
    sys.exit(run_tests())
