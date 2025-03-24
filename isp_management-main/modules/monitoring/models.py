"""
Database models for the logging and monitoring module.

This module contains SQLAlchemy models for:
- Centralized logging from all services
- System metrics and performance data
- Alert configurations and notifications
- Log retention policies
- Correlation of logs across services
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text, JSON, BigInteger
from sqlalchemy.orm import relationship

from backend_core.database import Base
import enum


class LogLevel(enum.Enum):
    """Standard log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(enum.Enum):
    """Types of system metrics that can be monitored."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_BANDWIDTH = "network_bandwidth"
    LATENCY = "latency"
    REQUEST_COUNT = "request_count"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    CONCURRENT_USERS = "concurrent_users"
    QUEUE_SIZE = "queue_size"
    DATABASE_CONNECTIONS = "database_connections"
    CACHE_HIT_RATE = "cache_hit_rate"
    CUSTOM = "custom"


class AlertSeverity(enum.Enum):
    """Severity levels for monitoring alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(enum.Enum):
    """Status of an alert."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class ServiceLog(Base):
    """Model for centralized logging from all services."""
    __tablename__ = "monitoring_service_logs"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    log_level = Column(Enum(LogLevel), nullable=False, index=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    trace_id = Column(String(100), index=True)  # For request tracing across services
    correlation_id = Column(String(100), index=True)  # For correlating related logs
    source_ip = Column(String(45))
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    request_path = Column(String(255))
    request_method = Column(String(10))
    response_status = Column(Integer)
    execution_time_ms = Column(Float)
    metadata = Column(JSON, nullable=True)  # Additional context data
    elasticsearch_synced = Column(Boolean, default=False, index=True)
    
    # Relationships
    user = relationship("User")


class SystemMetric(Base):
    """Model for storing system performance metrics."""
    __tablename__ = "monitoring_system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    host_name = Column(String(100), nullable=False, index=True)
    metric_type = Column(Enum(MetricType), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tags = Column(JSON, nullable=True)  # For additional categorization
    sampling_rate = Column(Float, default=1.0)  # For high-volume metrics
    elasticsearch_synced = Column(Boolean, default=False, index=True)


class LogRetentionPolicy(Base):
    """Model for log retention policies."""
    __tablename__ = "monitoring_log_retention_policies"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    log_level = Column(Enum(LogLevel), nullable=False)
    retention_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("User")


class AlertConfiguration(Base):
    """Model for alert configurations and thresholds."""
    __tablename__ = "monitoring_alert_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    service_name = Column(String(100), nullable=False)
    metric_type = Column(Enum(MetricType))
    log_level = Column(Enum(LogLevel))  # For log-based alerts
    condition_type = Column(String(20), nullable=False)  # threshold, pattern, anomaly
    threshold_value = Column(Float)  # For threshold-based alerts
    pattern = Column(String(255))  # For pattern-based alerts
    comparison_operator = Column(String(10))  # >, <, >=, <=, ==, !=, contains, regex
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    is_active = Column(Boolean, default=True)
    cooldown_minutes = Column(Integer, default=15)  # Minimum time between repeated alerts
    notification_channels = Column(JSON)  # Store notification preferences (email, SMS, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("User")
    alert_history = relationship("AlertHistory", back_populates="configuration", cascade="all, delete-orphan")


class AlertHistory(Base):
    """Model for storing alert history."""
    __tablename__ = "monitoring_alert_history"

    id = Column(Integer, primary_key=True, index=True)
    configuration_id = Column(Integer, ForeignKey("monitoring_alert_configurations.id"), nullable=False)
    triggered_value = Column(Float)
    matched_pattern = Column(String(255))
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    message = Column(Text, nullable=False)
    source_log_id = Column(Integer, ForeignKey("monitoring_service_logs.id"))
    source_metric_id = Column(Integer, ForeignKey("monitoring_system_metrics.id"))
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime)
    acknowledged_by = Column(Integer, ForeignKey("users.id"))
    resolution_notes = Column(Text)
    notification_sent = Column(Boolean, default=False)
    
    # Relationships
    configuration = relationship("AlertConfiguration", back_populates="alert_history")
    user = relationship("User", foreign_keys=[acknowledged_by])
    source_log = relationship("ServiceLog")
    source_metric = relationship("SystemMetric")


class DashboardConfiguration(Base):
    """Model for configuring monitoring dashboards."""
    __tablename__ = "monitoring_dashboard_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    layout = Column(JSON)  # Dashboard widget layout
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("User")
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")


class DashboardWidget(Base):
    """Model for individual dashboard widgets."""
    __tablename__ = "monitoring_dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("monitoring_dashboard_configurations.id"), nullable=False)
    widget_type = Column(String(50), nullable=False)  # chart, gauge, table, etc.
    title = Column(String(100), nullable=False)
    data_source = Column(String(100), nullable=False)  # metrics, logs, alerts
    query = Column(Text, nullable=False)  # Query to fetch data
    refresh_interval_seconds = Column(Integer, default=60)
    position_x = Column(Integer)
    position_y = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    visualization_options = Column(JSON)  # Colors, thresholds, etc.
    
    # Relationships
    dashboard = relationship("DashboardConfiguration", back_populates="widgets")
