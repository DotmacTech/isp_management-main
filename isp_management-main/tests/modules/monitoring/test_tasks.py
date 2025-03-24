"""
Unit tests for the Celery tasks in the Monitoring Module.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock

from modules.monitoring.tasks import (
    health_check_task,
    collect_system_metrics_task,
    check_service_availability_task,
    sync_logs_to_elasticsearch_task,
    sync_metrics_to_elasticsearch_task
)


@pytest.fixture
def mock_elasticsearch_client():
    """Fixture for mocking ElasticsearchClient."""
    with patch('isp_management.modules.monitoring.tasks.elasticsearch_client') as mock_client:
        # Configure mock client
        mock_client.is_enabled.return_value = True
        mock_client.sync_logs_to_elasticsearch.return_value = (10, 0)
        mock_client.sync_metrics_to_elasticsearch.return_value = (10, 0)
        
        yield mock_client


@pytest.fixture
def mock_settings():
    """Fixture for mocking settings."""
    with patch('isp_management.modules.monitoring.tasks.settings') as mock_settings:
        # Configure mock settings
        mock_settings.logging.elasticsearch.enabled = True
        
        yield mock_settings


@pytest.fixture
def mock_db_session():
    """Fixture for mocking database session."""
    with patch('isp_management.modules.monitoring.tasks.SessionLocal') as mock_session_local:
        # Configure mock session
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        yield mock_session


class TestElasticsearchTasks:
    """Tests for Elasticsearch-related Celery tasks."""
    
    def test_sync_logs_to_elasticsearch_task(self, mock_elasticsearch_client, mock_settings, mock_db_session):
        """Test sync_logs_to_elasticsearch_task."""
        # Call the task
        result = sync_logs_to_elasticsearch_task()
        
        # Verify the result
        assert result["status"] == "success"
        assert result["synced_count"] == 10
        assert result["error_count"] == 0
        
        # Verify the elasticsearch client was called
        mock_elasticsearch_client.sync_logs_to_elasticsearch.assert_called_once_with(mock_db_session)
        
        # Verify the session was closed
        mock_db_session.close.assert_called_once()
    
    def test_sync_logs_to_elasticsearch_task_disabled(self, mock_elasticsearch_client, mock_settings, mock_db_session):
        """Test sync_logs_to_elasticsearch_task when Elasticsearch is disabled."""
        # Configure mock settings
        mock_settings.logging.elasticsearch.enabled = False
        
        # Call the task
        result = sync_logs_to_elasticsearch_task()
        
        # Verify the result
        assert result["status"] == "skipped"
        assert result["reason"] == "elasticsearch_disabled"
        
        # Verify the elasticsearch client was not called
        mock_elasticsearch_client.sync_logs_to_elasticsearch.assert_not_called()
    
    def test_sync_logs_to_elasticsearch_task_error(self, mock_elasticsearch_client, mock_settings, mock_db_session):
        """Test sync_logs_to_elasticsearch_task when an error occurs."""
        # Configure mock client to raise an exception
        mock_elasticsearch_client.sync_logs_to_elasticsearch.side_effect = Exception("Test error")
        
        # Call the task
        result = sync_logs_to_elasticsearch_task()
        
        # Verify the result
        assert result["status"] == "error"
        assert result["error"] == "Test error"
        
        # Verify the elasticsearch client was called
        mock_elasticsearch_client.sync_logs_to_elasticsearch.assert_called_once_with(mock_db_session)
        
        # Verify the session was closed
        mock_db_session.close.assert_called_once()
    
    def test_sync_metrics_to_elasticsearch_task(self, mock_elasticsearch_client, mock_settings, mock_db_session):
        """Test sync_metrics_to_elasticsearch_task."""
        # Call the task
        result = sync_metrics_to_elasticsearch_task()
        
        # Verify the result
        assert result["status"] == "success"
        assert result["synced_count"] == 10
        assert result["error_count"] == 0
        
        # Verify the elasticsearch client was called
        mock_elasticsearch_client.sync_metrics_to_elasticsearch.assert_called_once_with(mock_db_session)
        
        # Verify the session was closed
        mock_db_session.close.assert_called_once()
    
    def test_sync_metrics_to_elasticsearch_task_disabled(self, mock_elasticsearch_client, mock_settings, mock_db_session):
        """Test sync_metrics_to_elasticsearch_task when Elasticsearch is disabled."""
        # Configure mock settings
        mock_settings.logging.elasticsearch.enabled = False
        
        # Call the task
        result = sync_metrics_to_elasticsearch_task()
        
        # Verify the result
        assert result["status"] == "skipped"
        assert result["reason"] == "elasticsearch_disabled"
        
        # Verify the elasticsearch client was not called
        mock_elasticsearch_client.sync_metrics_to_elasticsearch.assert_not_called()
    
    def test_sync_metrics_to_elasticsearch_task_error(self, mock_elasticsearch_client, mock_settings, mock_db_session):
        """Test sync_metrics_to_elasticsearch_task when an error occurs."""
        # Configure mock client to raise an exception
        mock_elasticsearch_client.sync_metrics_to_elasticsearch.side_effect = Exception("Test error")
        
        # Call the task
        result = sync_metrics_to_elasticsearch_task()
        
        # Verify the result
        assert result["status"] == "error"
        assert result["error"] == "Test error"
        
        # Verify the elasticsearch client was called
        mock_elasticsearch_client.sync_metrics_to_elasticsearch.assert_called_once_with(mock_db_session)
        
        # Verify the session was closed
        mock_db_session.close.assert_called_once()


class TestMonitoringTasks:
    """Tests for monitoring-related Celery tasks."""
    
    @patch('isp_management.modules.monitoring.tasks.MonitoringService')
    def test_health_check_task(self, mock_monitoring_service, mock_db_session):
        """Test health_check_task."""
        # Configure mock service
        mock_service_instance = mock_monitoring_service.return_value
        mock_service_instance.check_system_health.return_value = {
            "overall_status": "healthy",
            "components": {
                "database": {"status": "healthy"},
                "api": {"status": "healthy"}
            }
        }
        
        # Call the task
        result = health_check_task()
        
        # Verify the result
        assert result["status"] == "success"
        assert result["health_status"] == "healthy"
        assert len(result["components"]) == 2
        
        # Verify the monitoring service was called
        mock_service_instance.check_system_health.assert_called_once()
        
        # Verify the session was closed
        mock_db_session.close.assert_called_once()
    
    @patch('isp_management.modules.monitoring.tasks.MetricsService')
    def test_collect_system_metrics_task(self, mock_metrics_service, mock_db_session):
        """Test collect_system_metrics_task."""
        # Configure mock service
        mock_service_instance = mock_metrics_service.return_value
        mock_service_instance.collect_system_metrics.return_value = {
            "cpu_usage": 50.0,
            "memory_usage": 75.0,
            "disk_usage": 80.0
        }
        
        # Call the task
        result = collect_system_metrics_task()
        
        # Verify the result
        assert result["status"] == "success"
        assert "metrics" in result
        assert result["metrics"]["cpu_usage"] == 50.0
        
        # Verify the metrics service was called
        mock_service_instance.collect_system_metrics.assert_called_once()
        
        # Verify the session was closed
        mock_db_session.close.assert_called_once()
    
    @patch('isp_management.modules.monitoring.tasks.MonitoringService')
    def test_check_service_availability_task(self, mock_monitoring_service, mock_db_session):
        """Test check_service_availability_task."""
        # Configure mock service
        mock_service_instance = mock_monitoring_service.return_value
        mock_service_instance.check_service_availability.return_value = {
            "api_gateway": {"status": "available", "response_time_ms": 50},
            "billing": {"status": "available", "response_time_ms": 75}
        }
        
        # Call the task
        result = check_service_availability_task()
        
        # Verify the result
        assert result["status"] == "success"
        assert "services" in result
        assert len(result["services"]) == 2
        assert result["services"]["api_gateway"]["status"] == "available"
        
        # Verify the monitoring service was called
        mock_service_instance.check_service_availability.assert_called_once()
        
        # Verify the session was closed
        mock_db_session.close.assert_called_once()
