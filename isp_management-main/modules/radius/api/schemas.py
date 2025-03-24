"""
RADIUS API Schemas

This module defines Pydantic models for RADIUS API data validation,
serialization and documentation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class RadiusAuthRequestSchema(BaseModel):
    """Schema for RADIUS authentication requests."""
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")
    calling_station_id: Optional[str] = Field(None, description="Calling station identifier")
    called_station_id: Optional[str] = Field(None, description="Called station identifier")
    nas_ip_address: str = Field(..., description="NAS IP address")
    nas_identifier: Optional[str] = Field(None, description="NAS identifier")

    model_config = ConfigDict(from_attributes=True)


class RadiusAuthResponseSchema(BaseModel):
    """Schema for RADIUS authentication responses."""
    status: str = Field(..., description="Authentication status")
    message: str = Field(..., description="Status message")
    attributes: Optional[Dict[str, Any]] = Field(None, description="RADIUS attributes")

    model_config = ConfigDict(from_attributes=True)


class RadiusAuthResponseSchema(BaseModel):
    """Schema for RADIUS authentication responses."""
    success: bool = Field(..., description="Whether authentication was successful")
    user_id: Optional[int] = Field(None, description="User ID if authenticated")
    message: str = Field(..., description="Authentication message")
    attributes: Optional[Dict[str, Any]] = Field(None, description="RADIUS attributes")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusAuthResponse = RadiusAuthResponseSchema


class RadiusAccountingRequestSchema(BaseModel):
    """Schema for RADIUS accounting requests."""
    acct_status_type: str = Field(..., description="Accounting status type")
    username: str = Field(..., description="Username")
    nas_ip_address: str = Field(..., description="NAS IP address")
    acct_session_id: str = Field(..., description="Accounting session ID")
    acct_authentic: Optional[str] = Field(None, description="Accounting authentic")
    acct_input_octets: Optional[int] = Field(0, description="Input octets")
    acct_output_octets: Optional[int] = Field(0, description="Output octets")
    acct_session_time: Optional[int] = Field(0, description="Session time in seconds")
    acct_terminate_cause: Optional[str] = Field(None, description="Termination cause")
    framed_ip_address: Optional[str] = Field(None, description="Framed IP address")

    model_config = ConfigDict(from_attributes=True)


class RadiusAccountingResponseSchema(BaseModel):
    """Schema for RADIUS accounting responses."""
    status: str = Field(..., description="Accounting status")
    message: str = Field(..., description="Status message")

    model_config = ConfigDict(from_attributes=True)


class NasDeviceBase(BaseModel):
    """Base schema for NAS device data."""
    name: str = Field(..., description="NAS device name")
    ip_address: str = Field(..., description="IP address of the NAS")
    secret: str = Field(..., description="Shared secret for RADIUS communication")
    description: Optional[str] = Field(None, description="Device description")
    type: Optional[str] = Field(None, description="Device type/model")
    location: Optional[str] = Field(None, description="Physical location")
    is_active: bool = Field(True, description="Whether the device is active")
    
    model_config = ConfigDict(from_attributes=True)


class NasDeviceCreate(NasDeviceBase):
    """Schema for creating a new NAS device."""
    pass


class NasDeviceResponse(NasDeviceBase):
    """Schema for NAS device response data."""
    id: int = Field(..., description="Unique identifier for the NAS device")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last communication timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class NasDeviceUpdate(BaseModel):
    """Schema for updating a NAS device."""
    name: Optional[str] = Field(None, description="NAS device name")
    ip_address: Optional[str] = Field(None, description="IP address of the NAS")
    secret: Optional[str] = Field(None, description="Shared secret for RADIUS communication")
    description: Optional[str] = Field(None, description="Device description")
    type: Optional[str] = Field(None, description="Device type/model")
    location: Optional[str] = Field(None, description="Physical location")
    is_active: Optional[bool] = Field(None, description="Whether the device is active")
    
    model_config = ConfigDict(from_attributes=True)


class NasDeviceListResponseSchema(BaseModel):
    """Schema for NAS device list response."""
    total: int = Field(..., description="Total number of NAS devices")
    items: List[NasDeviceResponse] = Field(..., description="List of NAS devices")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
NasDeviceListResponse = NasDeviceListResponseSchema


class NasVendorAttributeBase(BaseModel):
    """Base schema for NAS vendor-specific attributes."""
    nas_id: int = Field(..., description="NAS device ID")
    attribute_name: str = Field(..., description="Attribute name")
    attribute_value: str = Field(..., description="Attribute value")
    vendor_id: Optional[int] = Field(None, description="RADIUS vendor ID")
    description: Optional[str] = Field(None, description="Attribute description")
    
    model_config = ConfigDict(from_attributes=True)


class NasVendorAttributeCreate(NasVendorAttributeBase):
    """Schema for creating a new NAS vendor-specific attribute."""
    pass


class NasVendorAttributeResponse(NasVendorAttributeBase):
    """Schema for NAS vendor-specific attribute response data."""
    id: int = Field(..., description="Unique identifier for the attribute")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class NasVendorAttributeUpdate(BaseModel):
    """Schema for updating a NAS vendor-specific attribute."""
    attribute_name: Optional[str] = Field(None, description="Attribute name")
    attribute_value: Optional[str] = Field(None, description="Attribute value")
    vendor_id: Optional[int] = Field(None, description="RADIUS vendor ID")
    description: Optional[str] = Field(None, description="Attribute description")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusBandwidthPolicyBase(BaseModel):
    """Base schema for RADIUS bandwidth policy."""
    name: str = Field(..., description="Policy name")
    download_rate: int = Field(..., description="Download rate in kbps", gt=0)
    upload_rate: int = Field(..., description="Upload rate in kbps", gt=0)
    burst_factor: Optional[float] = Field(1.0, description="Burst factor multiplier for peak rates")
    priority: Optional[int] = Field(None, description="Traffic priority (1-8, lower is higher)")
    description: Optional[str] = Field(None, description="Policy description")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusBandwidthPolicyCreate(RadiusBandwidthPolicyBase):
    """Schema for creating a new RADIUS bandwidth policy."""
    is_active: bool = Field(True, description="Whether the policy is active")


class RadiusBandwidthPolicyResponse(RadiusBandwidthPolicyBase):
    """Schema for RADIUS bandwidth policy response."""
    id: int = Field(..., description="Unique identifier for the policy")
    is_active: bool = Field(..., description="Whether the policy is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusBandwidthPolicyUpdate(BaseModel):
    """Schema for updating a RADIUS bandwidth policy."""
    name: Optional[str] = Field(None, description="Policy name")
    download_rate: Optional[int] = Field(None, description="Download rate in kbps", gt=0)
    upload_rate: Optional[int] = Field(None, description="Upload rate in kbps", gt=0)
    burst_factor: Optional[float] = Field(None, description="Burst factor multiplier for peak rates")
    priority: Optional[int] = Field(None, description="Traffic priority (1-8, lower is higher)")
    description: Optional[str] = Field(None, description="Policy description")
    is_active: Optional[bool] = Field(None, description="Whether the policy is active")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusProfileAttributeBase(BaseModel):
    """Base schema for RADIUS profile attributes."""
    profile_id: int = Field(..., description="RADIUS profile ID")
    attribute_name: str = Field(..., description="Attribute name")
    attribute_value: str = Field(..., description="Attribute value")
    vendor_id: Optional[int] = Field(None, description="RADIUS vendor ID")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusProfileAttributeCreate(RadiusProfileAttributeBase):
    """Schema for creating a new RADIUS profile attribute."""
    pass


class RadiusProfileAttributeResponse(RadiusProfileAttributeBase):
    """Schema for RADIUS profile attribute response."""
    id: int = Field(..., description="Unique identifier for the attribute")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusProfileAttributeUpdate(BaseModel):
    """Schema for updating a RADIUS profile attribute."""
    attribute_name: Optional[str] = Field(None, description="Attribute name")
    attribute_value: Optional[str] = Field(None, description="Attribute value")
    vendor_id: Optional[int] = Field(None, description="RADIUS vendor ID")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusCoARequest(BaseModel):
    """Schema for RADIUS Change of Authorization (CoA) request."""
    username: str = Field(..., description="Username of the target session")
    nas_ip_address: Optional[str] = Field(None, description="NAS IP address")
    session_id: Optional[str] = Field(None, description="Session ID if targeting a specific session")
    attributes: Dict[str, Any] = Field(..., description="Attributes to send in the CoA request")
    disconnect: bool = Field(False, description="Whether this is a disconnect request")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusCoAResponse(BaseModel):
    """Schema for RADIUS Change of Authorization (CoA) response."""
    success: bool = Field(..., description="Whether the CoA request was successful")
    message: str = Field(..., description="Response message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional response details")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusCoALogResponse(BaseModel):
    """Schema for RADIUS Change of Authorization (CoA) log response."""
    id: int = Field(..., description="Log entry ID")
    username: str = Field(..., description="Username of the target session")
    nas_ip_address: Optional[str] = Field(None, description="NAS IP address")
    session_id: Optional[str] = Field(None, description="Session ID if targeting a specific session")
    attributes: Dict[str, Any] = Field(..., description="Attributes sent in the CoA request")
    disconnect: bool = Field(..., description="Whether this was a disconnect request")
    success: bool = Field(..., description="Whether the CoA request was successful")
    error_message: Optional[str] = Field(None, description="Error message if request failed")
    created_at: datetime = Field(..., description="Timestamp when the CoA was sent")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusProfileCreateSchema(BaseModel):
    """Schema for creating a new RADIUS profile."""
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    speed_limit: int = Field(0, description="Speed limit in kbps (0 = unlimited)")
    data_cap: int = Field(0, description="Data cap in MB (0 = unlimited)")
    service_type: Optional[str] = Field("Framed-User", description="Service type")
    simultaneous_use: Optional[int] = Field(1, description="Maximum simultaneous connections")
    acct_interim_interval: Optional[int] = Field(300, description="Accounting interim interval")
    session_timeout: Optional[int] = Field(0, description="Session timeout")
    idle_timeout: Optional[int] = Field(0, description="Idle timeout")
    bandwidth_policy_id: Optional[int] = Field(None, description="Bandwidth policy ID")

    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusProfileCreate = RadiusProfileCreateSchema


class RadiusProfileResponseSchema(BaseModel):
    """Schema for RADIUS profile response."""
    id: int = Field(..., description="Unique identifier")
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    speed_limit: int = Field(..., description="Speed limit in kbps")
    data_cap: int = Field(..., description="Data cap in MB")
    service_type: str = Field(..., description="Service type")
    simultaneous_use: int = Field(..., description="Maximum simultaneous connections")
    acct_interim_interval: int = Field(..., description="Accounting interim interval")
    session_timeout: int = Field(..., description="Session timeout")
    idle_timeout: int = Field(..., description="Idle timeout")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusProfileResponse = RadiusProfileResponseSchema


class RadiusAuthRequestSchema(BaseModel):
    """Schema for RADIUS authentication requests."""
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")
    nas_identifier: Optional[str] = Field(None, description="NAS identifier")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusAuthRequest = RadiusAuthRequestSchema


class RadiusAccountingStartSchema(BaseModel):
    """Schema for RADIUS accounting start packets."""
    username: str = Field(..., description="Username for the session")
    session_id: str = Field(..., description="Unique session identifier")
    nas_identifier: Optional[str] = Field(None, description="NAS identifier")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    nas_ip: Optional[str] = Field(None, description="NAS IP address")
    session_time: Optional[int] = Field(None, description="Session time in seconds")
    input_octets: Optional[int] = Field(None, description="Bytes received from user")
    output_octets: Optional[int] = Field(None, description="Bytes sent to user")
    called_station_id: Optional[str] = Field(None, description="Called station ID")
    calling_station_id: Optional[str] = Field(None, description="Calling station ID")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusAccountingStart = RadiusAccountingStartSchema


class RadiusAccountingUpdateSchema(BaseModel):
    """Schema for RADIUS accounting update packets."""
    username: str = Field(..., description="Username for the session")
    session_id: str = Field(..., description="Unique session identifier")
    nas_identifier: Optional[str] = Field(None, description="NAS identifier")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    nas_ip: Optional[str] = Field(None, description="NAS IP address")
    session_time: int = Field(..., description="Session time in seconds", ge=0)
    input_octets: int = Field(..., description="Bytes received from user", ge=0)
    output_octets: int = Field(..., description="Bytes sent to user", ge=0)
    called_station_id: Optional[str] = Field(None, description="Called station ID")
    calling_station_id: Optional[str] = Field(None, description="Calling station ID")
    update_timestamp: datetime = Field(default_factory=datetime.now, description="Update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusAccountingUpdate = RadiusAccountingUpdateSchema


class RadiusAccountingStopSchema(BaseModel):
    """Schema for RADIUS accounting stop packets."""
    username: str = Field(..., description="Username for the session")
    session_id: str = Field(..., description="Unique session identifier")
    nas_identifier: Optional[str] = Field(None, description="NAS identifier")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    nas_ip: Optional[str] = Field(None, description="NAS IP address")
    session_time: int = Field(..., description="Total session time in seconds", ge=0)
    input_octets: int = Field(..., description="Total bytes received from user", ge=0)
    output_octets: int = Field(..., description="Total bytes sent to user", ge=0)
    called_station_id: Optional[str] = Field(None, description="Called station ID")
    calling_station_id: Optional[str] = Field(None, description="Calling station ID")
    termination_cause: Optional[str] = Field(None, description="Reason for session termination")
    stop_timestamp: datetime = Field(default_factory=datetime.now, description="Stop timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusAccountingStop = RadiusAccountingStopSchema


class RadiusAccountingResponseSchema(BaseModel):
    """Schema for RADIUS accounting responses."""
    status: str = Field("ok", description="Response status")
    message: Optional[str] = Field(None, description="Response message")
    session_id: Optional[str] = Field(None, description="Session ID")
    username: Optional[str] = Field(None, description="Username")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusAccountingResponse = RadiusAccountingResponseSchema


class RadiusSessionStatisticsSchema(BaseModel):
    """Schema for RADIUS session statistics."""
    username: str = Field(..., description="Username")
    session_count: int = Field(..., description="Total number of sessions")
    total_session_time: int = Field(..., description="Total session time in seconds")
    total_input_octets: int = Field(..., description="Total bytes received from user")
    total_output_octets: int = Field(..., description="Total bytes sent to user")
    average_session_time: float = Field(..., description="Average session time in seconds")
    last_session_time: Optional[datetime] = Field(None, description="Last session timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusSessionStatistics = RadiusSessionStatisticsSchema


class RadiusUserSession(BaseModel):
    """Schema for a single RADIUS user session."""
    session_id: str = Field(..., description="Unique session identifier")
    username: str = Field(..., description="Username")
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    duration: Optional[int] = Field(None, description="Session duration in seconds")
    input_octets: int = Field(0, description="Bytes received from user")
    output_octets: int = Field(0, description="Bytes sent to user")
    ip_address: Optional[str] = Field(None, description="User IP address")
    called_station_id: Optional[str] = Field(None, description="Called station ID")
    calling_station_id: Optional[str] = Field(None, description="Calling station ID")
    nas_identifier: Optional[str] = Field(None, description="NAS identifier")
    nas_ip_address: Optional[str] = Field(None, description="NAS IP address")
    termination_cause: Optional[str] = Field(None, description="Reason for session termination")
    
    model_config = ConfigDict(from_attributes=True)


class RadiusUserSessionsResponseSchema(BaseModel):
    """Schema for RADIUS user sessions response."""
    total: int = Field(..., description="Total number of sessions")
    sessions: List[RadiusUserSession] = Field(..., description="List of sessions")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusUserSessionsResponse = RadiusUserSessionsResponseSchema


class RadiusProfileUpdateSchema(BaseModel):
    """Schema for updating a RADIUS profile."""
    password: Optional[str] = Field(None, description="Password")
    speed_limit: Optional[int] = Field(None, description="Speed limit in kbps")
    data_cap: Optional[int] = Field(None, description="Data cap in MB")
    service_type: Optional[str] = Field(None, description="Service type")
    simultaneous_use: Optional[int] = Field(None, description="Maximum simultaneous connections")
    acct_interim_interval: Optional[int] = Field(None, description="Accounting interim interval")
    session_timeout: Optional[int] = Field(None, description="Session timeout")
    idle_timeout: Optional[int] = Field(None, description="Idle timeout")
    bandwidth_policy_id: Optional[int] = Field(None, description="Bandwidth policy ID")

    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
RadiusProfileUpdate = RadiusProfileUpdateSchema


class BandwidthPolicyCreateSchema(BaseModel):
    """Schema for creating a new bandwidth policy."""
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Description")
    download_rate: int = Field(..., description="Download rate in kbps")
    upload_rate: int = Field(..., description="Upload rate in kbps")
    burst_download_rate: Optional[int] = Field(None, description="Burst download rate")
    burst_upload_rate: Optional[int] = Field(None, description="Burst upload rate")
    burst_threshold: Optional[int] = Field(None, description="Burst threshold")
    burst_time: Optional[int] = Field(None, description="Burst time")
    priority: Optional[int] = Field(8, description="Traffic priority (0-15)")
    is_active: Optional[bool] = Field(True, description="Whether the policy is active")

    model_config = ConfigDict(from_attributes=True)


class BandwidthPolicyResponseSchema(BaseModel):
    """Schema for bandwidth policy response."""
    id: int = Field(..., description="Unique identifier")
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Description")
    download_rate: int = Field(..., description="Download rate in kbps")
    upload_rate: int = Field(..., description="Upload rate in kbps")
    burst_download_rate: Optional[int] = Field(None, description="Burst download rate")
    burst_upload_rate: Optional[int] = Field(None, description="Burst upload rate")
    burst_threshold: Optional[int] = Field(None, description="Burst threshold")
    burst_time: Optional[int] = Field(None, description="Burst time")
    priority: int = Field(..., description="Traffic priority")
    is_active: bool = Field(..., description="Whether the policy is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class RadiusSessionStatsSchema(BaseModel):
    """Schema for RADIUS session statistics."""
    total_sessions: int = Field(..., description="Total number of sessions")
    active_sessions: int = Field(..., description="Number of active sessions")
    total_bytes_in: int = Field(..., description="Total bytes in")
    total_bytes_out: int = Field(..., description="Total bytes out")
    average_session_time: float = Field(..., description="Average session time in seconds")

    model_config = ConfigDict(from_attributes=True)


class RadiusCoARequestSchema(BaseModel):
    """Schema for RADIUS Change of Authorization request."""
    profile_id: int = Field(..., description="Profile ID")
    nas_id: int = Field(..., description="NAS device ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    coa_type: str = Field(..., description="CoA type (disconnect, update)")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Attributes to change")

    model_config = ConfigDict(from_attributes=True)


class RadiusCoAResponseSchema(BaseModel):
    """Schema for RADIUS Change of Authorization response."""
    status: str = Field(..., description="Status")
    message: str = Field(..., description="Message")
    session_id: Optional[str] = Field(None, description="Session ID")

    model_config = ConfigDict(from_attributes=True)
