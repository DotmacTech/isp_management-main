#!/usr/bin/env python3
"""
Comprehensive Test Runner for ISP Management Platform

This script provides a flexible way to run tests for the entire backend application
or specific modules, with detailed reporting and coverage analysis.

Usage:
    python run_comprehensive_tests.py [--module MODULE_NAME] [--coverage] [--verbose]

Examples:
    # Run all tests
    python run_comprehensive_tests.py

    # Run tests for a specific module with coverage
    python run_comprehensive_tests.py --module auth --coverage

    # Run tests for multiple modules with verbose output
    python run_comprehensive_tests.py --module auth --module billing --verbose
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run tests for the ISP Management Platform"
    )
    parser.add_argument(
        "--module",
        action="append",
        help="Specific module to test (can be used multiple times)",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--html-report", action="store_true", help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--skip-lint", action="store_true", help="Skip linting checks"
    )
    return parser.parse_args()


def run_linting(verbose=False):
    """Run linting checks on the codebase."""
    print("\n=== Running linting checks ===")
    
    # Run flake8
    flake8_cmd = ["flake8", "modules", "backend_core", "tests"]
    if verbose:
        print(f"Running: {' '.join(flake8_cmd)}")
    
    result = subprocess.run(flake8_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Linting issues found:")
        print(result.stdout)
        return False
    else:
        print("No linting issues found.")
        return True


def run_tests(modules=None, coverage=False, verbose=False, html_report=False):
    """Run the tests with the specified options."""
    # Base pytest command
    pytest_cmd = ["pytest"]
    
    # Add verbosity if requested
    if verbose:
        pytest_cmd.append("-v")
    
    # Add coverage if requested
    if coverage:
        pytest_cmd.extend(["--cov=backend_core", "--cov=modules"])
        if html_report:
            pytest_cmd.append("--cov-report=html:coverage_report")
        pytest_cmd.append("--cov-report=term")
    
    # Add specific modules if requested
    if modules:
        for module in modules:
            pytest_cmd.append(f"tests/modules/{module}")
    else:
        # Run all tests if no specific modules are specified
        pytest_cmd.append("tests/")
    
    # Print the command being run
    print(f"\n=== Running: {' '.join(pytest_cmd)} ===")
    
    # Run the tests
    result = subprocess.run(pytest_cmd)
    return result.returncode == 0


def main():
    """Main function to run the tests."""
    args = parse_arguments()
    
    print("=== ISP Management Platform Test Runner ===")
    print(f"Project root: {project_root}")
    
    # Set environment variables for testing
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TESTING"] = "True"
    
    # Run linting checks if not skipped
    if not args.skip_lint:
        lint_success = run_linting(args.verbose)
        if not lint_success:
            print("\nWarning: Linting issues found. Continuing with tests...")
    
    # Run the tests
    test_success = run_tests(
        modules=args.module,
        coverage=args.coverage,
        verbose=args.verbose,
        html_report=args.html_report
    )
    
    # Print summary
    print("\n=== Test Summary ===")
    if test_success:
        print("All tests passed!")
        if args.coverage and args.html_report:
            print("Coverage report generated in coverage_report directory")
            print("Open coverage_report/index.html to view the detailed report")
    else:
        print("Tests failed. Please check the output above for details.")
    
    # Return appropriate exit code
    return 0 if test_success else 1


if __name__ == "__main__":
    sys.exit(main())
