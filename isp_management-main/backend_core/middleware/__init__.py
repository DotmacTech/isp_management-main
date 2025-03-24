"""
Middleware initialization for the ISP Management Platform.

This module provides functions to set up middleware for the FastAPI application.
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .versioning import APIVersioningMiddleware
from .rate_limiting import RateLimitingMiddleware
from backend_core.config import settings


def setup_middleware(app: FastAPI) -> None:
    """
    Set up middleware for the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    # Add API versioning middleware
    app.add_middleware(
        APIVersioningMiddleware,
        default_version=settings.api_version,
        supported_versions={
            "1.0": "/api/v1",
            "2.0": "/api/v2"
        }
    )
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitingMiddleware,
        rate_limit=settings.rate_limit,
        rate_limit_window=settings.rate_limit_window
    )
    
    # Add any other middleware here
