"""
Configuration models for the Configuration Management Module.

This module defines the database models for storing and managing system-wide
configurations, including version history and environment-specific settings.
"""

from datetime import datetime
import enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from backend_core.database import Base
from modules.core.utils import generate_uuid


class ConfigEnvironment(str, enum.Enum):
    """Enum for configuration environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    ALL = "all"  # For configurations that apply to all environments


class ConfigCategory(str, enum.Enum):
    """Enum for configuration categories."""
    SYSTEM = "system"
    SECURITY = "security"
    NETWORK = "network"
    BILLING = "billing"
    MONITORING = "monitoring"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"
    CUSTOM = "custom"


class Configuration(Base):
    """
    Model for system configurations.
    
    This model stores configuration key-value pairs with metadata such as
    environment, category, and validation schema.
    """
    __tablename__ = "configurations"
    
    id = Column(String(50), primary_key=True, default=generate_uuid)
    key = Column(String(255), nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    environment = Column(Enum(ConfigEnvironment), nullable=False, default=ConfigEnvironment.ALL)
    category = Column(Enum(ConfigCategory), nullable=False, default=ConfigCategory.SYSTEM)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    validation_schema = Column(JSON, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_by = Column(String(50), nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    history = relationship("ConfigurationHistory", back_populates="configuration", 
                          cascade="all, delete-orphan", order_by="desc(ConfigurationHistory.created_at)")
    group_items = relationship("ConfigurationGroupItem", back_populates="configuration", 
                              cascade="all, delete-orphan")
    
    # Ensure key+environment is unique for active configurations
    __table_args__ = (
        UniqueConstraint('key', 'environment', 'is_active', 
                         name='uix_config_key_env_active',
                         sqlite_on_conflict='REPLACE'),
    )
    
    def __repr__(self):
        return f"<Configuration(key='{self.key}', environment='{self.environment}', version={self.version})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the configuration.
        """
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "environment": self.environment,
            "category": self.category,
            "is_encrypted": self.is_encrypted,
            "validation_schema": self.validation_schema,
            "version": self.version,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }
    
    @hybrid_property
    def is_sensitive(self) -> bool:
        """
        Check if the configuration is sensitive.
        
        Returns:
            bool: True if the configuration is sensitive, False otherwise.
        """
        return self.is_encrypted or self.category == ConfigCategory.SECURITY
    
    def create_history_entry(self, action: str, user_id: str) -> "ConfigurationHistory":
        """
        Create a history entry for this configuration.
        
        Args:
            action: The action performed (create, update, delete)
            user_id: ID of the user who performed the action
            
        Returns:
            ConfigurationHistory: The created history entry
        """
        history_entry = ConfigurationHistory(
            configuration_id=self.id,
            key=self.key,
            value=self.value,
            environment=self.environment,
            category=self.category,
            is_encrypted=self.is_encrypted,
            version=self.version,
            action=action,
            created_by=user_id
        )
        return history_entry


class ConfigurationHistory(Base):
    """
    Model for configuration history.
    
    This model stores the history of changes to configurations, including
    the previous values and metadata about the change.
    """
    __tablename__ = "configuration_history"
    
    id = Column(String(50), primary_key=True, default=generate_uuid)
    configuration_id = Column(String(50), ForeignKey("configurations.id"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(JSON, nullable=False)
    environment = Column(Enum(ConfigEnvironment), nullable=False)
    category = Column(Enum(ConfigCategory), nullable=False)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # create, update, delete
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    configuration = relationship("Configuration", back_populates="history")
    
    def __repr__(self):
        return f"<ConfigurationHistory(key='{self.key}', version={self.version}, action='{self.action}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration history to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the configuration history.
        """
        return {
            "id": self.id,
            "configuration_id": self.configuration_id,
            "key": self.key,
            "value": self.value,
            "environment": self.environment,
            "category": self.category,
            "is_encrypted": self.is_encrypted,
            "version": self.version,
            "action": self.action,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }


class ConfigurationGroup(Base):
    """
    Model for grouping related configurations.
    
    This model allows for logical grouping of related configurations
    to simplify management and retrieval.
    """
    __tablename__ = "configuration_groups"
    
    id = Column(String(50), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_by = Column(String(50), nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    elasticsearch_synced = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    group_items = relationship("ConfigurationGroupItem", back_populates="group", 
                              cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ConfigurationGroup(name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration group to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the configuration group.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "elasticsearch_synced": self.elasticsearch_synced
        }


class ConfigurationGroupItem(Base):
    """
    Model for mapping configurations to groups.
    
    This model establishes the many-to-many relationship between
    configurations and configuration groups.
    """
    __tablename__ = "configuration_group_items"
    
    id = Column(String(50), primary_key=True, default=generate_uuid)
    group_id = Column(String(50), ForeignKey("configuration_groups.id"), nullable=False)
    configuration_id = Column(String(50), ForeignKey("configurations.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Ensure each configuration is only in a group once
    __table_args__ = (
        UniqueConstraint('group_id', 'configuration_id', 
                         name='uix_config_group_item'),
    )
    
    # Relationships
    group = relationship("ConfigurationGroup", back_populates="group_items")
    configuration = relationship("Configuration", back_populates="group_items")
    
    def __repr__(self):
        return f"<ConfigurationGroupItem(group_id='{self.group_id}', configuration_id='{self.configuration_id}')>"
