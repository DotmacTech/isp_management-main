"""
Communications module for the ISP Management Platform.

This module provides functionality for handling various communication needs
of the ISP Management Platform, including messages, notifications, announcements,
and support tickets.
"""

# Import and expose the API router
from .api import router

# Import and expose service classes from the services package
from .services.message_service import MessageService
from .services.notification_service import NotificationService
from .services.announcement_service import AnnouncementService
from .services.support_ticket_service import SupportTicketService
from .services.template_service import TemplateService

__all__ = [
    'router',
    'MessageService',
    'NotificationService',
    'AnnouncementService',
    'SupportTicketService',
    'TemplateService'
]
