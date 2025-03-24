"""
API router initialization for customer module.

This module provides the FastAPI router for customer endpoints.
"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router)

__all__ = ["router"]
