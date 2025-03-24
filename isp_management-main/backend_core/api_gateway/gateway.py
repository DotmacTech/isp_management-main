"""
API Gateway implementation for the ISP Management Platform.

This module provides a centralized entry point for all API requests, handling
routing, rate limiting, authentication, and other cross-cutting concerns.
"""

import logging
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, Request, Response, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis

from backend_core.api_gateway.rate_limiter import RateLimiter
from backend_core.api_gateway.circuit_breaker import CircuitBreaker
from backend_core.api_gateway.request_transformer import RequestTransformer
from backend_core.api_gateway.response_transformer import ResponseTransformer
from backend_core.api_gateway.router import Router
from backend_core.api_gateway.versioning import APIVersionManager, VersioningStrategy
from backend_core.api_gateway.config import settings
from backend_core.auth_service import AuthService


class APIGateway:
    """
    API Gateway for the ISP Management Platform.
    
    This class orchestrates all API Gateway functionality, including:
    - Routing requests to appropriate microservices
    - Rate limiting to control API request volumes
    - Circuit breaking to prevent cascading failures
    - Request/response transformation
    - API versioning
    - Security enforcement
    """
    
    def __init__(self, app: FastAPI, redis_client: Optional[Redis] = None):
        """
        Initialize the API Gateway.
        
        Args:
            app: The FastAPI application instance
            redis_client: Redis client for distributed rate limiting (optional)
        """
        self.app = app
        self.logger = logging.getLogger("api_gateway")
        
        # Initialize components
        self.rate_limiter = RateLimiter(redis_client)
        self.circuit_breaker = CircuitBreaker()
        self.request_transformer = RequestTransformer()
        self.response_transformer = ResponseTransformer()
        self.router = Router()
        self.version_manager = APIVersionManager()
        
        # Configure API versioning
        self.version_manager.configure(
            strategy=VersioningStrategy(settings.API_VERSIONING_STRATEGY),
            default_version=settings.API_DEFAULT_VERSION
        )
        
        # Register API versions
        for version, info in settings.API_VERSIONS.items():
            self.version_manager.register_version(
                version=version,
                description=info["description"],
                deprecated=info["deprecated"]
            )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=settings.CORS_METHODS,
            allow_headers=settings.CORS_HEADERS,
        )
        
        # Add exception handler for HTTPException
        @app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """
            Handle HTTP exceptions and format them consistently.
            
            Args:
                request: The incoming request
                exc: The HTTP exception
                
            Returns:
                JSONResponse: A formatted error response
            """
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": True,
                    "code": exc.status_code,
                    "message": "Error processing request",
                    "detail": exc.detail
                }
            )
        
        # Add gateway middleware
        @app.middleware("http")
        async def api_gateway_middleware(request: Request, call_next):
            """
            Middleware for API Gateway functionality.
            
            Args:
                request: The incoming request
                call_next: The next middleware in the chain
                
            Returns:
                Response: The response from the API
            """
            # Skip gateway processing for non-API routes
            if not request.url.path.startswith("/api"):
                return await call_next(request)
            
            # Check rate limits
            is_allowed, rate_limit_info = await self.rate_limiter.check_rate_limit(request)
            if not is_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": True,
                        "code": 429,
                        "message": "Rate limit exceeded",
                        "details": rate_limit_info
                    }
                )
            
            # Check circuit breaker
            if not await self.circuit_breaker.check_circuit(request.url.path):
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "error": True,
                        "code": 503,
                        "message": "Service temporarily unavailable",
                        "details": "Circuit breaker is open"
                    }
                )
            
            # Transform request
            request = await self.request_transformer.transform(request)
            
            try:
                # Process the request
                response = await call_next(request)
                
                # Record success for circuit breaker
                self.circuit_breaker.record_success(request.url.path)
                
                # Transform response
                response = await self.response_transformer.transform(response)
                
                # Add rate limit headers
                self.rate_limiter.add_rate_limit_headers(response, rate_limit_info)
                
                return response
                
            except Exception as e:
                # Record failure for circuit breaker
                self.circuit_breaker.record_failure(request.url.path)
                
                # Log the error
                self.logger.error(f"Error processing request: {str(e)}")
                
                # Return error response
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": True,
                        "code": 500,
                        "message": "Internal server error",
                    }
                )
        
        # Add metrics endpoint
        @app.get("/api/gateway/metrics")
        async def gateway_metrics(auth: AuthService = Depends()):
            """
            Get API Gateway metrics.
            
            Args:
                auth: Authentication service
                
            Returns:
                Dict: API Gateway metrics
            """
            if not auth.is_admin():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            
            return {
                "rate_limits": self.rate_limiter.get_metrics(),
                "circuit_breakers": self.circuit_breaker.get_metrics(),
                "routes": self.router.get_metrics(),
                "versions": self.version_manager.get_all_versions(),
            }
    
    def register_service(self, router: APIRouter, prefix: str, version: Optional[str] = None):
        """
        Register a service with the API Gateway.
        
        Args:
            router: The FastAPI router for the service
            prefix: URL prefix for the service (e.g., "/api/auth")
            version: API version (optional)
        """
        # Use default version if not specified
        if version is None:
            version = self.version_manager.default_version
        
        # Get versioned prefix based on versioning strategy
        versioned_prefix = self.version_manager.get_versioned_prefix(prefix, version)
        
        # Register routes with the router
        self.router.register_routes(router.routes, versioned_prefix, version)
        
        # Register endpoints with the version manager
        for route in router.routes:
            self.version_manager.register_endpoint(version, f"{versioned_prefix}{route.path}")
        
        # Include router in the FastAPI app
        self.app.include_router(router, prefix=versioned_prefix)
        
        self.logger.info(f"Registered service: {prefix} (version {version})")
    
    def set_rate_limit(self, path: str, limit: int, period: int = 60):
        """
        Set a rate limit for a specific path.
        
        Args:
            path: The API path to rate limit
            limit: Maximum number of requests
            period: Time period in seconds
        """
        self.rate_limiter.set_rate_limit(path, limit, period)
        self.logger.info(f"Set rate limit for {path}: {limit} requests per {period} seconds")
    
    def configure_circuit_breaker(self, path: str, threshold: int, recovery_time: int):
        """
        Configure a circuit breaker for a specific path.
        
        Args:
            path: The API path to apply circuit breaking to
            threshold: Number of failures before opening the circuit
            recovery_time: Time in seconds before attempting to close the circuit
        """
        self.circuit_breaker.configure(path, threshold, recovery_time)
        self.logger.info(f"Configured circuit breaker for {path}: threshold={threshold}, recovery_time={recovery_time}")
    
    def register_request_transformation(self, path: str, transformation: Dict):
        """
        Register a request transformation for a specific path.
        
        Args:
            path: The API path to transform
            transformation: The transformation configuration
        """
        self.request_transformer.register_transformation(path, transformation)
    
    def register_response_transformation(self, path: str, transformation: Dict):
        """
        Register a response transformation for a specific path.
        
        Args:
            path: The API path to transform
            transformation: The transformation configuration
        """
        self.response_transformer.register_transformation(path, transformation)
    
    def get_metrics(self) -> Dict:
        """
        Get metrics for the API Gateway.
        
        Returns:
            Dict: Metrics for rate limiting, circuit breakers, and routes
        """
        return {
            "rate_limits": self.rate_limiter.get_metrics(),
            "circuit_breakers": self.circuit_breaker.get_metrics(),
            "routes": self.router.get_metrics(),
            "versions": self.version_manager.get_all_versions(),
        }
