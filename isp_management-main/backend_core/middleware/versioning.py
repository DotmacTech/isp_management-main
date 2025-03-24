"""
API Versioning Middleware

This module provides middleware for handling API versioning through:
1. URL path versioning (e.g., /api/v1/resource)
2. Accept header versioning (e.g., Accept: application/json;version=1.0)
3. Custom header versioning (e.g., X-API-Version: 1.0)

It ensures backward compatibility while allowing new API versions to be introduced.
"""

from typing import Callable, Dict, Optional, Union
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend_core.config import settings


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling API versioning.
    
    This middleware supports multiple versioning strategies:
    - URL path versioning
    - Accept header versioning
    - Custom header versioning
    
    It will determine the requested API version and route to the appropriate
    version-specific handler.
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        default_version: str = "1.0",
        supported_versions: Dict[str, str] = None
    ):
        """
        Initialize the API versioning middleware.
        
        Args:
            app: The ASGI application
            default_version: The default API version to use if not specified
            supported_versions: Dictionary mapping version strings to their
                                corresponding URL prefixes
        """
        super().__init__(app)
        self.default_version = default_version
        self.supported_versions = supported_versions or {
            "1.0": "/api/v1",
            "2.0": "/api/v2"
        }
        
        # Validate that the default version is supported
        if self.default_version not in self.supported_versions:
            raise ValueError(f"Default version {default_version} is not in supported versions")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and determine the API version.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the next middleware or route handler
        """
        # Extract version from different sources
        version = self._get_version_from_request(request)
        
        # If no version is specified, use the default
        if not version:
            version = self.default_version
        
        # Check if the version is supported
        if version not in self.supported_versions:
            # If not supported, fall back to the default version
            version = self.default_version
        
        # Add version info to request state for access in route handlers
        request.state.api_version = version
        
        # Process the request
        response = await call_next(request)
        
        # Add version header to response
        response.headers["X-API-Version"] = version
        
        return response
    
    def _get_version_from_request(self, request: Request) -> Optional[str]:
        """
        Extract API version from the request.
        
        Checks for version in:
        1. URL path
        2. Accept header
        3. Custom X-API-Version header
        
        Args:
            request: The incoming request
            
        Returns:
            The API version if found, None otherwise
        """
        # Check URL path versioning
        path = request.url.path
        for version, prefix in self.supported_versions.items():
            if path.startswith(prefix):
                return version
        
        # Check Accept header versioning
        accept_header = request.headers.get("accept")
        if accept_header and "version=" in accept_header:
            try:
                # Extract version from Accept header
                # Example: application/json;version=1.0
                version_part = [
                    part for part in accept_header.split(";") 
                    if "version=" in part
                ]
                if version_part:
                    version = version_part[0].split("=")[1].strip()
                    return version
            except (IndexError, ValueError):
                pass
        
        # Check custom header versioning
        version_header = request.headers.get("X-API-Version")
        if version_header:
            return version_header
        
        return None


def get_api_version(request: Request) -> str:
    """
    Get the API version from the request state.
    
    This function can be used as a dependency in FastAPI route handlers
    to access the API version.
    
    Args:
        request: The request object
        
    Returns:
        The API version
    """
    return getattr(request.state, "api_version", settings.api_version)
