# API Gateway Module

## Overview

The API Gateway module provides centralized management of all API requests and responses in the ISP Management Platform. It serves as a single entry point for all client requests, handling routing, authentication, rate limiting, and other cross-cutting concerns.

## Key Features

### Rate Limiting

The API Gateway implements rate limiting to control API request volumes per client, preventing abuse and ensuring fair resource allocation.

```python
# Configure rate limits in api_gateway/config.py
RATE_LIMITS = {
    "/api/auth/login": {"limit": 10, "period": 60},  # 10 requests per minute
    "/api/auth/register": {"limit": 5, "period": 60}, # 5 requests per minute
}

# Apply rate limits in main.py
for path, config in gateway_settings.RATE_LIMITS.items():
    api_gateway.set_rate_limit(path, config["limit"], config["period"])
```

### Request Routing

The API Gateway directs requests to appropriate microservices based on path, headers, or other criteria.

```python
# Register services with the API Gateway in main.py
api_gateway.register_service(auth_router, "/api/auth", version="1")
api_gateway.register_service(billing_router, "/api/billing", version="1")
```

### Authentication

The API Gateway integrates with the Authentication Service to provide centralized API authentication and authorization.

```python
# Authentication is handled by middleware in the gateway
# See gateway.py for implementation details
```

### Request/Response Transformation

The API Gateway can modify requests and responses between client and services, enabling protocol adaptation and standardized error handling.

```python
# Configure transformations in api_gateway/config.py
REQUEST_TRANSFORMATIONS = {
    "/api/legacy": {
        "headers": {"X-Legacy-Support": "true"},
    },
}

# Apply transformations in request_transformer.py and response_transformer.py
```

### Circuit Breakers

The API Gateway implements circuit breakers to prevent cascading failures during service outages.

```python
# Configure circuit breakers in api_gateway/config.py
CIRCUIT_BREAKER_SETTINGS = {
    "/api/billing": {"threshold": 10, "recovery_time": 30},
    "/api/radius": {"threshold": 15, "recovery_time": 45},
}

# Apply circuit breaker settings in main.py
for path, config in gateway_settings.CIRCUIT_BREAKER_SETTINGS.items():
    api_gateway.configure_circuit_breaker(path, config["threshold"], config["recovery_time"])
```

### API Versioning

The API Gateway manages multiple API versions, supporting different versioning strategies and providing tools for deprecating and migrating between versions.

```python
# Configure versioning in api_gateway/config.py
API_VERSIONING_STRATEGY = "url_path"  # url_path, query_param, header, content_type
API_DEFAULT_VERSION = "1"
API_VERSIONS = {
    "1": {"description": "Initial API version", "deprecated": False},
    "2": {"description": "Enhanced API with additional features", "deprecated": False},
}

# Register versioned services in main.py
api_gateway.register_service(auth_router, "/api/auth", version="1")
```

## Technical Considerations

### Protocol Support

The API Gateway supports multiple protocols:

- **REST**: The primary protocol for most services
- **gRPC**: Supported for high-performance internal service communication

### Routing Rules

Routing rules can be configured based on:

- **Path**: The URL path of the request
- **Headers**: Request headers
- **Query Parameters**: URL query parameters

### Security Policies

The API Gateway enforces several security policies:

- **SSL**: All external communication must use HTTPS
- **CORS**: Cross-Origin Resource Sharing is configured centrally
- **Security Headers**: Standard security headers are added to all responses

### Monitoring

The API Gateway collects API usage metrics:

- **Request Counts**: Number of requests per endpoint
- **Response Times**: Time taken to process requests
- **Error Rates**: Number of errors per endpoint
- **Rate Limit Hits**: Number of rate limit violations

## Integration Points

### Microservices

All backend services integrate through the API Gateway:

```python
# Register a service with the API Gateway
api_gateway.register_service(my_service_router, "/api/my-service", version="1")
```

### Monitoring Module

The API Gateway collects API performance metrics that can be accessed through the monitoring module:

```python
# Access API Gateway metrics
@app.get("/api/gateway/metrics")
async def gateway_metrics(auth: AuthService = Depends()):
    if not auth.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return {
        "rate_limits": api_gateway.rate_limiter.get_metrics(),
        "circuit_breakers": api_gateway.circuit_breaker.get_metrics(),
        "routes": api_gateway.router.get_metrics(),
    }
```

### Security Module

The API Gateway integrates with the authentication and authorization systems:

```python
# Authentication is handled by middleware in the gateway
# See gateway.py for implementation details
```

## Security Considerations

### API Security

The API Gateway protects against common API vulnerabilities:

- **Rate Limiting**: Prevents brute force and DoS attacks
- **Input Validation**: Validates request parameters
- **Authentication**: Ensures proper authentication for protected endpoints
- **Authorization**: Enforces role-based access control

### Sensitive Data Protection

The API Gateway masks sensitive information in logs:

```python
# Mask sensitive data in request_transformer.py
def _mask_sensitive_data(self, request: Request):
    sensitive_headers = [
        "authorization",
        "cookie",
        "x-api-key",
    ]
    
    for i, (name, value) in enumerate(request.scope["headers"]):
        header_name = name.decode().lower()
        if header_name in sensitive_headers:
            request.scope["headers"][i] = (
                name,
                b"[REDACTED]"
            )
```

### Access Control

The API Gateway provides granular control over API endpoints through integration with the RBAC system.

## Performance Considerations

### Latency Optimization

The API Gateway is optimized for minimal overhead:

- **Efficient Routing**: Fast path-based routing
- **Caching**: Response caching for appropriate endpoints
- **Connection Pooling**: Reuse connections to backend services

### Scalability

The API Gateway can be horizontally scaled to handle increased load:

- **Stateless Design**: No session state stored in the gateway
- **Distributed Rate Limiting**: Using Redis for distributed rate limiting
- **Load Balancing**: Multiple gateway instances behind a load balancer

## Usage Examples

### Registering a New Service

```python
from fastapi import APIRouter
from backend_core.api_gateway import APIGateway

# Create a router for your service
my_service_router = APIRouter()

@my_service_router.get("/items")
async def get_items():
    return {"items": ["item1", "item2"]}

# Register with the API Gateway
api_gateway = APIGateway(app)
api_gateway.register_service(my_service_router, "/api/my-service", version="1")
```

### Configuring Rate Limits

```python
# Configure in api_gateway/config.py
RATE_LIMITS = {
    "/api/my-service/items": {"limit": 20, "period": 60},  # 20 requests per minute
}

# Or programmatically
api_gateway.set_rate_limit("/api/my-service/items", 20, 60)
```

### Implementing API Versioning

```python
# Register multiple versions of a service
api_gateway.register_service(my_service_router_v1, "/api/my-service", version="1")
api_gateway.register_service(my_service_router_v2, "/api/my-service", version="2")

# Access via URL path: /v1/api/my-service or /v2/api/my-service
```

## Troubleshooting

### Common Issues

1. **Rate Limiting Issues**
   - Check client IP address is correctly identified
   - Verify rate limit configuration for the endpoint

2. **Routing Problems**
   - Ensure service is registered with correct prefix
   - Check for path conflicts between services

3. **Circuit Breaker Tripping**
   - Investigate service health issues
   - Adjust threshold and recovery time if needed

4. **Authentication Failures**
   - Verify JWT token validity
   - Check user permissions for the endpoint

### Debugging

The API Gateway provides detailed logging:

```python
# Enable debug logging in logging_init.py
logging.getLogger("api_gateway").setLevel(logging.DEBUG)
```

## API Reference

See the [API Gateway API Reference](api_gateway_reference.md) for detailed information on all API Gateway classes and methods.

## Testing

The API Gateway module includes a comprehensive test suite that verifies the functionality of all components. The tests are organized by component and cover both unit tests and integration tests.

### Test Structure

- **test_gateway.py**: Tests for the main APIGateway class and integration tests.
- **test_rate_limiter.py**: Tests for the RateLimiter component.
- **test_circuit_breaker.py**: Tests for the CircuitBreaker component.
- **test_transformers.py**: Tests for the RequestTransformer and ResponseTransformer components.
- **test_router_versioning.py**: Tests for the Router and APIVersionManager components.
- **test_config.py**: Tests for the configuration settings.

### Running Tests

To run the API Gateway tests:

```bash
# Run all API Gateway tests
python tests/run_api_gateway_tests.py

# Run specific test file
pytest tests/backend_core/api_gateway/test_gateway.py -v

# Run with coverage
pytest tests/backend_core/api_gateway --cov=backend_core/api_gateway
```

### Test Coverage

The test suite aims for high code coverage to ensure reliability and robustness of the API Gateway module. Coverage reports can be generated in HTML format for detailed analysis.
