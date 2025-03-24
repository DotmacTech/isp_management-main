"""
Network Node Model for the ISP Management Platform Monitoring Module

This module defines the NetworkNode model for storing information about network devices
such as routers, switches, access points, and servers.
"""

import enum
from sqlalchemy import Column, String, Integer, Float, Enum, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from modules.core.database import Base


class NodeType(enum.Enum):
    """Enum for network node types."""
    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    SERVER = "server"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    OTHER = "other"


class NetworkNode(Base):
    """
    Model representing a network node in the ISP infrastructure.
    
    A network node can be a router, switch, access point, server, or other network device.
    """
    __tablename__ = "network_nodes"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv4 or IPv6
    type = Column(Enum(NodeType), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    
    # Hardware information
    model = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    
    # Network information
    mac_address = Column(String(17), nullable=True)  # Format: XX:XX:XX:XX:XX:XX
    subnet_mask = Column(String(45), nullable=True)
    gateway = Column(String(45), nullable=True)
    dns_servers = Column(JSON, nullable=True)  # List of DNS servers
    
    # Status information
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    uptime = Column(Float, nullable=True)  # in seconds
    
    # Management information
    snmp_community = Column(String(50), nullable=True)
    snmp_version = Column(String(10), nullable=True)
    ssh_username = Column(String(50), nullable=True)
    ssh_port = Column(Integer, default=22)
    http_port = Column(Integer, nullable=True)
    https_port = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    # metrics = relationship("SystemMetric", back_populates="node")
    
    def __repr__(self):
        return f"<NetworkNode(id='{self.id}', name='{self.name}', ip='{self.ip_address}', type='{self.type}')>"
