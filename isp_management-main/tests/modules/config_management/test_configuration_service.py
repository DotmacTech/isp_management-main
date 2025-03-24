"""
Unit tests for the Configuration Management Module's configuration service.

This module tests the functionality of the ConfigurationService class, which
is responsible for managing system configurations.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from modules.config_management.models.configuration import (
    Configuration, ConfigurationHistory, ConfigEnvironment, ConfigCategory
)
from modules.config_management.services.configuration_service import ConfigurationService


class TestConfigurationService:
    """Tests for the ConfigurationService class."""
    
    def test_get_configuration(self, configuration_service, sample_configurations):
        """Test getting a configuration by key."""
        # Get existing configuration
        config = configuration_service.get_configuration("system.max_connections")
        assert config is not None
        assert config.key == "system.max_connections"
        assert config.value == 1000
        
        # Get non-existent configuration
        config = configuration_service.get_configuration("non.existent.key")
        assert config is None
        
        # Get environment-specific configuration
        config = configuration_service.get_configuration("system.debug_mode", ConfigEnvironment.DEVELOPMENT)
        assert config is not None
        assert config.environment == ConfigEnvironment.DEVELOPMENT
        assert config.value is True
        
        # Get environment-specific configuration for a different environment
        config = configuration_service.get_configuration("system.debug_mode", ConfigEnvironment.PRODUCTION)
        assert config is not None
        assert config.environment == ConfigEnvironment.PRODUCTION
        assert config.value is False
    
    def test_get_configuration_value(self, configuration_service, sample_configurations):
        """Test getting a configuration value by key."""
        # Get existing configuration value
        value = configuration_service.get_configuration_value("system.max_connections")
        assert value == 1000
        
        # Get non-existent configuration value with default
        value = configuration_service.get_configuration_value("non.existent.key", default=42)
        assert value == 42
        
        # Get environment-specific configuration value
        value = configuration_service.get_configuration_value("system.debug_mode", ConfigEnvironment.DEVELOPMENT)
        assert value is True
    
    def test_get_configurations(self, configuration_service, sample_configurations):
        """Test getting configurations based on filters."""
        # Get all active configurations
        configs = configuration_service.get_configurations({"is_active": True})
        assert len(configs) == 6  # All except inactive_config
        
        # Filter by category
        configs = configuration_service.get_configurations({"category": ConfigCategory.SYSTEM})
        assert len(configs) == 3  # system_config, dev_config, prod_config (inactive_config is not active)
        
        # Filter by environment
        configs = configuration_service.get_configurations({"environment": ConfigEnvironment.DEVELOPMENT})
        assert len(configs) == 1  # dev_config
        
        # Filter by key (partial match)
        configs = configuration_service.get_configurations({"key": "system"})
        assert len(configs) == 3  # system_config, dev_config, prod_config (inactive_config is not active)
        
        # Filter by is_encrypted
        configs = configuration_service.get_configurations({"is_encrypted": True})
        assert len(configs) == 1  # api_key_config
    
    def test_create_configuration(self, configuration_service, db_session):
        """Test creating a new configuration."""
        # Create a new configuration
        config_data = {
            "key": "new.test.config",
            "value": "test value",
            "description": "Test configuration",
            "environment": ConfigEnvironment.ALL,
            "category": ConfigCategory.SYSTEM,
            "is_encrypted": False
        }
        
        config = configuration_service.create_configuration(config_data, "test_user")
        
        # Verify the configuration was created
        assert config.id is not None
        assert config.key == "new.test.config"
        assert config.value == "test value"
        assert config.created_by == "test_user"
        
        # Verify a history entry was created
        history = db_session.query(ConfigurationHistory).filter(
            ConfigurationHistory.configuration_id == config.id
        ).first()
        
        assert history is not None
        assert history.action == "create"
        assert history.key == config.key
        assert history.value == config.value
        
        # Try to create a duplicate configuration
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.create_configuration(config_data, "test_user")
        
        assert excinfo.value.status_code == 409  # Conflict
    
    def test_update_configuration(self, configuration_service, sample_configurations, db_session):
        """Test updating an existing configuration."""
        # Update an existing configuration
        config_data = {
            "value": 2000,
            "description": "Updated description"
        }
        
        config = configuration_service.update_configuration(
            "system.max_connections", config_data, "test_user"
        )
        
        # Verify the configuration was updated
        assert config.value == 2000
        assert config.description == "Updated description"
        assert config.updated_by == "test_user"
        assert config.version == 2  # Version incremented
        
        # Verify a history entry was created
        history = db_session.query(ConfigurationHistory).filter(
            ConfigurationHistory.configuration_id == config.id,
            ConfigurationHistory.version == 2
        ).first()
        
        assert history is not None
        assert history.action == "update"
        assert history.value == 2000
        
        # Try to update a non-existent configuration
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.update_configuration(
                "non.existent.key", {"value": "test"}, "test_user"
            )
        
        assert excinfo.value.status_code == 404  # Not Found
    
    def test_delete_configuration(self, configuration_service, sample_configurations, db_session):
        """Test deleting (deactivating) a configuration."""
        # Delete an existing configuration
        result = configuration_service.delete_configuration(
            "system.max_connections", "test_user"
        )
        
        assert result is True
        
        # Verify the configuration was deactivated
        config = db_session.query(Configuration).filter(
            Configuration.key == "system.max_connections"
        ).first()
        
        assert config is not None
        assert config.is_active is False
        assert config.updated_by == "test_user"
        
        # Verify a history entry was created
        history = db_session.query(ConfigurationHistory).filter(
            ConfigurationHistory.configuration_id == config.id,
            ConfigurationHistory.action == "delete"
        ).first()
        
        assert history is not None
        
        # Try to delete a non-existent configuration
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.delete_configuration(
                "non.existent.key", "test_user"
            )
        
        assert excinfo.value.status_code == 404  # Not Found
    
    def test_get_configuration_history(self, configuration_service, sample_configurations):
        """Test getting the history of a configuration."""
        # Get history of a configuration with history
        history = configuration_service.get_configuration_history("system.legacy_mode")
        
        assert len(history) == 1
        assert history[0].action == "create"
        assert history[0].value is True  # Previous value
        
        # Try to get history of a non-existent configuration
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.get_configuration_history("non.existent.key")
        
        assert excinfo.value.status_code == 404  # Not Found
    
    def test_bulk_update_configurations(self, configuration_service, sample_configurations, db_session):
        """Test updating multiple configurations in a single transaction."""
        # Update multiple configurations
        configs_data = [
            {
                "key": "system.max_connections",
                "value": 5000
            },
            {
                "key": "network.timeout",
                "value": 60
            },
            {
                "key": "new.bulk.config",  # New configuration
                "value": "bulk value",
                "description": "Created in bulk update",
                "category": ConfigCategory.CUSTOM
            }
        ]
        
        updated_configs = configuration_service.bulk_update_configurations(
            configs_data, "test_user"
        )
        
        assert len(updated_configs) == 3
        
        # Verify the configurations were updated
        system_config = next(c for c in updated_configs if c.key == "system.max_connections")
        assert system_config.value == 5000
        assert system_config.version == 2  # Version incremented
        
        network_config = next(c for c in updated_configs if c.key == "network.timeout")
        assert network_config.value == 60
        assert network_config.version == 2  # Version incremented
        
        new_config = next(c for c in updated_configs if c.key == "new.bulk.config")
        assert new_config.value == "bulk value"
        assert new_config.category == ConfigCategory.CUSTOM
        assert new_config.version == 1  # New configuration
        
        # Verify history entries were created
        history_count = db_session.query(ConfigurationHistory).filter(
            ConfigurationHistory.key.in_(["system.max_connections", "network.timeout", "new.bulk.config"])
        ).count()
        
        assert history_count == 3
    
    def test_encrypted_configuration(self, configuration_service, encryption_service, db_session):
        """Test handling of encrypted configurations."""
        # Create an encrypted configuration
        config_data = {
            "key": "encrypted.test.config",
            "value": "secret value",
            "description": "Encrypted test configuration",
            "environment": ConfigEnvironment.ALL,
            "category": ConfigCategory.SECURITY,
            "is_encrypted": True
        }
        
        with patch.object(encryption_service, 'encrypt', return_value="encrypted:secret value"):
            config = configuration_service.create_configuration(config_data, "test_user")
        
        # Verify the value was encrypted
        assert config.value == "encrypted:secret value"
        assert config.is_encrypted is True
        
        # Get the configuration with decryption
        with patch.object(encryption_service, 'decrypt', return_value="secret value"):
            retrieved_config = configuration_service.get_configuration("encrypted.test.config")
            assert retrieved_config.value == "secret value"  # Decrypted value
    
    def test_configuration_validation(self, configuration_service):
        """Test validation of configuration values against schemas."""
        # Create a configuration with a validation schema
        config_data = {
            "key": "validated.test.config",
            "value": 42,
            "description": "Configuration with validation",
            "environment": ConfigEnvironment.ALL,
            "category": ConfigCategory.SYSTEM,
            "validation_schema": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100
            }
        }
        
        # Valid value
        config = configuration_service.create_configuration(config_data, "test_user")
        assert config.value == 42
        
        # Invalid value (exceeds maximum)
        config_data["value"] = 101
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.create_configuration(
                {**config_data, "key": "validated.test.config2"}, "test_user"
            )
        
        assert excinfo.value.status_code == 400  # Bad Request
        assert "does not match validation schema" in excinfo.value.detail
        
        # Invalid value (wrong type)
        config_data["value"] = "not an integer"
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.create_configuration(
                {**config_data, "key": "validated.test.config3"}, "test_user"
            )
        
        assert excinfo.value.status_code == 400  # Bad Request
        assert "does not match validation schema" in excinfo.value.detail
