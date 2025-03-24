"""
Pydantic schemas for metric records.

This module defines Pydantic schemas for metric records, which are used for
recording metrics in the monitoring system.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict


class MetricType(str, Enum):
    """Enum for metric types."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    BANDWIDTH = "bandwidth"
    LATENCY = "latency"
    PACKET_LOSS = "packet_loss"
    RADIUS_AUTH = "radius_auth"
    RADIUS_ACCT = "radius_acct"
    API_RESPONSE_TIME = "api_response_time"
    DATABASE_CONNECTIONS = "database_connections"
    ACTIVE_USERS = "active_users"
    CONCURRENT_SESSIONS = "concurrent_sessions"
    QUEUE_LENGTH = "queue_length"
    CUSTOM = "custom"


class MetricUnit(str, Enum):
    """Enum for metric units."""
    PERCENT = "percent"
    BYTES = "bytes"
    KILOBYTES = "kilobytes"
    MEGABYTES = "megabytes"
    GIGABYTES = "gigabytes"
    TERABYTES = "terabytes"
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    MICROSECONDS = "microseconds"
    COUNT = "count"
    BPS = "bps"
    KBPS = "kbps"
    MBPS = "mbps"
    GBPS = "gbps"
    PACKETS = "packets"
    ERRORS = "errors"
    CUSTOM = "custom"


class MetricRecord(BaseModel):
    """Schema for a metric record."""
    id: Optional[UUID] = Field(default_factory=uuid4, description="Unique identifier for the metric record")
    metric_type: MetricType = Field(..., description="Type of the metric")
    host: str = Field(..., description="Host or source of the metric")
    service: Optional[str] = Field(None, description="Service associated with the metric")
    value: float = Field(..., description="Value of the metric")
    unit: MetricUnit = Field(MetricUnit.COUNT, description="Unit of the metric")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the metric was recorded")
    tags: Optional[Dict[str, str]] = Field(None, description="Tags associated with the metric")
    dimensions: Optional[Dict[str, Any]] = Field(None, description="Additional dimensions for the metric")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    model_config = ConfigDict(from_attributes=True)


class MetricRecordCreate(BaseModel):
    """Schema for creating a metric record."""
    metric_type: MetricType = Field(..., description="Type of the metric")
    host: str = Field(..., description="Host or source of the metric")
    service: Optional[str] = Field(None, description="Service associated with the metric")
    value: float = Field(..., description="Value of the metric")
    unit: MetricUnit = Field(MetricUnit.COUNT, description="Unit of the metric")
    timestamp: Optional[datetime] = Field(None, description="Timestamp when the metric was recorded")
    tags: Optional[Dict[str, str]] = Field(None, description="Tags associated with the metric")
    dimensions: Optional[Dict[str, Any]] = Field(None, description="Additional dimensions for the metric")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("timestamp", mode="before")
    @classmethod
    def set_timestamp(cls, v):
        return v or datetime.utcnow()


class MetricRecordUpdate(BaseModel):
    """Schema for updating a metric record."""
    value: Optional[float] = Field(None, description="Value of the metric")
    unit: Optional[MetricUnit] = Field(None, description="Unit of the metric")
    tags: Optional[Dict[str, str]] = Field(None, description="Tags associated with the metric")
    dimensions: Optional[Dict[str, Any]] = Field(None, description="Additional dimensions for the metric")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MetricRecordResponse(MetricRecord):
    """Schema for a metric record response."""
    pass


class MetricRecordBatch(BaseModel):
    """Schema for a batch of metric records."""
    metrics: List[MetricRecordCreate] = Field(..., description="List of metric records")
    source: Optional[str] = Field(None, description="Source of the metric batch")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the batch was created")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MetricRecordBatchResponse(BaseModel):
    """Schema for a batch of metric records response."""
    processed: int = Field(..., description="Number of metrics processed")
    failed: int = Field(..., description="Number of metrics that failed to process")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Errors encountered during processing")
    timestamp: datetime = Field(..., description="Timestamp when the batch was processed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
