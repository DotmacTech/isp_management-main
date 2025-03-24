#!/usr/bin/env python
"""
Wrapper script to run tests with the correct PYTHONPATH.
This ensures that modules like backend_core can be imported correctly.
"""

import os
import sys
import subprocess

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add project root to Python path
sys.path.insert(0, project_root)

# Set environment variables
os.environ["PYTHONPATH"] = project_root

# Run the original test script with all arguments passed through
test_script = os.path.join(project_root, "scripts", "run_service_tests.py")
args = [sys.executable, test_script] + sys.argv[1:]

# Execute the test script
result = subprocess.run(args)
sys.exit(result.returncode)
