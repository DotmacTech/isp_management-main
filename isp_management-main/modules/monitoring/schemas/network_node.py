"""
Network Node Schemas for the ISP Management Platform

This module defines Pydantic schemas for network nodes, used for validation and serialization.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, IPvAnyAddress, Field, field_validator, ConfigDict
from enum import Enum


class NodeTypeEnum(str, Enum):
    """Enum for network node types."""
    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    SERVER = "server"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    OTHER = "other"


class NetworkNodeBase(BaseModel):
    """Base schema for network nodes with common attributes."""
    name: str = Field(..., description="Name of the network node", min_length=1, max_length=100)
    ip_address: str = Field(..., description="IP address of the network node", min_length=7, max_length=45)
    type: NodeTypeEnum = Field(..., description="Type of network node")
    location: Optional[str] = Field(None, description="Physical location of the node", max_length=255)
    description: Optional[str] = Field(None, description="Description of the node", max_length=500)
    
    # Hardware information
    model: Optional[str] = Field(None, description="Hardware model", max_length=100)
    manufacturer: Optional[str] = Field(None, description="Hardware manufacturer", max_length=100)
    serial_number: Optional[str] = Field(None, description="Hardware serial number", max_length=100)
    firmware_version: Optional[str] = Field(None, description="Firmware version", max_length=50)
    
    # Network information
    mac_address: Optional[str] = Field(None, description="MAC address (format: XX:XX:XX:XX:XX:XX)", max_length=17)
    subnet_mask: Optional[str] = Field(None, description="Subnet mask", max_length=45)
    gateway: Optional[str] = Field(None, description="Default gateway", max_length=45)
    dns_servers: Optional[List[str]] = Field(None, description="List of DNS servers")
    
    # Status information
    is_active: Optional[bool] = Field(True, description="Whether the node is active")
    
    # Management information
    snmp_community: Optional[str] = Field(None, description="SNMP community string", max_length=50)
    snmp_version: Optional[str] = Field(None, description="SNMP version", max_length=10)
    ssh_username: Optional[str] = Field(None, description="SSH username", max_length=50)
    ssh_port: Optional[int] = Field(22, description="SSH port", ge=1, le=65535)
    http_port: Optional[int] = Field(None, description="HTTP port", ge=1, le=65535)
    https_port: Optional[int] = Field(None, description="HTTPS port", ge=1, le=65535)
    
    @field_validator('mac_address')
    def validate_mac_address(cls, v):
        """Validate MAC address format."""
        if v is None:
            return v
        
        import re
        if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', v):
            raise ValueError('MAC address must be in format XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX')
        return v
    
    @field_validator('ip_address')
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        if v is None:
            return v
        
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

    model_config = ConfigDict(from_attributes=True)


class NetworkNodeCreate(NetworkNodeBase):
    """Schema for creating a new network node."""
    id: str = Field(..., description="Unique identifier for the network node", min_length=1, max_length=50)


class NetworkNodeUpdate(BaseModel):
    """Schema for updating an existing network node."""
    name: Optional[str] = Field(None, description="Name of the network node", min_length=1, max_length=100)
    ip_address: Optional[str] = Field(None, description="IP address of the network node", min_length=7, max_length=45)
    type: Optional[NodeTypeEnum] = Field(None, description="Type of network node")
    location: Optional[str] = Field(None, description="Physical location of the node", max_length=255)
    description: Optional[str] = Field(None, description="Description of the node", max_length=500)
    
    # Hardware information
    model: Optional[str] = Field(None, description="Hardware model", max_length=100)
    manufacturer: Optional[str] = Field(None, description="Hardware manufacturer", max_length=100)
    serial_number: Optional[str] = Field(None, description="Hardware serial number", max_length=100)
    firmware_version: Optional[str] = Field(None, description="Firmware version", max_length=50)
    
    # Network information
    mac_address: Optional[str] = Field(None, description="MAC address (format: XX:XX:XX:XX:XX:XX)", max_length=17)
    subnet_mask: Optional[str] = Field(None, description="Subnet mask", max_length=45)
    gateway: Optional[str] = Field(None, description="Default gateway", max_length=45)
    dns_servers: Optional[List[str]] = Field(None, description="List of DNS servers")
    
    # Status information
    is_active: Optional[bool] = Field(None, description="Whether the node is active")
    last_seen: Optional[datetime] = Field(None, description="When the node was last seen")
    uptime: Optional[float] = Field(None, description="Node uptime in seconds")
    
    # Management information
    snmp_community: Optional[str] = Field(None, description="SNMP community string", max_length=50)
    snmp_version: Optional[str] = Field(None, description="SNMP version", max_length=10)
    ssh_username: Optional[str] = Field(None, description="SSH username", max_length=50)
    ssh_port: Optional[int] = Field(None, description="SSH port", ge=1, le=65535)
    http_port: Optional[int] = Field(None, description="HTTP port", ge=1, le=65535)
    https_port: Optional[int] = Field(None, description="HTTPS port", ge=1, le=65535)
    
    @field_validator('mac_address')
    def validate_mac_address(cls, v):
        """Validate MAC address format."""
        if v is None:
            return v
        
        import re
        if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', v):
            raise ValueError('MAC address must be in format XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX')
        return v
    
    @field_validator('ip_address')
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        if v is None:
            return v
        
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

    model_config = ConfigDict(from_attributes=True)


class NetworkNodeResponse(NetworkNodeBase):
    """Schema for network node responses."""
    id: str
    last_seen: Optional[datetime] = None
    uptime: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
