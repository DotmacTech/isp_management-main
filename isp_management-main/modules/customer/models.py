"""
Database models for the Customer Management Module.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, Enum as SQLAEnum, JSON, Table, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

from backend_core.database import Base
from backend_core.models import TimestampMixin


class CustomerType(str, Enum):
    """Customer type enumeration."""
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    GOVERNMENT = "government"
    EDUCATIONAL = "educational"
    NON_PROFIT = "non_profit"


class CustomerStatus(str, Enum):
    """Customer status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CLOSED = "closed"


class SubscriptionState(str, Enum):
    """Subscription state enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_ACTIVATION = "pending_activation"
    PENDING_PAYMENT = "pending_payment"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class VerificationStatus(str, Enum):
    """Verification status enumeration."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class CommunicationType(str, Enum):
    """Communication type enumeration."""
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    MAIL = "mail"
    PUSH = "push"


class DocumentType(str, Enum):
    """Document type enumeration."""
    ID_CARD = "id_card"
    PASSPORT = "passport"
    DRIVING_LICENSE = "driving_license"
    BUSINESS_REGISTRATION = "business_registration"
    TAX_ID = "tax_id"
    UTILITY_BILL = "utility_bill"
    CONTRACT = "contract"
    OTHER = "other"


class AddressType(str, Enum):
    """Address type enumeration."""
    BILLING = "billing"
    SERVICE = "service"
    MAILING = "mailing"
    LEGAL = "legal"
    OTHER = "other"


class ContactType(str, Enum):
    """Contact type enumeration."""
    PRIMARY = "primary"
    BILLING = "billing"
    TECHNICAL = "technical"
    EMERGENCY = "emergency"
    OTHER = "other"


class ContactMethodType(str, Enum):
    """Enum for contact method types."""
    EMAIL = "email"
    PHONE = "phone"
    MOBILE = "mobile"
    FAX = "fax"
    SOCIAL = "social"
    OTHER = "other"


# Association table for customer tags
customer_tags = Table(
    'customer_tags',
    Base.metadata,
    Column('customer_id', Integer, ForeignKey('customers.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('customer_tag_definitions.id'), primary_key=True)
)


class Customer(Base, TimestampMixin):
    """Customer model representing individuals or organizations."""
    __tablename__ = "customers"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    customer_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_type = Column(SQLAEnum(CustomerType), nullable=False, default=CustomerType.INDIVIDUAL)
    status = Column(SQLAEnum(CustomerStatus), nullable=False, default=CustomerStatus.PENDING)
    
    # Personal/Business information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company_name = Column(String(200), nullable=True)
    tax_id = Column(String(50), nullable=True)
    registration_number = Column(String(50), nullable=True)
    
    # Contact information
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    
    # Account information
    username = Column(String(100), nullable=True, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    portal_id = Column(String(50), nullable=True, unique=True, index=True)
    is_email_verified = Column(Boolean, default=False)
    email_verification_date = Column(DateTime, nullable=True)
    
    # Subscription information
    subscription_state = Column(SQLAEnum(SubscriptionState), nullable=False, default=SubscriptionState.PENDING_ACTIVATION)
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    
    # Marketing information
    marketing_consent = Column(Boolean, default=False)
    marketing_consent_date = Column(DateTime, nullable=True)
    referral_source = Column(String(100), nullable=True)
    
    # Additional information
    notes = Column(Text, nullable=True)
    properties = Column(JSON, nullable=True)
    
    # Relationships
    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    contacts = relationship("CustomerContact", back_populates="customer", cascade="all, delete-orphan")
    communication_preferences = relationship("CommunicationPreference", back_populates="customer", cascade="all, delete-orphan")
    documents = relationship("CustomerDocument", back_populates="customer", cascade="all, delete-orphan")
    customer_notes = relationship("CustomerNote", back_populates="customer", cascade="all, delete-orphan")
    email_verifications = relationship("EmailVerification", back_populates="customer", cascade="all, delete-orphan")
    tags = relationship("CustomerTagDefinition", secondary=customer_tags, back_populates="customers")
    custom_fields = relationship("CustomerCustomField", back_populates="customer", cascade="all, delete-orphan")
    contact_methods = relationship("CustomerContactMethod", back_populates="customer", cascade="all, delete-orphan")
    
    def __repr__(self):
        if self.customer_type == CustomerType.INDIVIDUAL:
            return f"<Customer {self.id}: {self.first_name} {self.last_name}>"
        else:
            return f"<Customer {self.id}: {self.company_name}>"


class CustomerAddress(Base, TimestampMixin):
    """Customer address model."""
    __tablename__ = "customer_addresses"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    address_type = Column(SQLAEnum(AddressType), nullable=False, default=AddressType.BILLING)
    
    street_address1 = Column(String(255), nullable=False)
    street_address2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    
    is_default = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verification_date = Column(DateTime, nullable=True)
    
    # Geolocation for service planning
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="addresses")
    
    def __repr__(self):
        return f"<CustomerAddress {self.id}: {self.address_type.value} for Customer {self.customer_id}>"


class CustomerContact(Base, TimestampMixin):
    """Customer contact person model for business customers."""
    __tablename__ = "customer_contacts"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    contact_type = Column(SQLAEnum(ContactType), nullable=False, default=ContactType.PRIMARY)
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    position = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="contacts")
    
    def __repr__(self):
        return f"<CustomerContact {self.id}: {self.first_name} {self.last_name} ({self.contact_type.value})>"


class CommunicationPreference(Base, TimestampMixin):
    """Customer communication preferences model."""
    __tablename__ = "communication_preferences"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    communication_type = Column(SQLAEnum(CommunicationType), nullable=False)
    enabled = Column(Boolean, default=True)
    
    # Specific preferences
    billing_notifications = Column(Boolean, default=True)
    service_notifications = Column(Boolean, default=True)
    marketing_communications = Column(Boolean, default=False)
    technical_notifications = Column(Boolean, default=True)
    emergency_alerts = Column(Boolean, default=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="communication_preferences")
    
    def __repr__(self):
        return f"<CommunicationPreference {self.id}: {self.communication_type.value} for Customer {self.customer_id}>"


class CustomerDocument(Base, TimestampMixin):
    """Customer document model for storing identity and verification documents."""
    __tablename__ = "customer_documents"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    document_type = Column(SQLAEnum(DocumentType), nullable=False)
    document_number = Column(String(100), nullable=True)
    document_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    mime_type = Column(String(100), nullable=True)
    
    issue_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    verification_status = Column(SQLAEnum(VerificationStatus), nullable=False, default=VerificationStatus.PENDING)
    verified_by = Column(String(100), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="documents")
    
    def __repr__(self):
        return f"<CustomerDocument {self.id}: {self.document_type.value} for Customer {self.customer_id}>"


class CustomerNote(Base, TimestampMixin):
    """Customer notes model for internal staff comments."""
    __tablename__ = "customer_notes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    created_by = Column(String(100), nullable=False)
    
    is_important = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)  # Private notes are only visible to admins
    
    # Relationships
    customer = relationship("Customer", back_populates="customer_notes")
    
    def __repr__(self):
        return f"<CustomerNote {self.id}: for Customer {self.customer_id}>"


class CustomerCustomField(Base, TimestampMixin):
    """Model for storing custom fields for customers."""
    __tablename__ = "customer_custom_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(50), nullable=False)  # string, number, boolean, date, etc.
    field_value = Column(String(500), nullable=True)
    is_searchable = Column(Boolean, default=True)
    is_api_visible = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="custom_fields")
    
    __table_args__ = (
        UniqueConstraint('customer_id', 'field_name', name='uix_customer_field_name'),
    )


class EmailVerification(Base, TimestampMixin):
    """Email verification model for tracking verification attempts."""
    __tablename__ = "email_verifications"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    email = Column(String(255), nullable=False)
    verification_token = Column(String(255), nullable=False, unique=True)
    
    status = Column(SQLAEnum(VerificationStatus), nullable=False, default=VerificationStatus.PENDING)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="email_verifications")
    
    def __repr__(self):
        return f"<EmailVerification {self.id}: {self.status.value} for {self.email}>"


class CustomerTagDefinition(Base, TimestampMixin):
    """Customer tag definitions for categorizing customers."""
    __tablename__ = "customer_tag_definitions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    
    # For automatic tagging based on criteria
    auto_assign = Column(Boolean, default=False)
    auto_assign_criteria = Column(JSON, nullable=True)
    
    # Relationships
    customers = relationship("Customer", secondary=customer_tags, back_populates="tags")
    
    def __repr__(self):
        return f"<CustomerTagDefinition {self.id}: {self.name}>"


class CustomerContactMethod(Base, TimestampMixin):
    """Model for storing multiple contact methods for customers."""
    __tablename__ = "customer_contact_methods"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    method_type = Column(SQLAEnum(ContactMethodType), nullable=False)
    value = Column(String(255), nullable=False)
    label = Column(String(100), nullable=True)  # e.g., "Work Email", "Personal Phone"
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verification_date = Column(DateTime, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="contact_methods")
    
    __table_args__ = (
        UniqueConstraint('customer_id', 'method_type', 'value', name='uix_customer_contact_method'),
    )
