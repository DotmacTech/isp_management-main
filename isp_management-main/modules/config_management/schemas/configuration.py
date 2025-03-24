"""
Schemas for configuration management.

This module defines Pydantic models for request and response validation
for the configuration management API.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

from modules.config_management.models.configuration import ConfigEnvironment, ConfigCategory


class ConfigurationBase(BaseModel):
    """Base schema for configuration data."""
    key: str = Field(..., description="Unique configuration key", min_length=1, max_length=255)
    value: Any = Field(..., description="Configuration value (can be any JSON-serializable data)")
    description: Optional[str] = Field(None, description="Description of the configuration")
    environment: ConfigEnvironment = Field(ConfigEnvironment.ALL, description="Environment this configuration applies to")
    category: ConfigCategory = Field(ConfigCategory.SYSTEM, description="Category of the configuration")
    is_encrypted: bool = Field(False, description="Whether the value should be encrypted")
    validation_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for validating the value")
    is_active: bool = Field(True, description="Whether the configuration is active")
    elasticsearch_synced: bool = Field(False, description="Whether the configuration is synced with Elasticsearch")

    class Config:
        model_config = {
            "use_enum_values": True
        }


class ConfigurationCreate(ConfigurationBase):
    """Schema for creating a new configuration."""
    pass


class ConfigurationUpdate(BaseModel):
    """Schema for updating an existing configuration."""
    value: Optional[Any] = Field(None, description="New configuration value")
    description: Optional[str] = Field(None, description="Updated description")
    environment: Optional[ConfigEnvironment] = Field(None, description="Updated environment")
    category: Optional[ConfigCategory] = Field(None, description="Updated category")
    is_encrypted: Optional[bool] = Field(None, description="Whether the value should be encrypted")
    validation_schema: Optional[Dict[str, Any]] = Field(None, description="Updated JSON Schema for validation")
    is_active: Optional[bool] = Field(None, description="Whether the configuration is active")

    class Config:
        model_config = {
            "use_enum_values": True
        }

    @model_validator(mode='after')
    def check_at_least_one_field(cls, model):
        """Ensure at least one field is provided for update."""
        # In Pydantic v2, we need to access model fields directly
        model_data = model.model_dump()
        # Check if any field has a non-None value
        if not any(v is not None for v in model_data.values()):
            raise ValueError("At least one field must be provided for update")
        return model


class ConfigurationBulkUpdate(BaseModel):
    """Schema for bulk updating configurations."""
    configurations: List[Dict[str, Any]] = Field(..., description="List of configurations to update")
    
    @field_validator('configurations')
    @classmethod
    def validate_configurations(cls, v):
        """Validate that each configuration has at least a key and value."""
        for config in v:
            if 'key' not in config:
                raise ValueError("Each configuration must have a 'key'")
            if 'value' not in config:
                raise ValueError("Each configuration must have a 'value'")
        return v


class ConfigurationResponse(ConfigurationBase):
    """Schema for configuration response."""
    id: str = Field(..., description="Unique identifier")
    version: int = Field(..., description="Configuration version")
    created_by: str = Field(..., description="User who created the configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_by: Optional[str] = Field(None, description="User who last updated the configuration")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    elasticsearch_synced: bool = Field(False, description="Whether the configuration is synced with Elasticsearch")

    class Config:
        model_config = {
            "from_attributes": True,
            "use_enum_values": True
        }


class ConfigurationHistoryResponse(BaseModel):
    """Schema for configuration history response."""
    id: str = Field(..., description="Unique identifier")
    configuration_id: str = Field(..., description="ID of the related configuration")
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value at this point in history")
    environment: str = Field(..., description="Environment this configuration applied to")
    category: str = Field(..., description="Category of the configuration")
    is_encrypted: bool = Field(..., description="Whether the value was encrypted")
    version: int = Field(..., description="Configuration version")
    action: str = Field(..., description="Action performed (create, update, delete)")
    created_by: str = Field(..., description="User who performed the action")
    created_at: datetime = Field(..., description="Timestamp of the action")
    elasticsearch_synced: bool = Field(False, description="Whether the configuration is synced with Elasticsearch")

    class Config:
        model_config = {
            "from_attributes": True
        }


class ConfigurationGroupBase(BaseModel):
    """Base schema for configuration group data."""
    name: str = Field(..., description="Group name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Group description")
    environment: ConfigEnvironment = Field(ConfigEnvironment.ALL, description="Environment this group applies to")
    is_active: bool = Field(True, description="Whether the group is active")
    
    class Config:
        model_config = {
            "use_enum_values": True
        }


class ConfigurationGroupCreate(ConfigurationGroupBase):
    """Schema for creating a new configuration group."""
    configurations: Optional[List[str]] = Field(None, description="IDs of configurations to add to the group")


class ConfigurationGroupUpdate(BaseModel):
    """Schema for updating a configuration group."""
    name: Optional[str] = Field(None, description="Updated group name")
    description: Optional[str] = Field(None, description="Updated group description")
    environment: Optional[ConfigEnvironment] = Field(None, description="Updated environment")
    is_active: Optional[bool] = Field(None, description="Whether the group is active")
    add_configuration_ids: Optional[List[str]] = Field(None, description="IDs of configurations to add to the group")
    remove_configuration_ids: Optional[List[str]] = Field(None, description="IDs of configurations to remove from the group")
    
    class Config:
        model_config = {
            "use_enum_values": True
        }

    @model_validator(mode='after')
    def check_at_least_one_field(cls, model):
        """Ensure at least one field is provided for update."""
        # In Pydantic v2, we need to access model fields directly
        model_data = model.model_dump()
        # Check if any field has a non-None value
        if not any(v is not None for v in model_data.values()):
            raise ValueError("At least one field must be provided for update")
        return model


class ConfigurationGroupResponse(ConfigurationGroupBase):
    """Schema for configuration group response."""
    id: str = Field(..., description="Unique identifier")
    created_by: str = Field(..., description="User who created the group")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_by: Optional[str] = Field(None, description="User who last updated the group")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    elasticsearch_synced: bool = Field(False, description="Whether the group is synced with Elasticsearch")
    configurations: Optional[List[ConfigurationResponse]] = Field(None, description="Configurations in this group")

    class Config:
        model_config = {
            "from_attributes": True,
            "use_enum_values": True
        }


class ConfigurationGroupItemResponse(BaseModel):
    """Schema for configuration group item response."""
    id: str = Field(..., description="Unique identifier")
    group_id: str = Field(..., description="ID of the group")
    configuration_id: str = Field(..., description="ID of the configuration")
    created_by: str = Field(..., description="User who created the group item")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        model_config = {
            "from_attributes": True
        }


class ConfigurationFilter(BaseModel):
    """Schema for filtering configurations."""
    key: Optional[str] = Field(None, description="Filter by key (supports partial match)")
    environment: Optional[ConfigEnvironment] = Field(None, description="Filter by environment")
    category: Optional[ConfigCategory] = Field(None, description="Filter by category")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_encrypted: Optional[bool] = Field(None, description="Filter by encryption status")
    created_by: Optional[str] = Field(None, description="Filter by creator")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date (after)")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date (before)")
    updated_after: Optional[datetime] = Field(None, description="Filter by update date (after)")
    updated_before: Optional[datetime] = Field(None, description="Filter by update date (before)")

    class Config:
        model_config = {
            "use_enum_values": True
        }


class ConfigurationSearchResponse(BaseModel):
    """Schema for configuration search results."""
    total: int = Field(..., description="Total number of results")
    items: List[ConfigurationResponse] = Field(..., description="List of configurations")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of results per page")
    query: str = Field(..., description="Search query")


class ConfigurationStatisticsResponse(BaseModel):
    """Schema for configuration statistics."""
    total_configurations: int = Field(..., description="Total number of configurations")
    active_configurations: int = Field(..., description="Number of active configurations")
    by_environment: Dict[str, int] = Field(..., description="Count of configurations by environment")
    by_category: Dict[str, int] = Field(..., description="Count of configurations by category")
    encrypted_count: int = Field(..., description="Count of encrypted configurations")
    last_updated: datetime = Field(..., description="Timestamp of last configuration update")
