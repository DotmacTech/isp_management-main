"""
Tests for the Router and Versioning components of the API Gateway.

This module contains tests for the Router and APIVersionManager classes,
which handle request routing and API versioning respectively.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import MagicMock

from fastapi import APIRouter
from fastapi.routing import APIRoute

from backend_core.api_gateway.router import Router, RouteMetrics
from backend_core.api_gateway.versioning import APIVersionManager, VersioningStrategy


@pytest.fixture
def router():
    """Create a Router instance for testing."""
    return Router()


@pytest.fixture
def version_manager():
    """Create an APIVersionManager instance for testing."""
    return APIVersionManager()


@pytest.fixture
def mock_routes():
    """Create mock FastAPI routes for testing."""
    route1 = MagicMock(spec=APIRoute)
    route1.path = "/users"
    route1.methods = {"GET", "POST"}
    route1.name = "get_users"
    route1.endpoint = lambda: None
    
    route2 = MagicMock(spec=APIRoute)
    route2.path = "/users/{user_id}"
    route2.methods = {"GET", "PUT", "DELETE"}
    route2.name = "get_user"
    route2.endpoint = lambda: None
    
    return [route1, route2]


class TestRouter:
    """Tests for the Router class."""
    
    def test_initialization(self):
        """Test Router initialization."""
        router_instance = Router()
        assert router_instance.routes == {}
        assert router_instance.hit_counts == {}
    
    def test_register_routes(self, router, mock_routes):
        """Test registering routes with the router."""
        prefix = "/api/auth"
        version = "1"
        
        router.register_routes(mock_routes, prefix, version)
        
        # Check if routes were registered
        assert f"{prefix}{mock_routes[0].path}" in router.routes
        assert f"{prefix}{mock_routes[1].path}" in router.routes
        
        # Check route information
        route_info = router.routes[f"{prefix}{mock_routes[0].path}"]
        assert route_info["path"] == f"{prefix}{mock_routes[0].path}"
        assert route_info["methods"] == mock_routes[0].methods
        assert route_info["name"] == mock_routes[0].name
        assert route_info["service"] == prefix.strip("/")
        assert route_info["version"] == version
    
    def test_get_all_routes(self, router, mock_routes):
        """Test getting all registered routes."""
        prefix = "/api/auth"
        version = "1"
        
        router.register_routes(mock_routes, prefix, version)
        
        routes = router.get_all_routes()
        
        assert len(routes) == 2
        assert routes[0]["path"] == f"{prefix}{mock_routes[0].path}"
        assert list(mock_routes[0].methods) == routes[0]["methods"] or set(routes[0]["methods"]) == mock_routes[0].methods
        assert routes[0]["name"] == mock_routes[0].name
        assert routes[0]["service"] == prefix.strip("/")
        assert routes[0]["version"] == version
    
    def test_get_route_by_path(self, router, mock_routes):
        """Test getting a route by path."""
        prefix = "/api/auth"
        
        router.register_routes(mock_routes, prefix)
        
        # Test exact match
        route = router.get_route_by_path(f"{prefix}{mock_routes[0].path}")
        assert route is not None
        assert route["path"] == f"{prefix}{mock_routes[0].path}"
        
        # Test pattern match
        route = router.get_route_by_path(f"{prefix}/users/123")
        assert route is not None
        assert route["path"] == f"{prefix}{mock_routes[1].path}"
        
        # Test no match
        route = router.get_route_by_path("/api/unknown")
        assert route is None
    
    def test_path_matches_pattern(self, router):
        """Test path pattern matching."""
        # Test exact match
        assert router._path_matches_pattern("/api/users", "/api/users") is True
        
        # Test pattern match
        assert router._path_matches_pattern("/api/users/123", "/api/users/{user_id}") is True
        
        # Test no match
        assert router._path_matches_pattern("/api/users/123/posts", "/api/users/{user_id}") is False
    
    def test_get_metrics(self, router, mock_routes):
        """Test getting router metrics."""
        prefix = "/api/auth"
        version = "1"
        
        router.register_routes(mock_routes, prefix, version)
        
        # Simulate some hits
        path1 = f"{prefix}{mock_routes[0].path}"
        path2 = f"{prefix}{mock_routes[1].path}"
        
        router.hit_counts[path1] = 5
        router.hit_counts[path2] = 10
        
        metrics = router.get_metrics()
        
        assert len(metrics) == 2
        assert isinstance(metrics[0], RouteMetrics)
        
        # Check metrics for first route
        metric1 = next(m for m in metrics if m.path == path1)
        assert metric1.methods == mock_routes[0].methods
        assert metric1.service == prefix.strip("/")
        assert metric1.version == version
        assert metric1.hit_count == 5
        
        # Check metrics for second route
        metric2 = next(m for m in metrics if m.path == path2)
        assert metric2.methods == mock_routes[1].methods
        assert metric2.service == prefix.strip("/")
        assert metric2.version == version
        assert metric2.hit_count == 10


class TestAPIVersionManager:
    """Tests for the APIVersionManager class."""
    
    def test_initialization(self):
        """Test APIVersionManager initialization."""
        manager = APIVersionManager()
        assert manager.versions == {}
        assert manager.default_version == "1"
        assert manager.strategy == VersioningStrategy.URL_PATH
        assert manager.header_name == "X-API-Version"
        assert manager.query_param_name == "version"
    
    def test_configure(self, version_manager):
        """Test configuring the versioning strategy."""
        strategy = VersioningStrategy.HEADER
        default_version = "2"
        
        version_manager.configure(strategy, default_version)
        
        assert version_manager.strategy == strategy
        assert version_manager.default_version == default_version
    
    def test_register_version(self, version_manager):
        """Test registering an API version."""
        version = "1"
        description = "Initial API version"
        deprecated = False
        
        version_manager.register_version(version, description, deprecated)
        
        assert version in version_manager.versions
        assert version_manager.versions[version]["version"] == version
        assert version_manager.versions[version]["description"] == description
        assert version_manager.versions[version]["deprecated"] == deprecated
        assert version_manager.versions[version]["endpoints"] == set()
    
    def test_register_endpoint(self, version_manager):
        """Test registering an endpoint for a specific API version."""
        version = "1"
        description = "Initial API version"
        path = "/api/users"
        
        # Register version first
        version_manager.register_version(version, description)
        
        # Register endpoint
        version_manager.register_endpoint(version, path)
        
        assert path in version_manager.versions[version]["endpoints"]
    
    def test_get_versioned_prefix_url_path(self, version_manager):
        """Test getting a versioned URL prefix with URL_PATH strategy."""
        version_manager.strategy = VersioningStrategy.URL_PATH
        prefix = "/api/users"
        version = "2"
        
        versioned_prefix = version_manager.get_versioned_prefix(prefix, version)
        
        assert versioned_prefix == f"/v{version}{prefix}"
    
    def test_get_versioned_prefix_other_strategies(self, version_manager):
        """Test getting a versioned URL prefix with other strategies."""
        # For other strategies, the prefix should remain unchanged
        strategies = [
            VersioningStrategy.QUERY_PARAM,
            VersioningStrategy.HEADER,
            VersioningStrategy.CONTENT_TYPE
        ]
        
        prefix = "/api/users"
        version = "2"
        
        for strategy in strategies:
            version_manager.strategy = strategy
            versioned_prefix = version_manager.get_versioned_prefix(prefix, version)
            assert versioned_prefix == prefix
    
    def test_extract_version_url_path(self, version_manager):
        """Test extracting API version from URL path."""
        version_manager.strategy = VersioningStrategy.URL_PATH
        path = "/v2/api/users"
        headers = {}
        query_params = {}
        
        version = version_manager.extract_version(path, headers, query_params)
        
        assert version == "2"
    
    def test_extract_version_query_param(self, version_manager):
        """Test extracting API version from query parameter."""
        version_manager.strategy = VersioningStrategy.QUERY_PARAM
        version_manager.query_param_name = "version"
        path = "/api/users"
        headers = {}
        query_params = {"version": "2"}
        
        version = version_manager.extract_version(path, headers, query_params)
        
        assert version == "2"
    
    def test_extract_version_header(self, version_manager):
        """Test extracting API version from header."""
        version_manager.strategy = VersioningStrategy.HEADER
        version_manager.header_name = "X-API-Version"
        path = "/api/users"
        headers = {"x-api-version": "2"}
        query_params = {}
        
        version = version_manager.extract_version(path, headers, query_params)
        
        assert version == "2"
    
    def test_extract_version_content_type(self, version_manager):
        """Test extracting API version from Content-Type header."""
        version_manager.strategy = VersioningStrategy.CONTENT_TYPE
        path = "/api/users"
        headers = {"content-type": "application/vnd.api.v2+json"}
        query_params = {}
        
        version = version_manager.extract_version(path, headers, query_params)
        
        assert version == "2"
    
    def test_extract_version_default(self, version_manager):
        """Test extracting API version when not found."""
        version_manager.default_version = "1"
        path = "/api/users"
        headers = {}
        query_params = {}
        
        version = version_manager.extract_version(path, headers, query_params)
        
        assert version == "1"
    
    def test_is_deprecated(self, version_manager):
        """Test checking if an API version is deprecated."""
        # Register non-deprecated version
        version_manager.register_version("1", "Initial version", deprecated=False)
        
        # Register deprecated version
        version_manager.register_version("2", "Old version", deprecated=True)
        
        assert version_manager.is_deprecated("1") is False
        assert version_manager.is_deprecated("2") is True
        assert version_manager.is_deprecated("3") is False  # Unknown version
    
    def test_get_all_versions(self, version_manager):
        """Test getting information about all registered API versions."""
        # Register versions
        version_manager.register_version("1", "Initial version", deprecated=False)
        version_manager.register_version("2", "Enhanced version", deprecated=False)
        version_manager.register_version("3", "Old version", deprecated=True)
        
        # Register some endpoints
        version_manager.register_endpoint("1", "/api/v1/users")
        version_manager.register_endpoint("1", "/api/v1/posts")
        version_manager.register_endpoint("2", "/api/v2/users")
        
        versions = version_manager.get_all_versions()
        
        assert len(versions) == 3
        
        # Check version 1
        v1 = next(v for v in versions if v["version"] == "1")
        assert v1["description"] == "Initial version"
        assert v1["deprecated"] is False
        assert v1["endpoint_count"] == 2
        
        # Check version 2
        v2 = next(v for v in versions if v["version"] == "2")
        assert v2["description"] == "Enhanced version"
        assert v2["deprecated"] is False
        assert v2["endpoint_count"] == 1
        
        # Check version 3
        v3 = next(v for v in versions if v["version"] == "3")
        assert v3["description"] == "Old version"
        assert v3["deprecated"] is True
        assert v3["endpoint_count"] == 0
