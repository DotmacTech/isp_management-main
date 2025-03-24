"""
Database models for the CRM & Ticketing module.
"""

from .customer import Customer, CustomerContact, CustomerNote
from .ticket import Ticket, TicketComment, TicketAttachment, TicketHistory
from .knowledge_base import KnowledgeBaseArticle, KnowledgeBaseCategory
from .sla import SLA, SLAMetric
from .common import TicketPriority, TicketStatus, TicketType, ContactType, ContactMethod

__all__ = [
    "Customer",
    "CustomerContact",
    "CustomerNote",
    "Ticket",
    "TicketComment",
    "TicketAttachment",
    "TicketHistory",
    "KnowledgeBaseArticle",
    "KnowledgeBaseCategory",
    "SLA",
    "SLAMetric",
    "TicketPriority",
    "TicketStatus",
    "TicketType",
    "ContactType",
    "ContactMethod"
]
