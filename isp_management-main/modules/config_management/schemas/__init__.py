"""
Schemas for the Configuration Management Module.

This module imports all schemas for the configuration management module to make them
available through a single import statement.
"""

from modules.config_management.schemas.configuration import (
    ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse,
    ConfigurationHistoryResponse, ConfigurationGroupCreate, ConfigurationGroupUpdate,
    ConfigurationGroupResponse, ConfigurationBulkUpdate, ConfigurationFilter
)

__all__ = [
    'ConfigurationCreate',
    'ConfigurationUpdate',
    'ConfigurationResponse',
    'ConfigurationHistoryResponse',
    'ConfigurationGroupCreate',
    'ConfigurationGroupUpdate',
    'ConfigurationGroupResponse',
    'ConfigurationBulkUpdate',
    'ConfigurationFilter'
]
