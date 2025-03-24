"""
Pydantic schemas for system health checks.

This module defines Pydantic schemas for system health checks and health status,
which are used for API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class HealthStatusEnum(str, Enum):
    """Enum for health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckTypeEnum(str, Enum):
    """Enum for health check types."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    CUSTOM = "custom"


# System Health Check Schemas
class SystemHealthCheckBase(BaseModel):
    """Base schema for system health checks."""
    name: str = Field(..., description="Name of the health check")
    description: Optional[str] = Field(None, description="Description of the health check")
    check_type: CheckTypeEnum = Field(..., description="Type of the health check")
    target: str = Field(..., description="Target of the health check")
    interval: int = Field(60, description="Check interval in seconds")
    timeout: int = Field(10, description="Check timeout in seconds")
    healthy_threshold: int = Field(2, description="Number of consecutive successful checks required to be considered healthy")
    unhealthy_threshold: int = Field(2, description="Number of consecutive failed checks required to be considered unhealthy")
    enabled: bool = Field(True, description="Whether the health check is enabled")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the health check")


class SystemHealthCheck(SystemHealthCheckBase):
    """Schema for system health checks."""
    id: str = Field(..., description="ID of the health check")
    created_at: datetime = Field(..., description="Time when the health check was created")
    updated_at: datetime = Field(..., description="Time when the health check was last updated")
    status: HealthStatusEnum = Field(HealthStatusEnum.UNKNOWN, description="Current status of the health check")
    last_checked_at: Optional[datetime] = Field(None, description="Time when the health check was last performed")
    
    model_config = ConfigDict(from_attributes=True)


class SystemHealthCheckInDB(SystemHealthCheckBase):
    """Schema for system health checks in the database."""
    id: str = Field(..., description="ID of the health check")
    created_at: datetime = Field(..., description="Time when the health check was created")
    updated_at: datetime = Field(..., description="Time when the health check was last updated")
    status: HealthStatusEnum = Field(HealthStatusEnum.UNKNOWN, description="Current status of the health check")
    last_checked_at: Optional[datetime] = Field(None, description="Time when the health check was last performed")
    
    model_config = ConfigDict(from_attributes=True)


class SystemHealthCheckCreate(SystemHealthCheckBase):
    """Schema for creating system health checks."""
    pass


class SystemHealthCheckUpdate(BaseModel):
    """Schema for updating system health checks."""
    name: Optional[str] = Field(None, description="Name of the health check")
    description: Optional[str] = Field(None, description="Description of the health check")
    check_type: Optional[CheckTypeEnum] = Field(None, description="Type of the health check")
    target: Optional[str] = Field(None, description="Target of the health check")
    interval: Optional[int] = Field(None, description="Check interval in seconds")
    timeout: Optional[int] = Field(None, description="Check timeout in seconds")
    healthy_threshold: Optional[int] = Field(None, description="Number of consecutive successful checks required to be considered healthy")
    unhealthy_threshold: Optional[int] = Field(None, description="Number of consecutive failed checks required to be considered unhealthy")
    enabled: Optional[bool] = Field(None, description="Whether the health check is enabled")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the health check")


class SystemHealthCheckResponse(SystemHealthCheck):
    """Schema for system health check responses."""
    pass


class SystemHealthCheckList(BaseModel):
    """Schema for a list of system health checks."""
    items: List[SystemHealthCheckResponse] = Field(..., description="List of system health checks")
    total: int = Field(..., description="Total number of system health checks")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class SystemHealthCheckFilter(BaseModel):
    """Schema for filtering system health checks."""
    check_type: Optional[CheckTypeEnum] = Field(None, description="Filter by check type")
    status: Optional[HealthStatusEnum] = Field(None, description="Filter by status")
    enabled: Optional[bool] = Field(None, description="Filter by enabled status")


# System Health Status Schemas
class SystemHealthStatusBase(BaseModel):
    """Base schema for system health status."""
    component: str = Field(..., description="Name of the system component")
    status: HealthStatusEnum = Field(..., description="Status of the component")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details about the component status")
    message: Optional[str] = Field(None, description="Message about the component status")


class SystemHealthStatus(SystemHealthStatusBase):
    """Schema for system health status."""
    id: str = Field(..., description="ID of the health status")
    created_at: datetime = Field(..., description="Time when the health status was created")
    updated_at: datetime = Field(..., description="Time when the health status was last updated")
    
    model_config = ConfigDict(from_attributes=True)


class SystemHealthStatusInDB(SystemHealthStatusBase):
    """Schema for system health status in the database."""
    id: str = Field(..., description="ID of the health status")
    created_at: datetime = Field(..., description="Time when the health status was created")
    updated_at: datetime = Field(..., description="Time when the health status was last updated")
    
    model_config = ConfigDict(from_attributes=True)


class SystemHealthStatusCreate(SystemHealthStatusBase):
    """Schema for creating system health status."""
    pass


class SystemHealthStatusUpdate(BaseModel):
    """Schema for updating system health status."""
    status: Optional[HealthStatusEnum] = Field(None, description="Status of the component")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details about the component status")
    message: Optional[str] = Field(None, description="Message about the component status")


class SystemHealthStatusResponse(SystemHealthStatus):
    """Schema for system health status responses."""
    pass


class SystemHealthStatusList(BaseModel):
    """Schema for a list of system health statuses."""
    items: List[SystemHealthStatusResponse] = Field(..., description="List of system health statuses")
    total: int = Field(..., description="Total number of system health statuses")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class SystemHealthSummary(BaseModel):
    """Schema for system health summary."""
    overall_status: HealthStatusEnum = Field(..., description="Overall status of the system")
    components: List[SystemHealthStatusResponse] = Field(..., description="List of component statuses")
    timestamp: datetime = Field(..., description="Time when the summary was generated")
    message: Optional[str] = Field(None, description="Message about the system health")


class HealthCheckComponentStatus(BaseModel):
    """Schema for health check component status."""
    name: str = Field(..., description="Name of the component")
    status: HealthStatusEnum = Field(..., description="Status of the component")
    message: Optional[str] = Field(None, description="Message about the component status")
    last_checked: datetime = Field(..., description="Time when the component was last checked")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details about the component status")


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""
    overall_status: HealthStatusEnum = Field(..., description="Overall status of the system")
    components: List[HealthCheckComponentStatus] = Field(..., description="List of component statuses")
    timestamp: datetime = Field(..., description="Time when the health check was performed")
    message: Optional[str] = Field(None, description="Message about the system health")
    services_healthy: int = Field(..., description="Number of healthy services")
    services_degraded: int = Field(..., description="Number of degraded services")
    services_unhealthy: int = Field(..., description="Number of unhealthy services")
    services_unknown: int = Field(..., description="Number of services with unknown status")


class ServiceHealthReport(BaseModel):
    """Schema for service health reports."""
    service_name: str = Field(..., description="Name of the service")
    status: HealthStatusEnum = Field(..., description="Status of the service")
    timestamp: datetime = Field(..., description="Time when the report was generated")
    version: Optional[str] = Field(None, description="Version of the service")
    message: Optional[str] = Field(None, description="Message about the service health")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details about the service health")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Service metrics")
    host: Optional[str] = Field(None, description="Host where the service is running")
    environment: Optional[str] = Field(None, description="Environment where the service is running")


# Alias classes for backward compatibility
HealthCheckCreate = SystemHealthCheckCreate
HealthCheckResponse = SystemHealthCheckResponse
HealthCheckResultCreate = SystemHealthStatusCreate
HealthCheckResultResponse = SystemHealthStatusResponse
HealthCheckResult = SystemHealthStatus
HealthCheckSummary = SystemHealthSummary
