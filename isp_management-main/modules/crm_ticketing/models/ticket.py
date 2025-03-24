"""
Ticket models for the CRM & Ticketing module.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Enum, Table
from sqlalchemy.orm import relationship

from backend_core.database import Base
from .common import TicketStatus, TicketPriority, TicketType, ContactMethod


# Association table for ticket tags
ticket_tags = Table(
    "crm_ticket_tags",
    Base.metadata,
    Column("ticket_id", Integer, ForeignKey("crm_tickets.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("crm_tags.id"), primary_key=True)
)


class Tag(Base):
    """Tag model for categorizing tickets."""
    __tablename__ = "crm_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    color = Column(String(7), nullable=True)  # Hex color code
    description = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tickets = relationship("Ticket", secondary=ticket_tags, back_populates="tags")
    
    def __repr__(self):
        return f"<Tag(id={self.id}, name={self.name})>"


class Ticket(Base):
    """
    Support ticket model.
    
    Represents a customer support ticket in the system.
    """
    __tablename__ = "crm_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(20), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False)
    
    # Basic ticket information
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.NEW, nullable=False)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    ticket_type = Column(Enum(TicketType), nullable=False)
    
    # Assignment information
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_team = Column(Integer, ForeignKey("teams.id"), nullable=True)
    
    # SLA information
    sla_id = Column(Integer, ForeignKey("crm_slas.id"), nullable=True)
    first_response_target = Column(DateTime, nullable=True)
    next_update_target = Column(DateTime, nullable=True)
    resolution_target = Column(DateTime, nullable=True)
    first_response_at = Column(DateTime, nullable=True)
    last_update_at = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False)
    
    # Source information
    source = Column(Enum(ContactMethod), nullable=False)
    source_details = Column(JSON, default=dict)
    
    # Related entities
    parent_ticket_id = Column(Integer, ForeignKey("crm_tickets.id"), nullable=True)
    related_service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    
    # Custom fields and metadata
    custom_fields = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="tickets")
    assignee = relationship("User", foreign_keys=[assigned_to])
    team = relationship("Team", foreign_keys=[assigned_team])
    sla = relationship("SLA")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    history = relationship("TicketHistory", back_populates="ticket", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=ticket_tags, back_populates="tickets")
    parent_ticket = relationship("Ticket", remote_side=[id], backref="child_tickets")
    related_service = relationship("Service")
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, number={self.ticket_number}, status={self.status})>"
    
    @property
    def is_overdue(self):
        """Check if the ticket is overdue based on SLA."""
        if self.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED]:
            return False
            
        now = datetime.utcnow()
        
        # Check first response SLA
        if not self.first_response_at and self.first_response_target and now > self.first_response_target:
            return True
            
        # Check resolution SLA
        if self.resolution_target and now > self.resolution_target:
            return True
            
        return False


class TicketComment(Base):
    """
    Comments on a ticket.
    
    Represents a comment or update on a ticket, either from a customer or staff member.
    """
    __tablename__ = "crm_ticket_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("crm_tickets.id"), nullable=False)
    
    content = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_internal = Column(Boolean, default=False)  # Whether visible to customer
    is_system = Column(Boolean, default=False)  # Whether generated by system
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")
    attachments = relationship("TicketAttachment", back_populates="comment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TicketComment(id={self.id}, ticket_id={self.ticket_id})>"


class TicketAttachment(Base):
    """
    Attachments for tickets and comments.
    
    Represents a file attached to a ticket or comment.
    """
    __tablename__ = "crm_ticket_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("crm_tickets.id"), nullable=False)
    comment_id = Column(Integer, ForeignKey("crm_ticket_comments.id"), nullable=True)
    
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_internal = Column(Boolean, default=False)  # Whether visible to customer
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")
    comment = relationship("TicketComment", back_populates="attachments")
    uploader = relationship("User")
    
    def __repr__(self):
        return f"<TicketAttachment(id={self.id}, filename={self.filename})>"


class TicketHistory(Base):
    """
    History of ticket changes.
    
    Tracks all changes made to a ticket for auditing purposes.
    """
    __tablename__ = "crm_ticket_history"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("crm_tickets.id"), nullable=False)
    
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="history")
    user = relationship("User")
    
    def __repr__(self):
        return f"<TicketHistory(id={self.id}, field={self.field_name})>"
