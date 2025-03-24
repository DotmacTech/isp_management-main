"""
Database models for the Integration Management Module.

This module defines the database models for managing integrations, their configurations,
versions, and activity logs.
"""

import enum
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from backend_core.database import Base


class IntegrationStatus(enum.Enum):
    """Enum for integration status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    FAILED = "failed"


class IntegrationEnvironment(enum.Enum):
    """Enum for integration environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class IntegrationType(enum.Enum):
    """Enum for integration types."""
    PAYMENT_GATEWAY = "payment_gateway"
    SMS_PROVIDER = "sms_provider"
    EMAIL_PROVIDER = "email_provider"
    ANALYTICS = "analytics"
    CRM = "crm"
    MONITORING = "monitoring"
    AUTHENTICATION = "authentication"
    STORAGE = "storage"
    CUSTOM = "custom"


class ActivityType(enum.Enum):
    """Enum for integration activity types."""
    WEBHOOK_RECEIVED = "webhook_received"
    API_CALL = "api_call"
    CONFIGURATION_UPDATED = "configuration_updated"
    CREDENTIALS_ROTATED = "credentials_rotated"
    STATUS_CHANGED = "status_changed"
    ERROR = "error"
    HEALTH_CHECK = "health_check"


class ActivityStatus(enum.Enum):
    """Enum for integration activity status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    PROCESSING = "processing"


class Integration(Base):
    """Model for storing integration configurations."""
    
    __tablename__ = "integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(IntegrationType), nullable=False)
    configuration = Column(JSON, nullable=False, default={})
    encrypted_credentials = Column(Text, nullable=False)
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.PENDING)
    environment = Column(Enum(IntegrationEnvironment), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    versions = relationship("IntegrationVersion", back_populates="integration", cascade="all, delete-orphan")
    activities = relationship("IntegrationActivity", back_populates="integration", cascade="all, delete-orphan")
    webhooks = relationship("WebhookEndpoint", back_populates="integration", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Integration {self.name} ({self.type.value}) - {self.status.value}>"


class IntegrationVersion(Base):
    """Model for storing integration version history."""
    
    __tablename__ = "integration_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)
    version = Column(String(50), nullable=False)
    configuration = Column(JSON, nullable=False)
    encrypted_credentials = Column(Text, nullable=False)
    active = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    integration = relationship("Integration", back_populates="versions")
    
    def __repr__(self):
        return f"<IntegrationVersion {self.integration_id} v{self.version} - {'Active' if self.active else 'Inactive'}>"


class IntegrationActivity(Base):
    """Model for storing integration activity logs."""
    
    __tablename__ = "integration_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)
    activity_type = Column(Enum(ActivityType), nullable=False)
    status = Column(Enum(ActivityStatus), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    integration = relationship("Integration", back_populates="activities")
    
    def __repr__(self):
        return f"<IntegrationActivity {self.integration_id} - {self.activity_type.value} ({self.status.value})>"


class WebhookEndpoint(Base):
    """Model for storing webhook endpoint configurations."""
    
    __tablename__ = "webhook_endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False, unique=True)
    secret_key = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    integration = relationship("Integration", back_populates="webhooks")
    events = relationship("WebhookEvent", back_populates="endpoint", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WebhookEndpoint {self.name} - {self.path}>"


class WebhookEvent(Base):
    """Model for storing webhook events."""
    
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("webhook_endpoints.id"), nullable=False)
    event_type = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    headers = Column(JSON, nullable=True)
    signature = Column(String(255), nullable=True)
    status = Column(Enum(ActivityStatus), default=ActivityStatus.PENDING)
    processing_attempts = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    endpoint = relationship("WebhookEndpoint", back_populates="events")
    
    def __repr__(self):
        return f"<WebhookEvent {self.id} - {self.event_type} ({self.status.value})>"
