"""
Log retention models for the monitoring module.

This module defines models for log retention policies and
log archiving configurations.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend_core.database import Base


class RetentionPeriodType(str, Enum):
    """Enum for retention period types."""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class LogRetentionPolicy(Base):
    """
    Model for log retention policies.
    
    This model stores log retention policies for different types of logs,
    including service logs, system metrics, and alerts.
    """
    __tablename__ = "log_retention_policies"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    log_type = Column(String, nullable=False)  # service_logs, system_metrics, alerts, etc.
    retention_period = Column(Integer, nullable=False)
    retention_period_type = Column(String, nullable=False)
    archive_enabled = Column(Boolean, default=False, nullable=False)
    archive_storage = Column(String, nullable=True)  # s3, local, etc.
    archive_configuration = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the log retention policy to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the log retention policy.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "log_type": self.log_type,
            "retention_period": self.retention_period,
            "retention_period_type": self.retention_period_type,
            "archive_enabled": self.archive_enabled,
            "archive_storage": self.archive_storage,
            "archive_configuration": self.archive_configuration,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_expiration_date(self, reference_date: Optional[datetime] = None) -> datetime:
        """
        Calculate the expiration date for logs based on the retention policy.
        
        Args:
            reference_date: Reference date to calculate from. Defaults to current time.
        
        Returns:
            Expiration date for logs.
        """
        if reference_date is None:
            reference_date = datetime.utcnow()
        
        if self.retention_period_type == RetentionPeriodType.DAYS:
            return reference_date - datetime.timedelta(days=self.retention_period)
        elif self.retention_period_type == RetentionPeriodType.WEEKS:
            return reference_date - datetime.timedelta(weeks=self.retention_period)
        elif self.retention_period_type == RetentionPeriodType.MONTHS:
            # Approximate months as 30 days
            return reference_date - datetime.timedelta(days=30 * self.retention_period)
        elif self.retention_period_type == RetentionPeriodType.YEARS:
            # Approximate years as 365 days
            return reference_date - datetime.timedelta(days=365 * self.retention_period)
        else:
            raise ValueError(f"Invalid retention period type: {self.retention_period_type}")


class LogArchive(Base):
    """
    Model for log archives.
    
    This model stores information about archived logs, including
    the archive location and status.
    """
    __tablename__ = "log_archives"
    
    id = Column(String, primary_key=True)
    policy_id = Column(String, ForeignKey("log_retention_policies.id"), nullable=False)
    log_type = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    archive_location = Column(String, nullable=False)
    archive_size = Column(Integer, nullable=True)  # Size in bytes
    status = Column(String, nullable=False)  # pending, in_progress, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    policy = relationship("LogRetentionPolicy")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the log archive to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the log archive.
        """
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "log_type": self.log_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "archive_location": self.archive_location,
            "archive_size": self.archive_size,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
