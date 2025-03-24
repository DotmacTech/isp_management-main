"""
Database models for the Network Management Module.
"""

import enum
import ipaddress
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import INET, CIDR

from core.database import Base
from core.models import TimestampMixin


class DeviceType(enum.Enum):
    """Enumeration of supported network device types."""
    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    FIREWALL = "firewall"
    MODEM = "modem"
    OLT = "olt"
    ONU = "onu"
    SERVER = "server"
    OTHER = "other"


class DeviceStatus(enum.Enum):
    """Enumeration of device operational statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    PROVISIONING = "provisioning"
    DECOMMISSIONED = "decommissioned"
    FAILED = "failed"


class Device(Base, TimestampMixin):
    """Model representing a network device."""
    __tablename__ = "network_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(INET, nullable=False)
    mac_address = Column(String(17), nullable=True)
    serial_number = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    device_type = Column(Enum(DeviceType), nullable=False)
    status = Column(Enum(DeviceStatus), nullable=False, default=DeviceStatus.PROVISIONING)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Management credentials (encrypted in the database)
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)
    enable_password = Column(String(255), nullable=True)
    snmp_community = Column(String(100), nullable=True)
    
    # Relationships
    group_id = Column(Integer, ForeignKey("network_device_groups.id"), nullable=True)
    group = relationship("DeviceGroup", back_populates="devices")
    
    current_config_id = Column(Integer, ForeignKey("network_device_configurations.id"), nullable=True)
    current_config = relationship("DeviceConfiguration", foreign_keys=[current_config_id])
    
    firmware_version_id = Column(Integer, ForeignKey("network_firmware_versions.id"), nullable=True)
    firmware_version = relationship("FirmwareVersion")
    
    configurations = relationship("DeviceConfiguration", 
                                back_populates="device", 
                                foreign_keys="DeviceConfiguration.device_id")
    
    update_tasks = relationship("FirmwareUpdateTask", back_populates="device")
    
    # Additional properties stored as JSON
    properties = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<Device {self.name} ({self.hostname})>"


class DeviceGroup(Base, TimestampMixin):
    """Model representing a group of network devices."""
    __tablename__ = "network_device_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    devices = relationship("Device", back_populates="group")
    
    def __repr__(self):
        return f"<DeviceGroup {self.name}>"


class ConfigurationTemplate(Base, TimestampMixin):
    """Model representing a configuration template for network devices."""
    __tablename__ = "network_configuration_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    device_type = Column(Enum(DeviceType), nullable=False)
    template_content = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)  # JSON schema for template variables
    
    # Versioning
    version = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<ConfigTemplate {self.name} v{self.version}>"


class DeviceConfiguration(Base, TimestampMixin):
    """Model representing a configuration version for a network device."""
    __tablename__ = "network_device_configurations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("network_devices.id"), nullable=False)
    device = relationship("Device", back_populates="configurations", foreign_keys=[device_id])
    
    # Configuration content
    config_content = Column(Text, nullable=False)
    version = Column(String(20), nullable=False)
    
    # Metadata
    applied_by = Column(String(100), nullable=True)  # Username who applied this config
    applied_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    
    # Source template if this was generated from a template
    template_id = Column(Integer, ForeignKey("network_configuration_templates.id"), nullable=True)
    template = relationship("ConfigurationTemplate")
    
    # Variables used if this was generated from a template
    template_variables = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<DeviceConfig {self.device_id} v{self.version}>"


class IPPoolType(enum.Enum):
    """Enumeration of IP pool types."""
    CUSTOMER = "customer"
    INFRASTRUCTURE = "infrastructure"
    MANAGEMENT = "management"
    PUBLIC = "public"
    PRIVATE = "private"


class IPPool(Base, TimestampMixin):
    """Model representing an IP address pool."""
    __tablename__ = "network_ip_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Network information
    network = Column(CIDR, nullable=False)
    gateway = Column(INET, nullable=True)
    dns_servers = Column(JSON, nullable=True)  # List of DNS server IPs
    
    # Pool type and status
    pool_type = Column(Enum(IPPoolType), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    addresses = relationship("IPAddress", back_populates="pool")
    
    def __repr__(self):
        return f"<IPPool {self.name} ({self.network})>"


class IPAddressStatus(enum.Enum):
    """Enumeration of IP address statuses."""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    RESERVED = "reserved"
    QUARANTINED = "quarantined"


class IPAddress(Base, TimestampMixin):
    """Model representing an IP address in a pool."""
    __tablename__ = "network_ip_addresses"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(INET, nullable=False, unique=True)
    status = Column(Enum(IPAddressStatus), nullable=False, default=IPAddressStatus.AVAILABLE)
    
    # Pool relationship
    pool_id = Column(Integer, ForeignKey("network_ip_pools.id"), nullable=False)
    pool = relationship("IPPool", back_populates="addresses")
    
    # Assignment information
    assigned_to_id = Column(Integer, nullable=True)  # Generic foreign key
    assigned_to_type = Column(String(50), nullable=True)  # Entity type (customer, device, etc.)
    assigned_at = Column(DateTime, nullable=True)
    
    # Additional metadata
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<IPAddress {self.address} ({self.status.value})>"


class FirmwareVersion(Base, TimestampMixin):
    """Model representing a firmware version for network devices."""
    __tablename__ = "network_firmware_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), nullable=False)
    device_type = Column(Enum(DeviceType), nullable=False)
    manufacturer = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    
    # File information
    file_path = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 hash
    file_size = Column(Integer, nullable=False)  # Size in bytes
    
    # Release information
    release_date = Column(DateTime, nullable=True)
    release_notes = Column(Text, nullable=True)
    is_recommended = Column(Boolean, default=False)
    
    # Validation
    is_validated = Column(Boolean, default=False)
    validation_notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<FirmwareVersion {self.manufacturer} {self.model} {self.version}>"


class FirmwareUpdateStatus(enum.Enum):
    """Enumeration of firmware update task statuses."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FirmwareUpdateTask(Base, TimestampMixin):
    """Model representing a firmware update task for a network device."""
    __tablename__ = "network_firmware_update_tasks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Device and firmware information
    device_id = Column(Integer, ForeignKey("network_devices.id"), nullable=False)
    device = relationship("Device", back_populates="update_tasks")
    
    firmware_version_id = Column(Integer, ForeignKey("network_firmware_versions.id"), nullable=False)
    firmware_version = relationship("FirmwareVersion")
    
    # Scheduling information
    scheduled_by = Column(String(100), nullable=False)  # Username
    scheduled_for = Column(DateTime, nullable=False)
    
    # Status information
    status = Column(Enum(FirmwareUpdateStatus), nullable=False, default=FirmwareUpdateStatus.SCHEDULED)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    success = Column(Boolean, nullable=True)
    log_output = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<FirmwareUpdateTask {self.device_id} to {self.firmware_version_id} ({self.status.value})>"
