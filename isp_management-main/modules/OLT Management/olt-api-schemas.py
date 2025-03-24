"""
OLT Management API Schemas

This module defines Pydantic models for API request and response data validation.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator


class OLTInfo(BaseModel):
    """OLT information model."""
    
    id: str = Field(..., description="OLT identifier")
    name: str = Field(..., description="OLT name")
    model: str = Field(..., description="OLT model")
    ip_address: str = Field(..., description="OLT IP address")
    status: str = Field(..., description="OLT status")
    version: Optional[str] = Field(None, description="OLT software version")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "1",
                "name": "OLT-HQ-01",
                "model": "MA5800",
                "ip_address": "192.168.1.10",
                "status": "online",
                "version": "V800R020C10"
            }
        }


class ONTInfo(BaseModel):
    """ONT information model."""
    
    id: str = Field(..., description="ONT identifier")
    serial_number: str = Field(..., description="ONT serial number")
    status: Optional[str] = Field(None, description="ONT status")
    description: Optional[str] = Field(None, description="ONT description")
    
    # Additional fields based on OLT type
    frame: Optional[str] = Field(None, description="Frame ID (Huawei)")
    slot: Optional[str] = Field(None, description="Slot ID (Huawei)")
    gpon_index: Optional[str] = Field(None, description="GPON index (ZTE)")
    
    # Additional details when available
    version: Optional[Dict[str, Any]] = Field(None, description="Version information")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "10",
                "serial_number": "HWTC12345678",
                "status": "online",
                "description": "Customer ONT - 123 Main St",
                "frame": "0",
                "slot": "0"
            }
        }


class ONTProvisionRequest(BaseModel):
    """ONT provisioning request model."""
    
    serial_number: str = Field(..., description="ONT serial number")
    name: Optional[str] = Field(None, description="ONT name")
    description: Optional[str] = Field(None, description="ONT description")
    
    class Config:
        schema_extra = {
            "example": {
                "serial_number": "HWTC87654321",
                "name": "Customer ONT",
                "description": "Customer ONT - 456 Oak Ave"
            }
        }


class ONTStatusInfo(BaseModel):
    """ONT status information model."""
    
    state: Optional[str] = Field(None, description="Operational state")
    uptime: Optional[str] = Field(None, description="Uptime duration")
    distance: Optional[str] = Field(None, description="Distance from OLT")
    rx_power: Optional[str] = Field(None, description="Receive optical power")
    tx_power: Optional[str] = Field(None, description="Transmit optical power")
    temperature: Optional[str] = Field(None, description="ONT temperature")
    voltage: Optional[str] = Field(None, description="ONT voltage")
    
    # Additional fields can be added dynamically
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional status fields")
    
    class Config:
        schema_extra = {
            "example": {
                "state": "online",
                "uptime": "10 days, 4 hours, 12 minutes",
                "distance": "1.2 km",
                "rx_power": "-18.5 dBm",
                "tx_power": "2.1 dBm",
                "temperature": "42.3 C",
                "voltage": "3.3 V"
            }
        }
        
        arbitrary_types_allowed = True


class VLANConfig(BaseModel):
    """VLAN configuration model."""
    
    interface_id: str = Field(..., description="Interface identifier")
    vlan_mode: str = Field(..., description="VLAN mode (access or trunk)")
    vlan_id: Optional[int] = Field(None, description="VLAN ID for access mode")
    
    @validator('vlan_mode')
    def validate_vlan_mode(cls, v):
        if v.lower() not in ['access', 'trunk']:
            raise ValueError("VLAN mode must be 'access' or 'trunk'")
        return v.lower()
    
    @validator('vlan_id')
    def validate_vlan_id(cls, v, values):
        if values.get('vlan_mode') == 'access' and v is None:
            raise ValueError("VLAN ID is required for access mode")
        if v is not None and (v < 1 or v > 4094):
            raise ValueError("VLAN ID must be between 1 and 4094")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "interface_id": "eth_0/1",
                "vlan_mode": "access",
                "vlan_id": 100
            }
        }


class IPConfig(BaseModel):
    """IP configuration model."""
    
    dhcp_enabled: Optional[bool] = Field(None, description="Whether DHCP is enabled")
    pppoe_enabled: Optional[bool] = Field(None, description="Whether PPPoE is enabled")
    ip_address: Optional[str] = Field(None, description="Static IP address")
    subnet_mask: Optional[str] = Field(None, description="Subnet mask")
    gateway: Optional[str] = Field(None, description="Default gateway")
    
    @validator('subnet_mask', 'gateway')
    def validate_ip_fields(cls, v, values):
        if values.get('ip_address') and v is None:
            raise ValueError("Subnet mask and gateway are required for static IP configuration")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "dhcp_enabled": False,
                "pppoe_enabled": False,
                "ip_address": "192.168.1.100",
                "subnet_mask": "255.255.255.0",
                "gateway": "192.168.1.1"
            }
        }


class TR069Config(BaseModel):
    """TR-069 configuration model."""
    
    acs_url: str = Field(..., description="ACS server URL")
    periodic_inform_interval: int = Field(..., description="Periodic inform interval in seconds")
    connection_request_username: str = Field(..., description="Connection request username")
    connection_request_password: str = Field(..., description="Connection request password")
    
    @validator('periodic_inform_interval')
    def validate_interval(cls, v):
        if v < 0:
            raise ValueError("Interval must be a positive value")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "acs_url": "http://acs.example.com:7547",
                "periodic_inform_interval": 86400,
                "connection_request_username": "acs_user",
                "connection_request_password": "acs_password"
            }
        }


class SpeedLimitConfig(BaseModel):
    """Speed limit configuration model."""
    
    download_limit: Optional[int] = Field(None, description="Download speed limit in Kbps")
    upload_limit: Optional[int] = Field(None, description="Upload speed limit in Kbps")
    
    @validator('download_limit', 'upload_limit')
    def validate_limits(cls, v):
        if v is not None and v < 0:
            raise ValueError("Speed limit must be a positive value")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "download_limit": 10240,  # 10 Mbps
                "upload_limit": 5120      # 5 Mbps
            }
        }