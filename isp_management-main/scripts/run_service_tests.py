#!/usr/bin/env python
"""
Script to run unit tests for the service availability monitoring feature.

This script runs pytest with specific options to test the service availability
monitoring components, including collectors, routes, and tasks.

Usage:
    python run_service_tests.py [--verbose] [--coverage] [--html-report]

Options:
    --verbose       Run tests in verbose mode
    --coverage      Generate coverage report
    --html-report   Generate HTML test report
"""

import os
import sys
import argparse
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_service_tests")

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Import test configuration to set up environment
try:
    from tests.test_config import setup_import_compatibility
    setup_import_compatibility()
    logger.info("Test environment configured successfully")
except ImportError as e:
    logger.error(f"Failed to import test configuration: {e}")


def run_tests(verbose=False, coverage=False, html_report=False):
    """Run the service availability monitoring tests."""
    try:
        # Base command
        cmd = ["pytest", "tests/modules/monitoring/test_service_availability.py"]
        
        # Add options
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=modules/monitoring",
                "--cov-report=term",
                "--cov-report=xml:coverage.xml"
            ])
        
        if html_report:
            cmd.append("--html=test-reports/service-availability-report.html")
            cmd.append("--self-contained-html")
        
        # Set environment variables for testing
        env = os.environ.copy()
        env["TESTING"] = "True"
        env["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/isp_test"
        env["ELASTICSEARCH_HOSTS"] = "http://localhost:9200"
        env["REDIS_URL"] = "redis://localhost:6379/1"
        env["PYTHONPATH"] = project_root
        
        # Run the tests
        logger.info(f"Running tests with command: {' '.join(cmd)}")
        process = subprocess.run(
            cmd,
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Print output
        print(process.stdout)
        if process.stderr:
            print(process.stderr, file=sys.stderr)
        
        # Check if tests passed
        if process.returncode == 0:
            logger.info("All tests passed successfully!")
            return True
        else:
            logger.error(f"Tests failed with return code: {process.returncode}")
            return False
    
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run service availability monitoring tests")
    parser.add_argument("--verbose", action="store_true", help="Run tests in verbose mode")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--html-report", action="store_true", help="Generate HTML test report")
    parser.add_argument("--setup-only", action="store_true", help="Only set up test environment without running tests")
    args = parser.parse_args()
    
    # Create test reports directory if needed
    if args.html_report:
        os.makedirs(os.path.join(project_root, "test-reports"), exist_ok=True)
    
    # If setup only, exit after setting up environment
    if args.setup_only:
        logger.info("Test environment setup complete")
        return 0
    
    # Run the tests
    success = run_tests(args.verbose, args.coverage, args.html_report)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
