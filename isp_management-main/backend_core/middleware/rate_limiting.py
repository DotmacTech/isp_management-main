"""
Rate Limiting Middleware

This module provides middleware for implementing rate limiting on API requests.
It adds rate limit headers to responses and enforces rate limits based on client IP
or authenticated user.
"""

import time
from typing import Callable, Dict, Optional, Tuple, Union
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis

from backend_core.config import settings


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for implementing rate limiting.
    
    This middleware:
    1. Tracks request counts per client
    2. Adds rate limit headers to responses
    3. Rejects requests that exceed the rate limit
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        rate_limit: int = 100,
        rate_limit_window: int = 60,
        redis_url: Optional[str] = None
    ):
        """
        Initialize the rate limiting middleware.
        
        Args:
            app: The ASGI application
            rate_limit: Maximum number of requests allowed in the window
            rate_limit_window: Time window in seconds
            redis_url: Redis URL for distributed rate limiting
        """
        super().__init__(app)
        self.rate_limit = rate_limit
        self.rate_limit_window = rate_limit_window
        
        # Use Redis for distributed rate limiting if available
        if redis_url:
            self.redis = redis.from_url(redis_url)
            self.use_redis = True
        else:
            # In-memory storage for rate limiting
            self.request_counts = {}
            self.use_redis = False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and apply rate limiting.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response with rate limit headers added
        """
        # Get client identifier (IP address or user ID)
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        current_count, reset_time = self._get_rate_limit_data(client_id)
        
        # Add rate limit info to request state
        request.state.rate_limit = self.rate_limit
        request.state.rate_limit_remaining = max(0, self.rate_limit - current_count)
        request.state.rate_limit_reset = reset_time
        
        # Check if rate limit exceeded
        if current_count > self.rate_limit:
            return Response(
                content={"detail": "Rate limit exceeded"},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=self._get_rate_limit_headers(request)
            )
        
        # Increment request count
        self._increment_request_count(client_id)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers.update(self._get_rate_limit_headers(request))
        
        return response
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client.
        
        Uses authenticated user ID if available, otherwise IP address.
        
        Args:
            request: The incoming request
            
        Returns:
            A unique identifier for the client
        """
        # If user is authenticated, use user ID
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Otherwise use client IP
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def _get_rate_limit_data(self, client_id: str) -> Tuple[int, int]:
        """
        Get current request count and reset time for a client.
        
        Args:
            client_id: The client identifier
            
        Returns:
            Tuple of (current_count, reset_time)
        """
        current_time = int(time.time())
        window_start = current_time - (current_time % self.rate_limit_window)
        reset_time = window_start + self.rate_limit_window
        
        if self.use_redis:
            # Use Redis for distributed rate limiting
            key = f"rate_limit:{client_id}:{window_start}"
            current_count = int(self.redis.get(key) or 0)
            
            # Set expiry if key doesn't exist
            if current_count == 0:
                self.redis.set(key, 0, ex=self.rate_limit_window * 2)
        else:
            # Use in-memory storage
            key = f"{client_id}:{window_start}"
            current_count = self.request_counts.get(key, 0)
            
            # Clean up expired entries
            self._cleanup_expired_counts(current_time)
        
        return current_count, reset_time
    
    def _increment_request_count(self, client_id: str) -> None:
        """
        Increment the request count for a client.
        
        Args:
            client_id: The client identifier
        """
        current_time = int(time.time())
        window_start = current_time - (current_time % self.rate_limit_window)
        
        if self.use_redis:
            # Use Redis for distributed rate limiting
            key = f"rate_limit:{client_id}:{window_start}"
            self.redis.incr(key)
        else:
            # Use in-memory storage
            key = f"{client_id}:{window_start}"
            self.request_counts[key] = self.request_counts.get(key, 0) + 1
    
    def _cleanup_expired_counts(self, current_time: int) -> None:
        """
        Clean up expired rate limit entries from in-memory storage.
        
        Args:
            current_time: The current timestamp
        """
        if not self.use_redis:
            # Only needed for in-memory storage
            window_start = current_time - (current_time % self.rate_limit_window)
            expired_keys = [
                key for key in self.request_counts
                if int(key.split(":")[-1]) < window_start - self.rate_limit_window
            ]
            
            for key in expired_keys:
                del self.request_counts[key]
    
    def _get_rate_limit_headers(self, request: Request) -> Dict[str, str]:
        """
        Generate rate limit headers for the response.
        
        Args:
            request: The request object with rate limit state
            
        Returns:
            Dictionary of rate limit headers
        """
        return {
            "X-RateLimit-Limit": str(self.rate_limit),
            "X-RateLimit-Remaining": str(getattr(request.state, "rate_limit_remaining", 0)),
            "X-RateLimit-Reset": str(getattr(request.state, "rate_limit_reset", 0))
        }
