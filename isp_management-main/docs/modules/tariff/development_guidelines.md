# Tariff Enforcement Module Development Guidelines

## Overview

This document provides guidelines for developing and maintaining the Tariff Enforcement Module, including its RADIUS and Billing integrations. Following these guidelines ensures consistent code quality, proper testing, and seamless integration with the ISP Management Platform.

## Branching Strategy

The project follows a modified GitFlow branching strategy:

- `main`: Production-ready code
- `develop`: Main development branch
- `feature/*`: For new features
- `bugfix/*`: For bug fixes
- `hotfix/*`: For critical production fixes
- `release/*`: For preparing releases

### Development Workflow

1. Create a new branch from `develop` for your feature or bugfix:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the coding standards and guidelines.

3. Commit your changes with descriptive commit messages:
   ```bash
   git commit -m "feat(tariff): Add support for time-based restrictions"
   ```

4. Push your branch to the remote repository:
   ```bash
   git push -u origin feature/your-feature-name
   ```

5. Create a pull request to merge your changes into the `develop` branch.

6. After code review and approval, your changes will be merged into `develop`.

7. Changes in `develop` are periodically merged into `release/*` branches for testing and eventual promotion to `main`.

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines.
- Use 4 spaces for indentation.
- Maximum line length is 88 characters.
- Use type hints for function parameters and return values.
- Document all functions, classes, and modules using docstrings.

### Naming Conventions

- Use `snake_case` for variables, functions, and methods.
- Use `PascalCase` for classes and type variables.
- Use `UPPER_CASE` for constants.
- Prefix private methods and variables with a single underscore (`_`).

### Code Organization

- Keep functions and methods short and focused on a single responsibility.
- Organize code into logical modules and packages.
- Separate business logic from API endpoints.
- Use dependency injection for better testability.

## Integration Guidelines

### RADIUS Integration

When working with the RADIUS integration:

1. All RADIUS API calls should be made through the `RadiusIntegration` class.
2. Always handle API errors and timeouts gracefully.
3. Log all API calls and responses for debugging purposes.
4. Use environment variables for configuration.
5. Ensure proper authentication is used for all API calls.
6. Implement retry logic for transient failures.

Example:

```python
from modules.tariff.radius_integration import RadiusIntegration

radius = RadiusIntegration(
    api_url=os.getenv("RADIUS_API_URL"),
    api_key=os.getenv("RADIUS_API_KEY"),
    timeout=float(os.getenv("RADIUS_API_TIMEOUT", "10.0"))
)

try:
    result = await radius.apply_policy(username="user123", policy_id=101)
    logger.info(f"Applied policy to user: {result}")
except Exception as e:
    logger.error(f"Failed to apply policy: {str(e)}")
    # Handle the error appropriately
```

### Billing Integration

When working with the Billing integration:

1. All Billing API calls should be made through the `BillingIntegration` class.
2. Use the Decimal type for all monetary values to avoid floating-point precision issues.
3. Always handle API errors and timeouts gracefully.
4. Log all API calls and responses for debugging purposes.
5. Use environment variables for configuration.
6. Ensure proper authentication is used for all API calls.

Example:

```python
from decimal import Decimal
from modules.tariff.billing_integration import BillingIntegration

billing = BillingIntegration(
    api_url=os.getenv("BILLING_API_URL"),
    api_key=os.getenv("BILLING_API_KEY"),
    timeout=float(os.getenv("BILLING_API_TIMEOUT", "10.0"))
)

try:
    result = await billing.create_invoice_item(
        user_id=123,
        amount=Decimal("29.99"),
        description="Monthly subscription - Basic Plan"
    )
    logger.info(f"Created invoice item: {result}")
except Exception as e:
    logger.error(f"Failed to create invoice item: {str(e)}")
    # Handle the error appropriately
```

## Testing Guidelines

### Unit Tests

- Write unit tests for all new functionality.
- Use pytest for testing.
- Mock external dependencies (database, APIs, etc.).
- Aim for at least 80% code coverage.
- Test both success and failure scenarios.

Example:

```python
import pytest
from unittest.mock import patch, MagicMock
from modules.tariff.radius_integration import RadiusIntegration

@pytest.mark.asyncio
async def test_apply_policy():
    # Arrange
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response
        
        radius = RadiusIntegration(
            api_url="http://test.com",
            api_key="test-key",
            timeout=10.0
        )
        
        # Act
        result = await radius.apply_policy(username="testuser", policy_id=101)
        
        # Assert
        assert result["status"] == "success"
        mock_request.assert_called_once()
```

### Integration Tests

- Write integration tests for API endpoints and service methods.
- Test the interaction between different components.
- Use a test database for database-related tests.
- Test API endpoints with different input scenarios.

### End-to-End Tests

- Write end-to-end tests for critical user flows.
- Test the entire system from API request to database changes.
- Use realistic test data.

## Error Handling

- Use structured error handling with specific exception types.
- Log all errors with appropriate context.
- Return meaningful error messages to clients.
- Handle expected errors gracefully.

Example:

```python
try:
    result = await radius.apply_policy(username="user123", policy_id=101)
except httpx.TimeoutException:
    logger.error("RADIUS API request timed out")
    raise HTTPException(
        status_code=503,
        detail="Service temporarily unavailable. Please try again later."
    )
except httpx.HTTPStatusError as e:
    logger.error(f"RADIUS API returned error: {e.response.text}")
    raise HTTPException(
        status_code=500,
        detail="Failed to apply policy. Please contact support."
    )
```

## Logging

- Use the structured logging provided by the platform.
- Include relevant context in log messages.
- Use appropriate log levels:
  - `DEBUG`: Detailed information for debugging.
  - `INFO`: General information about system operation.
  - `WARNING`: Potential issues that don't prevent operation.
  - `ERROR`: Errors that prevent specific operations.
  - `CRITICAL`: Critical errors that prevent system operation.

Example:

```python
logger.info(
    "Applying RADIUS policy",
    extra={
        "username": username,
        "policy_id": policy_id,
        "module": "tariff",
        "component": "radius_integration"
    }
)
```

## Documentation

- Document all public APIs using docstrings.
- Keep the API documentation up to date.
- Document configuration options and environment variables.
- Provide examples for common use cases.

## Deployment

- Follow the CI/CD pipeline for automated testing and deployment.
- Update Kubernetes manifests when adding new features that require configuration changes.
- Test changes in the staging environment before deploying to production.
- Monitor the application after deployment for any issues.

## Security Considerations

- Never hardcode sensitive information (API keys, passwords, etc.).
- Use environment variables for configuration.
- Validate and sanitize all user input.
- Use proper authentication and authorization for all API endpoints.
- Follow the principle of least privilege.

## Performance Considerations

- Use asynchronous programming for I/O-bound operations.
- Implement caching for frequently accessed data.
- Optimize database queries.
- Use connection pooling for external APIs.
- Monitor and optimize resource usage.

## Troubleshooting

### Common Issues

1. **RADIUS Integration Failures**:
   - Check RADIUS API URL and credentials
   - Verify network connectivity between services
   - Check RADIUS server logs for errors

2. **Billing Integration Issues**:
   - Verify Billing API URL and credentials
   - Check for consistent user IDs across systems
   - Review billing service logs

3. **Scheduled Tasks Not Running**:
   - Ensure Celery worker and beat are running
   - Check Redis connectivity
   - Verify task registration in `celery_config.py`

### Debugging Tools

- Use the Elasticsearch logging to search for errors.
- Use the monitoring dashboard to check system health.
- Use the API documentation to test endpoints manually.

## Conclusion

Following these guidelines ensures consistent, high-quality code that integrates well with the ISP Management Platform. If you have any questions or suggestions, please contact the platform team.
