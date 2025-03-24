"""
Request transformer implementation for the API Gateway.

This module provides functionality to modify API requests before they are
processed by backend services, allowing for protocol adaptation, header
manipulation, and other transformations.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import Request
from starlette.datastructures import Headers, QueryParams

from backend_core.config import settings


class RequestTransformer:
    """
    Request transformer for modifying API requests.
    
    This class implements functionality to transform requests before they are
    processed by backend services, including:
    - Header manipulation
    - Query parameter transformation
    - Protocol adaptation (REST to gRPC)
    - Request body transformation
    """
    
    def __init__(self):
        """Initialize the request transformer."""
        self.logger = logging.getLogger("request_transformer")
        self.transformations = {}
    
    async def transform(self, request: Request) -> Request:
        """
        Transform a request before it is processed.
        
        Args:
            request: The original request
            
        Returns:
            Request: The transformed request
        """
        # Check if we have a transformation for this path
        path = request.url.path
        
        if path in self.transformations:
            # Apply specific transformation
            return await self._apply_transformation(request, self.transformations[path])
        
        # Apply default transformations
        return await self._apply_default_transformations(request)
    
    async def _apply_default_transformations(self, request: Request) -> Request:
        """
        Apply default transformations to a request.
        
        Args:
            request: The original request
            
        Returns:
            Request: The transformed request
        """
        # Add standard headers
        request.scope["headers"].append(
            (b"x-gateway-timestamp", str(request.scope["router"].default_response_class().created).encode())
        )
        
        # Add trace ID for request tracking
        if "x-trace-id" not in request.headers:
            import uuid
            trace_id = str(uuid.uuid4())
            request.scope["headers"].append(
                (b"x-trace-id", trace_id.encode())
            )
        
        # Mask sensitive information in logs
        self._mask_sensitive_data(request)
        
        return request
    
    async def _apply_transformation(self, request: Request, transformation: Dict) -> Request:
        """
        Apply a specific transformation to a request.
        
        Args:
            request: The original request
            transformation: The transformation to apply
            
        Returns:
            Request: The transformed request
        """
        # Apply header transformations
        if "headers" in transformation:
            for header, value in transformation["headers"].items():
                request.scope["headers"].append(
                    (header.encode(), value.encode())
                )
        
        # Apply query parameter transformations
        if "query_params" in transformation:
            # This is more complex as we need to modify the URL
            # For now, we'll just log that we would do this
            self.logger.info(f"Would transform query params for {request.url.path}")
        
        # Apply body transformations
        if "body" in transformation and transformation["body"].get("enabled", False):
            # This would require more complex handling
            self.logger.info(f"Would transform request body for {request.url.path}")
        
        return request
    
    def _mask_sensitive_data(self, request: Request):
        """
        Mask sensitive data in the request for logging purposes.
        
        Args:
            request: The request to mask data in
        """
        # List of headers that might contain sensitive information
        sensitive_headers = [
            "authorization",
            "cookie",
            "x-api-key",
        ]
        
        # Mask sensitive headers
        for i, (name, value) in enumerate(request.scope["headers"]):
            header_name = name.decode().lower()
            if header_name in sensitive_headers:
                # Replace with masked value
                request.scope["headers"][i] = (
                    name,
                    b"[REDACTED]"
                )
    
    def register_transformation(self, path: str, transformation: Dict):
        """
        Register a transformation for a specific path.
        
        Args:
            path: The API path to transform
            transformation: The transformation configuration
        """
        self.transformations[path] = transformation
        self.logger.info(f"Registered request transformation for {path}")
    
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
            source_protocol: The source protocol (e.g., "rest")
            target_protocol: The target protocol (e.g., "grpc")
        """
        if path not in self.transformations:
            self.transformations[path] = {}
        
        self.transformations[path]["protocol"] = {
            "source": source_protocol,
            "target": target_protocol,
            "enabled": True
        }
        
        self.logger.info(f"Registered protocol transformation for {path}: {source_protocol} -> {target_protocol}")
