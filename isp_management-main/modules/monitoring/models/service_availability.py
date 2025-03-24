"""
Models for service availability monitoring.
"""

from datetime import datetime
import enum
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from backend_core.database import Base
from pydantic import BaseModel


# Helper function to generate UUID
def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class ProtocolType(enum.Enum):
    """Enum for service protocol types."""
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    DNS = "dns"
    RADIUS = "radius"
    SMTP = "smtp"
    POP3 = "pop3"
    IMAP = "imap"
    FTP = "ftp"
    SSH = "ssh"
    SNMP = "snmp"
    CUSTOM = "custom"


class StatusType(enum.Enum):
    """Enum for service status types."""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class SeverityLevel(enum.Enum):
    """Enum for outage severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ServiceEndpoint(Base):
    """Model for service endpoints to be monitored."""
    __tablename__ = "service_endpoints"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    url = Column(String(255), nullable=False)
    protocol = Column(Enum(ProtocolType), nullable=False)
    port = Column(Integer, nullable=True)
    check_interval = Column(Integer, nullable=False, default=60)  # seconds
    timeout = Column(Integer, nullable=False, default=5)  # seconds
    retries = Column(Integer, nullable=False, default=3)
    expected_status_code = Column(Integer, nullable=True)  # For HTTP
    expected_response_pattern = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    status_history = relationship("ServiceStatus", back_populates="endpoint", cascade="all, delete-orphan")
    outages = relationship("ServiceOutage", back_populates="endpoint", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ServiceEndpoint(id='{self.id}', name='{self.name}', protocol='{self.protocol}')>"


class ServiceStatus(Base):
    """Model for service status history."""
    __tablename__ = "service_status"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    endpoint_id = Column(String(50), ForeignKey("service_endpoints.id"), nullable=False)
    status = Column(Enum(StatusType), nullable=False)
    response_time = Column(Float, nullable=True)  # milliseconds
    status_message = Column(String(255), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    elasticsearch_synced = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    endpoint = relationship("ServiceEndpoint", back_populates="status_history")

    def __repr__(self):
        return f"<ServiceStatus(endpoint='{self.endpoint_id}', status='{self.status}', timestamp='{self.timestamp}')>"

    def model_dump(self):
        """Convert to dictionary for Elasticsearch indexing."""
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "endpoint_name": self.endpoint.name if self.endpoint else None,
            "protocol": self.endpoint.protocol.value if self.endpoint else None,
            "status": self.status.value,
            "response_time": self.response_time,
            "status_message": self.status_message,
            "timestamp": self.timestamp.isoformat(),
            "@timestamp": self.timestamp.isoformat(),
        }


class ServiceOutage(Base):
    """Model for service outages."""
    __tablename__ = "service_outages"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    endpoint_id = Column(String(50), ForeignKey("service_endpoints.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    severity = Column(Enum(SeverityLevel), nullable=False)
    affected_customers = Column(Integer, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    elasticsearch_synced = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    endpoint = relationship("ServiceEndpoint", back_populates="outages")
    alerts = relationship("ServiceAlert", back_populates="outage", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ServiceOutage(endpoint='{self.endpoint_id}', start='{self.start_time}', end='{self.end_time}')>"

    def model_dump(self):
        """Convert to dictionary for Elasticsearch indexing."""
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "endpoint_name": self.endpoint.name if self.endpoint else None,
            "protocol": self.endpoint.protocol.value if self.endpoint else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "severity": self.severity.value,
            "affected_customers": self.affected_customers,
            "resolution_notes": self.resolution_notes,
            "@timestamp": self.start_time.isoformat(),
            "is_active": self.end_time is None,
        }


class NotificationType(enum.Enum):
    """Enum for notification types."""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"


class ServiceAlert(Base):
    """Model for service alerts."""
    __tablename__ = "service_alerts"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    outage_id = Column(String(50), ForeignKey("service_outages.id"), nullable=False)
    alert_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    notification_type = Column(Enum(NotificationType), nullable=False)
    recipients = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    delivered = Column(Boolean, nullable=False, default=False)
    delivery_time = Column(DateTime, nullable=True)
    
    # Relationships
    outage = relationship("ServiceOutage", back_populates="alerts")

    def __repr__(self):
        return f"<ServiceAlert(outage='{self.outage_id}', type='{self.notification_type}', delivered='{self.delivered}')>"


class MaintenanceWindow(Base):
    """Model for scheduled maintenance windows."""
    __tablename__ = "maintenance_windows"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    affected_services = Column(String(255), nullable=True)  # Comma-separated list of service IDs
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MaintenanceWindow(name='{self.name}', start='{self.start_time}', end='{self.end_time}')>"

    def is_active(self):
        """Check if the maintenance window is currently active."""
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time

    def affects_service(self, service_id):
        """Check if the maintenance window affects a specific service."""
        if not self.affected_services:
            return False
        affected_ids = self.affected_services.split(',')
        return service_id in affected_ids
