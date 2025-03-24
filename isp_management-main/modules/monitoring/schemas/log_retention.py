"""
Pydantic schemas for log retention.

This module defines Pydantic schemas for log retention policies and log archives,
which are used for API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class RetentionPeriodTypeEnum(str, Enum):
    """Enum for retention period types."""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


# Log Retention Policy Schemas
class LogRetentionPolicyBase(BaseModel):
    """Base schema for log retention policies."""
    name: str = Field(..., description="Name of the log retention policy")
    description: Optional[str] = Field(None, description="Description of the log retention policy")
    log_type: str = Field(..., description="Type of logs this policy applies to")
    retention_period: int = Field(..., description="Retention period value")
    period_type: RetentionPeriodTypeEnum = Field(..., description="Type of retention period")
    compress_after: Optional[int] = Field(None, description="Days after which to compress logs")
    archive_after: Optional[int] = Field(None, description="Days after which to archive logs")
    delete_after: Optional[int] = Field(None, description="Days after which to delete logs")
    enabled: bool = Field(True, description="Whether the policy is enabled")


class LogRetentionPolicyCreate(LogRetentionPolicyBase):
    """Schema for creating log retention policies."""
    pass


class LogRetentionPolicyUpdate(BaseModel):
    """Schema for updating log retention policies."""
    name: Optional[str] = Field(None, description="Name of the log retention policy")
    description: Optional[str] = Field(None, description="Description of the log retention policy")
    retention_period: Optional[int] = Field(None, description="Retention period value")
    period_type: Optional[RetentionPeriodTypeEnum] = Field(None, description="Type of retention period")
    compress_after: Optional[int] = Field(None, description="Days after which to compress logs")
    archive_after: Optional[int] = Field(None, description="Days after which to archive logs")
    delete_after: Optional[int] = Field(None, description="Days after which to delete logs")
    enabled: Optional[bool] = Field(None, description="Whether the policy is enabled")


class LogRetentionPolicyInDB(LogRetentionPolicyBase):
    """Schema for log retention policies in the database."""
    id: str = Field(..., description="ID of the log retention policy")
    created_at: datetime = Field(..., description="Time when the policy was created")
    updated_at: datetime = Field(..., description="Time when the policy was last updated")

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


class LogRetentionPolicyFilter(BaseModel):
    """Schema for filtering log retention policies."""
    log_type: Optional[str] = Field(None, description="Filter by log type")
    enabled: Optional[bool] = Field(None, description="Filter by enabled status")


# Log Archive Schemas
class LogArchiveBase(BaseModel):
    """Base schema for log archives."""
    policy_id: str = Field(..., description="ID of the log retention policy")
    log_type: str = Field(..., description="Type of logs in this archive")
    start_date: datetime = Field(..., description="Start date of logs in this archive")
    end_date: datetime = Field(..., description="End date of logs in this archive")
    file_path: str = Field(..., description="Path to the archive file")
    file_size: int = Field(..., description="Size of the archive file in bytes")
    compressed: bool = Field(True, description="Whether the archive is compressed")
    encrypted: bool = Field(False, description="Whether the archive is encrypted")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class LogArchiveCreate(LogArchiveBase):
    """Schema for creating log archives."""
    pass


class LogArchiveUpdate(BaseModel):
    """Schema for updating log archives."""
    file_path: Optional[str] = Field(None, description="Path to the archive file")
    file_size: Optional[int] = Field(None, description="Size of the archive file in bytes")
    compressed: Optional[bool] = Field(None, description="Whether the archive is compressed")
    encrypted: Optional[bool] = Field(None, description="Whether the archive is encrypted")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class LogArchiveInDB(LogArchiveBase):
    """Schema for log archives in the database."""
    id: str = Field(..., description="ID of the log archive")
    created_at: datetime = Field(..., description="Time when the archive was created")
    updated_at: datetime = Field(..., description="Time when the archive was last updated")
    policy: LogRetentionPolicyResponse = Field(..., description="Log retention policy")

    model_config = ConfigDict(from_attributes=True)


class LogArchiveResponse(LogArchiveInDB):
    """Schema for log archive responses."""
    pass


class LogArchiveList(BaseModel):
    """Schema for a list of log archives."""
    items: List[LogArchiveResponse] = Field(..., description="List of log archives")
    total: int = Field(..., description="Total number of log archives")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class LogArchiveFilter(BaseModel):
    """Schema for filtering log archives."""
    policy_id: Optional[str] = Field(None, description="Filter by policy ID")
    log_type: Optional[str] = Field(None, description="Filter by log type")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    compressed: Optional[bool] = Field(None, description="Filter by compression status")
    encrypted: Optional[bool] = Field(None, description="Filter by encryption status")
