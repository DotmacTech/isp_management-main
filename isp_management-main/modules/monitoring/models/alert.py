"""
Alert models for the monitoring module.

This module defines models for alert configurations and alert history
for the monitoring module.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend_core.database import Base


class AlertSeverity(str, Enum):
    """Enum for alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Enum for alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertType(str, Enum):
    """Enum for alert types."""
    SERVICE_AVAILABILITY = "service_availability"
    SYSTEM_METRIC = "system_metric"
    NETWORK_PERFORMANCE = "network_performance"
    CUSTOMER_USAGE = "customer_usage"
    CUSTOM = "custom"


class AlertConfiguration(Base):
    """
    Model for alert configurations.
    
    This model stores alert configurations for different types of alerts,
    including thresholds, conditions, and notification settings.
    """
    __tablename__ = "alert_configurations"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    alert_type = Column(String, nullable=False)
    target_id = Column(String, nullable=True)  # ID of the target (service, metric, etc.)
    condition = Column(String, nullable=False)  # e.g., "value > 90" for CPU usage
    threshold = Column(Float, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds for the condition to be true
    severity = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    notification_channels = Column(JSON, nullable=True)  # List of notification channels
    cooldown_period = Column(Integer, nullable=True)  # Cooldown period in seconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    alerts = relationship("Alert", back_populates="configuration", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the alert configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the alert configuration.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "alert_type": self.alert_type,
            "target_id": self.target_id,
            "condition": self.condition,
            "threshold": self.threshold,
            "duration": self.duration,
            "severity": self.severity,
            "enabled": self.enabled,
            "notification_channels": self.notification_channels,
            "cooldown_period": self.cooldown_period,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Alert(Base):
    """
    Model for alerts.
    
    This model stores alerts generated when alert conditions are met.
    """
    __tablename__ = "alerts"
    
    id = Column(String, primary_key=True)
    configuration_id = Column(String, ForeignKey("alert_configurations.id"), nullable=False)
    status = Column(String, nullable=False, default=AlertStatus.ACTIVE)
    severity = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    configuration = relationship("AlertConfiguration", back_populates="alerts")
    history = relationship("AlertHistory", back_populates="alert", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the alert to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the alert.
        """
        return {
            "id": self.id,
            "configuration_id": self.configuration_id,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """
        Convert the alert to a format suitable for Elasticsearch.
        
        Returns:
            Dict[str, Any]: Elasticsearch-friendly representation of the alert.
        """
        return {
            "id": self.id,
            "configuration_id": self.configuration_id,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "@timestamp": datetime.utcnow().isoformat()
        }


class AlertHistory(Base):
    """
    Model for alert history.
    
    This model stores the history of status changes for alerts.
    """
    __tablename__ = "alert_history"
    
    id = Column(String, primary_key=True)
    alert_id = Column(String, ForeignKey("alerts.id"), nullable=False)
    status = Column(String, nullable=False)
    user_id = Column(String, nullable=True)  # User who changed the status
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    alert = relationship("Alert", back_populates="history")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the alert history to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the alert history.
        """
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "status": self.status,
            "user_id": self.user_id,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """
        Convert the alert history to a format suitable for Elasticsearch.
        
        Returns:
            Dict[str, Any]: Elasticsearch-friendly representation of the alert history.
        """
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "status": self.status,
            "user_id": self.user_id,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "@timestamp": datetime.utcnow().isoformat()
        }


class NotificationChannel(Base):
    """
    Model for notification channels.
    
    This model stores notification channels for alerts, such as email,
    SMS, Slack, etc.
    """
    __tablename__ = "notification_channels"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # email, sms, slack, webhook, etc.
    configuration = Column(JSON, nullable=False)  # Configuration for the channel
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the notification channel to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the notification channel.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "configuration": self.configuration,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
