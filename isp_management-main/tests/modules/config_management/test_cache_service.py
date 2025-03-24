"""
Unit tests for the Configuration Management Module's cache service.

This module tests the functionality of the CacheService class, which
is responsible for caching frequently accessed configurations.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from modules.config_management.services.cache_service import CacheService


class TestCacheService:
    """Tests for the CacheService class."""
    
    def test_init(self):
        """Test initializing the cache service."""
        service = CacheService(default_ttl=60, cleanup_interval=3600)
        assert service.default_ttl == 60
        assert service.cleanup_interval == 3600
        assert service.cache == {}
        assert service.last_cleanup is not None
    
    def test_get_set_operations(self):
        """Test basic get and set operations."""
        service = CacheService(default_ttl=60)
        
        # Set a value
        service.set("test_key", "test_value")
        
        # Get the value
        value = service.get("test_key")
        assert value == "test_value"
        
        # Get a non-existent key
        value = service.get("non_existent_key")
        assert value is None
        
        # Get a non-existent key with default
        value = service.get("non_existent_key", default="default_value")
        assert value == "default_value"
    
    def test_set_with_custom_ttl(self):
        """Test setting a value with a custom TTL."""
        service = CacheService(default_ttl=60)
        
        # Set a value with a custom TTL
        service.set("test_key", "test_value", ttl=10)
        
        # Verify the value is cached
        value = service.get("test_key")
        assert value == "test_value"
        
        # Wait for the TTL to expire
        time.sleep(11)
        
        # Verify the value is no longer cached
        value = service.get("test_key")
        assert value is None
    
    def test_delete(self):
        """Test deleting a cached value."""
        service = CacheService(default_ttl=60)
        
        # Set a value
        service.set("test_key", "test_value")
        
        # Verify the value is cached
        value = service.get("test_key")
        assert value == "test_value"
        
        # Delete the value
        service.delete("test_key")
        
        # Verify the value is no longer cached
        value = service.get("test_key")
        assert value is None
        
        # Delete a non-existent key (should not raise an exception)
        service.delete("non_existent_key")
    
    def test_clear(self):
        """Test clearing the entire cache."""
        service = CacheService(default_ttl=60)
        
        # Set multiple values
        service.set("key1", "value1")
        service.set("key2", "value2")
        service.set("key3", "value3")
        
        # Verify the values are cached
        assert service.get("key1") == "value1"
        assert service.get("key2") == "value2"
        assert service.get("key3") == "value3"
        
        # Clear the cache
        service.clear()
        
        # Verify the values are no longer cached
        assert service.get("key1") is None
        assert service.get("key2") is None
        assert service.get("key3") is None
    
    def test_cleanup(self):
        """Test automatic cleanup of expired cache entries."""
        service = CacheService(default_ttl=1, cleanup_interval=2)
        
        # Set multiple values with different TTLs
        service.set("key1", "value1", ttl=0.5)  # Short TTL
        service.set("key2", "value2", ttl=10)   # Long TTL
        
        # Wait for key1 to expire
        time.sleep(1)
        
        # Force a cleanup
        with patch.object(service, '_should_cleanup', return_value=True):
            # Get any key to trigger cleanup
            service.get("key2")
        
        # Verify key1 was cleaned up and key2 is still cached
        assert service.get("key1") is None
        assert service.get("key2") == "value2"
    
    def test_get_many(self):
        """Test getting multiple cached values at once."""
        service = CacheService(default_ttl=60)
        
        # Set multiple values
        service.set("key1", "value1")
        service.set("key2", "value2")
        service.set("key3", "value3")
        
        # Get multiple values
        values = service.get_many(["key1", "key2", "non_existent_key"])
        
        # Verify the results
        assert values == {
            "key1": "value1",
            "key2": "value2",
            "non_existent_key": None
        }
    
    def test_set_many(self):
        """Test setting multiple cached values at once."""
        service = CacheService(default_ttl=60)
        
        # Set multiple values
        service.set_many({
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        })
        
        # Verify the values are cached
        assert service.get("key1") == "value1"
        assert service.get("key2") == "value2"
        assert service.get("key3") == "value3"
    
    def test_delete_many(self):
        """Test deleting multiple cached values at once."""
        service = CacheService(default_ttl=60)
        
        # Set multiple values
        service.set("key1", "value1")
        service.set("key2", "value2")
        service.set("key3", "value3")
        
        # Delete multiple values
        service.delete_many(["key1", "key2", "non_existent_key"])
        
        # Verify the results
        assert service.get("key1") is None
        assert service.get("key2") is None
        assert service.get("key3") == "value3"  # Not deleted
    
    def test_has_key(self):
        """Test checking if a key exists in the cache."""
        service = CacheService(default_ttl=60)
        
        # Set a value
        service.set("test_key", "test_value")
        
        # Check if keys exist
        assert service.has_key("test_key") is True
        assert service.has_key("non_existent_key") is False
        
        # Check if a key exists after it expires
        service.set("expiring_key", "value", ttl=1)
        time.sleep(1.5)
        assert service.has_key("expiring_key") is False
    
    def test_get_with_default_factory(self):
        """Test getting a value with a default factory function."""
        service = CacheService(default_ttl=60)
        
        # Define a factory function that returns a computed value
        def factory():
            return "computed_value"
        
        # Get a non-existent key with the factory
        value = service.get("non_existent_key", default_factory=factory)
        assert value == "computed_value"
        
        # Verify the computed value was not cached
        assert "non_existent_key" not in service.cache
    
    def test_get_or_set(self):
        """Test getting a value or setting it if it doesn't exist."""
        service = CacheService(default_ttl=60)
        
        # Define a factory function that returns a computed value
        def factory():
            return "computed_value"
        
        # Get or set a non-existent key
        value = service.get_or_set("test_key", factory)
        assert value == "computed_value"
        
        # Verify the value was cached
        assert service.get("test_key") == "computed_value"
        
        # Define a new factory function that should not be called
        def new_factory():
            return "new_value"
        
        # Get or set an existing key
        value = service.get_or_set("test_key", new_factory)
        assert value == "computed_value"  # Original value, not new_value
