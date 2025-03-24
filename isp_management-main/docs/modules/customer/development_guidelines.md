# Customer Management Module Development Guidelines

## Architecture Overview

The Customer Management Module follows a layered architecture pattern:

1. **API Layer**: Endpoints for handling HTTP requests and responses
2. **Service Layer**: Business logic and data processing
3. **Data Access Layer**: Database interactions via SQLAlchemy models

## Directory Structure

```
modules/customer/
├── __init__.py
├── models.py                    # Database models
├── schemas.py                   # Pydantic schemas for validation
├── services.py                  # Core customer service
├── communication_service.py     # Communication preferences service
├── document_service.py          # Document management service
├── verification_service.py      # Email verification service
├── utils.py                     # Utility functions
├── endpoints.py                 # Main router and customer endpoints
├── address_endpoints.py         # Address management endpoints
├── contact_endpoints.py         # Contact management endpoints
├── communication_endpoints.py   # Communication preferences endpoints
├── document_endpoints.py        # Document management endpoints
├── note_endpoints.py            # Note management endpoints
├── tag_endpoints.py             # Tag management endpoints
└── verification_endpoints.py    # Email verification endpoints
```

## Development Workflow

### 1. Branching Strategy

Follow the project's GitFlow branching strategy:

- `main`: Production-ready code
- `develop`: Main development branch
- `feature/customer-*`: For new customer module features
- `bugfix/customer-*`: For bug fixes in the customer module
- `hotfix/customer-*`: For critical production fixes
- `release/customer-*`: For preparing customer module releases

### 2. Development Process

1. Create a new branch from `develop` for your feature or fix
2. Implement the required changes
3. Write tests for your implementation
4. Run the tests locally to ensure they pass
5. Submit a pull request to the `develop` branch
6. Address any review comments
7. Once approved, merge your changes into `develop`

### 3. Code Style Guidelines

- Follow PEP 8 for Python code style
- Use type hints for function parameters and return values
- Write docstrings for all classes and functions
- Use meaningful variable and function names
- Keep functions focused on a single responsibility
- Limit line length to 88 characters (Black formatter default)

### 4. Testing Guidelines

- Write unit tests for all services and endpoints
- Use pytest fixtures to set up test data
- Mock external dependencies
- Test both success and error cases
- Aim for at least 80% code coverage

## API Design Guidelines

### 1. Endpoint Structure

- Use RESTful principles for API design
- Use plural nouns for resource collections (e.g., `/customers/`)
- Use HTTP methods appropriately (GET, POST, PUT, DELETE)
- Use nested routes for related resources (e.g., `/customers/{id}/addresses/`)
- Return appropriate HTTP status codes

### 2. Request Validation

- Use Pydantic schemas for request validation
- Validate all user inputs
- Provide clear error messages for validation failures

### 3. Response Format

All API responses should follow this structure:

```json
{
  "data": { ... },  // The actual response data
  "meta": {         // Optional metadata
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total": 100
    }
  }
}
```

For error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }  // Optional additional details
  }
}
```

## Database Guidelines

### 1. Model Design

- Use SQLAlchemy ORM for database interactions
- Follow naming conventions for tables and columns
- Use appropriate data types
- Define relationships between models
- Use indexes for frequently queried columns

### 2. Migrations

- Use Alembic for database migrations
- Create a migration for each schema change
- Test migrations both forward and backward

## Security Guidelines

### 1. Authentication and Authorization

- All endpoints must be protected with appropriate authentication
- Use role-based access control for authorization
- Implement proper permission checks in services

### 2. Data Protection

- Hash passwords and sensitive data
- Validate and sanitize all user inputs
- Implement rate limiting for sensitive operations
- Follow the principle of least privilege

### 3. Document Handling

- Validate document uploads for size and file type
- Store documents securely
- Implement proper access controls for document retrieval

## Integration Guidelines

### 1. Event-Based Communication

- Use events for communicating with other modules
- Define clear event schemas
- Handle event failures gracefully

### 2. Service Dependencies

- Clearly document dependencies on other services
- Use dependency injection for service dependencies
- Mock dependencies in tests

## Documentation Guidelines

- Document all public APIs
- Keep documentation up-to-date with code changes
- Include examples for API usage
- Document configuration options

## Deployment Guidelines

- Update the CI/CD pipeline for any new dependencies
- Test changes in the staging environment before production
- Monitor for errors after deployment
- Have a rollback plan for critical issues

## Troubleshooting

### Common Issues

1. **Database connection issues**
   - Check database credentials
   - Verify network connectivity
   - Check for database locks

2. **Performance issues**
   - Look for N+1 query problems
   - Check for missing indexes
   - Review transaction isolation levels

3. **Authentication issues**
   - Verify JWT token validity
   - Check user permissions
   - Review role assignments

## Contact

For questions or issues related to the Customer Management Module, contact the module maintainers:

- Email: customer-module@isp-management.com
- Slack: #customer-module-dev
