#!/usr/bin/env python
"""
Test runner for Field Services Module tests.

This script runs all tests for the Field Services Module and generates a report.
"""

import os
import sys
import pytest
import argparse
from datetime import datetime


def run_tests(verbose=False, html_report=False):
    """Run all tests for the Field Services Module."""
    # Get the directory of this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Arguments for pytest
    args = [current_dir]
    
    # Add verbosity if requested
    if verbose:
        args.append('-v')
    
    # Add HTML report if requested
    if html_report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(current_dir, f'test_report_{timestamp}.html')
        args.extend(['--html', report_path, '--self-contained-html'])
    
    # Run the tests
    return pytest.main(args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Field Services Module tests')
    parser.add_argument('-v', '--verbose', action='store_true', help='Increase verbosity of output')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    
    args = parser.parse_args()
    
    print("Running Field Services Module tests...")
    exit_code = run_tests(verbose=args.verbose, html_report=args.html)
    
    sys.exit(exit_code)
