"""
Test fixtures for the Configuration Management Module.

This module provides pytest fixtures for testing the configuration management module.
"""

import sys
import os
from pathlib import Path
import pytest
import json
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import uuid
from unittest.mock import MagicMock

from modules.config_management.models.configuration import (
    Base, Configuration, ConfigurationHistory, ConfigurationGroup, 
    ConfigurationGroupItem, ConfigEnvironment, ConfigCategory
)
from modules.config_management.services.encryption_service import EncryptionService
from modules.config_management.services.cache_service import CacheService
from modules.config_management.services.elasticsearch_service import ConfigurationElasticsearchService
from modules.config_management.services.configuration_service import ConfigurationService


@pytest.fixture(scope="session")
def engine():
    """Create a SQLite in-memory database engine for testing."""
    return create_engine("sqlite:///:memory:", echo=False)


@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(engine, tables):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    # Clear any existing data to ensure test isolation
    session.execute(text("DELETE FROM configuration_group_items"))
    session.execute(text("DELETE FROM configuration_history"))
    session.execute(text("DELETE FROM configurations"))
    session.execute(text("DELETE FROM configuration_groups"))
    session.commit()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def encryption_service():
    """Provide an encryption service for testing."""
    return EncryptionService(key="test_encryption_key_for_unit_tests_only")


@pytest.fixture
def cache_service():
    """Provide a cache service for testing."""
    return CacheService(default_ttl=60, cleanup_interval=3600)


@pytest.fixture
def configuration_service(db_session, encryption_service, cache_service):
    """Provide a configuration service for testing."""
    return ConfigurationService(db=db_session, 
                               encryption_service=encryption_service,
                               cache_service=cache_service)


@pytest.fixture
def sample_configurations(db_session):
    """Create sample configurations for testing."""
    # System configurations
    system_config = Configuration(
        id="sys-config-1",
        key="system.max_connections",
        value=1000,
        description="Maximum number of concurrent connections allowed",
        environment=ConfigEnvironment.ALL,
        category=ConfigCategory.SYSTEM,
        is_encrypted=False,
        validation_schema={"type": "integer", "minimum": 1, "maximum": 10000},
        version=1,
        is_active=True,
        created_by="admin"
    )
    
    # Security configurations
    security_config = Configuration(
        id="sec-config-1",
        key="security.password_policy",
        value={
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_number": True,
            "require_special": True,
            "max_age_days": 90
        },
        description="Password policy settings",
        environment=ConfigEnvironment.ALL,
        category=ConfigCategory.SECURITY,
        is_encrypted=False,
        validation_schema={
            "type": "object",
            "properties": {
                "min_length": {"type": "integer", "minimum": 6},
                "require_uppercase": {"type": "boolean"},
                "require_lowercase": {"type": "boolean"},
                "require_number": {"type": "boolean"},
                "require_special": {"type": "boolean"},
                "max_age_days": {"type": "integer", "minimum": 1}
            },
            "required": ["min_length"]
        },
        version=1,
        is_active=True,
        created_by="admin"
    )
    
    # Network configurations
    network_config = Configuration(
        id="net-config-1",
        key="network.timeout",
        value=30,
        description="Network timeout in seconds",
        environment=ConfigEnvironment.ALL,
        category=ConfigCategory.NETWORK,
        is_encrypted=False,
        validation_schema={"type": "integer", "minimum": 1, "maximum": 300},
        version=1,
        is_active=True,
        created_by="admin"
    )
    
    # Environment-specific configurations
    dev_config = Configuration(
        id="dev-config-1",
        key="system.debug_mode",
        value=True,
        description="Enable debug mode",
        environment=ConfigEnvironment.DEVELOPMENT,
        category=ConfigCategory.SYSTEM,
        is_encrypted=False,
        validation_schema={"type": "boolean"},
        version=1,
        is_active=True,
        created_by="admin"
    )
    
    prod_config = Configuration(
        id="prod-config-1",
        key="system.debug_mode",
        value=False,
        description="Enable debug mode",
        environment=ConfigEnvironment.PRODUCTION,
        category=ConfigCategory.SYSTEM,
        is_encrypted=False,
        validation_schema={"type": "boolean"},
        version=1,
        is_active=True,
        created_by="admin"
    )
    
    # Encrypted configuration
    api_key_config = Configuration(
        id="api-key-config-1",
        key="integration.api_key",
        value="encrypted:api_key_value",  # This would normally be encrypted
        description="API key for external integration",
        environment=ConfigEnvironment.ALL,
        category=ConfigCategory.INTEGRATION,
        is_encrypted=True,
        version=1,
        is_active=True,
        created_by="admin"
    )
    
    # Inactive configuration
    inactive_config = Configuration(
        id="inactive-config-1",
        key="system.legacy_mode",
        value=False,
        description="Enable legacy mode (deprecated)",
        environment=ConfigEnvironment.ALL,
        category=ConfigCategory.SYSTEM,
        is_encrypted=False,
        version=2,
        is_active=False,
        created_by="admin"
    )
    
    db_session.add_all([
        system_config, security_config, network_config, 
        dev_config, prod_config, api_key_config, inactive_config
    ])
    db_session.commit()
    
    # Create some history entries
    history_entry = ConfigurationHistory(
        id="hist-1",
        configuration_id=inactive_config.id,
        key=inactive_config.key,
        value=True,  # Previous value
        environment=inactive_config.environment,
        category=inactive_config.category,
        is_encrypted=inactive_config.is_encrypted,
        version=1,
        action="create",
        created_by="admin"
    )
    
    db_session.add(history_entry)
    db_session.commit()
    
    return {
        "system": system_config,
        "security": security_config,
        "network": network_config,
        "development": dev_config,
        "production": prod_config,
        "api_key": api_key_config,
        "inactive": inactive_config
    }


@pytest.fixture
def sample_configuration_groups(db_session, sample_configurations):
    """Create sample configuration groups for testing."""
    # System group
    system_group = ConfigurationGroup(
        id="group-1",
        name="System Settings",
        description="Core system settings",
        created_by="admin"
    )
    
    # Security group
    security_group = ConfigurationGroup(
        id="group-2",
        name="Security Settings",
        description="Security-related settings",
        created_by="admin"
    )
    
    db_session.add_all([system_group, security_group])
    db_session.commit()
    
    # Add configurations to groups
    system_items = [
        ConfigurationGroupItem(
            id="item-1",
            group_id=system_group.id,
            configuration_id=sample_configurations["system"].id
        ),
        ConfigurationGroupItem(
            id="item-2",
            group_id=system_group.id,
            configuration_id=sample_configurations["network"].id
        )
    ]
    
    security_items = [
        ConfigurationGroupItem(
            id="item-3",
            group_id=security_group.id,
            configuration_id=sample_configurations["security"].id
        ),
        ConfigurationGroupItem(
            id="item-4",
            group_id=security_group.id,
            configuration_id=sample_configurations["api_key"].id
        )
    ]
    
    db_session.add_all(system_items + security_items)
    db_session.commit()
    
    return {
        "system": system_group,
        "security": security_group
    }
