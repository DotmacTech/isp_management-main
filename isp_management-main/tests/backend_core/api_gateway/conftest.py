"""
Test fixtures for the API Gateway tests.

This module provides common fixtures for testing the API Gateway module,
including mocked Redis clients, FastAPI test clients, and sample requests.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from redis import Redis

from backend_core.api_gateway import (
    APIGateway, RateLimiter, CircuitBreaker,
    RequestTransformer, ResponseTransformer,
    Router, APIVersionManager, VersioningStrategy
)
from backend_core.api_gateway.config import settings


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    redis_mock = MagicMock(spec=Redis)
    
    # Create a separate mock for the pipeline
    pipeline_mock = MagicMock()
    pipeline_mock.execute.return_value = [1, True, 60]
    
    # Mock Redis methods used by the rate limiter and circuit breaker
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = 60
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    
    # Setup pipeline to return the pipeline mock
    redis_mock.pipeline.return_value = pipeline_mock
    
    return redis_mock


@pytest.fixture
def rate_limiter(mock_redis):
    """Create a RateLimiter instance with a mock Redis client."""
    limiter = RateLimiter(redis_client=mock_redis)
    limiter.set_rate_limit("/api/test", 10, 60)
    limiter.set_rate_limit("/api/auth", 5, 60)
    return limiter


@pytest.fixture
def rate_limiter_no_redis():
    """Create a RateLimiter instance without Redis for in-memory testing."""
    limiter = RateLimiter()
    limiter.set_rate_limit("/api/test", 10, 60)
    limiter.set_rate_limit("/api/auth", 5, 60)
    return limiter


@pytest.fixture
def circuit_breaker(mock_redis):
    """Create a CircuitBreaker instance for testing."""
    breaker = CircuitBreaker()
    # Replace the Redis client with our mock
    breaker.redis = mock_redis
    breaker.configure("/api/test", 5, 30)
    breaker.configure("/api/auth", 3, 60)
    return breaker


@pytest.fixture
def circuit_breaker_no_redis():
    """Create a CircuitBreaker instance without Redis for in-memory testing."""
    breaker = CircuitBreaker()
    # Set Redis to None to force in-memory mode
    breaker.redis = None
    breaker.configure("/api/test", 5, 30)
    breaker.configure("/api/auth", 3, 60)
    return breaker


@pytest.fixture
def request_transformer():
    """Create a RequestTransformer instance for testing."""
    transformer = RequestTransformer()
    transformer.add_transformation(
        "/api/test",
        headers={"X-Test-Header": "test-value"},
        query_params={"test_param": "test-value"}
    )
    return transformer


@pytest.fixture
def response_transformer():
    """Create a ResponseTransformer instance for testing."""
    transformer = ResponseTransformer()
    transformer.add_transformation(
        "/api/test",
        headers={"X-Response-Header": "response-value"},
        content_type="application/json"
    )
    return transformer


@pytest.fixture
def router():
    """Create a Router instance for testing."""
    router = Router()
    router.add_route("/api/test", "http://test-service:8000/test")
    router.add_route("/api/auth", "http://auth-service:8000/auth")
    return router


@pytest.fixture
def version_manager():
    """Create an APIVersionManager instance for testing."""
    manager = APIVersionManager(strategy=VersioningStrategy.URL_PATH)
    manager.add_version("1", active=True)
    manager.add_version("2", active=True)
    return manager


@pytest.fixture
def api_gateway(
    rate_limiter, circuit_breaker, request_transformer,
    response_transformer, router, version_manager
):
    """Create a fully configured APIGateway instance for testing."""
    gateway = APIGateway(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        request_transformer=request_transformer,
        response_transformer=response_transformer,
        router=router,
        version_manager=version_manager
    )
    return gateway


@pytest.fixture
def api_gateway_no_redis(
    rate_limiter_no_redis, circuit_breaker_no_redis, request_transformer,
    response_transformer, router, version_manager
):
    """Create an APIGateway instance without Redis for in-memory testing."""
    gateway = APIGateway(
        rate_limiter=rate_limiter_no_redis,
        circuit_breaker=circuit_breaker_no_redis,
        request_transformer=request_transformer,
        response_transformer=response_transformer,
        router=router,
        version_manager=version_manager
    )
    return gateway


@pytest.fixture
def test_app():
    """Create a FastAPI application for testing."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "Test endpoint"}
    
    @app.get("/auth")
    async def auth_endpoint():
        return {"message": "Auth endpoint"}
    
    return app


@pytest.fixture
def test_client(test_app):
    """Create a TestClient for the test FastAPI application."""
    return TestClient(test_app)


@pytest.fixture
def sample_request():
    """Create a sample FastAPI Request object for testing."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/api/test"
    mock_request.headers = {"X-Original-Header": "original-value"}
    mock_request.query_params = {}
    mock_request.client.host = "127.0.0.1"
    return mock_request


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
