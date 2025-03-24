"""
Caching functionality for the UNMS API client.
"""
import json
import logging
import time
from typing import Optional, Any, Dict, List, Union
import re

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger('unms_api')


class CacheManager:
    """
    Cache manager for UNMS API.
    
    This class provides caching functionality for API responses.
    """
    
    def __init__(self, enabled: bool = False, default_ttl: int = 300, redis_url: Optional[str] = None):
        """
        Initialize the cache manager.
        
        Args:
            enabled (bool, optional): Whether caching is enabled. Defaults to False.
            default_ttl (int, optional): Default TTL for cached items in seconds. Defaults to 300.
            redis_url (Optional[str], optional): Redis URL for external caching. Defaults to None.
        """
        self._enabled = enabled
        self._default_ttl = default_ttl
        self._redis_url = redis_url
        self._redis = None
        self._memory_cache = {}
        
        if enabled and redis_url and REDIS_AVAILABLE:
            try:
                self._redis = redis.from_url(redis_url)
                logger.info(f"Connected to Redis cache at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                logger.info("Falling back to in-memory cache")
        elif enabled:
            logger.info("Using in-memory cache")
    
    def is_enabled(self) -> bool:
        """
        Check if caching is enabled.
        
        Returns:
            bool: Whether caching is enabled.
        """
        return self._enabled
    
    def _get_from_memory(self, key: str) -> Optional[Any]:
        """
        Get an item from the in-memory cache.
        
        Args:
            key (str): Cache key.
            
        Returns:
            Optional[Any]: Cached item or None if not found or expired.
        """
        if key not in self._memory_cache:
            return None
        
        item = self._memory_cache[key]
        
        # Check if item is expired
        if item['expires'] < time.time():
            del self._memory_cache[key]
            return None
        
        return item['data']
    
    def _set_in_memory(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set an item in the in-memory cache.
        
        Args:
            key (str): Cache key.
            value (Any): Value to cache.
            ttl (Optional[int], optional): TTL in seconds. Defaults to None.
        """
        if ttl is None:
            ttl = self._default_ttl
        
        self._memory_cache[key] = {
            'data': value,
            'expires': time.time() + ttl
        }
    
    def _get_from_redis(self, key: str) -> Optional[Any]:
        """
        Get an item from the Redis cache.
        
        Args:
            key (str): Cache key.
            
        Returns:
            Optional[Any]: Cached item or None if not found.
        """
        if not self._redis:
            return None
        
        try:
            data = self._redis.get(f"unms_api:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Error getting from Redis cache: {e}")
            return None
    
    def _set_in_redis(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set an item in the Redis cache.
        
        Args:
            key (str): Cache key.
            value (Any): Value to cache.
            ttl (Optional[int], optional): TTL in seconds. Defaults to None.
        """
        if not self._redis:
            return
        
        if ttl is None:
            ttl = self._default_ttl
        
        try:
            serialized = json.dumps(value)
            self._redis.setex(f"unms_api:{key}", ttl, serialized)
        except Exception as e:
            logger.warning(f"Error setting in Redis cache: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get an item from the cache.
        
        Args:
            key (str): Cache key.
            
        Returns:
            Optional[Any]: Cached item or None if not found.
        """
        if not self._enabled:
            return None
        
        # Try Redis first if available
        if self._redis:
            data = self._get_from_redis(key)
            if data is not None:
                return data
        
        # Fall back to in-memory cache
        return self._get_from_memory(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set an item in the cache.
        
        Args:
            key (str): Cache key.
            value (Any): Value to cache.
            ttl (Optional[int], optional): TTL in seconds. Defaults to None.
        """
        if not self._enabled:
            return
        
        # Set in Redis if available
        if self._redis:
            self._set_in_redis(key, value, ttl)
        
        # Always set in memory cache as fallback
        self._set_in_memory(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete an item from the cache.
        
        Args:
            key (str): Cache key.
            
        Returns:
            bool: Whether the item was deleted.
        """
        if not self._enabled:
            return False
        
        deleted = False
        
        # Delete from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
            deleted = True
        
        # Delete from Redis if available
        if self._redis:
            try:
                redis_deleted = self._redis.delete(f"unms_api:{key}")
                deleted = deleted or redis_deleted > 0
            except Exception as e:
                logger.warning(f"Error deleting from Redis cache: {e}")
        
        return deleted
    
    def clear(self) -> None:
        """
        Clear the entire cache.
        """
        if not self._enabled:
            return
        
        # Clear memory cache
        self._memory_cache = {}
        
        # Clear Redis cache if available
        if self._redis:
            try:
                keys = self._redis.keys("unms_api:*")
                if keys:
                    self._redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Error clearing Redis cache: {e}")
    
    def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern (str): Pattern to match.
            
        Returns:
            int: Number of invalidated entries.
        """
        if not self._enabled:
            return 0
        
        count = 0
        
        # Invalidate in memory cache
        regex = re.compile(pattern)
        keys_to_delete = [k for k in self._memory_cache.keys() if regex.search(k)]
        for key in keys_to_delete:
            del self._memory_cache[key]
            count += 1
        
        # Invalidate in Redis if available
        if self._redis:
            try:
                keys = self._redis.keys(f"unms_api:*{pattern}*")
                if keys:
                    count += len(keys)
                    self._redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Error invalidating Redis cache: {e}")
        
        return count
