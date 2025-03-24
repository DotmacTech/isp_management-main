"""
Services for the CRM & Ticketing module.
"""

from .customer_service import CustomerService
from .ticket_service import TicketService
from .knowledge_base_service import KnowledgeBaseService
from .sla_service import SLAService
from .notification_service import NotificationService
from .search_service import SearchService
from .reporting_service import ReportingService
from .workflow_service import WorkflowService

__all__ = [
    "CustomerService",
    "TicketService",
    "KnowledgeBaseService",
    "SLAService",
    "NotificationService",
    "SearchService",
    "ReportingService",
    "WorkflowService"
]
