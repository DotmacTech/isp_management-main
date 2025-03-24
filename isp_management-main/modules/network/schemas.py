"""
Pydantic schemas for the Network Management Module.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, IPvAnyAddress, IPvAnyNetwork, conint
from enum import Enum

from modules.network.models import DeviceType, DeviceStatus, IPPoolType, IPAddressStatus, FirmwareUpdateStatus


# Base schemas
class TimestampMixin(BaseModel):
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Device schemas
class DeviceBase(BaseModel):
    name: str = Field(..., description="Device name", min_length=1, max_length=255)
    hostname: str = Field(..., description="Device hostname or IP address", min_length=1, max_length=255)
    ip_address: str = Field(..., description="Management IP address")
    device_type: DeviceType = Field(..., description="Device type")
    mac_address: Optional[str] = Field(None, description="MAC address")
    serial_number: Optional[str] = Field(None, description="Serial number")
    model: Optional[str] = Field(None, description="Device model")
    manufacturer: Optional[str] = Field(None, description="Device manufacturer")
    location: Optional[str] = Field(None, description="Physical location")
    description: Optional[str] = Field(None, description="Device description")
    group_id: Optional[int] = Field(None, description="Device group ID")
    username: Optional[str] = Field(None, description="Management username")
    password: Optional[str] = Field(None, description="Management password")
    enable_password: Optional[str] = Field(None, description="Enable password")
    snmp_community: Optional[str] = Field(None, description="SNMP community string")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        try:
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Device name", min_length=1, max_length=255)
    hostname: Optional[str] = Field(None, description="Device hostname or IP address", min_length=1, max_length=255)
    ip_address: Optional[str] = Field(None, description="Management IP address")
    device_type: Optional[DeviceType] = Field(None, description="Device type")
    mac_address: Optional[str] = Field(None, description="MAC address")
    serial_number: Optional[str] = Field(None, description="Serial number")
    model: Optional[str] = Field(None, description="Device model")
    manufacturer: Optional[str] = Field(None, description="Device manufacturer")
    location: Optional[str] = Field(None, description="Physical location")
    description: Optional[str] = Field(None, description="Device description")
    group_id: Optional[int] = Field(None, description="Device group ID")
    username: Optional[str] = Field(None, description="Management username")
    password: Optional[str] = Field(None, description="Management password")
    enable_password: Optional[str] = Field(None, description="Enable password")
    snmp_community: Optional[str] = Field(None, description="SNMP community string")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")
    status: Optional[DeviceStatus] = Field(None, description="Device status")

    @field_validator('ip_address', pre=True)
    @classmethod
    def validate_ip_address(cls, v):
        if v is None:
            return v
        try:
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class DeviceResponse(DeviceBase, TimestampMixin):
    id: int = Field(..., description="Device ID")
    status: DeviceStatus = Field(..., description="Device status")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Router-01",
                "hostname": "router01.example.com",
                "ip_address": "192.168.1.1",
                "device_type": "ROUTER",
                "mac_address": "00:11:22:33:44:55",
                "serial_number": "ABC123XYZ",
                "model": "ASR-9000",
                "manufacturer": "Cisco",
                "location": "Data Center 1, Rack A3",
                "description": "Core router for main office",
                "group_id": 1,
                "username": "admin",
                "password": "********",
                "enable_password": "********",
                "snmp_community": "public",
                "properties": {"os_version": "IOS-XE 16.9.3", "memory": "8GB"},
                "status": "ACTIVE",
                "last_seen": "2023-01-01T12:00:00",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    )


class DeviceListResponse(BaseModel):
    items: List[DeviceResponse] = Field(..., description="List of devices")
    total: int = Field(..., description="Total number of devices")
    skip: int = Field(..., description="Number of devices skipped")
    limit: int = Field(..., description="Maximum number of devices returned")


# Device Group schemas
class DeviceGroupBase(BaseModel):
    name: str = Field(..., description="Group name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Group description")
    parent_id: Optional[int] = Field(None, description="Parent group ID")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")


class DeviceGroupCreate(DeviceGroupBase):
    pass


class DeviceGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Group name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Group description")
    parent_id: Optional[int] = Field(None, description="Parent group ID")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")


class DeviceGroupResponse(DeviceGroupBase, TimestampMixin):
    id: int = Field(..., description="Group ID")
    device_count: int = Field(..., description="Number of devices in group")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Core Routers",
                "description": "All core routers",
                "parent_id": None,
                "properties": {"location": "Main Data Center"},
                "device_count": 5,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    )


# IP Pool schemas
class IPPoolBase(BaseModel):
    name: str = Field(..., description="Pool name", min_length=1, max_length=255)
    network: str = Field(..., description="Network in CIDR notation")
    pool_type: IPPoolType = Field(..., description="Pool type")
    gateway: Optional[str] = Field(None, description="Default gateway")
    dns_servers: Optional[List[str]] = Field(None, description="DNS servers")
    description: Optional[str] = Field(None, description="Pool description")

    @field_validator('network')
    @classmethod
    def validate_network(cls, v):
        try:
            IPvAnyNetwork(v)
            return v
        except ValueError:
            raise ValueError("Invalid network format, must be in CIDR notation")

    @field_validator('gateway', 'dns_servers', each_item=True)
    @classmethod
    def validate_ip(cls, v):
        if v is None:
            return v
        try:
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class IPPoolCreate(IPPoolBase):
    pass


class IPPoolUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Pool name", min_length=1, max_length=255)
    gateway: Optional[str] = Field(None, description="Default gateway")
    dns_servers: Optional[List[str]] = Field(None, description="DNS servers")
    description: Optional[str] = Field(None, description="Pool description")
    is_active: Optional[bool] = Field(None, description="Whether the pool is active")

    @field_validator('gateway', 'dns_servers', each_item=True)
    @classmethod
    def validate_ip(cls, v):
        if v is None:
            return v
        try:
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class IPPoolResponse(IPPoolBase, TimestampMixin):
    id: int = Field(..., description="Pool ID")
    is_active: bool = Field(..., description="Whether the pool is active")
    total_addresses: int = Field(..., description="Total number of addresses in pool")
    used_addresses: int = Field(..., description="Number of used addresses in pool")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Customer Network",
                "network": "192.168.0.0/24",
                "pool_type": "CUSTOMER",
                "gateway": "192.168.0.1",
                "dns_servers": ["8.8.8.8", "8.8.4.4"],
                "description": "Network for customer devices",
                "is_active": True,
                "total_addresses": 254,
                "used_addresses": 45,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    )


class IPPoolListResponse(BaseModel):
    items: List[IPPoolResponse] = Field(..., description="List of IP pools")
    total: int = Field(..., description="Total number of IP pools")
    skip: int = Field(..., description="Number of IP pools skipped")
    limit: int = Field(..., description="Maximum number of IP pools returned")


class IPAddressBase(BaseModel):
    ip_address: str = Field(..., description="IP address")
    pool_id: int = Field(..., description="IP pool ID")
    status: IPAddressStatus = Field(..., description="IP address status")
    assigned_to_id: Optional[int] = Field(None, description="ID of entity assigned to")
    assigned_to_type: Optional[str] = Field(None, description="Type of entity assigned to")
    notes: Optional[str] = Field(None, description="Notes")

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        try:
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class IPAddressResponse(IPAddressBase, TimestampMixin):
    id: int = Field(..., description="IP address ID")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ip_address": "192.168.0.10",
                "pool_id": 1,
                "status": "ALLOCATED",
                "assigned_to_id": 123,
                "assigned_to_type": "customer",
                "notes": "Assigned to customer XYZ",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    )


# Configuration Template schemas
class ConfigTemplateBase(BaseModel):
    name: str = Field(..., description="Template name", min_length=1, max_length=255)
    device_type: DeviceType = Field(..., description="Device type")
    template_content: str = Field(..., description="Template content")
    version: str = Field(..., description="Template version", min_length=1, max_length=50)
    variables: Dict[str, Any] = Field(..., description="Template variables")
    description: Optional[str] = Field(None, description="Template description")


class ConfigTemplateCreate(ConfigTemplateBase):
    pass


class ConfigTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Template name", min_length=1, max_length=255)
    template_content: Optional[str] = Field(None, description="Template content")
    version: Optional[str] = Field(None, description="Template version", min_length=1, max_length=50)
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    description: Optional[str] = Field(None, description="Template description")
    is_active: Optional[bool] = Field(None, description="Whether the template is active")


class ConfigTemplateResponse(ConfigTemplateBase, TimestampMixin):
    id: int = Field(..., description="Template ID")
    is_active: bool = Field(..., description="Whether the template is active")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Cisco Router Base Config",
                "device_type": "ROUTER",
                "template_content": "hostname {{ hostname }}\ninterface GigabitEthernet0/0\n ip address {{ ip }} {{ mask }}",
                "version": "1.0.0",
                "variables": {"hostname": "string", "ip": "ipv4", "mask": "ipv4_netmask"},
                "description": "Base configuration for Cisco routers",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    )


# Device Configuration schemas
class DeviceConfigBase(BaseModel):
    device_id: int = Field(..., description="Device ID")
    config_content: str = Field(..., description="Configuration content")
    version: str = Field(..., description="Configuration version", min_length=1, max_length=50)
    template_id: Optional[int] = Field(None, description="Template ID used to generate this configuration")
    template_variables: Optional[Dict[str, Any]] = Field(None, description="Variables used with the template")


class DeviceConfigCreate(BaseModel):
    config_content: str = Field(..., description="Configuration content")
    version: str = Field(..., description="Configuration version", min_length=1, max_length=50)
    template_id: Optional[int] = Field(None, description="Template ID used to generate this configuration")
    template_variables: Optional[Dict[str, Any]] = Field(None, description="Variables used with the template")


class DeviceConfigResponse(DeviceConfigBase, TimestampMixin):
    id: int = Field(..., description="Configuration ID")
    is_active: bool = Field(..., description="Whether this is the active configuration")
    applied_at: Optional[datetime] = Field(None, description="When the configuration was applied")
    applied_by: Optional[str] = Field(None, description="Who applied the configuration")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "device_id": 1,
                "config_content": "hostname router01\ninterface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0",
                "version": "1.0.0",
                "template_id": 1,
                "template_variables": {"hostname": "router01", "ip": "192.168.1.1", "mask": "255.255.255.0"},
                "is_active": True,
                "applied_at": "2023-01-01T12:00:00",
                "applied_by": "admin",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    )


class DeviceConfigListResponse(BaseModel):
    items: List[DeviceConfigResponse] = Field(..., description="List of device configurations")
    total: int = Field(..., description="Total number of configurations")
    skip: int = Field(..., description="Number of configurations skipped")
    limit: int = Field(..., description="Maximum number of configurations returned")


# Firmware schemas
class FirmwareVersionBase(BaseModel):
    version: str = Field(..., description="Firmware version", min_length=1, max_length=50)
    device_type: DeviceType = Field(..., description="Device type")
    manufacturer: str = Field(..., description="Device manufacturer", min_length=1, max_length=255)
    model: str = Field(..., description="Device model", min_length=1, max_length=255)
    release_date: datetime = Field(..., description="Release date")
    file_path: str = Field(..., description="Path to firmware file")
    file_size: int = Field(..., description="Size of firmware file in bytes")
    checksum: str = Field(..., description="Firmware file checksum")
    checksum_type: str = Field(..., description="Checksum type (e.g., MD5, SHA256)")
    release_notes: Optional[str] = Field(None, description="Release notes")


class FirmwareVersionResponse(FirmwareVersionBase, TimestampMixin):
    id: int = Field(..., description="Firmware version ID")
    is_active: bool = Field(..., description="Whether the firmware version is active")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "version": "16.9.3",
                "device_type": "ROUTER",
                "manufacturer": "Cisco",
                "model": "ASR-9000",
                "release_date": "2023-01-01T00:00:00",
                "file_path": "/data/firmware/cisco_asr9k_16.9.3.bin",
                "file_size": 123456789,
                "checksum": "a1b2c3d4e5f6g7h8i9j0",
                "checksum_type": "SHA256",
                "release_notes": "Bug fixes and security updates",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00"
            }
        }
    )


class FirmwareUpdateTaskBase(BaseModel):
    device_id: int = Field(..., description="Device ID")
    firmware_id: int = Field(..., description="Firmware version ID")
    scheduled_time: Optional[datetime] = Field(None, description="Scheduled time for update")
    pre_update_config_backup: bool = Field(True, description="Whether to backup configuration before update")
    post_update_config_restore: bool = Field(True, description="Whether to restore configuration after update")
    notes: Optional[str] = Field(None, description="Update notes")


class FirmwareUpdateTaskCreate(FirmwareUpdateTaskBase):
    pass


class FirmwareUpdateTaskResponse(FirmwareUpdateTaskBase, TimestampMixin):
    id: int = Field(..., description="Update task ID")
    status: FirmwareUpdateStatus = Field(..., description="Update task status")
    started_at: Optional[datetime] = Field(None, description="When the update started")
    completed_at: Optional[datetime] = Field(None, description="When the update completed")
    result: Optional[str] = Field(None, description="Update result")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "device_id": 1,
                "firmware_id": 1,
                "scheduled_time": "2023-01-01T12:00:00",
                "pre_update_config_backup": True,
                "post_update_config_restore": True,
                "notes": "Critical security update",
                "status": "SCHEDULED",
                "started_at": None,
                "completed_at": None,
                "result": None,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
    )


# Topology schemas
class TopologyNode(BaseModel):
    id: str = Field(..., description="Node ID")
    label: str = Field(..., description="Node label")
    type: str = Field(..., description="Node type")
    properties: Dict[str, Any] = Field(..., description="Node properties")


class TopologyEdge(BaseModel):
    id: str = Field(..., description="Edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: Optional[str] = Field(None, description="Edge label")
    properties: Dict[str, Any] = Field(..., description="Edge properties")


class TopologyResponse(BaseModel):
    nodes: List[TopologyNode] = Field(..., description="Topology nodes")
    edges: List[TopologyEdge] = Field(..., description="Topology edges")
    metadata: Dict[str, Any] = Field(..., description="Topology metadata")


class TopologyMetric(BaseModel):
    name: str = Field(..., description="Metric name")
    value: Union[int, float, str] = Field(..., description="Metric value")
    description: str = Field(..., description="Metric description")


class TopologyAnalysisResponse(BaseModel):
    metrics: List[TopologyMetric] = Field(..., description="Topology metrics")
    critical_nodes: List[str] = Field(..., description="Critical nodes in the topology")
    redundancy_paths: List[Dict[str, Any]] = Field(..., description="Redundant paths in the topology")
    bottlenecks: List[str] = Field(..., description="Bottlenecks in the topology")
    recommendations: List[str] = Field(..., description="Recommendations for topology improvement")
