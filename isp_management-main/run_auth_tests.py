#!/usr/bin/env python
"""
Authentication Test Runner

This script runs the authentication tests and provides detailed feedback.
It's designed to work with minimal dependencies and focus on specific test modules.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime


def setup_test_environment():
    """Set up the test environment with necessary variables."""
    os.environ["SECRET_KEY"] = "test_secret_key"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
    os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
    os.environ["TOKEN_BLACKLIST_ENABLED"] = "True"
    os.environ["MFA_ISSUER_NAME"] = "ISP Management Test"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["TESTING"] = "True"


def run_test_module(module_path, verbose=True):
    """Run a specific test module."""
    print(f"\n{'='*80}")
    print(f"Running tests for: {module_path}")
    print(f"{'='*80}")
    
    cmd = ["python", "-m", "pytest", module_path]
    if verbose:
        cmd.append("-v")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
    
    return result.returncode == 0


def run_all_auth_tests(verbose=True):
    """Run all authentication tests."""
    print(f"\n{'='*80}")
    print(f"RUNNING ALL AUTHENTICATION TESTS")
    print(f"{'='*80}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_modules = [
        "tests/auth/test_auth_service.py",
        "tests/auth/test_session_core.py",
        "tests/auth/test_mfa_core.py",
        "tests/auth/test_rbac.py"
    ]
    
    results = {}
    all_passed = True
    
    for module in test_modules:
        passed = run_test_module(module, verbose)
        results[module] = passed
        if not passed:
            all_passed = False
    
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    for module, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{module}: {status}")
    
    print(f"\nOverall status: {'PASSED' if all_passed else 'FAILED'}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run authentication tests")
    parser.add_argument("--module", help="Specific test module to run")
    parser.add_argument("--quiet", action="store_true", help="Run tests with less output")
    args = parser.parse_args()
    
    setup_test_environment()
    
    if args.module:
        success = run_test_module(args.module, not args.quiet)
    else:
        success = run_all_auth_tests(not args.quiet)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
