"""
Tests for the API Gateway rate limiter component.

This module contains tests for the RateLimiter class, which provides
rate limiting functionality for the API Gateway.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import time
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from redis import Redis

from fastapi import Request

from backend_core.api_gateway.rate_limiter import RateLimiter


@pytest.fixture
def rate_limiter():
    """Create a RateLimiter instance for testing."""
    limiter = RateLimiter()
    # Set specific limits for testing
    limiter.set_rate_limit("/api/test", 10, 60)
    return limiter


@pytest.fixture
def rate_limiter_no_redis():
    """Create a RateLimiter instance without Redis for testing."""
    limiter = RateLimiter(redis_client=None)
    # Set specific limits for testing
    limiter.set_rate_limit("/api/test", 10, 60)
    return limiter


@pytest.fixture
def sample_request():
    """Create a sample Request object for testing."""
    mock_req = MagicMock(spec=Request)
    mock_req.url.path = "/api/test"
    mock_req.headers = {}
    mock_req.client.host = "127.0.0.1"
    return mock_req


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    return MagicMock(spec=Redis)


class TestRateLimiter:
    """Tests for the RateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_set_rate_limit(self, rate_limiter):
        """Test setting rate limits for paths."""
        # Set a new rate limit
        rate_limiter.set_rate_limit("/api/new", 20, 30)
        
        # Verify the limit was set
        assert "/api/new" in rate_limiter.limits
        assert rate_limiter.limits["/api/new"]["limit"] == 20
        assert rate_limiter.limits["/api/new"]["period"] == 30
    
    @pytest.mark.asyncio
    async def test_set_rate_limit_validation(self, rate_limiter):
        """Test validation when setting rate limits."""
        # Test with invalid limit
        with pytest.raises(ValueError):
            rate_limiter.set_rate_limit("/api/invalid", 0, 30)
        
        # Test with invalid period
        with pytest.raises(ValueError):
            rate_limiter.set_rate_limit("/api/invalid", 10, 0)
    
    @pytest.mark.asyncio
    async def test_get_client_identifier(self, rate_limiter, sample_request):
        """Test client identifier generation."""
        # Test with X-Forwarded-For header
        sample_request.headers = {"X-Forwarded-For": "192.168.1.1"}
        client_id = rate_limiter.get_client_identifier(sample_request)
        assert client_id == "192.168.1.1:/api/test"
        
        # Test without X-Forwarded-For header
        sample_request.headers = {}
        client_id = rate_limiter.get_client_identifier(sample_request)
        assert client_id == "127.0.0.1:/api/test"
    
    @pytest.mark.asyncio
    @patch('backend_core.api_gateway.rate_limiter.RateLimiter._check_redis_rate_limit')
    async def test_check_rate_limit_with_redis(self, mock_check_redis, rate_limiter, sample_request, mock_redis):
        """Test rate limiting with Redis."""
        # Replace the Redis client with our mock
        rate_limiter.redis_client = mock_redis
        rate_limiter.use_redis = True
        
        # Mock the _check_redis_rate_limit method to return controlled values
        # First request - allowed with 9 remaining
        mock_check_redis.return_value = (True, {"limit": 10, "remaining": 9, "reset": int(time.time() + 60)})
        is_allowed, info = await rate_limiter.check_rate_limit(sample_request)
        assert is_allowed is True
        assert info["limit"] == 10
        assert info["remaining"] == 9
        
        # Second request - at the limit with 0 remaining
        mock_check_redis.return_value = (True, {"limit": 10, "remaining": 0, "reset": int(time.time() + 30)})
        is_allowed, info = await rate_limiter.check_rate_limit(sample_request)
        assert is_allowed is True
        assert info["remaining"] == 0
        
        # Third request - exceeding the limit
        mock_check_redis.return_value = (False, {"limit": 10, "remaining": 0, "reset": int(time.time() + 25)})
        is_allowed, info = await rate_limiter.check_rate_limit(sample_request)
        assert is_allowed is False
        assert info["remaining"] == 0
        
        # Verify the mock was called with the expected arguments
        client_id = rate_limiter.get_client_identifier(sample_request)
        mock_check_redis.assert_called_with(client_id, 10, 60)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_in_memory(self, rate_limiter_no_redis, sample_request):
        """Test in-memory rate limiting."""
        # First request should be allowed
        is_allowed, info = await rate_limiter_no_redis.check_rate_limit(sample_request)
        assert is_allowed is True
        assert info["limit"] == 10  # We set this limit in the fixture
        assert info["remaining"] == 9
        
        # Make multiple requests to approach the limit
        for i in range(8):
            is_allowed, info = await rate_limiter_no_redis.check_rate_limit(sample_request)
            assert is_allowed is True
            assert info["remaining"] == 9 - (i + 1)
        
        # Last allowed request
        is_allowed, info = await rate_limiter_no_redis.check_rate_limit(sample_request)
        assert is_allowed is True
        assert info["remaining"] == 0
        
        # This request should exceed the limit
        is_allowed, info = await rate_limiter_no_redis.check_rate_limit(sample_request)
        assert is_allowed is False
        assert info["remaining"] == 0
    
    @pytest.mark.asyncio
    async def test_redis_fallback(self, rate_limiter, sample_request, mock_redis):
        """Test fallback to in-memory rate limiting when Redis fails."""
        # Replace the Redis client with our mock
        rate_limiter.redis_client = mock_redis
        
        # Make Redis fail
        mock_redis.incr.side_effect = Exception("Redis connection error")
        
        # Should fall back to in-memory rate limiting
        is_allowed, info = await rate_limiter.check_rate_limit(sample_request)
        assert is_allowed is True
        
        # Verify we're using in-memory counters
        client_id = rate_limiter.get_client_identifier(sample_request)
        assert client_id in rate_limiter.counters
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self, rate_limiter_no_redis, sample_request):
        """Test that rate limits reset after the specified period."""
        # Set a shorter period for testing
        rate_limiter_no_redis.set_rate_limit("/api/test", 5, 1)  # 5 requests per 1 second
        
        # Fill up to the limit
        for _ in range(5):
            is_allowed, _ = await rate_limiter_no_redis.check_rate_limit(sample_request)
            assert is_allowed is True
        
        # Next request should be blocked
        is_allowed, _ = await rate_limiter_no_redis.check_rate_limit(sample_request)
        assert is_allowed is False
        
        # Wait for the rate limit to reset
        time.sleep(1.1)  # Wait just over 1 second
        
        # Should be allowed again
        is_allowed, _ = await rate_limiter_no_redis.check_rate_limit(sample_request)
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_default_limits(self, rate_limiter_no_redis):
        """Test that default limits are applied for paths without specific limits."""
        # Create a request for a path without specific limits
        mock_req = MagicMock(spec=Request)
        mock_req.url.path = "/api/no-specific-limit"
        mock_req.headers = {}
        mock_req.client.host = "127.0.0.1"
        
        # Check the rate limit
        is_allowed, info = await rate_limiter_no_redis.check_rate_limit(mock_req)
        
        # Should use default limit (100)
        assert is_allowed is True
        assert info["limit"] == 100
        assert info["remaining"] == 99
    
    def test_get_metrics(self, rate_limiter_no_redis, sample_request):
        """Test getting rate limiting metrics."""
        # Set up some rate limits
        rate_limiter_no_redis.set_rate_limit("/api/path1", 10, 60)
        rate_limiter_no_redis.set_rate_limit("/api/path2", 20, 120)
        
        # Make some requests to generate metrics
        asyncio.run(rate_limiter_no_redis.check_rate_limit(sample_request))
        
        # Create a request for a different path
        mock_req2 = MagicMock(spec=Request)
        mock_req2.url.path = "/api/path1"
        mock_req2.headers = {}
        mock_req2.client.host = "127.0.0.1"
        asyncio.run(rate_limiter_no_redis.check_rate_limit(mock_req2))
        
        # Get metrics
        metrics = rate_limiter_no_redis.get_metrics()
        
        # Verify metrics
        assert len(metrics) >= 2  # At least the paths we configured
        
        # Check that our paths are in the metrics
        paths = [m["path"] for m in metrics]
        assert "/api/test" in paths
        assert "/api/path1" in paths
