"""
Logging models for the monitoring module.

This module defines models for logging configurations and log levels
for the monitoring module.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend_core.database import Base


class LogLevel(str, Enum):
    """Enum for log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LoggingConfiguration(Base):
    """
    Model for logging configurations.
    
    This model stores logging configurations for different components
    of the ISP Management Platform.
    """
    __tablename__ = "logging_configurations"
    
    id = Column(String, primary_key=True)
    component = Column(String, nullable=False)  # Component name
    log_level = Column(String, nullable=False, default=LogLevel.INFO)
    elasticsearch_enabled = Column(Boolean, default=True, nullable=False)
    file_logging_enabled = Column(Boolean, default=True, nullable=False)
    console_logging_enabled = Column(Boolean, default=True, nullable=False)
    log_format = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    rotation_size = Column(Integer, nullable=True)  # Size in bytes
    max_files = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the logging configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the logging configuration.
        """
        return {
            "id": self.id,
            "component": self.component,
            "log_level": self.log_level,
            "elasticsearch_enabled": self.elasticsearch_enabled,
            "file_logging_enabled": self.file_logging_enabled,
            "console_logging_enabled": self.console_logging_enabled,
            "log_format": self.log_format,
            "file_path": self.file_path,
            "rotation_size": self.rotation_size,
            "max_files": self.max_files,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class LogFilter(Base):
    """
    Model for log filters.
    
    This model stores log filters for filtering logs based on
    different criteria.
    """
    __tablename__ = "log_filters"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    component = Column(String, nullable=True)  # Component to filter
    log_level = Column(String, nullable=True)  # Log level to filter
    message_pattern = Column(String, nullable=True)  # Regex pattern for message
    include_stacktrace = Column(Boolean, default=True, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the log filter to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the log filter.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "component": self.component,
            "log_level": self.log_level,
            "message_pattern": self.message_pattern,
            "include_stacktrace": self.include_stacktrace,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
