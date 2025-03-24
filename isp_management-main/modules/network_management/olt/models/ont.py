"""
ONT Device Model Module

This module defines the data model for ONT devices.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class ONTDevice:
    """
    Data model for an ONT device.
    
    This class represents an Optical Network Terminal (ONT) device in the system,
    including its configuration, status, and metadata.
    """
    
    # Core attributes
    id: str
    serial_number: str
    olt_id: str
    
    # Identifiers
    name: Optional[str] = None
    description: Optional[str] = None
    
    # Location information
    frame_id: Optional[str] = None
    slot_id: Optional[str] = None
    port_id: Optional[str] = None
    ont_id: Optional[str] = None
    
    # Status and metadata
    status: str = "unknown"
    admin_status: str = "unknown"  # e.g., "enabled", "disabled"
    oper_status: str = "unknown"   # e.g., "up", "down"
    uptime: Optional[int] = None
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    model: Optional[str] = None
    vendor: Optional[str] = None
    
    # Signal metrics
    rx_power: Optional[float] = None  # Receive optical power (dBm)
    tx_power: Optional[float] = None  # Transmit optical power (dBm)
    temperature: Optional[float] = None
    distance: Optional[float] = None  # Distance from OLT (meters)
    
    # Network configuration
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    gateway: Optional[str] = None
    mac_address: Optional[str] = None
    dhcp_enabled: bool = False
    pppoe_enabled: bool = False
    
    # VLAN configuration
    vlan_mode: Optional[str] = None  # e.g., "access", "trunk"
    vlan_id: Optional[int] = None
    
    # Service configuration
    internet_enabled: bool = True
    iptv_enabled: bool = False
    voip_enabled: bool = False
    
    # Speed limits
    download_limit: Optional[int] = None  # in Kbps
    upload_limit: Optional[int] = None    # in Kbps
    
    # TR-069 configuration
    tr069_enabled: bool = False
    tr069_acs_url: Optional[str] = None
    tr069_periodic_inform_interval: Optional[int] = None
    
    # Customer information
    customer_id: Optional[str] = None
    service_profile_id: Optional[str] = None
    
    # Location information
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    
    # Timestamps
    provisioned_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Additional attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ONT device to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the ONT device
        """
        result = {
            "id": self.id,
            "serial_number": self.serial_number,
            "olt_id": self.olt_id,
            "status": self.status,
            "admin_status": self.admin_status,
            "oper_status": self.oper_status,
            "dhcp_enabled": self.dhcp_enabled,
            "pppoe_enabled": self.pppoe_enabled,
            "internet_enabled": self.internet_enabled,
            "iptv_enabled": self.iptv_enabled,
            "voip_enabled": self.voip_enabled,
            "tr069_enabled": self.tr069_enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        # Add optional fields if they exist
        optional_fields = [
            "name", "description", "frame_id", "slot_id", "port_id", "ont_id",
            "uptime", "firmware_version", "hardware_version", "model", "vendor",
            "rx_power", "tx_power", "temperature", "distance", "ip_address",
            "subnet_mask", "gateway", "mac_address", "vlan_mode", "vlan_id",
            "download_limit", "upload_limit", "tr069_acs_url", 
            "tr069_periodic_inform_interval", "customer_id", "service_profile_id",
            "latitude", "longitude", "location_name"
        ]
        
        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        # Add datetime fields if they exist
        if self.provisioned_at:
            result["provisioned_at"] = self.provisioned_at.isoformat()
        
        if self.last_seen:
            result["last_seen"] = self.last_seen.isoformat()
        
        # Add additional attributes
        if self.attributes:
            result["attributes"] = self.attributes
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ONTDevice':
        """
        Create an ONT device from a dictionary.
        
        Args:
            data: Dictionary containing ONT device data
            
        Returns:
            ONTDevice: An ONT device instance
        """
        # Handle datetime fields
        datetime_fields = ["created_at", "updated_at", "last_seen", "provisioned_at"]
        for field in datetime_fields:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        # Extract known fields for the constructor
        known_fields = {
            k: v for k, v in data.items() 
            if k in [f.name for f in fields(cls)]
        }
        
        # Create the instance
        instance = cls(**known_fields)
        
        # Add any additional attributes
        for k, v in data.items():
            if k not in known_fields:
                instance.attributes[k] = v
        
        return instance
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        Update the ONT device with new data.
        
        Args:
            data: Dictionary containing updated ONT device data
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.attributes[key] = value
        
        self.updated_at = datetime.now()
    
    def __str__(self) -> str:
        """
        Get a string representation of the ONT device.
        
        Returns:
            str: String representation
        """
        name_str = f" - {self.name}" if self.name else ""
        return f"ONT {self.serial_number}{name_str} ({self.status})"


# Helper function to get dataclass fields
def fields(cls):
    """Get the fields of a dataclass."""
    return cls.__dataclass_fields__.values()
