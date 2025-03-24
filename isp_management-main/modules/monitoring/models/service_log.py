"""
Service log models for the monitoring module.

This module defines models for logging service availability checks and status changes.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend_core.database import Base
from modules.monitoring.models.service_availability import ServiceEndpoint, ServiceStatus


class ServiceLog(Base):
    """
    Model for logging service availability checks.
    
    This model stores the results of service availability checks, including
    response times, status codes, and any error messages.
    """
    __tablename__ = "service_logs"
    
    id = Column(String, primary_key=True)
    endpoint_id = Column(String, ForeignKey("service_endpoints.id"), nullable=False)
    service_name = Column(String(255), nullable=True)  # Added to match test expectations
    status = Column(String, nullable=False)
    response_time = Column(Float, nullable=True)
    status_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)  # Added as alias for created_at
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    endpoint = relationship("ServiceEndpoint", back_populates="logs")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the service log to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the service log.
        """
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "service_name": self.service_name,
            "status": self.status,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """
        Convert the service log to a format suitable for Elasticsearch.
        
        Returns:
            Dict[str, Any]: Elasticsearch-friendly representation of the service log.
        """
        # Get endpoint details if available
        endpoint_name = None
        endpoint_url = None
        endpoint_protocol = None
        
        if self.endpoint:
            endpoint_name = self.endpoint.name
            endpoint_url = self.endpoint.url
            endpoint_protocol = self.endpoint.protocol
        
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "service_name": self.service_name,
            "endpoint_name": endpoint_name,
            "endpoint_url": endpoint_url,
            "endpoint_protocol": endpoint_protocol,
            "status": self.status,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "@timestamp": datetime.utcnow().isoformat()
        }


# Add back-reference to ServiceEndpoint model
ServiceEndpoint.logs = relationship("ServiceLog", back_populates="endpoint", cascade="all, delete-orphan")
