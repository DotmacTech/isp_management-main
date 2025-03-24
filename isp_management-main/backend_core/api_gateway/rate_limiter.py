"""
Rate Limiter for the API Gateway.

This module provides rate limiting functionality for the API Gateway,
controlling API request volumes per client to prevent abuse and ensure
fair resource allocation.
"""

import time
import logging
from typing import Dict, Tuple, Optional, Any, Union
import asyncio

from fastapi import Request
from redis import Redis

from backend_core.api_gateway.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for controlling API request volumes.
    
    This class implements rate limiting functionality to prevent abuse
    and ensure fair resource allocation. It supports both in-memory
    and Redis-based rate limiting.
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize the rate limiter.
        
        Args:
            redis_client: Optional Redis client for distributed rate limiting
        """
        self.limits: Dict[str, Dict[str, int]] = {}
        self.counters: Dict[str, Dict[str, Any]] = {}
        self.redis_client = redis_client
        self.use_redis = redis_client is not None
        
        # Default rate limit settings
        self.default_limit = settings.default_rate_limit
        self.default_period = settings.default_rate_limit_period
    
    def set_rate_limit(self, path: str, limit: int, period: int) -> None:
        """
        Set a rate limit for a specific path.
        
        Args:
            path: API path to set limit for
            limit: Maximum number of requests allowed
            period: Time period in seconds
        """
        if limit <= 0:
            raise ValueError("Rate limit must be positive")
        if period <= 0:
            raise ValueError("Rate limit period must be positive")
            
        self.limits[path] = {
            "limit": limit,
            "period": period
        }
        logger.info(f"Rate limit set for {path}: {limit} requests per {period} seconds")
    
    def get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client making the request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Unique client identifier
        """
        # Use X-Forwarded-For header if available (for clients behind proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
        
        # Include the path in the identifier to apply per-endpoint limits
        path = request.url.path
        
        return f"{client_ip}:{path}"
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict[str, int]]:
        """
        Check if a request is allowed based on rate limits.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        path = request.url.path
        client_id = self.get_client_identifier(request)
        
        # Find the most specific rate limit for this path
        limit_config = None
        for limit_path, config in self.limits.items():
            if path.startswith(limit_path):
                limit_config = config
                break
        
        # Use default limits if no specific limit is set
        if limit_config is None:
            limit_config = {
                "limit": self.default_limit,
                "period": self.default_period
            }
        
        limit = limit_config["limit"]
        period = limit_config["period"]
        
        # Use Redis for distributed rate limiting if available
        if self.use_redis:
            try:
                return await self._check_redis_rate_limit(client_id, limit, period)
            except Exception as e:
                logger.error(f"Redis rate limiting failed: {e}")
                # Fall back to in-memory rate limiting
                return await self._check_memory_rate_limit(client_id, limit, period)
        else:
            # Use in-memory rate limiting
            return await self._check_memory_rate_limit(client_id, limit, period)
    
    def add_rate_limit_headers(self, response: Any, rate_limit_info: Dict[str, int]) -> None:
        """
        Add rate limit headers to the response.
        
        Args:
            response: FastAPI response object
            rate_limit_info: Rate limit information
        """
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])
    
    async def _check_memory_rate_limit(
        self, client_id: str, limit: int, period: int
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check rate limit using in-memory counters.
        
        Args:
            client_id: Unique client identifier
            limit: Maximum number of requests allowed
            period: Time period in seconds
            
        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        
        # Initialize counter if it doesn't exist
        if client_id not in self.counters:
            self.counters[client_id] = {
                "count": 0,
                "reset_at": current_time + period
            }
        
        counter = self.counters[client_id]
        
        # Reset counter if the period has expired
        if current_time > counter["reset_at"]:
            counter["count"] = 0
            counter["reset_at"] = current_time + period
        
        # Check if limit is exceeded
        is_allowed = counter["count"] < limit
        
        # Increment counter if allowed
        if is_allowed:
            counter["count"] += 1
        
        # Calculate remaining requests
        remaining = max(0, limit - counter["count"])
        
        return is_allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset": int(counter["reset_at"])
        }
    
    async def _check_redis_rate_limit(
        self, client_id: str, limit: int, period: int
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check rate limit using Redis.
        
        Args:
            client_id: Unique client identifier
            limit: Maximum number of requests allowed
            period: Time period in seconds
            
        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        
        # Get current count
        count = self.redis_client.incr(client_id)
        
        # Set expiry if this is the first request
        if count == 1:
            self.redis_client.expire(client_id, period)
        
        # Get TTL (time to live)
        ttl = self.redis_client.ttl(client_id)
        
        # Check if limit is exceeded
        is_allowed = count <= limit
        
        # Calculate remaining requests
        remaining = max(0, limit - count)
        
        return is_allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset": int(time.time() + ttl)
        }
    
    def get_metrics(self) -> list:
        """
        Get rate limiting metrics.
        
        Returns:
            list: List of rate limit metrics
        """
        metrics = []
        
        for path, limit_config in self.limits.items():
            # Count active clients for this path
            active_clients = 0
            for client_id, counter in self.counters.items():
                if client_id.endswith(f":{path}"):
                    active_clients += 1
            
            metrics.append({
                "path": path,
                "limit": limit_config["limit"],
                "period": limit_config["period"],
                "active_clients": active_clients
            })
        
        return metrics
