"""
Database models for the Service Activation Module.
"""

import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, Boolean, JSON
from sqlalchemy.orm import relationship

from backend_core.database import Base


class ActivationStatus(enum.Enum):
    """Enum for service activation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK_IN_PROGRESS = "rollback_in_progress"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_FAILED = "rollback_failed"


class StepStatus(enum.Enum):
    """Enum for activation step status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLBACK_IN_PROGRESS = "rollback_in_progress"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_FAILED = "rollback_failed"


class ServiceActivation(Base):
    """Model for service activation records."""
    __tablename__ = "service_activations"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)
    status = Column(Enum(ActivationStatus), default=ActivationStatus.PENDING, nullable=False)
    payment_verified = Column(Boolean, default=False, nullable=False)
    prerequisites_checked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="service_activations")
    service = relationship("Service", back_populates="activations")
    tariff = relationship("Tariff", back_populates="activations")
    steps = relationship("ActivationStep", back_populates="activation", cascade="all, delete-orphan")
    logs = relationship("ActivationLog", back_populates="activation", cascade="all, delete-orphan")


class ActivationStep(Base):
    """Model for individual steps in the activation workflow."""
    __tablename__ = "activation_steps"

    id = Column(Integer, primary_key=True, index=True)
    activation_id = Column(Integer, ForeignKey("service_activations.id"), nullable=False)
    step_name = Column(String(100), nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(Enum(StepStatus), default=StepStatus.PENDING, nullable=False)
    description = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    is_rollback_step = Column(Boolean, default=False, nullable=False)
    depends_on_step_id = Column(Integer, ForeignKey("activation_steps.id"), nullable=True)
    
    # Relationships
    activation = relationship("ServiceActivation", back_populates="steps")
    depends_on = relationship("ActivationStep", remote_side=[id], backref="dependent_steps")


class ActivationLog(Base):
    """Model for logging activation events."""
    __tablename__ = "activation_logs"

    id = Column(Integer, primary_key=True, index=True)
    activation_id = Column(Integer, ForeignKey("service_activations.id"), nullable=False)
    step_id = Column(Integer, ForeignKey("activation_steps.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Relationships
    activation = relationship("ServiceActivation", back_populates="logs")
    step = relationship("ActivationStep", backref="logs")
