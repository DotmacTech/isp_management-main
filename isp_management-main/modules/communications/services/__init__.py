"""
Service layer for the communications module.

This package contains service classes for handling communications-related operations
in the ISP Management Platform, including messages, notifications, announcements,
and support tickets.
"""

# Import all service classes to expose them at the package level
# These will be imported directly from their respective modules
# by the main __init__.py file

__all__ = [
    'MessageService',
    'NotificationService',
    'AnnouncementService',
    'SupportTicketService',
    'TemplateService'
]
