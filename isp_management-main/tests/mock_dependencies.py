"""
Mock dependencies for testing the ISP Management Platform.

This module provides mock implementations of external dependencies
such as Redis, Elasticsearch, and authentication services.
"""

import sys
from unittest import mock
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

# Mock Redis exceptions
class RedisError(Exception):
    """Base exception for Redis errors"""
    pass

class ConnectionError(RedisError):
    """Redis connection error"""
    pass

class TimeoutError(RedisError):
    """Redis timeout error"""
    pass

class ResponseError(RedisError):
    """Redis response error"""
    pass

class WatchError(RedisError):
    """Redis watch error"""
    pass

class LockError(RedisError):
    """Redis lock error"""
    pass

# Create a mock redis module with exceptions
class MockRedisModule:
    def __init__(self):
        self.exceptions = type('exceptions', (), {
            'RedisError': RedisError,
            'ConnectionError': ConnectionError,
            'TimeoutError': TimeoutError,
            'ResponseError': ResponseError,
            'WatchError': WatchError,
            'LockError': LockError
        })

# Mock User for authentication
class MockUser:
    """Mock user for authentication testing."""
    
    def __init__(self, id="test-user", username="test", email="test@example.com", 
                 is_active=True, is_admin=True):
        self.id = id
        self.username = username
        self.email = email
        self.is_active = is_active
        self.is_admin = is_admin
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


# Mock Redis implementation
class MockRedis:
    """Mock Redis implementation for testing."""
    
    def __init__(self, *args, **kwargs):
        self.data = {}
        self.pubsub_channels = {}
    
    def get(self, key):
        """Get a value from the mock Redis."""
        return self.data.get(key)
    
    def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        """Set a value in the mock Redis."""
        self.data[key] = value
        return True
    
    def delete(self, *keys):
        """Delete keys from the mock Redis."""
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                count += 1
        return count
    
    def exists(self, key):
        """Check if a key exists in the mock Redis."""
        return key in self.data
    
    def expire(self, key, time):
        """Set an expiration on a key."""
        if key in self.data:
            return True
        return False
    
    def pubsub(self, **kwargs):
        """Get a PubSub object."""
        return MockPubSub(self)
    
    def publish(self, channel, message):
        """Publish a message to a channel."""
        if channel not in self.pubsub_channels:
            self.pubsub_channels[channel] = []
        self.pubsub_channels[channel].append(message)
        return len(self.pubsub_channels[channel])


class MockPubSub:
    """Mock PubSub implementation for Redis."""
    
    def __init__(self, redis):
        self.redis = redis
        self.channels = {}
        self.patterns = {}
        self.subscribed = False
    
    def subscribe(self, *channels):
        """Subscribe to channels."""
        for channel in channels:
            self.channels[channel] = []
        self.subscribed = True
    
    def psubscribe(self, *patterns):
        """Subscribe to patterns."""
        for pattern in patterns:
            self.patterns[pattern] = []
        self.subscribed = True
    
    def get_message(self, timeout=None):
        """Get a message from subscribed channels."""
        for channel, messages in self.redis.pubsub_channels.items():
            if channel in self.channels and messages:
                return {
                    'type': 'message',
                    'channel': channel,
                    'data': messages.pop(0)
                }
        return None


# Mock Elasticsearch implementation
class MockElasticsearch:
    """Mock Elasticsearch implementation for testing."""
    
    def __init__(self, hosts=None, **kwargs):
        self.hosts = hosts or ["http://localhost:9200"]
        self.indices = MockIndices()
        self.data = {}  # Store indexed documents
    
    def index(self, index, body, id=None, **kwargs):
        """Index a document."""
        if index not in self.data:
            self.data[index] = {}
        
        doc_id = id or f"doc_{len(self.data[index]) + 1}"
        self.data[index][doc_id] = body
        
        return {
            "_index": index,
            "_id": doc_id,
            "_version": 1,
            "result": "created",
            "_shards": {
                "total": 2,
                "successful": 2,
                "failed": 0
            },
            "_seq_no": 0,
            "_primary_term": 1
        }
    
    def bulk(self, body, **kwargs):
        """Perform bulk operations."""
        items = []
        
        # Process bulk operations
        for i in range(0, len(body), 2):
            if i + 1 < len(body):
                action = list(body[i].keys())[0]
                index = body[i][action].get("_index")
                doc_id = body[i][action].get("_id")
                
                if action == "index" or action == "create":
                    if index not in self.data:
                        self.data[index] = {}
                    
                    self.data[index][doc_id] = body[i + 1]
                    items.append({
                        action: {
                            "_index": index,
                            "_id": doc_id,
                            "_version": 1,
                            "result": "created",
                            "_shards": {
                                "total": 2,
                                "successful": 2,
                                "failed": 0
                            },
                            "status": 201
                        }
                    })
                
                elif action == "update":
                    if index in self.data and doc_id in self.data[index]:
                        if "doc" in body[i + 1]:
                            for key, value in body[i + 1]["doc"].items():
                                self.data[index][doc_id][key] = value
                        
                        items.append({
                            action: {
                                "_index": index,
                                "_id": doc_id,
                                "_version": 2,
                                "result": "updated",
                                "_shards": {
                                    "total": 2,
                                    "successful": 2,
                                    "failed": 0
                                },
                                "status": 200
                            }
                        })
                
                elif action == "delete":
                    if index in self.data and doc_id in self.data[index]:
                        del self.data[index][doc_id]
                        items.append({
                            action: {
                                "_index": index,
                                "_id": doc_id,
                                "_version": 2,
                                "result": "deleted",
                                "_shards": {
                                    "total": 2,
                                    "successful": 2,
                                    "failed": 0
                                },
                                "status": 200
                            }
                        })
        
        return {
            "took": 5,
            "errors": False,
            "items": items
        }
    
    def search(self, index, body=None, **kwargs):
        """Search for documents."""
        hits = []
        
        if index in self.data:
            for doc_id, doc in self.data[index].items():
                hits.append({
                    "_index": index,
                    "_id": doc_id,
                    "_score": 1.0,
                    "_source": doc
                })
        
        return {
            "took": 5,
            "timed_out": False,
            "_shards": {
                "total": 5,
                "successful": 5,
                "skipped": 0,
                "failed": 0
            },
            "hits": {
                "total": {
                    "value": len(hits),
                    "relation": "eq"
                },
                "max_score": 1.0,
                "hits": hits
            }
        }
    
    def get(self, index, id, **kwargs):
        """Get a document by ID."""
        if index in self.data and id in self.data[index]:
            return {
                "_index": index,
                "_id": id,
                "_version": 1,
                "_seq_no": 0,
                "_primary_term": 1,
                "found": True,
                "_source": self.data[index][id]
            }
        
        return {
            "_index": index,
            "_id": id,
            "found": False
        }
    
    def delete(self, index, id, **kwargs):
        """Delete a document by ID."""
        if index in self.data and id in self.data[index]:
            del self.data[index][id]
            return {
                "_index": index,
                "_id": id,
                "_version": 1,
                "result": "deleted",
                "_shards": {
                    "total": 2,
                    "successful": 2,
                    "failed": 0
                },
                "_seq_no": 0,
                "_primary_term": 1
            }
        
        return {
            "_index": index,
            "_id": id,
            "_version": 1,
            "result": "not_found",
            "_shards": {
                "total": 2,
                "successful": 2,
                "failed": 0
            },
            "_seq_no": 0,
            "_primary_term": 1
        }
    
    def ping(self, **kwargs):
        """Check if Elasticsearch is available."""
        return True


class MockIndices:
    """Mock Indices implementation for Elasticsearch."""
    
    def __init__(self):
        self.indices = {}
    
    def create(self, index, body=None, **kwargs):
        """Create an index."""
        self.indices[index] = body or {}
        return {"acknowledged": True, "shards_acknowledged": True, "index": index}
    
    def exists(self, index, **kwargs):
        """Check if an index exists."""
        return index in self.indices
    
    def delete(self, index, **kwargs):
        """Delete an index."""
        if index in self.indices:
            del self.indices[index]
            return {"acknowledged": True}
        return {"acknowledged": False, "error": f"index '{index}' not found"}
    
    def refresh(self, index, **kwargs):
        """Refresh an index."""
        return {"_shards": {"total": 5, "successful": 5, "failed": 0}}
    
    def put_template(self, name, body, **kwargs):
        """Put an index template."""
        return {"acknowledged": True}
    
    def put_index_template(self, name, body, **kwargs):
        """Put an index template (ES 7.x+)."""
        return {"acknowledged": True}


# Mock authentication service
class MockAuthService:
    """Mock authentication service for testing."""
    
    def __init__(self):
        self.users = {
            "test-user": MockUser()
        }
    
    def get_current_user(self, *args, **kwargs):
        """Get the current user."""
        return self.users["test-user"]
    
    def get_current_active_user(self, *args, **kwargs):
        """Get the current active user."""
        user = self.users["test-user"]
        if not user.is_active:
            raise ValueError("Inactive user")
        return user
    
    def get_current_admin_user(self, *args, **kwargs):
        """Get the current admin user."""
        user = self.users["test-user"]
        if not user.is_admin:
            raise ValueError("Not an admin user")
        return user


# Function to set up mock dependencies
def setup_mock_dependencies():
    """
    Set up mock dependencies for testing.
    
    This function patches various modules with mock implementations
    to allow for isolated testing without external dependencies.
    
    Returns:
        dict: A dictionary of mock objects.
    """
    # Create mock objects
    mock_redis = MockRedis()
    mock_redis_module = MockRedisModule()
    mock_elasticsearch = MockElasticsearch()
    mock_auth_service = MockAuthService()
    
    # Add mock modules to sys.modules
    sys.modules["redis"] = mock.MagicMock()
    sys.modules["redis.Redis"] = MockRedis
    sys.modules["redis.exceptions"] = mock_redis_module.exceptions
    
    sys.modules["elasticsearch"] = mock.MagicMock()
    sys.modules["elasticsearch.Elasticsearch"] = MockElasticsearch
    
    # Mock authentication modules
    auth_mock = mock.MagicMock()
    auth_mock.get_current_user = mock_auth_service.get_current_user
    auth_mock.get_current_active_user = mock_auth_service.get_current_active_user
    auth_mock.get_current_admin_user = mock_auth_service.get_current_admin_user
    
    sys.modules["backend_core.auth"] = auth_mock
    sys.modules["isp_management.backend_core.auth"] = auth_mock
    
    # Return mock objects for use in tests
    return {
        "redis": mock_redis,
        "elasticsearch": mock_elasticsearch,
        "auth_service": mock_auth_service
    }
