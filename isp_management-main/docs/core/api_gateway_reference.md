# API Gateway API Reference

## APIGateway

The main class that orchestrates all API Gateway functionality.

```python
class APIGateway:
    def __init__(self, app: FastAPI):
        """
        Initialize the API Gateway.
        
        Args:
            app: The FastAPI application instance
        """
```

### Methods

#### register_service

```python
def register_service(self, router: APIRouter, prefix: str, version: Optional[str] = None):
    """
    Register a service with the API Gateway.
    
    Args:
        router: The FastAPI router for the service
        prefix: URL prefix for the service (e.g., "/api/auth")
        version: API version (optional)
    """
```

#### set_rate_limit

```python
def set_rate_limit(self, path: str, limit: int, period: int = 60):
    """
    Set a rate limit for a specific path.
    
    Args:
        path: The API path to rate limit
        limit: Maximum number of requests
        period: Time period in seconds
    """
```

#### configure_circuit_breaker

```python
def configure_circuit_breaker(self, path: str, threshold: int, recovery_time: int):
    """
    Configure a circuit breaker for a specific path.
    
    Args:
        path: The API path to apply circuit breaking to
        threshold: Number of failures before opening the circuit
        recovery_time: Time in seconds before attempting to close the circuit
    """
```

#### get_metrics

```python
def get_metrics(self) -> Dict:
    """
    Get metrics for the API Gateway.
    
    Returns:
        Dict: Metrics for rate limiting, circuit breakers, and routes
    """
```

## RateLimiter

Class for controlling API request volumes per client.

```python
class RateLimiter:
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize the rate limiter.
        
        Args:
            redis_client: Redis client for distributed rate limiting (optional)
        """
```

### Methods

#### check_rate_limit

```python
async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
    """
    Check if a request exceeds the rate limit.
    
    Args:
        request: The request to check
        
    Returns:
        Tuple[bool, Dict]: (is_allowed, rate_limit_info)
    """
```

#### set_rate_limit

```python
def set_rate_limit(self, path: str, limit: int, period: int = 60):
    """
    Set a rate limit for a specific path.
    
    Args:
        path: The API path to rate limit
        limit: Maximum number of requests
        period: Time period in seconds
    """
```

#### get_client_identifier

```python
def get_client_identifier(self, request: Request) -> str:
    """
    Get a unique identifier for the client.
    
    Args:
        request: The client request
        
    Returns:
        str: Unique client identifier
    """
```

#### get_metrics

```python
def get_metrics(self) -> List[Dict]:
    """
    Get rate limiting metrics.
    
    Returns:
        List[Dict]: Rate limiting metrics
    """
```

## CircuitBreaker

Class for preventing cascading failures during service outages.

```python
class CircuitBreaker:
    def __init__(self):
        """Initialize the circuit breaker."""
```

### Methods

#### check_circuit

```python
async def check_circuit(self, path: str) -> bool:
    """
    Check if a circuit is closed (requests allowed).
    
    Args:
        path: The API path to check
        
    Returns:
        bool: True if the circuit is closed (requests allowed)
    """
```

#### record_success

```python
def record_success(self, path: str):
    """
    Record a successful request.
    
    Args:
        path: The API path
    """
```

#### record_failure

```python
def record_failure(self, path: str):
    """
    Record a failed request.
    
    Args:
        path: The API path
    """
```

#### configure

```python
def configure(self, path: str, threshold: int, recovery_time: int):
    """
    Configure a circuit breaker for a specific path.
    
    Args:
        path: The API path
        threshold: Number of failures before opening the circuit
        recovery_time: Time in seconds before attempting to close the circuit
    """
```

#### get_metrics

```python
def get_metrics(self) -> List[Dict]:
    """
    Get circuit breaker metrics.
    
    Returns:
        List[Dict]: Circuit breaker metrics
    """
```

## RequestTransformer

Class for modifying API requests before they are processed.

```python
class RequestTransformer:
    def __init__(self):
        """Initialize the request transformer."""
```

### Methods

#### transform

```python
async def transform(self, request: Request) -> Request:
    """
    Transform a request before it is processed.
    
    Args:
        request: The original request
        
    Returns:
        Request: The transformed request
    """
```

#### register_transformation

```python
def register_transformation(self, path: str, transformation: Dict):
    """
    Register a transformation for a specific path.
    
    Args:
        path: The API path to transform
        transformation: The transformation configuration
    """
```

#### register_header_transformation

```python
def register_header_transformation(self, path: str, header: str, value: str):
    """
    Register a header transformation for a specific path.
    
    Args:
        path: The API path to transform
        header: The header to add or modify
        value: The header value
    """
```

#### register_protocol_transformation

```python
def register_protocol_transformation(self, path: str, source_protocol: str, target_protocol: str):
    """
    Register a protocol transformation for a specific path.
    
    Args:
        path: The API path to transform
        source_protocol: The source protocol (e.g., "rest")
        target_protocol: The target protocol (e.g., "grpc")
    """
```

## ResponseTransformer

Class for modifying API responses before they are returned to clients.

```python
class ResponseTransformer:
    def __init__(self):
        """Initialize the response transformer."""
```

### Methods

#### transform

```python
async def transform(self, response: Response) -> Response:
    """
    Transform a response before it is returned to the client.
    
    Args:
        response: The original response
        
    Returns:
        Response: The transformed response
    """
```

#### register_transformation

```python
def register_transformation(self, path: str, transformation: Dict):
    """
    Register a transformation for a specific path.
    
    Args:
        path: The API path to transform
        transformation: The transformation configuration
    """
```

#### register_header_transformation

```python
def register_header_transformation(self, path: str, header: str, value: str):
    """
    Register a header transformation for a specific path.
    
    Args:
        path: The API path to transform
        header: The header to add or modify
        value: The header value
    """
```

#### register_protocol_transformation

```python
def register_protocol_transformation(self, path: str, source_protocol: str, target_protocol: str):
    """
    Register a protocol transformation for a specific path.
    
    Args:
        path: The API path to transform
        source_protocol: The source protocol (e.g., "grpc")
        target_protocol: The target protocol (e.g., "rest")
    """
```

## Router

Class for directing API requests to appropriate services.

```python
class Router:
    def __init__(self):
        """Initialize the router."""
```

### Methods

#### register_routes

```python
def register_routes(self, routes: List[APIRoute], prefix: str, version: Optional[str] = None):
    """
    Register routes with the router.
    
    Args:
        routes: List of FastAPI routes
        prefix: URL prefix for the routes
        version: API version (optional)
    """
```

#### get_all_routes

```python
def get_all_routes(self) -> List[Dict]:
    """
    Get all registered routes.
    
    Returns:
        List[Dict]: All registered routes
    """
```

#### get_route_by_path

```python
def get_route_by_path(self, path: str) -> Optional[Dict]:
    """
    Get route information for a specific path.
    
    Args:
        path: The API path
        
    Returns:
        Optional[Dict]: Route information if found, None otherwise
    """
```

#### get_metrics

```python
def get_metrics(self) -> List[RouteMetrics]:
    """
    Get metrics for all routes.
    
    Returns:
        List[RouteMetrics]: Route metrics
    """
```

## APIVersionManager

Class for managing multiple API versions.

```python
class APIVersionManager:
    def __init__(self):
        """Initialize the API version manager."""
```

### Methods

#### configure

```python
def configure(self, strategy: VersioningStrategy, default_version: str):
    """
    Configure the versioning strategy.
    
    Args:
        strategy: The versioning strategy to use
        default_version: The default API version
    """
```

#### register_version

```python
def register_version(self, version: str, description: str, deprecated: bool = False):
    """
    Register an API version.
    
    Args:
        version: The API version (e.g., "1", "2")
        description: Description of this version
        deprecated: Whether this version is deprecated
    """
```

#### register_endpoint

```python
def register_endpoint(self, version: str, path: str):
    """
    Register an endpoint for a specific API version.
    
    Args:
        version: The API version
        path: The endpoint path
    """
```

#### get_versioned_prefix

```python
def get_versioned_prefix(self, prefix: str, version: str) -> str:
    """
    Get a versioned URL prefix based on the configured strategy.
    
    Args:
        prefix: The original URL prefix
        version: The API version
        
    Returns:
        str: The versioned URL prefix
    """
```

#### extract_version

```python
def extract_version(self, path: str, headers: Dict[str, str], query_params: Dict[str, str]) -> str:
    """
    Extract the API version from a request based on the configured strategy.
    
    Args:
        path: The request path
        headers: The request headers
        query_params: The request query parameters
        
    Returns:
        str: The extracted API version, or the default version if not found
    """
```

#### is_deprecated

```python
def is_deprecated(self, version: str) -> bool:
    """
    Check if an API version is deprecated.
    
    Args:
        version: The API version
        
    Returns:
        bool: True if the version is deprecated
    """
```

#### get_all_versions

```python
def get_all_versions(self) -> List[Dict]:
    """
    Get information about all registered API versions.
    
    Returns:
        List[Dict]: Information about all versions
    """
```

## Configuration

The API Gateway configuration is defined in `api_gateway/config.py`.

```python
class APIGatewaySettings(BaseSettings):
    """Configuration settings for the API Gateway."""
    
    # Version
    API_GATEWAY_VERSION: str = "1.0.0"
    
    # Rate limiting
    DEFAULT_RATE_LIMIT: int = 100
    DEFAULT_RATE_LIMIT_PERIOD: int = 60  # seconds
    RATE_LIMITS: Dict[str, Dict[str, int]] = {...}
    
    # Circuit breaker
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD: int = 5
    DEFAULT_CIRCUIT_BREAKER_RECOVERY_TIME: int = 60  # seconds
    CIRCUIT_BREAKER_SETTINGS: Dict[str, Dict[str, int]] = {...}
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: app_settings.CORS_ORIGINS)
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Security
    SECURITY_HEADERS: Dict[str, str] = {...}
    
    # API versioning
    API_VERSIONING_STRATEGY: str = "url_path"  # url_path, query_param, header, content_type
    API_DEFAULT_VERSION: str = "1"
    API_VERSIONS: Dict[str, Dict] = {...}
    
    # Request transformation
    REQUEST_TRANSFORMATIONS: Dict[str, Dict] = {...}
    
    # Response transformation
    RESPONSE_TRANSFORMATIONS: Dict[str, Dict] = {...}
    
    # Protocol support
    SUPPORTED_PROTOCOLS: List[str] = ["rest", "grpc"]
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_ENDPOINT: str = "/api/gateway/metrics"
```
