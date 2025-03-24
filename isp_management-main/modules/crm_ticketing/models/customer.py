"""
Customer models for the CRM & Ticketing module.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship

from backend_core.database import Base
from .common import ContactType, ContactMethod


class Customer(Base):
    """
    Customer model for CRM tracking.
    
    This model extends the core customer data with CRM-specific information.
    It links to the core customer model in the customer management module.
    """
    __tablename__ = "crm_customers"
    
    id = Column(Integer, primary_key=True, index=True)
    core_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    
    # CRM-specific fields
    satisfaction_score = Column(Integer, nullable=True)  # 1-10 scale
    lifetime_value = Column(Integer, nullable=True)  # In cents
    acquisition_channel = Column(String(50), nullable=True)
    acquisition_date = Column(DateTime, nullable=True)
    last_contact_date = Column(DateTime, nullable=True)
    preferred_contact_method = Column(Enum(ContactMethod), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contacts = relationship("CustomerContact", back_populates="customer", cascade="all, delete-orphan")
    customer_notes = relationship("CustomerNote", back_populates="customer", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="customer")
    
    # Relationship to core customer
    core_customer = relationship("Customer", foreign_keys=[core_customer_id], 
                                primaryjoin="Customer.id == CRMCustomer.core_customer_id")
    
    def __repr__(self):
        return f"<CRMCustomer(id={self.id}, core_customer_id={self.core_customer_id})>"


class CustomerContact(Base):
    """
    Customer contact information.
    
    Stores additional contact information for customers beyond what's in the core customer model.
    """
    __tablename__ = "crm_customer_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False)
    
    contact_type = Column(Enum(ContactType), nullable=False)
    contact_method = Column(Enum(ContactMethod), nullable=False)
    
    name = Column(String(100), nullable=False)
    value = Column(String(255), nullable=False)  # Email, phone number, etc.
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="contacts")
    
    def __repr__(self):
        return f"<CustomerContact(id={self.id}, type={self.contact_type}, method={self.contact_method})>"


class CustomerNote(Base):
    """
    Notes about customer interactions.
    
    Allows support staff to record notes about customer interactions that aren't
    directly related to tickets.
    """
    __tablename__ = "crm_customer_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False)
    
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_private = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="customer_notes")
    author = relationship("User")
    
    def __repr__(self):
        return f"<CustomerNote(id={self.id}, title={self.title})>"
