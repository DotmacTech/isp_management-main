"""
Mock modules for testing the service availability monitoring feature.
This file creates mock versions of all the required dependencies to isolate the tests.
"""

import sys
from unittest.mock import MagicMock

# Create mock classes and modules
class MockServiceLog:
    """Mock ServiceLog model."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.elasticsearch_synced = False
    
    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class MockSystemMetric:
    """Mock SystemMetric model."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.elasticsearch_synced = False
    
    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class MockLoggingService:
    """Mock LoggingService."""
    def __init__(self, db=None):
        self.db = db
    
    def log_request(self, *args, **kwargs):
        return MockServiceLog(id="test-log")
    
    def log_response(self, *args, **kwargs):
        return MockServiceLog(id="test-log")
    
    def log_error(self, *args, **kwargs):
        return MockServiceLog(id="test-log")

class MockElasticsearchClient:
    """Mock ElasticsearchClient."""
    def __init__(self, hosts=None):
        self.hosts = hosts or ["http://localhost:9200"]
    
    def index(self, index, body, **kwargs):
        return {"result": "created", "_id": "test-id"}
    
    def bulk(self, body, **kwargs):
        return {"errors": False, "items": []}
    
    def search(self, index, body, **kwargs):
        return {"hits": {"total": {"value": 0}, "hits": []}}
    
    def indices(self):
        return MagicMock()

# Create mock modules
mock_service_log = MagicMock()
mock_service_log.ServiceLog = MockServiceLog

mock_system_metric = MagicMock()
mock_system_metric.SystemMetric = MockSystemMetric

mock_models = MagicMock()
mock_models.ServiceLog = MockServiceLog
mock_models.SystemMetric = MockSystemMetric

mock_services = MagicMock()
mock_services.LoggingService = MockLoggingService

mock_elasticsearch = MagicMock()
mock_elasticsearch.ElasticsearchClient = MockElasticsearchClient

mock_middleware = MagicMock()
mock_middleware.setup_request_logging = MagicMock()

# Register mock modules
sys.modules['modules.monitoring.models.service_log'] = mock_service_log
sys.modules['modules.monitoring.models.system_metric'] = mock_system_metric
sys.modules['modules.monitoring.models'] = mock_models
sys.modules['modules.monitoring.services'] = mock_services
sys.modules['modules.monitoring.elasticsearch'] = mock_elasticsearch
sys.modules['modules.monitoring.middleware'] = mock_middleware

# Mock FastAPI dependencies
mock_fastapi = MagicMock()
sys.modules['fastapi'] = mock_fastapi

# Mock SQLAlchemy
mock_sqlalchemy = MagicMock()
sys.modules['sqlalchemy'] = mock_sqlalchemy

# Mock Redis
mock_redis = MagicMock()
sys.modules['redis'] = mock_redis

# Mock requests
mock_requests = MagicMock()
sys.modules['requests'] = mock_requests
