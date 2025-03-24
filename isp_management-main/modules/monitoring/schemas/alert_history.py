"""
Pydantic schemas for alert history.

This module defines Pydantic schemas for alert history, which are used for
API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class AlertHistoryBase(BaseModel):
    """Base schema for alert history."""
    alert_config_id: int = Field(..., description="ID of the alert configuration")
    service_name: str = Field(..., description="Name of the service that triggered the alert")
    severity: str = Field(..., description="Severity of the alert")
    message: str = Field(..., description="Alert message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    status: str = Field("new", description="Status of the alert")
    acknowledged_by: Optional[int] = Field(None, description="ID of the user who acknowledged the alert")
    resolved_by: Optional[int] = Field(None, description="ID of the user who resolved the alert")
    acknowledged_at: Optional[datetime] = Field(None, description="Time when the alert was acknowledged")
    resolved_at: Optional[datetime] = Field(None, description="Time when the alert was resolved")


class AlertHistoryCreate(AlertHistoryBase):
    """Schema for creating alert history."""
    pass


class AlertHistoryUpdate(BaseModel):
    """Schema for updating alert history."""
    status: Optional[str] = Field(None, description="Status of the alert")
    acknowledged_by: Optional[int] = Field(None, description="ID of the user who acknowledged the alert")
    resolved_by: Optional[int] = Field(None, description="ID of the user who resolved the alert")
    acknowledged_at: Optional[datetime] = Field(None, description="Time when the alert was acknowledged")
    resolved_at: Optional[datetime] = Field(None, description="Time when the alert was resolved")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class AlertHistoryInDB(AlertHistoryBase):
    """Schema for alert history in the database."""
    id: int = Field(..., description="ID of the alert history")
    created_at: datetime = Field(..., description="Time when the alert was created")
    updated_at: Optional[datetime] = Field(None, description="Time when the alert was last updated")

    model_config = ConfigDict(from_attributes=True)


class AlertHistoryResponse(AlertHistoryInDB):
    """Schema for alert history responses."""
    pass


class AlertHistoryList(BaseModel):
    """Schema for a list of alert history."""
    items: List[AlertHistoryResponse] = Field(..., description="List of alert history")
    total: int = Field(..., description="Total number of alert history")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
