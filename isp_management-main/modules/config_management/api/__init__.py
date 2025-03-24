"""
API router initialization for config_management module.

This module provides the FastAPI router for config_management endpoints.
"""

from fastapi import APIRouter
from modules.config_management.routes import configuration_router

router = APIRouter()
router.include_router(configuration_router)

__all__ = ["router"]
