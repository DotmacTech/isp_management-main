"""
Router configuration for the Communications module.

This module defines the FastAPI router for the Communications module,
which includes endpoints for messages, notifications, announcements,
support tickets, templates, webhooks, and external services.
"""

from fastapi import APIRouter

from modules.communications.endpoints import (
    message_router,
    notification_router,
    announcement_router,
    ticket_router,
    template_router
)
from modules.communications.webhook_endpoints import webhook_router
from modules.communications.external_service_endpoints import external_service_router

# Create a combined router for the communications module
router = APIRouter(prefix="/communications", tags=["Communications"])

# Include all the sub-routers
router.include_router(message_router)
router.include_router(notification_router)
router.include_router(announcement_router)
router.include_router(ticket_router)
router.include_router(template_router)
router.include_router(webhook_router)
router.include_router(external_service_router)
