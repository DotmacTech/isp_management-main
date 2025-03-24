"""
Field Services Module for ISP Management Platform.

This module manages field technician operations, job scheduling, and service delivery.
"""

from fastapi import APIRouter

from .endpoints import router as field_services_router

router = APIRouter()
router.include_router(field_services_router, prefix="/field-services", tags=["Field Services"])
