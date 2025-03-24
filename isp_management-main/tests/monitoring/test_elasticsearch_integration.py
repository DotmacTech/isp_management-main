"""
Tests for the Elasticsearch integration in the monitoring module.

This module contains tests for the Elasticsearch client and integration with
service availability monitoring, ensuring that logs and metrics are properly
indexed and synchronized with Elasticsearch.
"""

import unittest
from unittest import mock
import json
from datetime import datetime, timedelta
import uuid
from elasticsearch import Elasticsearch

from modules.monitoring.elasticsearch import ElasticsearchClient
from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, ServiceOutage,
    ProtocolType, StatusType, SeverityLevel,
    generate_uuid
)


class TestElasticsearchIntegration(unittest.TestCase):
    """Test cases for the Elasticsearch integration."""

    def setUp(self):
        """Set up test environment."""
        # Mock Elasticsearch client with all required methods/attributes
        self.mock_es = mock.MagicMock(spec=Elasticsearch)
        
        # Mock ping method to ensure connection test passes
        self.mock_es.ping = mock.MagicMock(return_value=True)
        
        # Mock indices methods
        self.mock_es.indices = mock.MagicMock()
        self.mock_es.indices.exists = mock.MagicMock(return_value=False)
        self.mock_es.indices.create = mock.MagicMock(return_value={"acknowledged": True})
        
        # Mock search method with expected return structure
        self.mock_es.search = mock.MagicMock(return_value={
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "status": "up",
                            "response_time": 0.345
                        }
                    }
                ]
            }
        })
        
        # Mock other methods
        self.mock_es.index = mock.MagicMock(return_value={"result": "created"})
        self.mock_es.bulk = mock.MagicMock(return_value={"errors": False})
        self.mock_es.update = mock.MagicMock(return_value={"result": "updated"})
        
        # Important: Patch the Elasticsearch class that's imported in the module being tested
        patcher = mock.patch('modules.monitoring.elasticsearch.Elasticsearch', return_value=self.mock_es)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Create client with patched Elasticsearch
        self.es_client = ElasticsearchClient()
            
        # Print debug info
        print(f"Client type: {type(self.es_client.client)}")
        print(f"Enabled: {self.es_client.enabled}")
        print(f"Is enabled: {self.es_client.is_enabled()}")
    
    def test_index_service_status(self):
        """Test indexing a service status to Elasticsearch."""
        # Create a mock service status
        endpoint_id = generate_uuid()
        status_id = generate_uuid()
        
        status = mock.MagicMock(spec=ServiceStatus)
        status.id = status_id
        status.endpoint_id = endpoint_id
        status.status = StatusType.UP
        status.response_time = 0.345
        status.status_message = "Service is up and running"
        status.timestamp = datetime.utcnow()
        status.elasticsearch_synced = False
        
        # Mock the endpoint relationship
        endpoint = mock.MagicMock(spec=ServiceEndpoint)
        endpoint.id = endpoint_id
        endpoint.name = "Test API"
        endpoint.url = "https://api.example.com"
        status.endpoint = endpoint
        
        # Mock the model_dump method
        status.model_dump.return_value = {
            "id": status_id,
            "endpoint_id": endpoint_id,
            "status": "up",
            "response_time": 0.345,
            "status_message": "Service is up and running",
            "timestamp": status.timestamp.isoformat(),
            "endpoint_name": "Test API",
            "endpoint_url": "https://api.example.com"
        }
        
        # Call the method
        result = self.es_client.index_service_status(status)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify Elasticsearch index was called
        self.mock_es.index.assert_called_once()
        
        # Check the index name and document
        args, kwargs = self.mock_es.index.call_args
        self.assertEqual(kwargs['index'], 'service-status')
        self.assertEqual(kwargs['id'], status_id)
        
        # Verify the document contains the expected data
        doc = kwargs['document']
        self.assertEqual(doc['id'], status_id)
        self.assertEqual(doc['status'], 'up')
        self.assertEqual(doc['response_time'], 0.345)
        self.assertEqual(doc['endpoint_name'], 'Test API')
    
    def test_index_service_outage(self):
        """Test indexing a service outage to Elasticsearch."""
        # Create a mock service outage
        endpoint_id = generate_uuid()
        outage_id = generate_uuid()
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow() - timedelta(hours=1)
        
        outage = mock.MagicMock(spec=ServiceOutage)
        outage.id = outage_id
        outage.endpoint_id = endpoint_id
        outage.start_time = start_time
        outage.end_time = end_time
        outage.duration = 3600  # 1 hour in seconds
        outage.severity = SeverityLevel.HIGH
        outage.affected_customers = 150
        outage.resolution_notes = "Fixed network connectivity issue"
        outage.elasticsearch_synced = False
        
        # Mock the endpoint relationship
        endpoint = mock.MagicMock(spec=ServiceEndpoint)
        endpoint.id = endpoint_id
        endpoint.name = "Test API"
        endpoint.url = "https://api.example.com"
        outage.endpoint = endpoint
        
        # Mock the model_dump method
        outage.model_dump.return_value = {
            "id": outage_id,
            "endpoint_id": endpoint_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": 3600,
            "severity": "high",
            "affected_customers": 150,
            "resolution_notes": "Fixed network connectivity issue",
            "endpoint_name": "Test API",
            "endpoint_url": "https://api.example.com"
        }
        
        # Call the method
        result = self.es_client.index_service_outage(outage)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify Elasticsearch index was called
        self.mock_es.index.assert_called_once()
        
        # Check the index name and document
        args, kwargs = self.mock_es.index.call_args
        self.assertEqual(kwargs['index'], 'service-outages')
        self.assertEqual(kwargs['id'], outage_id)
        
        # Verify the document contains the expected data
        doc = kwargs['document']
        self.assertEqual(doc['id'], outage_id)
        self.assertEqual(doc['severity'], 'high')
        self.assertEqual(doc['duration'], 3600)
        self.assertEqual(doc['affected_customers'], 150)
        self.assertEqual(doc['endpoint_name'], 'Test API')
    
    def test_update_service_outage(self):
        """Test updating a service outage in Elasticsearch."""
        # Create a mock service outage
        outage_id = generate_uuid()
        
        # Mock the model_dump method to return updated data
        updated_data = {
            "id": outage_id,
            "end_time": datetime.utcnow().isoformat(),
            "duration": 3600,
            "resolution_notes": "Fixed network connectivity issue"
        }
        
        # Call the method
        result = self.es_client.update_service_outage(outage_id, updated_data)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify Elasticsearch update was called
        self.mock_es.update.assert_called_once()
        
        # Check the index name, document ID and update data
        args, kwargs = self.mock_es.update.call_args
        self.assertEqual(kwargs['index'], 'service-outages')
        self.assertEqual(kwargs['id'], outage_id)
        self.assertEqual(kwargs['doc'], updated_data)
    
    def test_bulk_index_service_statuses(self):
        """Test bulk indexing of service statuses to Elasticsearch."""
        # Create mock service statuses
        statuses = []
        for i in range(3):
            status = mock.MagicMock(spec=ServiceStatus)
            status.id = generate_uuid()
            status.model_dump.return_value = {
                "id": status.id,
                "status": "up",
                "timestamp": datetime.utcnow().isoformat()
            }
            statuses.append(status)
        
        # Call the method
        result = self.es_client.bulk_index_service_statuses(statuses)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify Elasticsearch bulk was called
        self.mock_es.bulk.assert_called_once()
        
        # Check the bulk request
        args, kwargs = self.mock_es.bulk.call_args
        self.assertEqual(kwargs['index'], 'service-status')
        
        # The bulk body should contain 3 operations (3 index operations)
        body = kwargs['body']
        self.assertEqual(len(body), 6)  # 3 operations * 2 lines each (action + source)
    
    def test_search_service_outages(self):
        """Test searching for service outages in Elasticsearch."""
        # Mock Elasticsearch search response
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": generate_uuid(),
                        "_source": {
                            "endpoint_name": "API Service",
                            "severity": "high",
                            "start_time": datetime.utcnow().isoformat(),
                            "duration": 3600
                        }
                    },
                    {
                        "_id": generate_uuid(),
                        "_source": {
                            "endpoint_name": "Auth Service",
                            "severity": "critical",
                            "start_time": datetime.utcnow().isoformat(),
                            "duration": 7200
                        }
                    }
                ]
            }
        }
        self.mock_es.search.return_value = mock_response
        
        # Call the method
        query = {"query": {"match": {"severity": "high"}}}
        results = self.es_client.search_service_outages(query)
        
        # Verify Elasticsearch search was called
        self.mock_es.search.assert_called_once()
        
        # Check the search parameters
        args, kwargs = self.mock_es.search.call_args
        self.assertEqual(kwargs['index'], 'service-outages')
        self.assertEqual(kwargs['body'], query)
        
        # Verify the results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['endpoint_name'], 'API Service')
        self.assertEqual(results[1]['endpoint_name'], 'Auth Service')
    
    def test_get_service_status_history(self):
        """Test getting service status history from Elasticsearch."""
        # Mock Elasticsearch search response
        mock_response = {
            "hits": {
                "total": {"value": 24},
                "hits": [
                    {
                        "_source": {
                            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                            "status": "up" if i % 4 != 0 else "down",
                            "response_time": 0.2 + (i * 0.01)
                        }
                    } for i in range(24)
                ]
            },
            "aggregations": {
                "availability": {
                    "buckets": [
                        {"key": "up", "doc_count": 18},
                        {"key": "down", "doc_count": 6}
                    ]
                },
                "avg_response_time": {"value": 0.35}
            }
        }
        self.mock_es.search.return_value = mock_response
        
        # Call the method
        endpoint_id = generate_uuid()
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        
        history, stats = self.es_client.get_service_status_history(
            endpoint_id, start_time, end_time
        )
        
        # Verify Elasticsearch search was called
        self.mock_es.search.assert_called_once()
        
        # Verify the results
        self.assertEqual(len(history), 24)
        self.assertEqual(stats['availability_percentage'], 75.0)  # 18/24 * 100
        self.assertEqual(stats['avg_response_time'], 0.35)
    
    def test_create_elasticsearch_indices(self):
        """Test creating Elasticsearch indices."""
        # Call the method
        self.es_client.create_elasticsearch_indices()
        
        # Verify Elasticsearch indices.create was called for each index
        expected_indices = [
            'service-status',
            'service-outages',
            'system-metrics',
            'service-logs'
        ]
        
        self.assertEqual(self.mock_es.indices.create.call_count, len(expected_indices))
        
        # Check that each index was created with the correct settings
        for i, call_args in enumerate(self.mock_es.indices.create.call_args_list):
            args, kwargs = call_args
            self.assertIn(kwargs['index'], expected_indices)
            self.assertIn('mappings', kwargs['body'])
            self.assertIn('settings', kwargs['body'])


if __name__ == "__main__":
    unittest.main()
