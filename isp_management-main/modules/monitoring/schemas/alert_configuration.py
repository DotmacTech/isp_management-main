"""
Pydantic schemas for alert configurations.

This module defines Pydantic schemas for alert configurations, which are used for
API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class AlertConditionType(str, Enum):
    """Enum for alert condition types."""
    THRESHOLD = "threshold"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    HEARTBEAT = "heartbeat"
    CUSTOM = "custom"


class AlertAction(str, Enum):
    """Enum for alert actions."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    PAGERDUTY = "pagerduty"
    CUSTOM = "custom"


class AlertConfigurationBase(BaseModel):
    """Base schema for alert configurations."""
    name: str = Field(..., description="Name of the alert configuration")
    description: Optional[str] = Field(None, description="Description of the alert configuration")
    service_name: str = Field(..., description="Name of the service to monitor")
    condition_type: AlertConditionType = Field(..., description="Type of condition to check")
    condition_params: Dict[str, Any] = Field(..., description="Parameters for the condition")
    severity: str = Field(..., description="Severity of the alert")
    actions: List[AlertAction] = Field(..., description="Actions to take when the alert is triggered")
    action_params: Dict[str, Any] = Field(..., description="Parameters for the actions")
    enabled: bool = Field(True, description="Whether the alert configuration is enabled")


class AlertConfigurationCreate(AlertConfigurationBase):
    """Schema for creating alert configurations."""
    pass


class AlertConfigurationUpdate(BaseModel):
    """Schema for updating alert configurations."""
    name: Optional[str] = Field(None, description="Name of the alert configuration")
    description: Optional[str] = Field(None, description="Description of the alert configuration")
    service_name: Optional[str] = Field(None, description="Name of the service to monitor")
    condition_type: Optional[AlertConditionType] = Field(None, description="Type of condition to check")
    condition_params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the condition")
    severity: Optional[str] = Field(None, description="Severity of the alert")
    actions: Optional[List[AlertAction]] = Field(None, description="Actions to take when the alert is triggered")
    action_params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the actions")
    enabled: Optional[bool] = Field(None, description="Whether the alert configuration is enabled")


class AlertConfigurationInDB(AlertConfigurationBase):
    """Schema for alert configurations in the database."""
    id: int = Field(..., description="ID of the alert configuration")
    created_at: datetime = Field(..., description="Time when the alert configuration was created")
    updated_at: Optional[datetime] = Field(None, description="Time when the alert configuration was last updated")

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
