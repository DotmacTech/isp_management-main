"""
Pydantic schemas for log retention policies.

This module defines Pydantic schemas for log retention policies, which are used for
API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class RetentionPeriod(str, Enum):
    """Enum for retention periods."""
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    CUSTOM = "custom"


class RetentionPeriodTypeEnum(str, Enum):
    """Enum for retention period types."""
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    COUNT_BASED = "count_based"
    CUSTOM = "custom"


class LogRetentionPolicyBase(BaseModel):
    """Base schema for log retention policies."""
    name: str = Field(..., description="Name of the log retention policy")
    description: Optional[str] = Field(None, description="Description of the log retention policy")
    service_name: Optional[str] = Field(None, description="Name of the service to apply the policy to")
    log_level: Optional[str] = Field(None, description="Log level to apply the policy to")
    retention_period: RetentionPeriod = Field(..., description="Retention period")
    retention_type: RetentionPeriodTypeEnum = Field(RetentionPeriodTypeEnum.TIME_BASED, description="Type of retention period")
    custom_period_days: Optional[int] = Field(None, description="Custom retention period in days")
    archive_enabled: bool = Field(False, description="Whether to archive logs before deletion")
    archive_storage_path: Optional[str] = Field(None, description="Path to archive storage")
    enabled: bool = Field(True, description="Whether the policy is enabled")


class LogRetentionPolicyCreate(LogRetentionPolicyBase):
    """Schema for creating log retention policies."""
    pass


class LogRetentionPolicyUpdate(BaseModel):
    """Schema for updating log retention policies."""
    name: Optional[str] = Field(None, description="Name of the log retention policy")
    description: Optional[str] = Field(None, description="Description of the log retention policy")
    service_name: Optional[str] = Field(None, description="Name of the service to apply the policy to")
    log_level: Optional[str] = Field(None, description="Log level to apply the policy to")
    retention_period: Optional[RetentionPeriod] = Field(None, description="Retention period")
    retention_type: Optional[RetentionPeriodTypeEnum] = Field(None, description="Type of retention period")
    custom_period_days: Optional[int] = Field(None, description="Custom retention period in days")
    archive_enabled: Optional[bool] = Field(None, description="Whether to archive logs before deletion")
    archive_storage_path: Optional[str] = Field(None, description="Path to archive storage")
    enabled: Optional[bool] = Field(None, description="Whether the policy is enabled")


class LogRetentionPolicyInDB(LogRetentionPolicyBase):
    """Schema for log retention policies in the database."""
    id: int = Field(..., description="ID of the log retention policy")
    created_at: datetime = Field(..., description="Time when the log retention policy was created")
    updated_at: Optional[datetime] = Field(None, description="Time when the log retention policy was last updated")
    last_applied_at: Optional[datetime] = Field(None, description="Time when the log retention policy was last applied")

    model_config = ConfigDict(from_attributes=True)


class LogRetentionPolicyResponse(LogRetentionPolicyInDB):
    """Schema for log retention policy responses."""
    pass


class LogRetentionPolicyList(BaseModel):
    """Schema for a list of log retention policies."""
    items: List[LogRetentionPolicyResponse] = Field(..., description="List of log retention policies")
    total: int = Field(..., description="Total number of log retention policies")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
