"""
Database models for the Communications module.

This module defines the database models for handling various types of communications
in the ISP Management Platform, including notifications, announcements, support tickets,
and messaging.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, Table, JSON
from sqlalchemy.orm import relationship
import enum

from backend_core.database import Base


class MessagePriority(str, enum.Enum):
    """Enum for message priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(str, enum.Enum):
    """Enum for message status."""
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class NotificationType(str, enum.Enum):
    """Enum for notification types."""
    SYSTEM = "system"
    BILLING = "billing"
    SERVICE = "service"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    MARKETING = "marketing"
    OTHER = "other"


class TicketStatus(str, enum.Enum):
    """Enum for support ticket status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_THIRD_PARTY = "waiting_third_party"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    """Enum for support ticket priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, enum.Enum):
    """Enum for support ticket categories."""
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    SERVICE_REQUEST = "service_request"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    OTHER = "other"


class AnnouncementType(str, enum.Enum):
    """Enum for announcement types."""
    GENERAL = "general"
    MAINTENANCE = "maintenance"
    SERVICE_UPDATE = "service_update"
    PROMOTION = "promotion"
    POLICY_UPDATE = "policy_update"
    OTHER = "other"


class DeliveryMethod(str, enum.Enum):
    """Enum for message delivery methods."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    PORTAL = "portal"


# Association table for message recipients
message_recipients = Table(
    "message_recipients",
    Base.metadata,
    Column("message_id", Integer, ForeignKey("messages.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True)
)


# Association table for notification recipients
notification_recipients = Table(
    "notification_recipients",
    Base.metadata,
    Column("notification_id", Integer, ForeignKey("notifications.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True)
)


# Association table for announcement recipients
announcement_recipients = Table(
    "announcement_recipients",
    Base.metadata,
    Column("announcement_id", Integer, ForeignKey("announcements.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True)
)


class Message(Base):
    """Model for messages between users or from system to users."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"))
    priority = Column(Enum(MessagePriority), default=MessagePriority.MEDIUM)
    status = Column(Enum(MessageStatus), default=MessageStatus.DRAFT)
    delivery_method = Column(Enum(DeliveryMethod), default=DeliveryMethod.IN_APP)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    recipients = relationship("User", secondary=message_recipients)
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Message(id={self.id}, subject='{self.subject}', status={self.status})>"


class MessageAttachment(Base):
    """Model for message attachments."""
    __tablename__ = "message_attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    content_type = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="attachments")
    
    def __repr__(self):
        return f"<MessageAttachment(id={self.id}, file_name='{self.file_name}')>"


class Notification(Base):
    """Model for system notifications to users."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), default=NotificationType.SYSTEM)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_actionable = Column(Boolean, default=False)
    action_url = Column(String(512), nullable=True)
    delivery_method = Column(Enum(DeliveryMethod), default=DeliveryMethod.IN_APP)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    recipients = relationship("User", secondary=notification_recipients, back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, title='{self.title}', type={self.notification_type})>"


class Announcement(Base):
    """Model for system-wide or targeted announcements."""
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    announcement_type = Column(Enum(AnnouncementType), default=AnnouncementType.GENERAL)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # If True, visible to all users without login
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("User", foreign_keys=[created_by])
    targeted_recipients = relationship("User", secondary=announcement_recipients, back_populates="announcements")
    
    def __repr__(self):
        return f"<Announcement(id={self.id}, title='{self.title}', type={self.announcement_type})>"


class SupportTicket(Base):
    """Model for customer support tickets."""
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(20), unique=True, index=True, nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(TicketCategory), default=TicketCategory.TECHNICAL)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="submitted_tickets")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tickets")
    responses = relationship("TicketResponse", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SupportTicket(id={self.id}, ticket_number='{self.ticket_number}', status={self.status})>"


class TicketResponse(Base):
    """Model for responses to support tickets."""
    __tablename__ = "ticket_responses"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    responder_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # If True, only visible to staff
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticket = relationship("SupportTicket", back_populates="responses")
    responder = relationship("User", foreign_keys=[responder_id])
    attachments = relationship("ResponseAttachment", back_populates="response", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TicketResponse(id={self.id}, ticket_id={self.ticket_id}, is_internal={self.is_internal})>"


class TicketAttachment(Base):
    """Model for attachments to support tickets."""
    __tablename__ = "ticket_attachments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    content_type = Column(String(100), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = relationship("SupportTicket", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    
    def __repr__(self):
        return f"<TicketAttachment(id={self.id}, file_name='{self.file_name}')>"


class ResponseAttachment(Base):
    """Model for attachments to ticket responses."""
    __tablename__ = "response_attachments"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("ticket_responses.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    content_type = Column(String(100), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    response = relationship("TicketResponse", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    
    def __repr__(self):
        return f"<ResponseAttachment(id={self.id}, file_name='{self.file_name}')>"


class Template(Base):
    """Model for message and notification templates."""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    template_type = Column(String(50), nullable=False)  # email, sms, notification, etc.
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<Template(id={self.id}, name='{self.name}', type='{self.template_type}')>"


class Webhook(Base):
    """Model for external service webhooks."""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(512), nullable=False)
    events = Column(JSON, nullable=False)  # List of event types this webhook subscribes to
    is_active = Column(Boolean, default=True)
    secret = Column(String(255), nullable=True)  # Secret for signing webhook payloads
    headers = Column(JSON, nullable=True)  # Custom headers to include in webhook requests
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    logs = relationship("WebhookLog", back_populates="webhook", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Webhook(id={self.id}, name='{self.name}', active={self.is_active})>"


class WebhookLog(Base):
    """Model for webhook delivery logs."""
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False)
    event = Column(String(100), nullable=False)
    request_payload = Column(JSON, nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    webhook = relationship("Webhook", back_populates="logs")
    
    def __repr__(self):
        return f"<WebhookLog(id={self.id}, webhook_id={self.webhook_id}, event='{self.event}', success={self.success})>"


class ExternalService(Base):
    """Model for external service integrations."""
    __tablename__ = "external_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    service_type = Column(String(50), nullable=False)  # e.g., "sms", "email", "chat"
    config = Column(JSON, nullable=False)  # Configuration for the service
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ExternalService(id={self.id}, name='{self.name}', type='{self.service_type}', active={self.is_active})>"


# Update User model relationships (to be added to the User model in backend_core/models.py)
"""
# Add these relationships to the User model in backend_core/models.py

# Messages
sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
received_messages = relationship("User", secondary="message_recipients", back_populates="recipients")

# Notifications
notifications = relationship("Notification", secondary="notification_recipients", back_populates="recipients")

# Announcements
announcements = relationship("Announcement", secondary="announcement_recipients", back_populates="targeted_recipients")

# Support Tickets
submitted_tickets = relationship("SupportTicket", foreign_keys="SupportTicket.customer_id", back_populates="customer")
assigned_tickets = relationship("SupportTicket", foreign_keys="SupportTicket.assigned_to", back_populates="assignee")
"""
