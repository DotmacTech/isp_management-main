"""
Pydantic schemas for service availability monitoring.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, ConfigDict

from modules.monitoring.models.service_availability import ProtocolType, StatusType, SeverityLevel, NotificationType


class ServiceEndpointBase(BaseModel):
    """Base schema for service endpoint."""
    name: str
    description: Optional[str] = None
    url: str
    protocol: ProtocolType
    port: Optional[int] = None
    check_interval: int = 60
    timeout: int = 5
    retries: int = 3
    expected_status_code: Optional[int] = None
    expected_response_pattern: Optional[str] = None
    is_active: bool = True


class ServiceEndpointCreate(ServiceEndpointBase):
    """Schema for creating a service endpoint."""
    id: str


class ServiceEndpointUpdate(ServiceEndpointBase):
    """Schema for updating a service endpoint."""
    name: Optional[str] = None
    url: Optional[str] = None
    protocol: Optional[ProtocolType] = None


class ServiceEndpointInDB(ServiceEndpointBase):
    """Schema for service endpoint in database."""
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceStatusBase(BaseModel):
    """Base schema for service status."""
    status: StatusType
    response_time: Optional[float] = None
    status_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceStatusCreate(ServiceStatusBase):
    """Schema for creating a service status."""
    endpoint_id: str


class ServiceStatusInDB(ServiceStatusBase):
    """Schema for service status in database."""
    id: str
    endpoint_id: str
    elasticsearch_synced: bool = False

    model_config = ConfigDict(from_attributes=True)


class ServiceOutageBase(BaseModel):
    """Base schema for service outage."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    severity: SeverityLevel
    affected_customers: Optional[int] = None
    resolution_notes: Optional[str] = None


class ServiceOutageCreate(ServiceOutageBase):
    """Schema for creating a service outage."""
    endpoint_id: str


class ServiceOutageUpdate(BaseModel):
    """Schema for updating a service outage."""
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    severity: Optional[SeverityLevel] = None
    affected_customers: Optional[int] = None
    resolution_notes: Optional[str] = None


class ServiceOutageInDB(ServiceOutageBase):
    """Schema for service outage in database."""
    id: str
    endpoint_id: str
    elasticsearch_synced: bool = False

    model_config = ConfigDict(from_attributes=True)


class ServiceAlertBase(BaseModel):
    """Base schema for service alert."""
    notification_type: NotificationType
    recipients: Optional[str] = None
    message: str
    delivered: bool = False
    delivery_time: Optional[datetime] = None
    alert_time: datetime = Field(default_factory=datetime.utcnow)


class ServiceAlertCreate(ServiceAlertBase):
    """Schema for creating a service alert."""
    outage_id: str


class ServiceAlertInDB(ServiceAlertBase):
    """Schema for service alert in database."""
    id: str
    outage_id: str

    model_config = ConfigDict(from_attributes=True)


class MaintenanceWindowBase(BaseModel):
    """Base schema for maintenance window."""
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    affected_services: Optional[str] = None


class MaintenanceWindowCreate(MaintenanceWindowBase):
    """Schema for creating a maintenance window."""
    created_by: str


class MaintenanceWindowUpdate(BaseModel):
    """Schema for updating a maintenance window."""
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    affected_services: Optional[str] = None


class MaintenanceWindowInDB(MaintenanceWindowBase):
    """Schema for maintenance window in database."""
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Response schemas
class ServiceEndpointResponse(ServiceEndpointInDB):
    """Response schema for service endpoint."""
    current_status: Optional[Dict[str, Any]] = None


class ServiceStatusResponse(ServiceStatusInDB):
    """Response schema for service status."""
    endpoint: ServiceEndpointInDB


class ServiceOutageResponse(ServiceOutageInDB):
    """Response schema for service outage."""
    endpoint: ServiceEndpointInDB
    alerts: List[ServiceAlertInDB] = []


class ServiceAlertResponse(ServiceAlertInDB):
    """Response schema for service alert."""
    outage: ServiceOutageInDB


class MaintenanceWindowResponse(MaintenanceWindowInDB):
    """Response schema for maintenance window."""
    is_active: bool


# List response schemas
class ServiceEndpointListResponse(BaseModel):
    """Response schema for list of service endpoints."""
    items: List[ServiceEndpointResponse]
    total: int


class ServiceStatusListResponse(BaseModel):
    """Response schema for list of service statuses."""
    items: List[ServiceStatusResponse]
    total: int


class ServiceOutageListResponse(BaseModel):
    """Response schema for list of service outages."""
    items: List[ServiceOutageResponse]
    total: int


class ServiceAlertListResponse(BaseModel):
    """Response schema for list of service alerts."""
    items: List[ServiceAlertResponse]
    total: int


class MaintenanceWindowListResponse(BaseModel):
    """Response schema for list of maintenance windows."""
    items: List[MaintenanceWindowResponse]
    total: int
