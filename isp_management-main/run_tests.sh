#!/bin/bash

# Run tests with coverage report
echo "Running tests with coverage..."
python -m pytest tests/ --cov=backend_core --cov=modules --cov-report=term --cov-report=html:coverage_report

# Check if tests passed
if [ $? -eq 0 ]; then
    echo "All tests passed!"
    echo "Coverage report generated in coverage_report directory"
    echo "Open coverage_report/index.html to view the detailed report"
else
    echo "Tests failed. Please check the output above for details."
fi
