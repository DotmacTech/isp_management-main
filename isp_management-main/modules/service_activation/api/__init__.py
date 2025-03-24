"""
API router initialization for service_activation module.

This module provides the FastAPI router for service_activation endpoints.
"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router)

__all__ = ["router"]
