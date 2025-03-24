"""
API Gateway Module for ISP Management Platform.

This module provides centralized management of API requests and responses,
implementing features such as rate limiting, request routing, authentication,
request/response transformation, circuit breaking, and API versioning.

Components:
- APIGateway: Main gateway class that orchestrates all functionality
- RateLimiter: Controls API request volumes per client
- CircuitBreaker: Prevents cascading failures during service outages
- RequestTransformer: Modifies API requests before processing
- ResponseTransformer: Modifies API responses before returning to clients
- Router: Directs requests to appropriate services
- APIVersionManager: Manages multiple API versions
"""

from backend_core.api_gateway.gateway import APIGateway
from backend_core.api_gateway.rate_limiter import RateLimiter
from backend_core.api_gateway.circuit_breaker import CircuitBreaker
from backend_core.api_gateway.request_transformer import RequestTransformer
from backend_core.api_gateway.response_transformer import ResponseTransformer
from backend_core.api_gateway.router import Router
from backend_core.api_gateway.versioning import APIVersionManager, VersioningStrategy
from backend_core.api_gateway.config import settings as gateway_settings

__all__ = [
    'APIGateway',
    'RateLimiter',
    'CircuitBreaker',
    'RequestTransformer',
    'ResponseTransformer',
    'Router',
    'APIVersionManager',
    'VersioningStrategy',
    'gateway_settings',
]
