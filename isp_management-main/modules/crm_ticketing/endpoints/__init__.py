"""
API endpoints for the CRM & Ticketing module.

This package contains all the API endpoints for the CRM & Ticketing module,
including ticket management, SLA management, reporting, and notifications.
"""

from fastapi import APIRouter
from .sla_endpoints import router as sla_router
from .reporting_endpoints import router as reporting_router
from .notification_endpoints import router as notification_router
from .ticket_endpoints import router as ticket_router

# Create a main router for the CRM & Ticketing module
router = APIRouter(
    prefix="/crm",
    tags=["CRM & Ticketing"],
)

# Include all sub-routers
router.include_router(ticket_router)
router.include_router(sla_router)
router.include_router(reporting_router)
router.include_router(notification_router)

# Export the main router
__all__ = ["router"]
