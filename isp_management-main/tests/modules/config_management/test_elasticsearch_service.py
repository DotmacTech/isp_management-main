"""
Unit tests for the Configuration Management Module's Elasticsearch service.

This module contains tests for the ConfigurationElasticsearchService class,
which is responsible for indexing and searching configurations in Elasticsearch.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytest

from modules.config_management.services.elasticsearch_service import ConfigurationElasticsearchService
from modules.config_management.models.configuration import (
    Configuration, ConfigurationHistory, ConfigurationGroup, 
    ConfigEnvironment, ConfigCategory
)


class TestConfigurationElasticsearchService(unittest.TestCase):
    """Test cases for the ConfigurationElasticsearchService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_es_client = MagicMock()
        # Patch the create_indices_if_not_exist method to prevent it from being called in constructor
        with patch.object(ConfigurationElasticsearchService, 'create_indices_if_not_exist'):
            self.es_service = ConfigurationElasticsearchService(
                es_client=self.mock_es_client,
                index_prefix="test"
            )
        
        # Reset mock call counts after initialization
        self.mock_es_client.reset_mock()
        
        # Sample configuration for testing
        self.sample_config = Configuration(
            id="1",
            key="test.key",
            value={"setting": "value"},
            description="Test configuration",
            environment=ConfigEnvironment.DEVELOPMENT,
            category=ConfigCategory.SYSTEM,
            is_encrypted=False,
            validation_schema=None,
            version=1,
            is_active=True,
            created_by="test_user",
            created_at=datetime.now(timezone.utc),
            updated_by=None,
            updated_at=None
        )
        
        # Sample configuration history for testing
        self.sample_history = ConfigurationHistory(
            id="1",
            configuration_id="1",
            key="test.key",
            value={"setting": "value"},
            environment=ConfigEnvironment.DEVELOPMENT,
            category=ConfigCategory.SYSTEM,
            is_encrypted=False,
            version=1,
            action="create",
            created_by="test_user",
            created_at=datetime.now(timezone.utc)
        )
        
        # Sample configuration group for testing
        self.sample_group = ConfigurationGroup(
            id="1",
            name="Test Group",
            description="Test configuration group",
            created_by="test_user",
            created_at=datetime.now(timezone.utc),
            updated_by=None,
            updated_at=None
        )

    def test_index_configuration(self):
        """Test indexing a configuration."""
        # Configure mock
        self.mock_es_client.index.return_value = {"_id": "1", "result": "created"}
        
        # Call the method
        result = self.es_service.index_configuration(self.sample_config)
        
        # Verify the result
        self.assertEqual(result["_id"], "1")
        self.assertEqual(result["result"], "created")
        
        # Verify the mock was called correctly
        self.mock_es_client.index.assert_called_once()
        args, kwargs = self.mock_es_client.index.call_args
        self.assertEqual(kwargs["index"], "test-configurations")
        self.assertEqual(kwargs["id"], "1")
        
        # Verify document contents
        doc = kwargs["document"]
        self.assertEqual(doc["key"], "test.key")
        self.assertEqual(doc["environment"], ConfigEnvironment.DEVELOPMENT)
        self.assertEqual(doc["is_active"], True)

    def test_index_configuration_history(self):
        """Test indexing a configuration history entry."""
        # Configure mock
        self.mock_es_client.index.return_value = {"_id": "1", "result": "created"}
        
        # Call the method
        result = self.es_service.index_configuration_history(self.sample_history)
        
        # Verify the result
        self.assertEqual(result["_id"], "1")
        self.assertEqual(result["result"], "created")
        
        # Verify the mock was called correctly
        self.mock_es_client.index.assert_called_once()
        args, kwargs = self.mock_es_client.index.call_args
        self.assertEqual(kwargs["index"], "test-configuration-history")
        self.assertEqual(kwargs["id"], "1")
        
        # Verify document contents
        doc = kwargs["document"]
        self.assertEqual(doc["key"], "test.key")
        self.assertEqual(doc["action"], "create")
        self.assertEqual(doc["configuration_id"], "1")

    def test_index_configuration_group(self):
        """Test indexing a configuration group."""
        # Configure mock
        self.mock_es_client.index.return_value = {"_id": "1", "result": "created"}
        
        # Call the method
        result = self.es_service.index_configuration_group(self.sample_group)
        
        # Verify the result
        self.assertEqual(result["_id"], "1")
        self.assertEqual(result["result"], "created")
        
        # Verify the mock was called correctly
        self.mock_es_client.index.assert_called_once()
        args, kwargs = self.mock_es_client.index.call_args
        self.assertEqual(kwargs["index"], "test-configuration-groups")
        self.assertEqual(kwargs["id"], "1")
        
        # Verify document contents
        doc = kwargs["document"]
        self.assertEqual(doc["name"], "Test Group")

    def test_search_configurations(self):
        """Test searching configurations."""
        # Configure mock
        mock_search_result = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "1",
                        "_score": 1.0,
                        "_source": {
                            "key": "test.key",
                            "value": {"setting": "value"},
                            "environment": ConfigEnvironment.DEVELOPMENT,
                            "category": ConfigCategory.SYSTEM,
                            "is_active": True,
                            "version": 1,
                            "created_by": "test_user",
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                ]
            }
        }
        self.mock_es_client.search.return_value = mock_search_result
        
        # Call the method
        results = self.es_service.search_configurations(
            query="test",
            filters={
                "environment": ConfigEnvironment.DEVELOPMENT,
                "category": ConfigCategory.SYSTEM,
                "is_active": True
            }
        )
        
        # Verify the results
        self.assertEqual(results["total"], 1)
        self.assertEqual(len(results["results"]), 1)
        self.assertEqual(results["results"][0]["key"], "test.key")
        self.assertEqual(results["results"][0]["environment"], ConfigEnvironment.DEVELOPMENT)
        
        # Verify the mock was called correctly
        self.mock_es_client.search.assert_called_once()
        args, kwargs = self.mock_es_client.search.call_args
        self.assertEqual(kwargs["index"], "test-configurations")
        
        # Verify query
        query = kwargs["body"]["query"]
        self.assertIn("bool", query)
        self.assertIn("must", query["bool"])
        self.assertIn("filter", query["bool"])

    def test_get_configuration_statistics(self):
        """Test getting configuration statistics."""
        # Configure mock for the count API
        self.mock_es_client.count.return_value = {"count": 100}
        
        # Configure mock for the search API (for aggregations)
        mock_aggs_result = {
            "aggregations": {
                "by_environment": {
                    "buckets": [
                        {"key": ConfigEnvironment.DEVELOPMENT, "doc_count": 30},
                        {"key": ConfigEnvironment.PRODUCTION, "doc_count": 40},
                        {"key": ConfigEnvironment.ALL, "doc_count": 30}
                    ]
                },
                "by_category": {
                    "buckets": [
                        {"key": ConfigCategory.SYSTEM, "doc_count": 50},
                        {"key": ConfigCategory.NETWORK, "doc_count": 30},
                        {"key": ConfigCategory.BILLING, "doc_count": 20}
                    ]
                },
                "by_active": {
                    "buckets": [
                        {"key": 1, "doc_count": 80},
                        {"key": 0, "doc_count": 20}
                    ]
                },
                "by_encrypted": {
                    "buckets": [
                        {"key": 1, "doc_count": 40},
                        {"key": 0, "doc_count": 60}
                    ]
                }
            }
        }
        self.mock_es_client.search.return_value = mock_aggs_result
        
        # Call the method
        stats = self.es_service.get_configuration_statistics()
        
        # Verify the results
        self.assertEqual(stats["total_count"], 100)
        self.assertEqual(stats["active_count"], 80)
        self.assertEqual(stats["inactive_count"], 20)
        self.assertEqual(stats["encrypted_count"], 40)
        self.assertEqual(stats["by_environment"][ConfigEnvironment.DEVELOPMENT], 30)
        self.assertEqual(stats["by_environment"][ConfigEnvironment.PRODUCTION], 40)
        self.assertEqual(stats["by_category"][ConfigCategory.SYSTEM], 50)
        self.assertEqual(stats["by_category"][ConfigCategory.NETWORK], 30)
        
        # Verify the mocks were called correctly
        self.mock_es_client.count.assert_called_once()
        self.mock_es_client.search.assert_called_once()

    def test_bulk_index_configurations(self):
        """Test bulk indexing configurations."""
        # Configure mock
        self.mock_es_client.bulk.return_value = {
            "items": [{"index": {"_id": "1", "status": 201}}],
            "errors": False
        }
        
        # Call the method with a list of configurations
        count = self.es_service.bulk_index_configurations([self.sample_config])
        
        # Verify the result
        self.assertEqual(count, 1)
        
        # Verify the mock was called correctly
        self.mock_es_client.bulk.assert_called_once()
        args, kwargs = self.mock_es_client.bulk.call_args
        self.assertEqual(kwargs["index"], "test-configurations")
        
        # Verify actions
        actions = kwargs["operations"]
        self.assertEqual(len(actions), 2)  # 2 operations per document (action + source)
        self.assertEqual(actions[0], {"index": {"_id": "1"}})

    def test_bulk_index_configuration_history(self):
        """Test bulk indexing configuration history."""
        # Configure mock
        self.mock_es_client.bulk.return_value = {
            "items": [{"index": {"_id": "1", "status": 201}}],
            "errors": False
        }
        
        # Call the method with a list of history items
        count = self.es_service.bulk_index_configuration_history([self.sample_history])
        
        # Verify the result
        self.assertEqual(count, 1)
        
        # Verify the mock was called correctly
        self.mock_es_client.bulk.assert_called_once()
        args, kwargs = self.mock_es_client.bulk.call_args
        self.assertEqual(kwargs["index"], "test-configuration-history")

    def test_bulk_index_configuration_groups(self):
        """Test bulk indexing configuration groups."""
        # Configure mock
        self.mock_es_client.bulk.return_value = {
            "items": [{"index": {"_id": "1", "status": 201}}],
            "errors": False
        }
        
        # Call the method with a list of groups
        count = self.es_service.bulk_index_configuration_groups([self.sample_group])
        
        # Verify the result
        self.assertEqual(count, 1)
        
        # Verify the mock was called correctly
        self.mock_es_client.bulk.assert_called_once()
        args, kwargs = self.mock_es_client.bulk.call_args
        self.assertEqual(kwargs["index"], "test-configuration-groups")

    def test_create_indices(self):
        """Test creating indices if they don't exist."""
        # Configure mock
        self.mock_es_client.indices.exists.return_value = False
        self.mock_es_client.indices.create.return_value = {"acknowledged": True}
        
        # Call the method
        self.es_service.create_indices_if_not_exist()
        
        # Verify the mocks were called correctly
        self.assertEqual(self.mock_es_client.indices.exists.call_count, 3)
        self.assertEqual(self.mock_es_client.indices.create.call_count, 3)

    def test_dont_create_indices_if_exist(self):
        """Test not creating indices if they already exist."""
        # Configure mock
        self.mock_es_client.indices.exists.return_value = True
        
        # Call the method
        self.es_service.create_indices_if_not_exist()
        
        # Verify the mocks were called correctly
        self.assertEqual(self.mock_es_client.indices.exists.call_count, 3)
        self.mock_es_client.indices.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
