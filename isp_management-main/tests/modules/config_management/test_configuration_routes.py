"""
Unit tests for the Configuration Management Module's API routes.

This module tests the functionality of the configuration API routes, which
provide RESTful endpoints for managing system configurations.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.config_management.routes.configuration_routes import configuration_router
from modules.config_management.models.configuration import (
    Configuration, ConfigurationHistory, ConfigEnvironment, ConfigCategory
)
from modules.config_management.services.configuration_service import ConfigurationService
from backend_core.auth import get_current_user


@pytest.fixture
def app():
    """Create a FastAPI app with the configuration router for testing."""
    app = FastAPI()
    app.include_router(configuration_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    # Setup dependency overrides
    def mock_get_db():
        yield None

    def mock_get_current_user():
        return {
            "id": "test_user", 
            "role": "admin",
            "permissions": ["admin", "configurations:read", "configurations:create", "configurations:update", "configurations:delete"]
        }

    # Mock require_permissions function that's called directly in routes
    def mock_require_permissions(user, required_permissions):
        # Just pass validation, as we're mocking a user with all permissions
        return None

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # Patch the require_permissions function in the module
    with patch("modules.config_management.routes.configuration_routes.require_permissions", mock_require_permissions):
        # For any database dependency that might be used
        from backend_core.database import get_session
        app.dependency_overrides[get_session] = mock_get_db
        
        yield TestClient(app)


@pytest.fixture
def configuration_service():
    """Create a mock ConfigurationService."""
    return MagicMock(spec=ConfigurationService)


@pytest.fixture
def sample_configurations():
    """Create sample configurations for testing."""
    return [
        Configuration(
            id="sys-config-1",
            key="system.max_connections",
            value=1000,
            description="Maximum number of concurrent connections allowed",
            environment=ConfigEnvironment.ALL,
            category=ConfigCategory.SYSTEM,
            is_encrypted=False,
            version=1,
            is_active=True,
            created_by="admin",
            created_at=datetime.now(),
            updated_by=None,
            updated_at=None,
            elasticsearch_synced=False,
            validation_schema=None
        ),
        Configuration(
            id="prod-config-1",
            key="system.debug_mode",
            value=False,
            description="Enable debug mode",
            environment=ConfigEnvironment.PRODUCTION,
            category=ConfigCategory.SYSTEM,
            is_encrypted=False,
            version=1,
            is_active=True,
            created_by="admin",
            created_at=datetime.now(),
            updated_by=None,
            updated_at=None,
            elasticsearch_synced=False,
            validation_schema=None
        )
    ]


class TestConfigurationRoutes:
    """Tests for the configuration API routes."""

    def test_get_configurations(self, client, configuration_service, sample_configurations):
        """Test getting all configurations."""
        # Mock the ConfigurationService.get_configurations method
        configuration_service.get_configurations.return_value = sample_configurations
        
        # Make the request
        with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
            response = client.get("/api/v1/configurations/")

        # Verify the response
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["key"] == "system.max_connections"
        assert response.json()[1]["key"] == "system.debug_mode"

    def test_get_configuration(self, client, configuration_service, sample_configurations):
        """Test getting a specific configuration."""
        # Mock the ConfigurationService.get_configuration method
        def side_effect(key, environment=None):
            for config in sample_configurations:
                if config.key == key:
                    if environment is None or config.environment == environment:
                        return config
            return None
        configuration_service.get_configuration.side_effect = side_effect
        
        # Make the request
        with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
            response = client.get("/api/v1/configurations/system.max_connections")

        # Verify the response
        assert response.status_code == 200
        assert response.json()["key"] == "system.max_connections"
        assert response.json()["value"] == 1000

    def test_create_configuration(self, client, configuration_service):
        """Test creating a new configuration."""
        # Mock the ConfigurationService.create_configuration method
        def side_effect(config_data, created_by):
            return Configuration(
                id="new-config-1",
                key=config_data["key"],
                value=config_data["value"],
                description=config_data.get("description", ""),
                environment=config_data.get("environment", ConfigEnvironment.ALL),
                category=config_data.get("category", ConfigCategory.SYSTEM),
                is_encrypted=config_data.get("is_encrypted", False),
                version=1,
                is_active=True,
                created_by=created_by,
                created_at=datetime.now(),
                updated_by=None,
                updated_at=None,
                elasticsearch_synced=False,
                validation_schema=None
            )
        configuration_service.create_configuration.side_effect = side_effect
        
        # Make the request
        with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
            response = client.post(
                "/api/v1/configurations/",
                json={
                    "key": "new.test.config",
                    "value": "test value",
                    "description": "Test configuration",
                    "environment": "development",
                    "category": "custom"
                }
            )

        # Verify the response
        assert response.status_code == 201
        assert response.json()["key"] == "new.test.config"
        assert response.json()["value"] == "test value"
        assert response.json()["created_by"] == "test_user"

    def test_update_configuration(self, client, configuration_service, sample_configurations):
        """Test updating an existing configuration."""
        # Mock the ConfigurationService.update_configuration method
        def side_effect(key, config_data, updated_by, environment=None):
            for config in sample_configurations:
                if config.key == key:
                    if environment is None or config.environment == environment:
                        # Update the configuration with the passed data
                        for k, v in config_data.items():
                            if v is not None:
                                setattr(config, k, v)
                        config.updated_by = updated_by
                        config.updated_at = datetime.now()
                        config.version += 1
                        return config
            return None
        configuration_service.update_configuration.side_effect = side_effect
        
        # Create a mock for the entire schema validation process
        mock_config_update = MagicMock()
        mock_config_update.model_dump.return_value = {
            "value": 2000,
            "description": "Updated description"
        }
        
        # Patch the ConfigurationUpdate class and its instantiation
        with patch("modules.config_management.routes.configuration_routes.ConfigurationUpdate") as mock_config_class:
            mock_config_class.return_value = mock_config_update
            
            # Make the request
            with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
                response = client.put(
                    "/api/v1/configurations/system.max_connections",
                    json={
                        "value": 2000,
                        "description": "Updated description"
                    }
                )

        # Verify the response
        assert response.status_code == 200
        assert response.json()["key"] == "system.max_connections"
        assert response.json()["value"] == 2000
        assert response.json()["version"] == 2

    def test_delete_configuration(self, client, configuration_service):
        """Test deleting (deactivating) a configuration."""
        # Mock the ConfigurationService.delete_configuration method
        configuration_service.delete_configuration.return_value = None
        
        # Make the request
        with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
            response = client.delete("/api/v1/configurations/system.max_connections")

        # Verify the response
        assert response.status_code == 204
        assert response.content == b''  # No content for 204 response

    def test_get_configuration_history(self, client, configuration_service):
        """Test getting the history of a configuration."""
        # Mock the ConfigurationService.get_configuration_history method
        configuration_service.get_configuration_history.return_value = [
            ConfigurationHistory(
                id="history-1",
                configuration_id="sys-config-1",
                key="system.max_connections",
                value=500,
                environment=ConfigEnvironment.ALL,
                category=ConfigCategory.SYSTEM,
                is_encrypted=False,
                version=1,
                action="create",
                created_by="admin",
                created_at=datetime.now(),
                elasticsearch_synced=False
            ),
            ConfigurationHistory(
                id="history-2",
                configuration_id="sys-config-1",
                key="system.max_connections",
                value=1000,
                environment=ConfigEnvironment.ALL,
                category=ConfigCategory.SYSTEM,
                is_encrypted=False,
                version=2,
                action="update",
                created_by="admin",
                created_at=datetime.now(),
                elasticsearch_synced=False
            )
        ]
        
        # Make the request
        with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
            response = client.get("/api/v1/configurations/system.max_connections/history")

        # Verify the response
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["action"] == "create"
        assert response.json()[1]["action"] == "update"

    def test_bulk_update_configurations(self, client, configuration_service):
        """Test updating multiple configurations in a single request."""
        # Mock the ConfigurationService.bulk_update_configurations method
        def side_effect(configs_data, updated_by):
            return [
                Configuration(
                    id=f"config-{i}",
                    key=config["key"],
                    value=config["value"],
                    environment=ConfigEnvironment.ALL,
                    category=ConfigCategory.SYSTEM,
                    is_encrypted=False,
                    version=1,
                    is_active=True,
                    created_by=updated_by,
                    created_at=datetime.now(),
                    updated_by=None,
                    updated_at=None,
                    elasticsearch_synced=False,
                    validation_schema=None
                )
                for i, config in enumerate(configs_data)
            ]
        configuration_service.bulk_update_configurations.side_effect = side_effect
        
        # Make the request
        with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
            response = client.post(
                "/api/v1/configurations/bulk",
                json={
                    "configurations": [
                        {
                            "key": "system.max_connections",
                            "value": 5000
                        },
                        {
                            "key": "network.timeout",
                            "value": 60
                        },
                        {
                            "key": "new.bulk.config",
                            "value": "bulk value",
                            "description": "Created in bulk update",
                            "category": "custom"
                        }
                    ]
                }
            )

        # Verify the response
        assert response.status_code == 200
        assert len(response.json()) == 3
        assert response.json()[0]["key"] == "system.max_connections"
        assert response.json()[1]["key"] == "network.timeout"
        assert response.json()[2]["key"] == "new.bulk.config"

    def test_get_configuration_by_environment(self, client, configuration_service, sample_configurations):
        """Test getting a configuration for a specific environment."""
        # Mock the ConfigurationService.get_configuration method
        def side_effect(key, environment=None):
            for config in sample_configurations:
                if config.key == key:
                    if environment is None or config.environment == environment:
                        return config
            return None
        configuration_service.get_configuration.side_effect = side_effect
        
        # Make the request
        with patch("modules.config_management.routes.configuration_routes.ConfigurationService", return_value=configuration_service):
            response = client.get("/api/v1/configurations/system.debug_mode?environment=production")

        # Verify the response
        assert response.status_code == 200
        assert response.json()["key"] == "system.debug_mode"
        assert response.json()["environment"] == "production"
        assert response.json()["value"] is False
