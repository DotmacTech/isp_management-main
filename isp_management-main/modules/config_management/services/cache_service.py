"""
Cache service for the Configuration Management Module.

This service provides caching capabilities for frequently accessed configurations
to reduce database load and improve performance.
"""

import logging
import time
from typing import Any, Dict, Optional, List, Union, Callable
import json
import threading
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class CacheItem:
    """Class representing a cached item with expiration."""
    
    def __init__(self, value: Any, ttl: int = 300):
        """
        Initialize a cache item.
        
        Args:
            value: The value to cache
            ttl: Time to live in seconds (default: 5 minutes)
        """
        self.value = value
        self.expiry = datetime.utcnow() + timedelta(seconds=ttl)
    
    def is_expired(self) -> bool:
        """
        Check if the cache item is expired.
        
        Returns:
            True if expired, False otherwise
        """
        return datetime.utcnow() > self.expiry


class CacheService:
    """Service for caching frequently accessed configurations."""
    
    def __init__(self, default_ttl: int = 300, cleanup_interval: int = 3600):
        """
        Initialize the cache service.
        
        Args:
            default_ttl: Default time to live in seconds (default: 5 minutes)
            cleanup_interval: Interval for cleanup thread in seconds (default: 1 hour)
        """
        self.cache = {}
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.lock = threading.RLock()
        self.last_cleanup = datetime.utcnow()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_loop(self):
        """Background thread to periodically clean up expired cache items."""
        while True:
            time.sleep(self.cleanup_interval)
            try:
                if self._should_cleanup():
                    self.cleanup()
            except Exception as e:
                logger.error(f"Error in cache cleanup: {str(e)}")
    
    def _should_cleanup(self) -> bool:
        """
        Determine if a cleanup operation should be performed.
        
        Returns:
            True if cleanup should be performed, False otherwise
        """
        now = datetime.utcnow()
        time_since_last_cleanup = (now - self.last_cleanup).total_seconds()
        return time_since_last_cleanup >= self.cleanup_interval
    
    def cleanup(self):
        """Remove expired items from the cache."""
        with self.lock:
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")
            
            self.last_cleanup = datetime.utcnow()
            return len(expired_keys)
    
    def get(self, key: str, default: Any = None, default_factory: Callable = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value to return if key is not found
            default_factory: Callable that returns a default value
            
        Returns:
            Cached value if found and not expired, default value or default_factory() result otherwise
        """
        with self.lock:
            if key in self.cache:
                item = self.cache[key]
                if not item.is_expired():
                    return item.value
                else:
                    # Remove expired item
                    del self.cache[key]
            
            # Return default value if key not found or expired
            if default_factory is not None:
                return default_factory()
            return default
    
    def has_key(self, key: str) -> bool:
        """
        Check if a key exists in the cache and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and not expired, False otherwise
        """
        with self.lock:
            if key in self.cache:
                item = self.cache[key]
                if not item.is_expired():
                    return True
                else:
                    # Remove expired item
                    del self.cache[key]
            return False
    
    def get_many(self, keys: List[str], default: Any = None) -> Dict[str, Any]:
        """
        Get multiple values from the cache.
        
        Args:
            keys: List of cache keys
            default: Default value for keys not found in cache
            
        Returns:
            Dictionary mapping keys to values
        """
        result = {}
        for key in keys:
            result[key] = self.get(key, default=default)
        return result
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (if None, uses default_ttl)
        """
        with self.lock:
            self.cache[key] = CacheItem(value, ttl or self.default_ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was found and deleted, False otherwise
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear the entire cache."""
        with self.lock:
            self.cache.clear()
    
    def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Set multiple values in the cache.
        
        Args:
            items: Dictionary of keys and values to cache
            ttl: Time to live in seconds (if None, uses default_ttl)
        """
        with self.lock:
            for key, value in items.items():
                self.set(key, value, ttl)
    
    def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple values from the cache.
        
        Args:
            keys: List of cache keys to delete
            
        Returns:
            Number of keys deleted
        """
        count = 0
        with self.lock:
            for key in keys:
                if key in self.cache:
                    del self.cache[key]
                    count += 1
        return count
    
    def get_or_set(self, key: str, default_factory: Callable, ttl: Optional[int] = None) -> Any:
        """
        Get a value from the cache, or set it if not found.
        
        Args:
            key: Cache key
            default_factory: Function to call to get the default value if not in cache
            ttl: Time to live in seconds (if None, uses default_ttl)
            
        Returns:
            Cached value if found, or new value from default_factory
        """
        with self.lock:
            value = self.get(key)
            if value is None:
                value = default_factory()
                self.set(key, value, ttl)
            return value
            
    # Configuration-specific cache methods
    
    def set_configuration(self, config, ttl: Optional[int] = None) -> None:
        """
        Cache a configuration value.
        
        Args:
            config: Configuration object
            ttl: Time to live in seconds (if None, uses default_ttl)
        """
        cache_key = f"config:{config.environment}:{config.key}"
        self.set(cache_key, config, ttl)
    
    def get_configuration(self, key: str, environment: str) -> Any:
        """
        Get a cached configuration value.
        
        Args:
            key: Configuration key
            environment: Configuration environment
            
        Returns:
            Cached configuration value if found, None otherwise
        """
        cache_key = f"config:{environment}:{key}"
        return self.get(cache_key)
    
    def delete_configuration(self, key: str, environment: str) -> bool:
        """
        Delete a cached configuration value.
        
        Args:
            key: Configuration key
            environment: Configuration environment
            
        Returns:
            True if the key was deleted, False otherwise
        """
        cache_key = f"config:{environment}:{key}"
        return self.delete(cache_key)
    
    def reset_configuration_cache(self) -> None:
        """
        Reset the entire configuration cache.
        Removes all cached configuration values.
        """
        with self.lock:
            config_keys = [k for k in self.cache.keys() if k.startswith("config:")]
            for key in config_keys:
                del self.cache[key]
    
    def increment(self, key: str, delta: int = 1) -> int:
        """
        Increment a numeric value in the cache.
        
        Args:
            key: Cache key
            delta: Amount to increment by
            
        Returns:
            New value
            
        Raises:
            ValueError: If the cached value is not a number
        """
        with self.lock:
            value = self.get(key)
            if value is None:
                value = 0
            
            if not isinstance(value, (int, float)):
                raise ValueError(f"Cannot increment non-numeric value: {value}")
            
            new_value = value + delta
            self.set(key, new_value)
            return new_value
    
    def decrement(self, key: str, delta: int = 1) -> int:
        """
        Decrement a numeric value in the cache.
        
        Args:
            key: Cache key
            delta: Amount to decrement by
            
        Returns:
            New value
            
        Raises:
            ValueError: If the cached value is not a number
        """
        return self.increment(key, -delta)
    
    def touch(self, key: str, ttl: Optional[int] = None) -> bool:
        """
        Update the expiration time of a cached item.
        
        Args:
            key: Cache key
            ttl: New time to live in seconds (if None, uses default_ttl)
            
        Returns:
            True if key was found and updated, False otherwise
        """
        with self.lock:
            if key in self.cache:
                value = self.cache[key].value
                self.set(key, value, ttl)
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            total_items = len(self.cache)
            expired_items = sum(1 for item in self.cache.values() if item.is_expired())
            
            return {
                "total_items": total_items,
                "active_items": total_items - expired_items,
                "expired_items": expired_items
            }
