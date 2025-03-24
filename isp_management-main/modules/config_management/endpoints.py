"""
Configuration Management Module endpoints for the ISP Management Platform.

This module registers all API routes for the configuration management module
with the FastAPI application.
"""

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.orm import Session

from backend_core.database import get_db
from modules.config_management.routes import configuration_router


def register_endpoints(app: FastAPI) -> None:
    """
    Register all configuration management endpoints with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Include all routers
    app.include_router(configuration_router)
