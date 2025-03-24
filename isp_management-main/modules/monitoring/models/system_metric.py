"""
System metric models for the monitoring module.

This module defines models for tracking system metrics such as CPU, memory,
disk usage, and network performance.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship

from backend_core.database import Base


class MetricType(str, Enum):
    """Enum for system metric types."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    CUSTOM = "custom"


class SystemMetric(Base):
    """
    Model for system metrics.
    
    This model stores system metrics such as CPU, memory, disk usage,
    and network performance.
    """
    __tablename__ = "system_metrics"
    
    id = Column(String, primary_key=True)
    host = Column(String, nullable=False)
    metric_type = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the system metric to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the system metric.
        """
        return {
            "id": self.id,
            "host": self.host,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """
        Convert the system metric to a format suitable for Elasticsearch.
        
        Returns:
            Dict[str, Any]: Elasticsearch-friendly representation of the system metric.
        """
        return {
            "id": self.id,
            "host": self.host,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "@timestamp": datetime.utcnow().isoformat()
        }


class NetworkPerformanceMetric(Base):
    """
    Model for network performance metrics.
    
    This model stores network performance metrics such as latency,
    jitter, packet loss, and throughput.
    """
    __tablename__ = "network_performance_metrics"
    
    id = Column(String, primary_key=True)
    source_host = Column(String, nullable=False)
    destination_host = Column(String, nullable=False)
    latency = Column(Float, nullable=True)  # in milliseconds
    jitter = Column(Float, nullable=True)  # in milliseconds
    packet_loss = Column(Float, nullable=True)  # percentage
    throughput = Column(Float, nullable=True)  # in Mbps
    hop_count = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the network performance metric to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the network performance metric.
        """
        return {
            "id": self.id,
            "source_host": self.source_host,
            "destination_host": self.destination_host,
            "latency": self.latency,
            "jitter": self.jitter,
            "packet_loss": self.packet_loss,
            "throughput": self.throughput,
            "hop_count": self.hop_count,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """
        Convert the network performance metric to a format suitable for Elasticsearch.
        
        Returns:
            Dict[str, Any]: Elasticsearch-friendly representation of the network performance metric.
        """
        return {
            "id": self.id,
            "source_host": self.source_host,
            "destination_host": self.destination_host,
            "latency": self.latency,
            "jitter": self.jitter,
            "packet_loss": self.packet_loss,
            "throughput": self.throughput,
            "hop_count": self.hop_count,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "@timestamp": datetime.utcnow().isoformat()
        }


class CustomerUsageMetric(Base):
    """
    Model for customer usage metrics.
    
    This model stores customer usage metrics such as data transfer,
    connection time, and bandwidth usage.
    """
    __tablename__ = "customer_usage_metrics"
    
    id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False)
    metric_type = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the customer usage metric to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the customer usage metric.
        """
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """
        Convert the customer usage metric to a format suitable for Elasticsearch.
        
        Returns:
            Dict[str, Any]: Elasticsearch-friendly representation of the customer usage metric.
        """
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "@timestamp": datetime.utcnow().isoformat()
        }
