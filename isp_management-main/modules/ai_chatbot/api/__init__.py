"""
API router initialization for ai_chatbot module.

This module provides the FastAPI router for ai_chatbot endpoints.
"""

from fastapi import APIRouter
from .endpoints import router as endpoints_router

router = APIRouter()
router.include_router(endpoints_router)

__all__ = ["router"]
