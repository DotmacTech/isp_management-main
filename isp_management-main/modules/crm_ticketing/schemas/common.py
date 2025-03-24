"""
Common schema definitions for the CRM & Ticketing module.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field


class TicketStatusEnum(str, Enum):
    """Status of a support ticket."""
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_THIRD_PARTY = "waiting_on_third_party"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    CANCELLED = "cancelled"


class TicketPriorityEnum(str, Enum):
    """Priority level of a support ticket."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TicketTypeEnum(str, Enum):
    """Type of support ticket."""
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    SERVICE_REQUEST = "service_request"
    COMPLAINT = "complaint"
    INQUIRY = "inquiry"
    FEEDBACK = "feedback"
    OTHER = "other"


class ContactTypeEnum(str, Enum):
    """Type of customer contact."""
    PRIMARY = "primary"
    BILLING = "billing"
    TECHNICAL = "technical"
    EMERGENCY = "emergency"
    OTHER = "other"


class ContactMethodEnum(str, Enum):
    """Method of customer contact."""
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    CHAT = "chat"
    PORTAL = "portal"
    SOCIAL = "social"
    IN_PERSON = "in_person"
    OTHER = "other"


class SLAStatusEnum(str, Enum):
    """Status of an SLA target."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BREACHED = "breached"


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")


class PaginatedResponse(BaseModel):
    """Base model for paginated responses."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class TimeRangeParams(BaseModel):
    """Common time range parameters for filtering."""
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")


class SortParams(BaseModel):
    """Common sorting parameters."""
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", description="Sort order (asc or desc)")


class SearchParams(BaseModel):
    """Common search parameters."""
    query: Optional[str] = Field(None, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")


class FilterParams(BaseModel):
    """Common filter parameters."""
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply")
