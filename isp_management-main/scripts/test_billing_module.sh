#!/bin/bash

# Script to run the expanded billing module tests
# This script sets up the test environment and runs the tests

# Set environment variables for testing
export TESTING=1
export DATABASE_URL="postgresql://localhost/isp_management_test"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up test environment for ISP Management Billing Module...${NC}"

# Create test database if it doesn't exist
echo "Checking if test database exists..."
if ! psql -lqt | cut -d \| -f 1 | grep -qw isp_management_test; then
    echo "Creating test database..."
    createdb isp_management_test
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create test database. Please ensure PostgreSQL is running and you have the necessary permissions.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Test database created successfully.${NC}"
else
    echo -e "${GREEN}Test database already exists.${NC}"
fi

# Run migrations on test database
echo "Running database migrations..."
cd "$(dirname "$0")/.." # Navigate to project root
alembic upgrade head
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to run database migrations. Please check the error message above.${NC}"
    exit 1
fi
echo -e "${GREEN}Database migrations completed successfully.${NC}"

# Run the tests
echo -e "${YELLOW}Running expanded billing module tests...${NC}"
pytest tests/modules/billing/test_expanded_billing.py -v

# Check the test result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
else
    echo -e "${RED}Some tests failed. Please review the test output above.${NC}"
    exit 1
fi

# Optional: Generate test coverage report
echo -e "${YELLOW}Generating test coverage report...${NC}"
pytest tests/modules/billing/test_expanded_billing.py --cov=modules.billing --cov-report=term

echo -e "${GREEN}Testing completed.${NC}"
