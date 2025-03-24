"""
API router initialization for communications module.

This module provides the FastAPI router for communications endpoints.
"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router)

__all__ = ["router"]
