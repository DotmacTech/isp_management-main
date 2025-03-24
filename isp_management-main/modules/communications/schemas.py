
"""
Pydantic schemas for the Communications module.

This module defines the Pydantic schemas for validating and serializing data
related to communications in the ISP Management Platform.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, HttpUrl, ConfigDict
from enum import Enum


# Enum schemas
class MessagePriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatusEnum(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class NotificationTypeEnum(str, Enum):
    SYSTEM = "system"
    BILLING = "billing"
    SERVICE = "service"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    MARKETING = "marketing"
    OTHER = "other"


class TicketStatusEnum(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_THIRD_PARTY = "waiting_third_party"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategoryEnum(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    SERVICE_REQUEST = "service_request"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    OTHER = "other"


class AnnouncementTypeEnum(str, Enum):
    GENERAL = "general"
    MAINTENANCE = "maintenance"
    SERVICE_UPDATE = "service_update"
    PROMOTION = "promotion"
    POLICY_UPDATE = "policy_update"
    OTHER = "other"


class DeliveryMethodEnum(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    PORTAL = "portal"


# Base schemas
class UserBase(BaseModel):
    id: int
    username: str
    email: EmailStr


# Message schemas
class MessageAttachmentBase(BaseModel):
    file_name: str
    file_size: int
    content_type: str


class MessageAttachmentCreate(MessageAttachmentBase):
    file_path: str


class MessageAttachment(MessageAttachmentBase):
    id: int
    message_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    subject: str
    body: str
    priority: MessagePriorityEnum = MessagePriorityEnum.MEDIUM
    delivery_method: DeliveryMethodEnum = DeliveryMethodEnum.IN_APP


class MessageCreate(MessageBase):
    recipient_ids: List[int]
    attachments: Optional[List[MessageAttachmentCreate]] = None


class MessageUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    priority: Optional[MessagePriorityEnum] = None
    status: Optional[MessageStatusEnum] = None
    is_read: Optional[bool] = None


class Message(MessageBase):
    id: int
    sender_id: int
    status: MessageStatusEnum
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sender: UserBase
    recipients: List[UserBase]
    attachments: List[MessageAttachment] = []
    
    model_config = ConfigDict(from_attributes=True)


# Notification schemas
class NotificationBase(BaseModel):
    title: str
    content: str
    notification_type: NotificationTypeEnum = NotificationTypeEnum.SYSTEM
    is_actionable: bool = False
    action_url: Optional[str] = None
    delivery_method: DeliveryMethodEnum = DeliveryMethodEnum.IN_APP


class NotificationCreate(NotificationBase):
    recipient_ids: List[int]
    expires_at: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None


class Notification(NotificationBase):
    id: int
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    recipients: List[UserBase]
    
    model_config = ConfigDict(from_attributes=True)


# Announcement schemas
class AnnouncementBase(BaseModel):
    title: str
    content: str
    announcement_type: AnnouncementTypeEnum = AnnouncementTypeEnum.GENERAL
    is_public: bool = False
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None


class AnnouncementCreate(AnnouncementBase):
    targeted_recipient_ids: Optional[List[int]] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    announcement_type: Optional[AnnouncementTypeEnum] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    targeted_recipient_ids: Optional[List[int]] = None


class Announcement(AnnouncementBase):
    id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    author: UserBase
    targeted_recipients: Optional[List[UserBase]] = None
    
    model_config = ConfigDict(from_attributes=True)


# Support ticket schemas
class TicketAttachmentBase(BaseModel):
    file_name: str
    file_size: int
    content_type: str


class TicketAttachmentCreate(TicketAttachmentBase):
    file_path: str


class TicketAttachment(TicketAttachmentBase):
    id: int
    ticket_id: int
    uploaded_by: int
    created_at: datetime
    uploader: UserBase
    
    model_config = ConfigDict(from_attributes=True)


class ResponseAttachmentBase(BaseModel):
    file_name: str
    file_size: int
    content_type: str


class ResponseAttachmentCreate(ResponseAttachmentBase):
    file_path: str


class ResponseAttachment(ResponseAttachmentBase):
    id: int
    response_id: int
    uploaded_by: int
    created_at: datetime
    uploader: UserBase
    
    model_config = ConfigDict(from_attributes=True)


class TicketResponseBase(BaseModel):
    response_text: str
    is_internal: bool = False


class TicketResponseCreate(TicketResponseBase):
    attachments: Optional[List[ResponseAttachmentCreate]] = None


class TicketResponse(TicketResponseBase):
    id: int
    ticket_id: int
    responder_id: int
    created_at: datetime
    updated_at: datetime
    responder: UserBase
    attachments: List[ResponseAttachment] = []
    
    model_config = ConfigDict(from_attributes=True)


class SupportTicketBase(BaseModel):
    subject: str
    description: str
    category: TicketCategoryEnum = TicketCategoryEnum.TECHNICAL
    priority: TicketPriorityEnum = TicketPriorityEnum.MEDIUM


class SupportTicketCreate(SupportTicketBase):
    attachments: Optional[List[TicketAttachmentCreate]] = None


class SupportTicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TicketCategoryEnum] = None
    status: Optional[TicketStatusEnum] = None
    priority: Optional[TicketPriorityEnum] = None
    assigned_to: Optional[int] = None


class SupportTicket(SupportTicketBase):
    id: int
    ticket_number: str
    status: TicketStatusEnum
    customer_id: int
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    customer: UserBase
    assignee: Optional[UserBase] = None
    responses: List[TicketResponse] = []
    attachments: List[TicketAttachment] = []
    
    model_config = ConfigDict(from_attributes=True)


# Template schemas
class TemplateBase(BaseModel):
    name: str
    subject: str
    body: str
    template_type: str
    is_active: bool = True


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    template_type: Optional[str] = None
    is_active: Optional[bool] = None


class Template(TemplateBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    author: UserBase
    
    model_config = ConfigDict(from_attributes=True)


# Pagination schemas
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: List[Any], total: int, page: int, size: int):
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


# Response schemas for specific endpoints
class MessageResponse(BaseModel):
    message: str


class FileUploadResponse(BaseModel):
    file_name: str
    file_path: str
    file_size: int
    content_type: str


class TicketStatistics(BaseModel):
    total: int
    open: int
    in_progress: int
    waiting_customer: int
    waiting_third_party: int
    resolved: int
    closed: int


class UserNotificationSettings(BaseModel):
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    in_app_notifications: bool = True
    
    billing_notifications: bool = True
    service_notifications: bool = True
    marketing_notifications: bool = False
    security_notifications: bool = True
    
    @model_validator(mode='after')
    def check_at_least_one_method(self) -> 'UserNotificationSettings':
        if not any([
            self.email_notifications,
            self.sms_notifications,
            self.push_notifications,
            self.in_app_notifications
        ]):
            raise ValueError("At least one notification method must be enabled")
        return self


# Webhook schemas
class WebhookBase(BaseModel):
    """Base schema for webhook data."""
    name: str = Field(..., description="Name of the webhook")
    url: HttpUrl = Field(..., description="URL to send webhook events to")
    events: List[str] = Field(..., description="List of events to subscribe to")
    is_active: bool = Field(True, description="Whether the webhook is active")
    description: Optional[str] = Field(None, description="Description of the webhook")


class WebhookCreate(WebhookBase):
    """Schema for creating a new webhook."""
    secret: Optional[str] = Field(None, description="Secret for signing webhook payloads")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers to include in webhook requests")


class WebhookUpdate(BaseModel):
    """Schema for updating an existing webhook."""
    name: Optional[str] = Field(None, description="Name of the webhook")
    url: Optional[HttpUrl] = Field(None, description="URL to send webhook events to")
    events: Optional[List[str]] = Field(None, description="List of events to subscribe to")
    is_active: Optional[bool] = Field(None, description="Whether the webhook is active")
    secret: Optional[str] = Field(None, description="Secret for signing webhook payloads")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers to include in webhook requests")
    description: Optional[str] = Field(None, description="Description of the webhook")


class Webhook(WebhookBase):
    """Schema for a webhook."""
    id: int
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class WebhookLogBase(BaseModel):
    """Base schema for webhook log data."""
    event: str = Field(..., description="Event type")
    request_payload: Dict[str, Any] = Field(..., description="Webhook request payload")
    response_status: int = Field(..., description="HTTP status code of the response")
    response_body: Optional[str] = Field(None, description="Response body")
    success: bool = Field(..., description="Whether the webhook delivery was successful")


class WebhookLog(WebhookLogBase):
    """Schema for a webhook log."""
    id: int
    webhook_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ExternalServiceBase(BaseModel):
    """Base schema for external service data."""
    name: str = Field(..., description="Name of the external service")
    service_type: str = Field(..., description="Type of service (e.g., 'sms', 'email', 'chat')")
    config: Dict[str, Any] = Field(..., description="Configuration for the service")
    is_active: bool = Field(True, description="Whether the service is active")


class ExternalServiceCreate(ExternalServiceBase):
    """Schema for creating a new external service."""
    description: Optional[str] = Field(None, description="Description of the external service")


class ExternalServiceUpdate(BaseModel):
    """Schema for updating an existing external service."""
    name: Optional[str] = Field(None, description="Name of the external service")
    service_type: Optional[str] = Field(None, description="Type of service (e.g., 'sms', 'email', 'chat')")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the service")
    is_active: Optional[bool] = Field(None, description="Whether the service is active")


class ExternalService(ExternalServiceBase):
    """Schema for an external service."""
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Event schemas for different webhook events

class MessageEvent(BaseModel):
    """Schema for message events."""
    message_id: int
    subject: str
    sender_id: int
    recipient_ids: List[int]
    status: str


class NotificationEvent(BaseModel):
    """Schema for notification events."""
    notification_id: int
    title: str
    notification_type: str
    recipient_ids: List[int]


class AnnouncementEvent(BaseModel):
    """Schema for announcement events."""
    announcement_id: int
    title: str
    announcement_type: str
    is_public: bool


class TicketEvent(BaseModel):
    """Schema for ticket events."""
    ticket_id: int
    ticket_number: str
    subject: str
    status: str
    priority: str
    customer_id: int
    assigned_to: Optional[int]
