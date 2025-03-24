from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict

class TicketPriority(str, Enum):
    P1 = "p1"  # Critical - 4h resolution target
    P2 = "p2"  # High - 24h resolution target
    P3 = "p3"  # Medium - 72h resolution target
    P4 = "p4"  # Low - Best effort

class TicketStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketSource(str, Enum):
    CUSTOMER_PORTAL = "customer_portal"
    EMAIL = "email"
    PHONE = "phone"
    CHAT = "chat"
    SOCIAL = "social"
    SYSTEM = "system"

class CustomerStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_ACTIVATION = "pending_activation"
    CANCELED = "canceled"

class CustomerBase(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    status: CustomerStatus = CustomerStatus.PENDING_ACTIVATION
    notes: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TicketBase(BaseModel):
    customer_id: int
    subject: str
    description: str
    priority: TicketPriority = TicketPriority.P3
    source: TicketSource = TicketSource.CUSTOMER_PORTAL

class TicketCreate(TicketBase):
    pass

class TicketResponse(TicketBase):
    id: int
    status: TicketStatus
    assigned_to: Optional[int] = None  # User ID of the agent
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    time_to_resolution: Optional[int] = None  # In minutes, if resolved

    model_config = ConfigDict(from_attributes=True)

class TicketCommentBase(BaseModel):
    ticket_id: int
    user_id: int
    comment: str
    is_internal: bool = False  # True if only visible to staff

class TicketCommentCreate(TicketCommentBase):
    pass

class TicketCommentResponse(TicketCommentBase):
    id: int
    created_at: datetime
    user_name: str  # Name of the user who created the comment

    model_config = ConfigDict(from_attributes=True)

class TicketAssignmentUpdate(BaseModel):
    assigned_to: int  # User ID of the agent

class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    comment: Optional[str] = None

class CustomerSearch(BaseModel):
    query: str
    status: Optional[CustomerStatus] = None
    limit: int = 10
    offset: int = 0
