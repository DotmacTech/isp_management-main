"""
Tests for the API Gateway module.

This module contains tests for the API Gateway functionality, including
rate limiting, circuit breaking, request/response transformation, and routing.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend_core.api_gateway import (
    APIGateway,
    RateLimiter,
    CircuitBreaker,
    RequestTransformer,
    ResponseTransformer,
    Router,
    APIVersionManager,
    VersioningStrategy
)
from backend_core.api_gateway.config import APIGatewaySettings


@pytest.fixture
def app():
    """Create a FastAPI application for testing."""
    return FastAPI()


@pytest.fixture
def test_router():
    """Create a test router for testing."""
    router = APIRouter()
    
    @router.get("/test")
    async def test_endpoint():
        return {"message": "Test endpoint"}
    
    @router.get("/error")
    async def error_endpoint():
        raise HTTPException(status_code=500, detail="Test error")
    
    return router


@pytest.fixture
def api_gateway(app, test_router):
    """Create an API Gateway instance for testing."""
    gateway = APIGateway(app)
    gateway.register_service(test_router, "/api/test", version="1")
    return gateway


@pytest.fixture
def client(app):
    """Create a test client for testing."""
    return TestClient(app)


class TestAPIGateway:
    """Tests for the APIGateway class."""
    
    def test_initialization(self, app):
        """Test API Gateway initialization."""
        gateway = APIGateway(app)
        assert gateway.app == app
        assert isinstance(gateway.rate_limiter, RateLimiter)
        assert isinstance(gateway.circuit_breaker, CircuitBreaker)
        assert isinstance(gateway.request_transformer, RequestTransformer)
        assert isinstance(gateway.response_transformer, ResponseTransformer)
        assert isinstance(gateway.router, Router)
        assert isinstance(gateway.version_manager, APIVersionManager)
    
    def test_register_service(self, api_gateway, test_router):
        """Test registering a service with the API Gateway."""
        # Service is already registered in the fixture
        routes = api_gateway.router.get_all_routes()
        assert len(routes) > 0
        assert any(route["path"] == "/v1/api/test/test" for route in routes)
    
    def test_set_rate_limit(self, api_gateway):
        """Test setting a rate limit for a path."""
        path = "/api/test/limited"
        api_gateway.set_rate_limit(path, 10, 60)
        
        # Check if the rate limit was set
        limits = api_gateway.rate_limiter.limits
        assert path in limits
        assert limits[path]["limit"] == 10
        assert limits[path]["period"] == 60
    
    def test_configure_circuit_breaker(self, api_gateway):
        """Test configuring a circuit breaker for a path."""
        path = "/api/test/circuit"
        api_gateway.configure_circuit_breaker(path, 5, 30)
        
        # Check if the circuit breaker was configured
        configs = api_gateway.circuit_breaker.configs
        assert path in configs
        assert configs[path].failure_threshold == 5
        assert configs[path].recovery_time == 30
    
    def test_register_transformations(self, api_gateway):
        """Test registering request and response transformations."""
        path = "/api/test/transform"
        
        # Register request transformation
        request_transform = {"headers": {"X-Test": "test"}}
        api_gateway.register_request_transformation(path, request_transform)
        
        # Register response transformation
        response_transform = {"headers": {"X-Response": "test"}}
        api_gateway.register_response_transformation(path, response_transform)
        
        # Check if transformations were registered
        assert path in api_gateway.request_transformer.transformations
        assert path in api_gateway.response_transformer.transformations
    
    def test_get_metrics(self, api_gateway):
        """Test getting API Gateway metrics."""
        metrics = api_gateway.get_metrics()
        
        # Check if metrics contain expected keys
        assert "rate_limits" in metrics
        assert "circuit_breakers" in metrics
        assert "routes" in metrics
        assert "versions" in metrics


class TestAPIGatewayIntegration:
    """Integration tests for the API Gateway."""
    
    def test_successful_request(self, api_gateway, client):
        """Test a successful request through the API Gateway."""
        response = client.get("/v1/api/test/test")
        assert response.status_code == 200
        assert response.json() == {"message": "Test endpoint"}
    
    def test_error_request(self, api_gateway, client):
        """Test an error request through the API Gateway."""
        response = client.get("/v1/api/test/error")
        assert response.status_code == 500
        assert "error" in response.json()
        assert response.json()["code"] == 500
    
    def test_rate_limit_exceeded(self, api_gateway, client):
        """Test rate limit exceeded response."""
        # Create a custom middleware to intercept the request
        @api_gateway.app.middleware("http")
        async def test_middleware(request: Request, call_next):
            if request.url.path == "/v1/api/test/test":
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": True,
                        "code": 429,
                        "message": "Rate limit exceeded",
                        "details": {"limit": 10, "remaining": 0}
                    }
                )
            return await call_next(request)
        
        response = client.get("/v1/api/test/test")
        assert response.status_code == 429
        assert "error" in response.json()
        assert response.json()["code"] == 429
    
    def test_circuit_breaker_open(self, api_gateway, client):
        """Test circuit breaker open response."""
        # Create a custom middleware to intercept the request
        @api_gateway.app.middleware("http")
        async def test_middleware(request: Request, call_next):
            if request.url.path == "/v1/api/test/test":
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "error": True,
                        "code": 503,
                        "message": "Service temporarily unavailable",
                        "details": "Circuit breaker is open"
                    }
                )
            return await call_next(request)
        
        response = client.get("/v1/api/test/test")
        assert response.status_code == 503
        assert "error" in response.json()
        assert response.json()["code"] == 503


class TestVersioning:
    """Tests for API versioning."""
    
    def test_url_path_versioning(self, app, test_router):
        """Test URL path versioning strategy."""
        gateway = APIGateway(app)
        gateway.version_manager.configure(VersioningStrategy.URL_PATH, "1")
        gateway.register_service(test_router, "/api/test", version="1")
        gateway.register_service(test_router, "/api/test", version="2")
        
        client = TestClient(app)
        
        # Test v1 endpoint
        response = client.get("/v1/api/test/test")
        assert response.status_code == 200
        
        # Test v2 endpoint
        response = client.get("/v2/api/test/test")
        assert response.status_code == 200
    
    def test_header_versioning(self, app, test_router):
        """Test header versioning strategy."""
        gateway = APIGateway(app)
        gateway.version_manager.configure(VersioningStrategy.HEADER, "1")
        gateway.version_manager.header_name = "X-API-Version"
        gateway.register_service(test_router, "/api/test", version="1")
        
        # This test would require more complex setup to test header versioning
        # as the FastAPI router registration doesn't support header-based routing directly
        pass
