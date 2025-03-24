"""
OLT Device Model Module

This module defines the data model for OLT devices.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class OLTDevice:
    """
    Data model for an OLT device.
    
    This class represents an Optical Line Terminal (OLT) device in the system,
    including its configuration, status, and metadata.
    """
    
    # Core attributes
    id: str
    name: str
    vendor: str
    model: str
    host: str
    port: int
    
    # Authentication
    username: str
    password_encrypted: Optional[str] = None
    
    # Status and metadata
    status: str = "unknown"
    uptime: Optional[int] = None
    firmware_version: Optional[str] = None
    serial_number: Optional[str] = None
    
    # Hardware information
    total_ports: Optional[int] = None
    used_ports: Optional[int] = None
    temperature: Optional[float] = None
    
    # Network information
    management_ip: Optional[str] = None
    subnet_mask: Optional[str] = None
    gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    
    # Location information
    site_id: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Configuration
    config_backup_path: Optional[str] = None
    config_last_backup: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_seen: Optional[datetime] = None
    
    # Additional attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the OLT device to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the OLT device
        """
        result = {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "model": self.model,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        # Add optional fields if they exist
        optional_fields = [
            "uptime", "firmware_version", "serial_number", "total_ports", 
            "used_ports", "temperature", "management_ip", "subnet_mask", 
            "gateway", "site_id", "location_name", "latitude", "longitude", 
            "config_backup_path"
        ]
        
        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        # Add list fields if they're not empty
        if self.dns_servers:
            result["dns_servers"] = self.dns_servers
        
        # Add datetime fields if they exist
        if self.config_last_backup:
            result["config_last_backup"] = self.config_last_backup.isoformat()
        
        if self.last_seen:
            result["last_seen"] = self.last_seen.isoformat()
        
        # Add additional attributes
        if self.attributes:
            result["attributes"] = self.attributes
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OLTDevice':
        """
        Create an OLT device from a dictionary.
        
        Args:
            data: Dictionary containing OLT device data
            
        Returns:
            OLTDevice: An OLT device instance
        """
        # Handle datetime fields
        datetime_fields = ["created_at", "updated_at", "last_seen", "config_last_backup"]
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
        Update the OLT device with new data.
        
        Args:
            data: Dictionary containing updated OLT device data
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.attributes[key] = value
        
        self.updated_at = datetime.now()
    
    def __str__(self) -> str:
        """
        Get a string representation of the OLT device.
        
        Returns:
            str: String representation
        """
        return f"{self.name} ({self.vendor} {self.model}) - {self.host}:{self.port}"


# Helper function to get dataclass fields
def fields(cls):
    """Get the fields of a dataclass."""
    return cls.__dataclass_fields__.values()
