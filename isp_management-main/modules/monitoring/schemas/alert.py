"""
Pydantic schemas for alerts.

This module defines Pydantic schemas for alerts, alert configurations,
and notification channels, which are used for API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class AlertSeverityEnum(str, Enum):
    """Enum for alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatusEnum(str, Enum):
    """Enum for alert statuses."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AlertTypeEnum(str, Enum):
    """Enum for alert types."""
    SERVICE_AVAILABILITY = "service_availability"
    SYSTEM_METRIC = "system_metric"
    NETWORK_PERFORMANCE = "network_performance"
    CUSTOMER_USAGE = "customer_usage"
    CUSTOM = "custom"


# Alert Configuration Schemas
class AlertConfigurationBase(BaseModel):
    """Base schema for alert configurations."""
    name: str = Field(..., description="Name of the alert configuration")
    description: Optional[str] = Field(None, description="Description of the alert configuration")
    alert_type: AlertTypeEnum = Field(..., description="Type of the alert")
    severity: AlertSeverityEnum = Field(..., description="Severity of the alert")
    condition: Dict[str, Any] = Field(..., description="Condition for triggering the alert")
    enabled: bool = Field(True, description="Whether the alert configuration is enabled")
    cooldown_period: Optional[int] = Field(None, description="Cooldown period in seconds")
    auto_resolve: Optional[bool] = Field(True, description="Whether to auto-resolve the alert")
    auto_resolve_period: Optional[int] = Field(None, description="Auto-resolve period in seconds")


class AlertConfigurationCreate(AlertConfigurationBase):
    """Schema for creating alert configurations."""
    pass


class AlertConfigurationUpdate(BaseModel):
    """Schema for updating alert configurations."""
    name: Optional[str] = Field(None, description="Name of the alert configuration")
    description: Optional[str] = Field(None, description="Description of the alert configuration")
    severity: Optional[AlertSeverityEnum] = Field(None, description="Severity of the alert")
    condition: Optional[Dict[str, Any]] = Field(None, description="Condition for triggering the alert")
    enabled: Optional[bool] = Field(None, description="Whether the alert configuration is enabled")
    cooldown_period: Optional[int] = Field(None, description="Cooldown period in seconds")
    auto_resolve: Optional[bool] = Field(None, description="Whether to auto-resolve the alert")
    auto_resolve_period: Optional[int] = Field(None, description="Auto-resolve period in seconds")


class AlertConfigurationInDB(AlertConfigurationBase):
    """Schema for alert configurations in the database."""
    id: str = Field(..., description="ID of the alert configuration")
    created_at: datetime = Field(..., description="Time when the alert configuration was created")
    updated_at: datetime = Field(..., description="Time when the alert configuration was last updated")

    model_config = ConfigDict(from_attributes=True)


class AlertConfigurationResponse(AlertConfigurationInDB):
    """Schema for alert configuration responses."""
    pass


class AlertConfigurationList(BaseModel):
    """Schema for a list of alert configurations."""
    items: List[AlertConfigurationResponse] = Field(..., description="List of alert configurations")
    total: int = Field(..., description="Total number of alert configurations")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


# Alert Schemas
class AlertBase(BaseModel):
    """Base schema for alerts."""
    configuration_id: str = Field(..., description="ID of the alert configuration")
    status: AlertStatusEnum = Field(..., description="Status of the alert")
    message: str = Field(..., description="Alert message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    source_id: Optional[str] = Field(None, description="ID of the source that triggered the alert")
    source_type: Optional[str] = Field(None, description="Type of the source that triggered the alert")


class AlertCreate(AlertBase):
    """Schema for creating alerts."""
    pass


class AlertUpdate(BaseModel):
    """Schema for updating alerts."""
    status: Optional[AlertStatusEnum] = Field(None, description="Status of the alert")
    message: Optional[str] = Field(None, description="Alert message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class AlertInDB(AlertBase):
    """Schema for alerts in the database."""
    id: str = Field(..., description="ID of the alert")
    created_at: datetime = Field(..., description="Time when the alert was created")
    updated_at: datetime = Field(..., description="Time when the alert was last updated")
    configuration: AlertConfigurationResponse = Field(..., description="Alert configuration")

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(AlertInDB):
    """Schema for alert responses."""
    pass


class AlertList(BaseModel):
    """Schema for a list of alerts."""
    items: List[AlertResponse] = Field(..., description="List of alerts")
    total: int = Field(..., description="Total number of alerts")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class AlertFilter(BaseModel):
    """Schema for filtering alerts."""
    configuration_id: Optional[str] = Field(None, description="Filter by configuration ID")
    status: Optional[AlertStatusEnum] = Field(None, description="Filter by status")
    severity: Optional[AlertSeverityEnum] = Field(None, description="Filter by severity")
    alert_type: Optional[AlertTypeEnum] = Field(None, description="Filter by alert type")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    source_id: Optional[str] = Field(None, description="Filter by source ID")
    source_type: Optional[str] = Field(None, description="Filter by source type")


# Alert History Schemas
class AlertHistoryBase(BaseModel):
    """Base schema for alert history."""
    alert_id: str = Field(..., description="ID of the alert")
    old_status: Optional[AlertStatusEnum] = Field(None, description="Old status of the alert")
    new_status: AlertStatusEnum = Field(..., description="New status of the alert")
    comment: Optional[str] = Field(None, description="Comment on the status change")
    user_id: Optional[str] = Field(None, description="ID of the user who changed the status")


class AlertHistoryCreate(AlertHistoryBase):
    """Schema for creating alert history."""
    pass


class AlertHistoryUpdate(BaseModel):
    """Schema for updating alert history."""
    comment: Optional[str] = Field(None, description="Comment on the status change")
    user_id: Optional[str] = Field(None, description="ID of the user who changed the status")


class AlertHistoryInDB(AlertHistoryBase):
    """Schema for alert history in the database."""
    id: str = Field(..., description="ID of the alert history")
    created_at: datetime = Field(..., description="Time when the alert history was created")

    model_config = ConfigDict(from_attributes=True)


class AlertHistoryResponse(AlertHistoryInDB):
    """Schema for alert history responses."""
    pass


# Alert Summary Schema
class AlertSummary(BaseModel):
    """Schema for alert summary statistics."""
    total: int = Field(..., description="Total number of alerts")
    active: int = Field(..., description="Number of active alerts")
    acknowledged: int = Field(..., description="Number of acknowledged alerts")
    resolved: int = Field(..., description="Number of resolved alerts")
    closed: int = Field(..., description="Number of closed alerts")
    info: int = Field(..., description="Number of info alerts")
    warning: int = Field(..., description="Number of warning alerts")
    error: int = Field(..., description="Number of error alerts")
    critical: int = Field(..., description="Number of critical alerts")
    last_24h: int = Field(..., description="Number of alerts in the last 24 hours")
    last_7d: int = Field(..., description="Number of alerts in the last 7 days")


# Notification Channel Schemas
class NotificationChannelTypeEnum(str, Enum):
    """Enum for notification channel types."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    CUSTOM = "custom"


class NotificationChannelBase(BaseModel):
    """Base schema for notification channels."""
    name: str = Field(..., description="Name of the notification channel")
    description: Optional[str] = Field(None, description="Description of the notification channel")
    channel_type: NotificationChannelTypeEnum = Field(..., description="Type of the notification channel")
    configuration: Dict[str, Any] = Field(..., description="Configuration for the notification channel")
    enabled: bool = Field(True, description="Whether the notification channel is enabled")


class NotificationChannelCreate(NotificationChannelBase):
    """Schema for creating notification channels."""
    pass


class NotificationChannelUpdate(BaseModel):
    """Schema for updating notification channels."""
    name: Optional[str] = Field(None, description="Name of the notification channel")
    description: Optional[str] = Field(None, description="Description of the notification channel")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Configuration for the notification channel")
    enabled: Optional[bool] = Field(None, description="Whether the notification channel is enabled")


class NotificationChannelInDB(NotificationChannelBase):
    """Schema for notification channels in the database."""
    id: str = Field(..., description="ID of the notification channel")
    created_at: datetime = Field(..., description="Time when the notification channel was created")
    updated_at: datetime = Field(..., description="Time when the notification channel was last updated")

    model_config = ConfigDict(from_attributes=True)


class NotificationChannelResponse(NotificationChannelInDB):
    """Schema for notification channel responses."""
    pass
