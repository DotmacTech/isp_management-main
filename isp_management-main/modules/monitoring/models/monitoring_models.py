"""
Shared Pydantic models for the monitoring module.

This module contains Pydantic models used by the monitoring and logging services.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class LogLevel(str, Enum):
    """Enum for log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class HealthStatusEnum(str, Enum):
    """Enum for health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"

class MetricTypeEnum(str, Enum):
    """Enum for metric types."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"

class LogLevelEnum(str, Enum):
    """Enum for log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogSortOrderEnum(str, Enum):
    """Enum for log sort order."""
    ASC = "asc"
    DESC = "desc"

class AlertSortOrderEnum(str, Enum):
    """Enum for alert sort order."""
    ASC = "asc"
    DESC = "desc"

class ServiceLogBase(BaseModel):
    """Base schema for service logs."""
    endpoint_id: str = Field(..., description="ID of the service endpoint")
    status: str = Field(..., description="Status of the service")
    response_time: Optional[float] = Field(None, description="Response time in milliseconds")
    status_code: Optional[str] = Field(None, description="Status code returned by the service")
    error_message: Optional[str] = Field(None, description="Error message if any")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    model_config = {"from_attributes": True}

class ServiceLogCreate(ServiceLogBase):
    """Schema for creating service logs."""
    pass

class ServiceLogUpdate(BaseModel):
    """Schema for updating service logs."""
    status: Optional[str] = Field(None, description="Status of the service")
    response_time: Optional[float] = Field(None, description="Response time in milliseconds")
    status_code: Optional[str] = Field(None, description="Status code returned by the service")
    error_message: Optional[str] = Field(None, description="Error message if any")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    elasticsearch_synced: Optional[bool] = Field(None, description="Whether the log has been synced to Elasticsearch")
    model_config = {"from_attributes": True}

class ServiceLogInDB(ServiceLogBase):
    """Schema for service logs in the database."""
    id: str = Field(..., description="ID of the service log")
    created_at: datetime = Field(..., description="Time when the log was created")
    elasticsearch_synced: bool = Field(..., description="Whether the log has been synced to Elasticsearch")
    model_config = {"from_attributes": True}

class ServiceLogResponse(ServiceLogInDB):
    """Schema for service log responses."""
    pass

class LogSearchParams(BaseModel):
    """Parameters for log search."""
    service_names: Optional[List[str]] = Field(None, description="Filter by service names")
    log_levels: Optional[List[LogLevel]] = Field(None, description="Filter by log levels")
    start_time: Optional[datetime] = Field(None, description="Filter by start time")
    end_time: Optional[datetime] = Field(None, description="Filter by end time")
    trace_id: Optional[str] = Field(None, description="Filter by trace ID")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    message_contains: Optional[str] = Field(None, description="Filter by message content")
    request_path: Optional[str] = Field(None, description="Filter by request path")
    use_elasticsearch: bool = Field(True, description="Whether to use Elasticsearch for search")
    offset: int = Field(0, description="Pagination offset")
    limit: int = Field(50, description="Pagination limit")
    model_config = {"from_attributes": True}

class LogSearchResult(BaseModel):
    """Result of a log search."""
    logs: List[ServiceLogResponse] = Field(..., description="List of logs")
    total: int = Field(..., description="Total number of logs matching the search criteria")
    model_config = {"from_attributes": True}

class HealthCheckComponentStatus(BaseModel):
    """Status of a system component in a health check."""
    name: str = Field(..., description="Name of the component")
    status: HealthStatusEnum = Field(..., description="Health status of the component")
    details: Optional[str] = Field(None, description="Additional details about the component status")
    model_config = {"from_attributes": True}

class HealthCheckResponse(BaseModel):
    """Response from a system health check."""
    status: HealthStatusEnum = Field(..., description="Overall health status of the system")
    timestamp: datetime = Field(..., description="Time when the health check was performed")
    components: List[HealthCheckComponentStatus] = Field(..., description="Status of individual components")
    model_config = {"from_attributes": True}

class ServiceHealthReport(BaseModel):
    """Health report for a service."""
    service_name: str = Field(..., description="Name of the service")
    status: HealthStatusEnum = Field(..., description="Current health status")
    uptime_percentage: float = Field(..., description="Uptime percentage over the reporting period")
    average_response_time: float = Field(..., description="Average response time in milliseconds")
    error_count: int = Field(..., description="Number of errors during the reporting period")
    outage_count: int = Field(0, description="Number of outages during the reporting period")
    total_outage_duration: int = Field(0, description="Total outage duration in seconds")
    start_time: datetime = Field(..., description="Start time of the reporting period")
    end_time: datetime = Field(..., description="End time of the reporting period")
    model_config = {"from_attributes": True}

class SystemHealthCheck(BaseModel):
    """System health check model."""
    id: str = Field(..., description="ID of the health check")
    component_name: str = Field(..., description="Name of the component")
    check_type: str = Field(..., description="Type of health check")
    status: HealthStatusEnum = Field(..., description="Health status of the component")
    details: Optional[str] = Field(None, description="Additional details about the health check")
    timestamp: datetime = Field(..., description="Time when the health check was performed")
    model_config = {"from_attributes": True}
