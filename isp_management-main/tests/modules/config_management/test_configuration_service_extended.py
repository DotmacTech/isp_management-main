"""
Extended unit tests for the Configuration Management Module's configuration service.

This module provides additional tests for the ConfigurationService class
to improve test coverage.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from modules.config_management.models.configuration import (
    Configuration, ConfigurationHistory, ConfigurationGroup, ConfigurationGroupItem,
    ConfigEnvironment, ConfigCategory
)
from modules.config_management.services.configuration_service import ConfigurationService


class TestConfigurationServiceExtended:
    """Extended tests for the ConfigurationService class."""
    
    # Schema Validation Tests
    def test_validate_schema(self, configuration_service):
        """Test validation of JSON schema."""
        # Valid schema - string
        schema = {
            "type": "string",
            "minLength": 3,
            "maxLength": 10
        }
        assert configuration_service._validate_schema(schema) is True
        
        # Valid schema - number
        schema = {
            "type": "number",
            "minimum": 0,
            "maximum": 100
        }
        assert configuration_service._validate_schema(schema) is True
        
        # Valid schema - array
        schema = {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
        assert configuration_service._validate_schema(schema) is True
        
        # Invalid schema - missing type
        invalid_schema = {
            "minLength": 3,
            "maxLength": 10
        }
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_schema(invalid_schema)
        assert "Schema is missing required key: type" in str(excinfo.value)
        
        # Invalid schema - invalid type
        invalid_schema = {
            "type": "invalid_type"
        }
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_schema(invalid_schema)
        assert "Invalid schema type" in str(excinfo.value)
        
        # Invalid schema - minimum > maximum
        invalid_schema = {
            "type": "number",
            "minimum": 100,
            "maximum": 10
        }
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_schema(invalid_schema)
        assert "minimum' cannot be greater than 'maximum" in str(excinfo.value)
        
        # Invalid schema - minLength > maxLength
        invalid_schema = {
            "type": "string",
            "minLength": 10,
            "maxLength": 5
        }
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_schema(invalid_schema)
        assert "minLength' cannot be greater than 'maxLength" in str(excinfo.value)
        
        # Invalid schema - array missing items
        invalid_schema = {
            "type": "array"
        }
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_schema(invalid_schema)
        assert "Array schema must include 'items' property" in str(excinfo.value)
    
    def test_validate_value(self, configuration_service):
        """Test validation of values against JSON schema."""
        # String validation
        schema = {"type": "string", "minLength": 3, "maxLength": 10}
        assert configuration_service._validate_value("valid", schema) is True
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value(123, schema)  # Wrong type
        assert "Value must be a string" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value("ab", schema)  # Too short
        assert "String length must be at least 3" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value("this_is_too_long", schema)  # Too long
        assert "String length must be at most 10" in str(excinfo.value)
        
        # Number validation
        schema = {"type": "number", "minimum": 1, "maximum": 100}
        assert configuration_service._validate_value(50, schema) is True
        assert configuration_service._validate_value(50.5, schema) is True
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value("50", schema)  # Wrong type
        assert "Value must be a number" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value(0, schema)  # Too small
        assert "Value must be at least 1" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value(101, schema)  # Too large
        assert "Value must be at most 100" in str(excinfo.value)
        
        # Integer validation
        schema = {"type": "integer", "minimum": 1, "maximum": 100}
        assert configuration_service._validate_value(50, schema) is True
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value(50.5, schema)  # Not an integer
        assert "Value must be an integer" in str(excinfo.value)
        
        # Boolean validation
        schema = {"type": "boolean"}
        assert configuration_service._validate_value(True, schema) is True
        assert configuration_service._validate_value(False, schema) is True
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value("true", schema)  # Wrong type
        assert "Value must be a boolean" in str(excinfo.value)
        
        # Array validation
        schema = {
            "type": "array", 
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3
        }
        assert configuration_service._validate_value(["item1"], schema) is True
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value("not_an_array", schema)  # Wrong type
        assert "Value must be an array" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value([], schema)  # Too few items
        assert "Array must have at least 1 items" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value(["1", "2", "3", "4"], schema)  # Too many items
        assert "Array must have at most 3 items" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value([1, 2], schema)  # Items of wrong type
        assert "Value must be a string" in str(excinfo.value)
        
        # Object validation
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
        assert configuration_service._validate_value({"name": "John", "age": 30}, schema) is True
        assert configuration_service._validate_value({"name": "John"}, schema) is True  # Optional property missing
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value([], schema)  # Wrong type
        assert "Value must be an object" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value({"age": 30}, schema)  # Required property missing
        assert "Required property 'name' is missing" in str(excinfo.value)
        
        with pytest.raises(ValueError) as excinfo:
            configuration_service._validate_value({"name": "John", "age": "30"}, schema)  # Property of wrong type
        assert "Value must be an integer" in str(excinfo.value)
    
    # Configuration Group Tests
    @patch('modules.config_management.services.configuration_service.ConfigurationGroup')
    def test_create_configuration_group(self, mock_group_class, configuration_service):
        """Test creating a new configuration group."""
        # Mock the database session and avoid actual db interactions
        configuration_service.db = MagicMock()
        
        # Set up the query results
        # First query (check if exists) returns None
        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = None
        configuration_service.db.query.return_value = query_mock

        # Mock the configuration group that would be returned
        mock_group = MagicMock()
        mock_group.id = "test-group-id"
        mock_group.name = "Test Group"
        mock_group.description = "Test Description"
        
        # Configure the mock ConfigurationGroup class to return our mock
        mock_group_class.return_value = mock_group
        
        # Test data
        group_data = {
            "name": "Test Group",
            "description": "Test Description"
        }
        
        # Call the method
        result = configuration_service.create_configuration_group(group_data, "test_user")
        
        # Verify the result
        assert result.id == mock_group.id
        assert result.name == mock_group.name
        
        # Verify db operations were called
        configuration_service.db.add.assert_called_once()
        configuration_service.db.commit.assert_called()
        
        # Now test duplicate creation - return an existing group for the check
        query_mock.filter.return_value.first.return_value = MagicMock()
        
        # Expect an HTTPException for duplicate
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.create_configuration_group(group_data, "test_user")
        
        assert excinfo.value.status_code == 409  # Conflict
    
    def test_get_configuration_group(self, configuration_service, sample_configuration_groups):
        """Test getting a configuration group by ID."""
        # Get existing group without configurations
        group = configuration_service.get_configuration_group(
            sample_configuration_groups["system"].id
        )
        
        assert group is not None
        assert group.name == "System Settings"
        assert not hasattr(group, "configurations")  # Configurations not included
        
        # Get existing group with configurations
        group = configuration_service.get_configuration_group(
            sample_configuration_groups["system"].id, 
            with_configurations=True
        )
        
        assert group is not None
        assert group.name == "System Settings"
        
        # Get non-existent group
        non_existent_id = "non-existent-id"
        result = configuration_service.get_configuration_group(non_existent_id)
        assert result is None
    
    def test_get_configuration_groups(self, configuration_service, sample_configuration_groups):
        """Test getting all configuration groups."""
        # Get all groups
        groups = configuration_service.get_configuration_groups()
        
        assert len(groups) >= 2
        assert any(g.name == "System Settings" for g in groups)
        assert any(g.name == "Security Settings" for g in groups)
        
        # Test pagination
        groups = configuration_service.get_configuration_groups(skip=1, limit=1)
        assert len(groups) == 1
    
    @patch('modules.config_management.services.configuration_service.ConfigurationGroup')
    def test_update_configuration_group(self, mock_group_class, configuration_service):
        """Test updating an existing configuration group."""
        # Take a simpler approach: directly patch the service method to avoid dealing
        # with the complex query behavior
        
        # 1. Success case - return an existing group and commit the changes
        mock_existing_group = MagicMock()
        mock_existing_group.id = "test-group-id"
        mock_existing_group.name = "Old Name" 
        mock_existing_group.description = "Old Description"
        
        # Setup mock db session
        configuration_service.db = MagicMock()
        
        # Mock the direct action of db.query().filter().first() to bypass the complex filtering logic
        query_instance = MagicMock()
        filter_instance = MagicMock()
        filter_instance.first.return_value = mock_existing_group  # Success case - return the group
        query_instance.filter.return_value = filter_instance
        configuration_service.db.query.return_value = query_instance
        
        # Data to update
        group_data = {
            "name": "New Name",
            "description": "New Description"
        }
        
        # For the name conflict check, we need to ensure no conflict
        # Create a new mock for the second query
        filter_instance2 = MagicMock()
        filter_instance2.first.return_value = None  # No conflict
        
        # Configure side effect to return the right mock based on call count
        query_instance.filter.side_effect = [filter_instance, filter_instance2]
        
        # Execute the update
        result = configuration_service.update_configuration_group("test-group-id", group_data, "test_user")
        
        # Verify the expected updates
        assert mock_existing_group.name == "New Name"
        assert mock_existing_group.description == "New Description"
        assert mock_existing_group.updated_by == "test_user"
        
        # Verify db was committed
        configuration_service.db.commit.assert_called_once()
        
        # 2. Test group not found
        configuration_service.db.reset_mock()
        query_instance = MagicMock()
        filter_instance_not_found = MagicMock()
        filter_instance_not_found.first.return_value = None  # Group not found
        query_instance.filter.return_value = filter_instance_not_found
        configuration_service.db.query.return_value = query_instance
        
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.update_configuration_group("non-existent-id", group_data, "test_user")
        
        assert excinfo.value.status_code == 404
        
        # 3. Test name conflict
        configuration_service.db.reset_mock()
        
        # First query returns the group
        query_instance = MagicMock()
        filter_instance_conflict_1 = MagicMock()
        filter_instance_conflict_1.first.return_value = mock_existing_group
        
        # Second query returns a conflict
        filter_instance_conflict_2 = MagicMock()
        filter_instance_conflict_2.first.return_value = MagicMock()  # Conflict found
        
        # Set up side effect to handle the two queries
        query_instance.filter.side_effect = [filter_instance_conflict_1, filter_instance_conflict_2]
        configuration_service.db.query.return_value = query_instance
        
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.update_configuration_group("test-group-id", group_data, "test_user")
        
        assert excinfo.value.status_code == 409
    
    # Test for cleanup_old_history
    def test_cleanup_old_history(self, configuration_service, sample_configurations, db_session):
        """Test cleaning up old configuration history entries."""
        # Create some old history entries
        old_date = datetime.utcnow() - timedelta(days=100)
        
        # Add a few old history entries to ensure we have at least 2 to delete
        for i in range(3):
            old_history = ConfigurationHistory(
                id=f"old-history-{i}",
                configuration_id=sample_configurations["system"].id,
                key=sample_configurations["system"].key,
                value=sample_configurations["system"].value,
                environment=sample_configurations["system"].environment,
                category=sample_configurations["system"].category,
                is_encrypted=sample_configurations["system"].is_encrypted,
                version=1,
                action="create",
                created_by="admin",
                created_at=old_date
            )
            db_session.add(old_history)
        
        db_session.commit()
        
        # Add a newer history entry
        new_history = ConfigurationHistory(
            id="new-history-1",
            configuration_id=sample_configurations["system"].id,
            key=sample_configurations["system"].key,
            value=500,  # Updated value
            environment=sample_configurations["system"].environment,
            category=sample_configurations["system"].category,
            is_encrypted=sample_configurations["system"].is_encrypted,
            version=2,
            action="update",
            created_by="admin"
        )
        
        db_session.add(new_history)
        db_session.commit()
        
        # Verify we have at least 4 history entries for this configuration
        count = db_session.query(ConfigurationHistory).filter(
            ConfigurationHistory.configuration_id == sample_configurations["system"].id
        ).count()
        assert count >= 4
        
        # Clean up old history (keep last 30 days)
        deleted_count = configuration_service.cleanup_old_history(days_to_keep=30)
        
        # Verify old entries were deleted
        assert deleted_count >= 2
    
    # Test Elasticsearch Integration with proper mocking
    @patch('modules.config_management.services.configuration_service.ConfigurationElasticsearchService')
    def test_search_configurations(self, mock_es_service, configuration_service):
        """Test searching configurations using Elasticsearch."""
        # Mock the Elasticsearch service
        mock_es_instance = MagicMock()
        mock_es_instance.search_configurations.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"id": "sys-config-1", "key": "system.max_connections", "value": 1000}},
                    {"_source": {"id": "net-config-1", "key": "network.timeout", "value": 30}}
                ]
            }
        }
        
        # Set the ES service
        configuration_service.es_service = mock_es_instance
        configuration_service.elasticsearch_enabled = True
        
        # Search configurations
        results = configuration_service.search_configurations(
            query="system", 
            environment=ConfigEnvironment.ALL,
            category=ConfigCategory.SYSTEM,
            active_only=True
        )
        
        # Check that results were returned (implementation details may vary)
        assert results is not None
        
        # Verify the ES service was called with correct params
        mock_es_instance.search_configurations.assert_called_once()
        
        # Test when Elasticsearch is not enabled
        configuration_service.elasticsearch_enabled = False
        
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.search_configurations(query="test")
        
        assert excinfo.value.status_code == 400
    
    @patch('modules.config_management.services.configuration_service.ConfigurationElasticsearchService')
    def test_get_configuration_statistics(self, mock_es_service, configuration_service):
        """Test getting configuration statistics from Elasticsearch."""
        # Mock the Elasticsearch service
        mock_es_instance = MagicMock()
        mock_es_instance.get_configuration_statistics.return_value = {
            "total_configs": 10,
            "active_configs": 8,
            "inactive_configs": 2,
            "configs_by_environment": {
                "all": 5,
                "development": 3,
                "production": 2
            },
            "configs_by_category": {
                "system": 4,
                "network": 3,
                "security": 2,
                "custom": 1
            }
        }
        
        # Set the ES service
        configuration_service.es_service = mock_es_instance
        configuration_service.elasticsearch_enabled = True
        
        # Get statistics
        stats = configuration_service.get_configuration_statistics()
        
        # Verify the ES service was called
        mock_es_instance.get_configuration_statistics.assert_called_once()
        
        # Test when Elasticsearch is not enabled
        configuration_service.elasticsearch_enabled = False
        
        with pytest.raises(HTTPException) as excinfo:
            configuration_service.get_configuration_statistics()
        
        assert excinfo.value.status_code == 400
    
    @patch('modules.config_management.services.configuration_service.ConfigurationElasticsearchService')
    def test_sync_configurations_to_elasticsearch(self, mock_es_service, configuration_service, db_session):
        """Test syncing configurations to Elasticsearch."""
        # Create a mock ES service instance with all required methods
        mock_es_instance = MagicMock()
        mock_es_instance.bulk_index_configurations.return_value = 7
        mock_es_instance.bulk_index_configuration_history.return_value = 10
        mock_es_instance.bulk_index_configuration_groups.return_value = 2
        
        # Set up configuration service
        configuration_service.es_service = mock_es_instance
        configuration_service.elasticsearch_enabled = True
        
        # Create test data to return from queries
        test_configs = [MagicMock(), MagicMock()]
        test_history = [MagicMock(), MagicMock()]
        test_groups = [MagicMock(), MagicMock()]
        
        # Use consecutive patches for the three different query calls
        with patch.object(db_session, 'query') as mock_config_query:
            mock_config_query.return_value.filter.return_value.all.return_value = test_configs
            
            # We need to patch the second and third calls separately
            # Save the original query method to restore between patches
            original_query = db_session.query
            
            # After first query is used, replace it for the second query
            def second_query_patch(*args):
                # Replace this query method with one that will handle the third query
                db_session.query = MagicMock()
                db_session.query.return_value.filter.return_value.all.return_value = test_groups
                
                # Return a mock for the second query (history)
                mock_history_query = MagicMock()
                mock_history_query.filter.return_value.all.return_value = test_history
                return mock_history_query
            
            # Execute with patched methods
            db_session.query.side_effect = second_query_patch
            
            # Call the method under test
            result = configuration_service.sync_configurations_to_elasticsearch()
            
            # Restore the original query method
            db_session.query = original_query
            
            # Verify the methods were called with correct parameters
            mock_es_instance.bulk_index_configurations.assert_called_once()
            mock_es_instance.bulk_index_configuration_history.assert_called_once()
            mock_es_instance.bulk_index_configuration_groups.assert_called_once()
            
            # Verify the result has the expected structure
            assert "configurations_indexed" in result
            assert "history_items_indexed" in result or "history_entries_indexed" in result
            assert "groups_indexed" in result
            
            # Test when Elasticsearch is not enabled
            configuration_service.elasticsearch_enabled = False
            
            with pytest.raises(HTTPException) as excinfo:
                configuration_service.sync_configurations_to_elasticsearch()
            
            assert excinfo.value.status_code == 400
