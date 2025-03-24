"""
Tests for the logging service in the monitoring module.

This module contains tests for the logging service, ensuring that
log creation, searching, and Elasticsearch syncing work correctly.
"""

import unittest
from unittest import mock
from datetime import datetime, timedelta
import uuid

from sqlalchemy.orm import Session

from modules.monitoring.models.service_log import ServiceLog
from modules.monitoring.models.log_retention import LogRetentionPolicy
from modules.monitoring.models.monitoring_models import (
    ServiceLogCreate, ServiceLogResponse, LogSearchParams, 
    LogSearchResult, LogLevel
)
from modules.monitoring.services.logging_service import LoggingService


class TestLoggingService(unittest.TestCase):
    """Test cases for the logging service."""

    def setUp(self):
        """Set up test environment."""
        # Mock database session
        self.db = mock.MagicMock(spec=Session)
        
        # Create logging service with mocked DB
        self.logging_service = LoggingService(self.db)
        
        # Mock Elasticsearch client
        self.logging_service.es_client = mock.MagicMock()
        self.logging_service.es_client.is_connected.return_value = True
        
    def test_create_log(self):
        """Test creating a log entry."""
        # Create test data
        log_data = ServiceLogCreate(
            endpoint_id=str(uuid.uuid4()),
            status="success",
            response_time=150.5,
            status_code="200",
            error_message=None,
            details={"method": "GET", "path": "/api/users"}
        )
        
        # Mock DB behavior
        mock_log = mock.MagicMock(spec=ServiceLog)
        self.db.add.return_value = None
        self.db.commit.return_value = None
        self.db.refresh.side_effect = lambda x: setattr(x, 'id', str(uuid.uuid4()))
        
        # Call the method
        result = self.logging_service.create_log(log_data)
        
        # Verify results
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        
    def test_search_logs_elasticsearch(self):
        """Test searching logs using Elasticsearch."""
        # Mock Elasticsearch response
        es_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "id": str(uuid.uuid4()),
                            "endpoint_id": str(uuid.uuid4()),
                            "status": "success",
                            "response_time": 150.5,
                            "status_code": "200",
                            "error_message": None,
                            "details": {"method": "GET", "path": "/api/users"},
                            "created_at": datetime.utcnow().isoformat(),
                            "elasticsearch_synced": True
                        }
                    },
                    {
                        "_source": {
                            "id": str(uuid.uuid4()),
                            "endpoint_id": str(uuid.uuid4()),
                            "status": "error",
                            "response_time": 450.2,
                            "status_code": "500",
                            "error_message": "Internal server error",
                            "details": {"method": "POST", "path": "/api/users"},
                            "created_at": datetime.utcnow().isoformat(),
                            "elasticsearch_synced": True
                        }
                    }
                ]
            }
        }
        
        self.logging_service.es_client.search.return_value = es_response
        
        # Call the method
        result = self.logging_service.search_logs(
            service_names=["auth_service", "user_service"],
            log_levels=[LogLevel.ERROR, LogLevel.INFO],
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
            message_contains="error",
            limit=10
        )
        
        # Verify results
        self.logging_service.es_client.search.assert_called_once()
        self.assertEqual(len(result.logs), 2)
        self.assertEqual(result.total, 2)
        
    def test_search_logs_database(self):
        """Test searching logs using the database."""
        # Create mock logs
        mock_logs = [
            mock.MagicMock(spec=ServiceLog),
            mock.MagicMock(spec=ServiceLog)
        ]
        
        # Configure mocks
        for i, log in enumerate(mock_logs):
            log.id = str(uuid.uuid4())
            log.endpoint_id = str(uuid.uuid4())
            log.status = "success" if i == 0 else "error"
            log.response_time = 150.5 if i == 0 else 450.2
            log.status_code = "200" if i == 0 else "500"
            log.error_message = None if i == 0 else "Internal server error"
            log.details = {"method": "GET" if i == 0 else "POST", "path": "/api/users"}
            log.created_at = datetime.utcnow()
            log.elasticsearch_synced = True
        
        # Mock query chain
        mock_query = mock.MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_logs
        mock_query.count.return_value = len(mock_logs)
        
        self.db.query.return_value = mock_query
        
        # Force database search by disabling Elasticsearch
        self.logging_service.es_client.is_connected.return_value = False
        
        # Call the method
        result = self.logging_service.search_logs(
            service_names=["auth_service", "user_service"],
            log_levels=[LogLevel.ERROR, LogLevel.INFO],
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
            message_contains="error",
            limit=10
        )
        
        # Verify results
        self.db.query.assert_called_with(ServiceLog)
        self.assertEqual(len(result.logs), 2)
        self.assertEqual(result.total, 2)
        
    def test_apply_retention_policy(self):
        """Test applying log retention policy."""
        # Create mock policy
        mock_policy = mock.MagicMock(spec=LogRetentionPolicy)
        mock_policy.retention_days = 30
        
        # Mock query chain for policy
        mock_policy_query = mock.MagicMock()
        mock_policy_query.first.return_value = mock_policy
        
        # Mock query chain for logs
        mock_logs_query = mock.MagicMock()
        mock_logs_query.filter.return_value = mock_logs_query
        mock_logs_query.delete.return_value = 5  # 5 logs deleted
        
        # Configure db.query to return different query objects based on the argument
        def query_side_effect(model):
            if model == LogRetentionPolicy:
                return mock_policy_query
            elif model == ServiceLog:
                return mock_logs_query
            return mock.MagicMock()
            
        self.db.query.side_effect = query_side_effect
        
        # Call the method
        result = self.logging_service.apply_retention_policy()
        
        # Verify results
        self.assertEqual(result, 5)
        self.db.commit.assert_called_once()
        
    def test_sync_logs_to_elasticsearch(self):
        """Test syncing logs to Elasticsearch."""
        # Create mock logs
        mock_logs = [
            mock.MagicMock(spec=ServiceLog),
            mock.MagicMock(spec=ServiceLog)
        ]
        
        # Configure mocks
        for i, log in enumerate(mock_logs):
            log.id = str(uuid.uuid4())
            log.service_name = f"service_{i}"
            log.log_level = "info" if i == 0 else "error"
            log.message = f"Test message {i}"
            log.timestamp = datetime.utcnow()
            log.trace_id = str(uuid.uuid4())
            log.correlation_id = str(uuid.uuid4())
            log.user_id = i + 1
            log.request_path = f"/api/resource/{i}"
            log.request_method = "GET" if i == 0 else "POST"
            log.response_status = 200 if i == 0 else 500
            log.response_time = 150.5 if i == 0 else 450.2
            log.ip_address = f"192.168.1.{i+1}"
            log.user_agent = f"Mozilla/5.0 (Test {i})"
            log.additional_data = {"key": f"value_{i}"}
            log.elasticsearch_synced = False
        
        # Mock query chain
        mock_query = mock.MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_logs
        
        mock_update_query = mock.MagicMock()
        mock_update_query.filter.return_value = mock_update_query
        mock_update_query.update.return_value = len(mock_logs)
        
        # Configure db.query to return different query objects based on call count
        self.db.query.side_effect = [mock_query, mock_update_query]
        
        # Mock bulk method
        self.logging_service.es_client.bulk.return_value = {"errors": False}
        
        # Call the method
        result = self.logging_service.sync_logs_to_elasticsearch()
        
        # Verify results
        self.assertEqual(result, 2)
        self.logging_service.es_client.bulk.assert_called_once()
        self.db.commit.assert_called_once()
        
    def test_get_log_by_id(self):
        """Test getting a log by ID."""
        # Create mock log
        mock_log = mock.MagicMock(spec=ServiceLog)
        mock_log.id = str(uuid.uuid4())
        
        # Mock query chain
        mock_query = mock.MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = mock_log
        
        self.db.query.return_value = mock_query
        
        # Call the method
        log_id = mock_log.id
        result = self.logging_service.get_log_by_id(log_id)
        
        # Verify results
        self.db.query.assert_called_with(ServiceLog)
        mock_query.filter_by.assert_called_with(id=log_id)
        self.assertEqual(result, mock_log)
        
    def test_update_log(self):
        """Test updating a log."""
        # Create mock log
        mock_log = mock.MagicMock(spec=ServiceLog)
        mock_log.id = str(uuid.uuid4())
        
        # Mock get_log_by_id
        self.logging_service.get_log_by_id = mock.MagicMock(return_value=mock_log)
        
        # Call the method
        log_data = {
            "status": "updated",
            "response_time": 200.5,
            "elasticsearch_synced": True
        }
        result = self.logging_service.update_log(mock_log.id, log_data)
        
        # Verify results
        self.logging_service.get_log_by_id.assert_called_with(mock_log.id)
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(mock_log)
        self.assertEqual(result, mock_log)
        
        # Verify that attributes were updated
        self.assertEqual(mock_log.status, "updated")
        self.assertEqual(mock_log.response_time, 200.5)
        self.assertEqual(mock_log.elasticsearch_synced, True)
        
    def test_delete_log(self):
        """Test deleting a log."""
        # Create mock log
        mock_log = mock.MagicMock(spec=ServiceLog)
        mock_log.id = str(uuid.uuid4())
        
        # Mock get_log_by_id
        self.logging_service.get_log_by_id = mock.MagicMock(return_value=mock_log)
        
        # Call the method
        result = self.logging_service.delete_log(mock_log.id)
        
        # Verify results
        self.logging_service.get_log_by_id.assert_called_with(mock_log.id)
        self.db.delete.assert_called_once_with(mock_log)
        self.db.commit.assert_called_once()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
