"""
System health check models for the ISP Management Platform.

This module defines the database models for system health checks and system health status.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

from backend_core.database import Base
from modules.monitoring.schemas.system_health import HealthStatusEnum, CheckTypeEnum


class SystemHealthCheck(Base):
    """
    Model for system health checks.
    
    This model stores information about health checks that are performed on system components.
    """
    __tablename__ = "system_health_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    component_name = Column(String(255), nullable=False, index=True)
    check_type = Column(Enum(CheckTypeEnum), nullable=False)
    check_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    interval_seconds = Column(Integer, nullable=False, default=60)
    timeout_seconds = Column(Integer, nullable=False, default=10)
    retry_count = Column(Integer, nullable=False, default=3)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    statuses = relationship("SystemHealthStatus", back_populates="health_check", cascade="all, delete-orphan")


class SystemHealthStatus(Base):
    """
    Model for system health status.
    
    This model stores the status of health checks performed on system components.
    """
    __tablename__ = "system_health_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    health_check_id = Column(Integer, ForeignKey("system_health_checks.id"), nullable=False)
    component_name = Column(String(255), nullable=True)  
    status = Column(Enum(HealthStatusEnum), nullable=False, default=HealthStatusEnum.UNKNOWN)
    response_time_ms = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    last_checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    health_check = relationship("SystemHealthCheck", back_populates="statuses")
