"""
Response transformer implementation for the API Gateway.

This module provides functionality to modify API responses before they are
returned to clients, allowing for protocol adaptation, header manipulation,
and other transformations.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import Response
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers

from backend_core.api_gateway.config import settings as api_gateway_settings


class ResponseTransformer:
    """
    Response transformer for modifying API responses.
    
    This class implements functionality to transform responses before they are
    returned to clients, including:
    - Header manipulation
    - Response body transformation
    - Protocol adaptation (gRPC to REST)
    - Error standardization
    """
    
    def __init__(self):
        """Initialize the response transformer."""
        self.logger = logging.getLogger("response_transformer")
        self.transformations = {}
    
    async def transform(self, response: Response) -> Response:
        """
        Transform a response before it is returned to the client.
        
        Args:
            response: The original response
            
        Returns:
            Response: The transformed response
        """
        # Get the request path from the response scope if available
        path = getattr(response, "path", None)
        
        if path and path in self.transformations:
            # Apply specific transformation
            return await self._apply_transformation(response, self.transformations[path])
        
        # Apply default transformations
        return await self._apply_default_transformations(response)
    
    async def _apply_default_transformations(self, response: Response) -> Response:
        """
        Apply default transformations to a response.
        
        Args:
            response: The original response
            
        Returns:
            Response: The transformed response
        """
        # Add standard headers
        response.headers["X-Gateway-Version"] = api_gateway_settings.API_GATEWAY_VERSION
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Add CORS headers if not already present
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = ", ".join(api_gateway_settings.cors_allowed_origins)
        
        # Standardize error responses
        if 400 <= response.status_code < 600:
            return await self._standardize_error_response(response)
        
        return response
    
    async def _apply_transformation(self, response: Response, transformation: Dict) -> Response:
        """
        Apply a specific transformation to a response.
        
        Args:
            response: The original response
            transformation: The transformation to apply
            
        Returns:
            Response: The transformed response
        """
        # Apply header transformations
        if "headers" in transformation:
            for header, value in transformation["headers"].items():
                response.headers[header] = value
        
        # Apply body transformations
        if "body" in transformation and transformation["body"].get("enabled", False):
            # This would require more complex handling
            self.logger.info("Would transform response body")
        
        return response
    
    async def _standardize_error_response(self, response: Response) -> Response:
        """
        Standardize error responses.
        
        Args:
            response: The original error response
            
        Returns:
            Response: The standardized error response
        """
        if isinstance(response, JSONResponse):
            content = response.body
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = {"detail": "Unknown error"}
            
            # Create standardized error response
            error_response = {
                "error": True,
                "code": response.status_code,
                "message": data.get("detail", "Unknown error"),
                "gateway_version": api_gateway_settings.API_GATEWAY_VERSION
            }
            
            # Add path if available
            if hasattr(response, "path") and response.path:
                error_response["path"] = response.path
            
            # Add timestamp if available
            if hasattr(response, "timestamp") and response.timestamp:
                error_response["timestamp"] = response.timestamp
            
            # Create new JSON response with standardized format
            return JSONResponse(
                content=error_response,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        return response
    
    def register_transformation(self, path: str, transformation: Dict):
        """
        Register a transformation for a specific path.
        
        Args:
            path: The API path to transform
            transformation: The transformation configuration
        """
        self.transformations[path] = transformation
        self.logger.info(f"Registered response transformation for {path}")
    
    def register_header_transformation(self, path: str, header: str, value: str):
        """
        Register a header transformation for a specific path.
        
        Args:
            path: The API path to transform
            header: The header to add or modify
            value: The header value
        """
        if path not in self.transformations:
            self.transformations[path] = {}
        
        if "headers" not in self.transformations[path]:
            self.transformations[path]["headers"] = {}
        
        self.transformations[path]["headers"][header] = value
        self.logger.info(f"Registered header transformation for {path}: {header}={value}")
    
    def register_protocol_transformation(self, path: str, source_protocol: str, target_protocol: str):
        """
        Register a protocol transformation for a specific path.
        
        Args:
            path: The API path to transform
            source_protocol: The source protocol (e.g., "grpc")
            target_protocol: The target protocol (e.g., "rest")
        """
        if path not in self.transformations:
            self.transformations[path] = {}
        
        self.transformations[path]["protocol"] = {
            "source": source_protocol,
            "target": target_protocol,
            "enabled": True
        }
        
        self.logger.info(f"Registered protocol transformation for {path}: {source_protocol} -> {target_protocol}")
