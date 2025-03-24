from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict

class RadiusProfileBase(BaseModel):
    user_id: int
    username: str
    speed_limit: int = 0  # 0 means unlimited
    data_cap: int = 0     # 0 means unlimited
    service_type: Optional[str] = "Framed-User"
    simultaneous_use: Optional[int] = 1
    acct_interim_interval: Optional[int] = 300
    session_timeout: Optional[int] = 0
    idle_timeout: Optional[int] = 0
    bandwidth_policy_id: Optional[int] = None

class RadiusProfileCreate(RadiusProfileBase):
    password: str

class RadiusProfileUpdate(BaseModel):
    speed_limit: Optional[int] = None
    data_cap: Optional[int] = None
    service_type: Optional[str] = None
    simultaneous_use: Optional[int] = None
    acct_interim_interval: Optional[int] = None
    session_timeout: Optional[int] = None
    idle_timeout: Optional[int] = None
    bandwidth_policy_id: Optional[int] = None
    password: Optional[str] = None

class RadiusProfileResponse(RadiusProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RadiusAuthRequest(BaseModel):
    username: str
    password: str
    nas_ip_address: str
    nas_identifier: Optional[str] = None
    calling_station_id: Optional[str] = None
    called_station_id: Optional[str] = None
    framed_protocol: Optional[str] = None

class RadiusAuthResponse(BaseModel):
    status: str  # "accept", "reject"
    message: str
    attributes: Optional[Dict[str, Any]] = None

class RadiusAccountingBase(BaseModel):
    session_id: str
    profile_id: int
    nas_ip_address: str
    bytes_in: int = 0
    bytes_out: int = 0
    session_time: int = 0
    nas_id: Optional[int] = None
    framed_ip_address: Optional[str] = None
    framed_protocol: Optional[str] = None
    calling_station_id: Optional[str] = None
    called_station_id: Optional[str] = None
    acct_authentic: Optional[str] = None
    acct_input_octets: Optional[int] = 0
    acct_output_octets: Optional[int] = 0
    acct_input_packets: Optional[int] = 0
    acct_output_packets: Optional[int] = 0
    acct_session_id: Optional[str] = None
    acct_multi_session_id: Optional[str] = None
    acct_link_count: Optional[int] = 0

class RadiusAccountingStart(RadiusAccountingBase):
    pass

class RadiusAccountingUpdate(RadiusAccountingBase):
    pass

class RadiusAccountingStop(RadiusAccountingBase):
    terminate_cause: Optional[str] = None

class RadiusAccountingResponse(RadiusAccountingBase):
    id: int
    start_time: datetime
    stop_time: Optional[datetime] = None
    terminate_cause: Optional[str] = None
    acct_interim_updates: Optional[int] = 0
    last_interim_update: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class NasDeviceBase(BaseModel):
    name: str
    ip_address: str
    vendor: str
    model: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = "other"
    description: Optional[str] = None
    ports: Optional[int] = 0
    community: Optional[str] = None
    version: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True

class NasDeviceCreate(NasDeviceBase):
    secret: str

class NasDeviceUpdate(BaseModel):
    name: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    ports: Optional[int] = None
    community: Optional[str] = None
    version: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    secret: Optional[str] = None

class NasDeviceResponse(NasDeviceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class NasVendorAttributeBase(BaseModel):
    nas_id: int
    attribute_name: str
    attribute_value: str
    vendor_type: Optional[int] = None
    vendor_id: Optional[int] = None
    description: Optional[str] = None

class NasVendorAttributeCreate(NasVendorAttributeBase):
    pass

class NasVendorAttributeUpdate(BaseModel):
    attribute_name: Optional[str] = None
    attribute_value: Optional[str] = None
    vendor_type: Optional[int] = None
    vendor_id: Optional[int] = None
    description: Optional[str] = None

class NasVendorAttributeResponse(NasVendorAttributeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RadiusBandwidthPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    download_rate: int
    upload_rate: int
    burst_download_rate: Optional[int] = None
    burst_upload_rate: Optional[int] = None
    burst_threshold: Optional[int] = None
    burst_time: Optional[int] = None
    priority: Optional[int] = 8
    time_based_limits: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True

class RadiusBandwidthPolicyCreate(RadiusBandwidthPolicyBase):
    pass

class RadiusBandwidthPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    download_rate: Optional[int] = None
    upload_rate: Optional[int] = None
    burst_download_rate: Optional[int] = None
    burst_upload_rate: Optional[int] = None
    burst_threshold: Optional[int] = None
    burst_time: Optional[int] = None
    priority: Optional[int] = None
    time_based_limits: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class RadiusBandwidthPolicyResponse(RadiusBandwidthPolicyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RadiusProfileAttributeBase(BaseModel):
    profile_id: int
    attribute_name: str
    attribute_value: str
    vendor_id: Optional[int] = None
    vendor_type: Optional[int] = None

class RadiusProfileAttributeCreate(RadiusProfileAttributeBase):
    pass

class RadiusProfileAttributeUpdate(BaseModel):
    attribute_name: Optional[str] = None
    attribute_value: Optional[str] = None
    vendor_id: Optional[int] = None
    vendor_type: Optional[int] = None

class RadiusProfileAttributeResponse(RadiusProfileAttributeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RadiusCoARequest(BaseModel):
    profile_id: int
    nas_id: int
    session_id: Optional[str] = None
    coa_type: str  # disconnect, update
    attributes: Optional[Dict[str, Any]] = None

class RadiusCoAResponse(BaseModel):
    id: int
    profile_id: int
    nas_id: int
    session_id: Optional[str] = None
    coa_type: str
    attributes_changed: Optional[Dict[str, Any]] = None
    result: str
    error_message: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SessionStatistics(BaseModel):
    total_sessions: int
    active_sessions: int
    total_bytes_in: int
    total_bytes_out: int
    average_session_time: float
    
class UserSessionStatistics(SessionStatistics):
    user_id: int
    username: str

class NasSessionStatistics(SessionStatistics):
    nas_id: int
    nas_name: str

class BandwidthUsageReport(BaseModel):
    user_id: int
    username: str
    total_bytes: int
    download_bytes: int
    upload_bytes: int
    period_start: datetime
    period_end: datetime
    average_download_rate: float  # in kbps
    average_upload_rate: float    # in kbps
    peak_download_rate: float     # in kbps
    peak_upload_rate: float       # in kbps
