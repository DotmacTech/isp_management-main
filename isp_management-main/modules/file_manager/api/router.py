"""
Main router for the File Manager module.

This module registers all API endpoints for the File Manager module.
"""

from fastapi import APIRouter
from .endpoints import router as file_endpoints

router = APIRouter()

# Include file endpoints
router.include_router(file_endpoints, prefix="/file-manager", tags=["File Manager"])
