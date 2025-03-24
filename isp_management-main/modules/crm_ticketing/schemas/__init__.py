"""
Pydantic schemas for the CRM & Ticketing module.
"""

from .customer import (
    CustomerBase, CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerContactBase, CustomerContactCreate, CustomerContactUpdate, CustomerContactResponse,
    CustomerNoteBase, CustomerNoteCreate, CustomerNoteUpdate, CustomerNoteResponse
)
from .ticket import (
    TicketBase, TicketCreate, TicketUpdate, TicketResponse,
    TicketCommentBase, TicketCommentCreate, TicketCommentUpdate, TicketCommentResponse,
    TicketAttachmentBase, TicketAttachmentCreate, TicketAttachmentResponse,
    TicketHistoryResponse, TagBase, TagCreate, TagUpdate, TagResponse
)
from .knowledge_base import (
    KBCategoryBase, KBCategoryCreate, KBCategoryUpdate, KBCategoryResponse,
    KBArticleBase, KBArticleCreate, KBArticleUpdate, KBArticleResponse
)
from .sla import (
    SLABase, SLACreate, SLAUpdate, SLAResponse,
    SLAMetricResponse
)
from .common import (
    TicketStatusEnum, TicketPriorityEnum, TicketTypeEnum,
    ContactTypeEnum, ContactMethodEnum, SLAStatusEnum
)

__all__ = [
    "CustomerBase", "CustomerCreate", "CustomerUpdate", "CustomerResponse",
    "CustomerContactBase", "CustomerContactCreate", "CustomerContactUpdate", "CustomerContactResponse",
    "CustomerNoteBase", "CustomerNoteCreate", "CustomerNoteUpdate", "CustomerNoteResponse",
    "TicketBase", "TicketCreate", "TicketUpdate", "TicketResponse",
    "TicketCommentBase", "TicketCommentCreate", "TicketCommentUpdate", "TicketCommentResponse",
    "TicketAttachmentBase", "TicketAttachmentCreate", "TicketAttachmentResponse",
    "TicketHistoryResponse", "TagBase", "TagCreate", "TagUpdate", "TagResponse",
    "KBCategoryBase", "KBCategoryCreate", "KBCategoryUpdate", "KBCategoryResponse",
    "KBArticleBase", "KBArticleCreate", "KBArticleUpdate", "KBArticleResponse",
    "SLABase", "SLACreate", "SLAUpdate", "SLAResponse", "SLAMetricResponse",
    "TicketStatusEnum", "TicketPriorityEnum", "TicketTypeEnum",
    "ContactTypeEnum", "ContactMethodEnum", "SLAStatusEnum"
]
