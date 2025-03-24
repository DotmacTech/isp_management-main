"""
Tests for the Request and Response Transformer components of the API Gateway.

This module contains tests for the RequestTransformer and ResponseTransformer
classes, which modify API requests and responses before processing and
returning to clients.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
import asyncio
from unittest.mock import MagicMock, patch

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, URL

from backend_core.api_gateway.request_transformer import RequestTransformer
from backend_core.api_gateway.response_transformer import ResponseTransformer


@pytest.fixture
def request_transformer():
    """Create a RequestTransformer instance for testing."""
    return RequestTransformer()


@pytest.fixture
def response_transformer():
    """Create a ResponseTransformer instance for testing."""
    return ResponseTransformer()


@pytest.fixture
def mock_request():
    """Create a mock Request object for testing."""
    mock_req = MagicMock(spec=Request)
    mock_req.url = URL("http://testserver/api/test")
    mock_req.headers = Headers({"content-type": "application/json"})
    mock_req.scope = {
        "headers": [
            (b"content-type", b"application/json"),
            (b"user-agent", b"test-client"),
        ],
        "router": MagicMock(),
    }
    return mock_req


@pytest.fixture
def mock_response():
    """Create a mock Response object for testing."""
    content = json.dumps({"message": "test"}).encode()
    response = JSONResponse(
        content={"message": "test"},
        status_code=200,
        headers={"content-type": "application/json"}
    )
    response.body = content
    response.path = "/api/test"
    return response


class TestRequestTransformer:
    """Tests for the RequestTransformer class."""
    
    def test_initialization(self):
        """Test RequestTransformer initialization."""
        transformer = RequestTransformer()
        assert transformer.transformations == {}
    
    def test_register_transformation(self, request_transformer):
        """Test registering a transformation for a path."""
        path = "/api/test"
        transformation = {
            "headers": {"X-Test": "test"},
            "query_params": {"param": "value"},
        }
        
        request_transformer.register_transformation(path, transformation)
        
        assert path in request_transformer.transformations
        assert request_transformer.transformations[path] == transformation
    
    def test_register_header_transformation(self, request_transformer):
        """Test registering a header transformation for a path."""
        path = "/api/test"
        header = "X-Test"
        value = "test"
        
        request_transformer.register_header_transformation(path, header, value)
        
        assert path in request_transformer.transformations
        assert "headers" in request_transformer.transformations[path]
        assert request_transformer.transformations[path]["headers"][header] == value
    
    def test_register_protocol_transformation(self, request_transformer):
        """Test registering a protocol transformation for a path."""
        path = "/api/test"
        source = "rest"
        target = "grpc"
        
        request_transformer.register_protocol_transformation(path, source, target)
        
        assert path in request_transformer.transformations
        assert "protocol" in request_transformer.transformations[path]
        assert request_transformer.transformations[path]["protocol"]["source"] == source
        assert request_transformer.transformations[path]["protocol"]["target"] == target
    
    @pytest.mark.asyncio
    async def test_transform_default(self, request_transformer, mock_request):
        """Test default request transformation."""
        # Apply default transformations
        transformed_request = await request_transformer.transform(mock_request)
        
        # Check if gateway timestamp header was added
        headers = dict(transformed_request.scope["headers"])
        assert b"x-gateway-timestamp" in headers
        
        # Check if trace ID was added
        assert b"x-trace-id" in headers
    
    @pytest.mark.asyncio
    async def test_transform_specific(self, request_transformer, mock_request):
        """Test specific request transformation."""
        path = "/api/test"
        transformation = {
            "headers": {"X-Test": "test-value"},
        }
        
        # Register transformation
        request_transformer.register_transformation(path, transformation)
        
        # Apply transformation
        transformed_request = await request_transformer.transform(mock_request)
        
        # Check if custom header was added
        headers = dict(transformed_request.scope["headers"])
        assert (b"X-Test", b"test-value") in transformed_request.scope["headers"]
    
    @pytest.mark.asyncio
    async def test_mask_sensitive_data(self, request_transformer, mock_request):
        """Test masking sensitive data in requests."""
        # Add sensitive headers
        mock_request.scope["headers"].append(
            (b"authorization", b"Bearer token123")
        )
        mock_request.scope["headers"].append(
            (b"cookie", b"session=abc123")
        )
        
        # Apply transformation
        transformed_request = await request_transformer.transform(mock_request)
        
        # Check if sensitive headers were masked
        headers = dict(transformed_request.scope["headers"])
        assert headers.get(b"authorization") == b"[REDACTED]"
        assert headers.get(b"cookie") == b"[REDACTED]"


class TestResponseTransformer:
    """Tests for the ResponseTransformer class."""
    
    def test_initialization(self):
        """Test ResponseTransformer initialization."""
        transformer = ResponseTransformer()
        assert transformer.transformations == {}
    
    def test_register_transformation(self, response_transformer):
        """Test registering a transformation for a path."""
        path = "/api/test"
        transformation = {
            "headers": {"X-Test": "test"},
        }
        
        response_transformer.register_transformation(path, transformation)
        
        assert path in response_transformer.transformations
        assert response_transformer.transformations[path] == transformation
    
    def test_register_header_transformation(self, response_transformer):
        """Test registering a header transformation for a path."""
        path = "/api/test"
        header = "X-Test"
        value = "test"
        
        response_transformer.register_header_transformation(path, header, value)
        
        assert path in response_transformer.transformations
        assert "headers" in response_transformer.transformations[path]
        assert response_transformer.transformations[path]["headers"][header] == value
    
    def test_register_protocol_transformation(self, response_transformer):
        """Test registering a protocol transformation for a path."""
        path = "/api/test"
        source = "grpc"
        target = "rest"
        
        response_transformer.register_protocol_transformation(path, source, target)
        
        assert path in response_transformer.transformations
        assert "protocol" in response_transformer.transformations[path]
        assert response_transformer.transformations[path]["protocol"]["source"] == source
        assert response_transformer.transformations[path]["protocol"]["target"] == target
    
    @pytest.mark.asyncio
    async def test_transform_default(self, response_transformer, mock_response):
        """Test default response transformation."""
        # Apply default transformations
        transformed_response = await response_transformer.transform(mock_response)
        
        # Check if security headers were added
        assert "X-Content-Type-Options" in transformed_response.headers
        assert transformed_response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in transformed_response.headers
        assert transformed_response.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in transformed_response.headers
        assert transformed_response.headers["X-XSS-Protection"] == "1; mode=block"
    
    @pytest.mark.asyncio
    async def test_transform_specific(self, response_transformer, mock_response):
        """Test specific response transformation."""
        path = "/api/test"
        transformation = {
            "headers": {"X-Test": "test-value"},
        }
        
        # Register transformation
        response_transformer.register_transformation(path, transformation)
        
        # Apply transformation
        transformed_response = await response_transformer.transform(mock_response)
        
        # Check if custom header was added
        assert "X-Test" in transformed_response.headers
        assert transformed_response.headers["X-Test"] == "test-value"
    
    @pytest.mark.asyncio
    async def test_standardize_error_response(self, response_transformer):
        """Test standardizing error responses."""
        # Create an error response
        error_response = JSONResponse(
            content={"detail": "An error occurred"},
            status_code=400
        )
        error_response.path = "/api/test"
        
        # Apply transformation
        transformed_response = await response_transformer.transform(error_response)
        
        # Check if response was standardized
        content = json.loads(transformed_response.body)
        assert "error" in content
        assert content["error"] is True
        assert "code" in content
        assert content["code"] == 400
        assert "message" in content
        assert content["message"] == "An error occurred"
