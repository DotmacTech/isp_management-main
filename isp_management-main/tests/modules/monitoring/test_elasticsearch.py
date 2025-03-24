"""
Unit tests for the Elasticsearch integration in the Monitoring Module.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import datetime
from unittest.mock import patch, MagicMock, call
from elasticsearch import Elasticsearch, helpers

from modules.monitoring.elasticsearch import ElasticsearchClient
from modules.monitoring.models import ServiceLog, SystemMetric, LogLevel, MetricType


@pytest.fixture
def mock_elasticsearch():
    """Fixture for mocking Elasticsearch client."""
    with patch('elasticsearch.Elasticsearch') as mock_es:
        # Mock the client's ping method to return True
        mock_es.return_value.ping.return_value = True
        yield mock_es


@pytest.fixture
def elasticsearch_client(mock_elasticsearch):
    """Fixture for creating an ElasticsearchClient with mocked Elasticsearch."""
    with patch('isp_management.modules.monitoring.elasticsearch.settings') as mock_settings:
        # Configure mock settings
        mock_settings.logging.elasticsearch.enabled = True
        mock_settings.logging.elasticsearch.hosts = ["http://localhost:9200"]
        mock_settings.logging.elasticsearch.username = None
        mock_settings.logging.elasticsearch.password = None
        mock_settings.logging.elasticsearch.verify_certs = True
        mock_settings.logging.elasticsearch.log_index_prefix = "test-logs"
        mock_settings.logging.elasticsearch.metric_index_prefix = "test-metrics"
        mock_settings.logging.elasticsearch.index_date_format = "YYYY.MM.dd"
        mock_settings.logging.elasticsearch.number_of_shards = 1
        mock_settings.logging.elasticsearch.number_of_replicas = 0
        
        # Create client
        client = ElasticsearchClient()
        
        # Ensure client is initialized
        assert client.enabled
        assert client.client is not None
        
        yield client


@pytest.fixture
def mock_db_session():
    """Fixture for mocking database session."""
    mock_session = MagicMock()
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.order_by.return_value = mock_session
    mock_session.limit.return_value = mock_session
    
    yield mock_session


class TestElasticsearchClient:
    """Tests for the ElasticsearchClient class."""
    
    def test_init(self, mock_elasticsearch):
        """Test initialization of ElasticsearchClient."""
        with patch('isp_management.modules.monitoring.elasticsearch.settings') as mock_settings:
            # Configure mock settings
            mock_settings.logging.elasticsearch.enabled = True
            mock_settings.logging.elasticsearch.hosts = ["http://localhost:9200"]
            
            # Create client
            client = ElasticsearchClient()
            
            # Verify client is initialized
            assert client.enabled
            assert client.client is not None
            
            # Verify Elasticsearch was initialized with correct parameters
            mock_elasticsearch.assert_called_once_with(
                hosts=["http://localhost:9200"],
                http_auth=None,
                verify_certs=mock_settings.logging.elasticsearch.verify_certs
            )
    
    def test_is_enabled(self, elasticsearch_client):
        """Test is_enabled method."""
        assert elasticsearch_client.is_enabled()
        
        # Test when client is disabled
        elasticsearch_client.enabled = False
        assert not elasticsearch_client.is_enabled()
        
        # Test when client is None
        elasticsearch_client.enabled = True
        elasticsearch_client.client = None
        assert not elasticsearch_client.is_enabled()
    
    def test_get_log_index_name(self, elasticsearch_client):
        """Test get_log_index_name method."""
        # Test with default timestamp (current time)
        index_name = elasticsearch_client.get_log_index_name()
        assert index_name.startswith("test-logs-")
        
        # Test with specific timestamp
        timestamp = datetime.datetime(2023, 1, 1)
        index_name = elasticsearch_client.get_log_index_name(timestamp)
        assert index_name == "test-logs-2023.01.01"
    
    def test_get_metric_index_name(self, elasticsearch_client):
        """Test get_metric_index_name method."""
        # Test with default timestamp (current time)
        index_name = elasticsearch_client.get_metric_index_name()
        assert index_name.startswith("test-metrics-")
        
        # Test with specific timestamp
        timestamp = datetime.datetime(2023, 1, 1)
        index_name = elasticsearch_client.get_metric_index_name(timestamp)
        assert index_name == "test-metrics-2023.01.01"
    
    def test_create_log_index_template(self, elasticsearch_client):
        """Test create_log_index_template method."""
        # Mock the client's indices.put_template method
        elasticsearch_client.client.indices.put_template = MagicMock()
        
        # Call the method
        result = elasticsearch_client.create_log_index_template()
        
        # Verify the result
        assert result is True
        
        # Verify the method was called with correct parameters
        elasticsearch_client.client.indices.put_template.assert_called_once()
        
        # Verify template name and pattern
        args, kwargs = elasticsearch_client.client.indices.put_template.call_args
        assert kwargs["name"] == "test-logs-template"
        assert kwargs["body"]["index_patterns"] == ["test-logs-*"]
    
    def test_create_metric_index_template(self, elasticsearch_client):
        """Test create_metric_index_template method."""
        # Mock the client's indices.put_template method
        elasticsearch_client.client.indices.put_template = MagicMock()
        
        # Call the method
        result = elasticsearch_client.create_metric_index_template()
        
        # Verify the result
        assert result is True
        
        # Verify the method was called with correct parameters
        elasticsearch_client.client.indices.put_template.assert_called_once()
        
        # Verify template name and pattern
        args, kwargs = elasticsearch_client.client.indices.put_template.call_args
        assert kwargs["name"] == "test-metrics-template"
        assert kwargs["body"]["index_patterns"] == ["test-metrics-*"]
    
    def test_bulk_index_logs(self, elasticsearch_client):
        """Test bulk_index_logs method."""
        # Mock the helpers.bulk method
        with patch('elasticsearch.helpers.bulk') as mock_bulk:
            # Configure mock to return success
            mock_bulk.return_value = (3, [])
            
            # Create test logs
            logs = [
                {
                    "id": 1,
                    "timestamp": "2023-01-01T00:00:00",
                    "service_name": "test-service",
                    "log_level": "INFO",
                    "message": "Test message 1",
                    "metadata": {"test": "data"}
                },
                {
                    "id": 2,
                    "timestamp": "2023-01-01T00:01:00",
                    "service_name": "test-service",
                    "log_level": "ERROR",
                    "message": "Test message 2",
                    "metadata": {"test": "data"}
                },
                {
                    "id": 3,
                    "timestamp": datetime.datetime(2023, 1, 1, 0, 2, 0),
                    "service_name": "test-service",
                    "log_level": "WARNING",
                    "message": "Test message 3",
                    "metadata": {"test": "data"}
                }
            ]
            
            # Call the method
            success, errors = elasticsearch_client.bulk_index_logs(logs)
            
            # Verify the result
            assert success == 3
            assert errors == 0
            
            # Verify the bulk method was called with correct parameters
            mock_bulk.assert_called_once()
            
            # Verify actions
            args, kwargs = mock_bulk.call_args
            assert args[0] == elasticsearch_client.client
            assert len(kwargs["actions"]) == 3
            
            # Verify index names
            assert kwargs["actions"][0]["_index"] == "test-logs-2023.01.01"
            assert kwargs["actions"][1]["_index"] == "test-logs-2023.01.01"
            assert kwargs["actions"][2]["_index"] == "test-logs-2023.01.01"
    
    def test_bulk_index_metrics(self, elasticsearch_client):
        """Test bulk_index_metrics method."""
        # Mock the helpers.bulk method
        with patch('elasticsearch.helpers.bulk') as mock_bulk:
            # Configure mock to return success
            mock_bulk.return_value = (3, [])
            
            # Create test metrics
            metrics = [
                {
                    "id": 1,
                    "timestamp": "2023-01-01T00:00:00",
                    "service_name": "test-service",
                    "host_name": "test-host",
                    "metric_type": "CPU_USAGE",
                    "value": 50.0,
                    "unit": "percent",
                    "tags": {"test": "data"}
                },
                {
                    "id": 2,
                    "timestamp": "2023-01-01T00:01:00",
                    "service_name": "test-service",
                    "host_name": "test-host",
                    "metric_type": "MEMORY_USAGE",
                    "value": 75.0,
                    "unit": "percent",
                    "tags": {"test": "data"}
                },
                {
                    "id": 3,
                    "timestamp": datetime.datetime(2023, 1, 1, 0, 2, 0),
                    "service_name": "test-service",
                    "host_name": "test-host",
                    "metric_type": "DISK_USAGE",
                    "value": 80.0,
                    "unit": "percent",
                    "tags": {"test": "data"}
                }
            ]
            
            # Call the method
            success, errors = elasticsearch_client.bulk_index_metrics(metrics)
            
            # Verify the result
            assert success == 3
            assert errors == 0
            
            # Verify the bulk method was called with correct parameters
            mock_bulk.assert_called_once()
            
            # Verify actions
            args, kwargs = mock_bulk.call_args
            assert args[0] == elasticsearch_client.client
            assert len(kwargs["actions"]) == 3
            
            # Verify index names
            assert kwargs["actions"][0]["_index"] == "test-metrics-2023.01.01"
            assert kwargs["actions"][1]["_index"] == "test-metrics-2023.01.01"
            assert kwargs["actions"][2]["_index"] == "test-metrics-2023.01.01"
    
    def test_sync_logs_to_elasticsearch(self, elasticsearch_client, mock_db_session):
        """Test sync_logs_to_elasticsearch method."""
        # Create mock logs
        mock_logs = [
            MagicMock(spec=ServiceLog),
            MagicMock(spec=ServiceLog),
            MagicMock(spec=ServiceLog)
        ]
        
        # Configure mock logs
        for i, log in enumerate(mock_logs):
            log.id = i + 1
            log.timestamp = datetime.datetime(2023, 1, 1, 0, i, 0)
            log.service_name = "test-service"
            log.log_level = LogLevel.INFO
            log.message = f"Test message {i+1}"
            log.metadata = {"test": "data"}
        
        # Configure mock session to return logs
        mock_db_session.all.return_value = mock_logs
        
        # Mock the bulk_index_logs method
        elasticsearch_client.bulk_index_logs = MagicMock(return_value=(3, 0))
        
        # Call the method
        success, errors = elasticsearch_client.sync_logs_to_elasticsearch(mock_db_session)
        
        # Verify the result
        assert success == 3
        assert errors == 0
        
        # Verify the query was built correctly
        mock_db_session.query.assert_called_once()
        mock_db_session.filter.assert_called_once()
        mock_db_session.order_by.assert_called_once()
        mock_db_session.limit.assert_called_once()
        
        # Verify the bulk_index_logs method was called with correct parameters
        elasticsearch_client.bulk_index_logs.assert_called_once()
        args, kwargs = elasticsearch_client.bulk_index_logs.call_args
        assert len(args[0]) == 3
        
        # Verify the session was updated
        mock_db_session.query.assert_called_once()
        mock_db_session.filter.assert_called_once()
        mock_db_session.update.assert_called_once_with(
            {"elasticsearch_synced": True},
            synchronize_session=False
        )
        mock_db_session.commit.assert_called_once()
    
    def test_sync_metrics_to_elasticsearch(self, elasticsearch_client, mock_db_session):
        """Test sync_metrics_to_elasticsearch method."""
        # Create mock metrics
        mock_metrics = [
            MagicMock(spec=SystemMetric),
            MagicMock(spec=SystemMetric),
            MagicMock(spec=SystemMetric)
        ]
        
        # Configure mock metrics
        for i, metric in enumerate(mock_metrics):
            metric.id = i + 1
            metric.timestamp = datetime.datetime(2023, 1, 1, 0, i, 0)
            metric.service_name = "test-service"
            metric.host_name = "test-host"
            metric.metric_type = MetricType.CPU_USAGE
            metric.value = 50.0 + i * 10
            metric.unit = "percent"
            metric.tags = {"test": "data"}
            metric.sampling_rate = 1.0
        
        # Configure mock session to return metrics
        mock_db_session.all.return_value = mock_metrics
        
        # Mock the bulk_index_metrics method
        elasticsearch_client.bulk_index_metrics = MagicMock(return_value=(3, 0))
        
        # Call the method
        success, errors = elasticsearch_client.sync_metrics_to_elasticsearch(mock_db_session)
        
        # Verify the result
        assert success == 3
        assert errors == 0
        
        # Verify the query was built correctly
        mock_db_session.query.assert_called_once()
        mock_db_session.filter.assert_called_once()
        mock_db_session.order_by.assert_called_once()
        mock_db_session.limit.assert_called_once()
        
        # Verify the bulk_index_metrics method was called with correct parameters
        elasticsearch_client.bulk_index_metrics.assert_called_once()
        args, kwargs = elasticsearch_client.bulk_index_metrics.call_args
        assert len(args[0]) == 3
        
        # Verify the session was updated
        mock_db_session.query.assert_called_once()
        mock_db_session.filter.assert_called_once()
        mock_db_session.update.assert_called_once_with(
            {"elasticsearch_synced": True},
            synchronize_session=False
        )
        mock_db_session.commit.assert_called_once()
