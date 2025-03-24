# Customer Management Module Tests

This directory contains tests for the Customer Management Module of the ISP Management Platform.

## Overview

The tests are organized to cover all aspects of the Customer Management Module:

- Service layer tests
- API endpoint tests
- Utility function tests
- Document handling tests

## Test Structure

```
tests/modules/customer/
├── conftest.py                  # Test fixtures and configuration
├── test_customer_service.py     # Tests for core customer service
├── test_customer_endpoints.py   # Tests for customer API endpoints
├── test_document_service.py     # Tests for document management service
├── test_utils.py                # Tests for utility functions
└── README.md                    # This file
```

## Running Tests

To run all customer module tests:

```bash
pytest tests/modules/customer/ -v
```

To run a specific test file:

```bash
pytest tests/modules/customer/test_customer_service.py -v
```

To run a specific test function:

```bash
pytest tests/modules/customer/test_customer_service.py::test_create_customer -v
```

## Test Coverage

To generate a coverage report:

```bash
pytest tests/modules/customer/ --cov=modules/customer --cov-report=html
```

This will create an HTML coverage report in the `htmlcov` directory.

## Test Fixtures

The `conftest.py` file provides fixtures for:

- Database sessions (both real and mocked)
- Sample customer data (individual and business)
- Sample address, contact, document, and other related data
- Pre-created database records for testing
- Mock objects for external dependencies

## Writing New Tests

When adding new tests, follow these guidelines:

1. **Use Appropriate Fixtures**: Leverage existing fixtures in `conftest.py` to set up test data.
2. **Mock External Dependencies**: Use `unittest.mock` to mock external services and dependencies.
3. **Test Both Success and Error Cases**: Ensure that both successful operations and error handling are tested.
4. **Follow Naming Conventions**: Name test functions with `test_` prefix followed by the function being tested.
5. **Use Descriptive Test Names**: Make test names descriptive of what is being tested.

Example:

```python
@pytest.mark.asyncio
async def test_create_customer_with_valid_data(mock_db_session, sample_individual_customer_data):
    """Test creating a customer with valid data."""
    customer_service = CustomerService()
    
    # Set up any mocks needed
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Call the function being tested
    result = await customer_service.create_customer(
        session=mock_db_session,
        customer_type=sample_individual_customer_data["customer_type"],
        first_name=sample_individual_customer_data["first_name"],
        last_name=sample_individual_customer_data["last_name"],
        email=sample_individual_customer_data["email"]
    )
    
    # Assert the results
    assert result is not None
    assert result.first_name == sample_individual_customer_data["first_name"]
    assert result.email == sample_individual_customer_data["email"]
```

## Integration with CI/CD

The tests are automatically run as part of the CI/CD pipeline defined in `.github/workflows/customer-module-ci.yml`. The pipeline runs on:

- Pushes to `main` and `develop` branches
- Pull requests to `main` and `develop` branches

The pipeline will:

1. Set up a test environment with PostgreSQL and Redis
2. Install dependencies
3. Run the tests
4. Generate and upload a coverage report

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure that the project root is in the Python path. The `conftest.py` file adds it automatically.
2. **Database Connection Issues**: For local testing, ensure that the database is running and accessible.
3. **Async Test Failures**: Make sure to use `@pytest.mark.asyncio` for async test functions.

### Debugging Tests

To enable more verbose output:

```bash
pytest tests/modules/customer/ -v --log-cli-level=DEBUG
```

To stop on the first failure:

```bash
pytest tests/modules/customer/ -v -x
```

To use the debugger on failures:

```bash
pytest tests/modules/customer/ -v --pdb
```

## Contributing

When contributing new tests or modifying existing ones:

1. Follow the project's GitFlow branching strategy
2. Create a feature branch for your changes: `feature/customer-tests-<feature>`
3. Ensure all tests pass before submitting a pull request
4. Update this README if necessary
