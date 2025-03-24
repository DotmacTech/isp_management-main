"""
Tests for the monitoring service in the monitoring module.

This module contains tests for the monitoring service, ensuring that
system health checks, component status, and metrics retrieval work correctly.
"""

import unittest
from unittest import mock
from datetime import datetime, timedelta
import uuid

from sqlalchemy.orm import Session

from modules.monitoring.models.monitoring_models import (
    HealthCheckResponse, HealthCheckComponentStatus, 
    HealthStatusEnum, MetricTypeEnum, LogLevelEnum
)
from modules.monitoring.services.monitoring_service import MonitoringService


class TestMonitoringService(unittest.TestCase):
    """Test cases for the monitoring service."""

    def setUp(self):
        """Set up test environment."""
        # Mock database session
        self.db = mock.MagicMock(spec=Session)
        
        # Create monitoring service with mocked DB
        self.monitoring_service = MonitoringService(self.db)
        
        # Mock logging and metrics services
        self.monitoring_service.logging_service = mock.MagicMock()
        self.monitoring_service.metrics_service = mock.MagicMock()
        
    def test_check_system_health(self):
        """Test checking system health."""
        # Mock settings
        with mock.patch('modules.monitoring.services.monitoring_service.settings') as mock_settings:
            mock_settings.health_check_services = {
                "database": "postgresql://localhost:5432",
                "cache": "redis://localhost:6379",
                "api": "http://localhost:8000/health"
            }
            
            # Mock _update_health_status method
            self.monitoring_service._update_health_status = mock.MagicMock()
            
            # Call the method
            result = self.monitoring_service.check_system_health()
            
            # Verify results
            self.assertIsInstance(result, HealthCheckResponse)
            self.assertEqual(len(result.components), 3)
            self.assertEqual(result.status, HealthStatusEnum.HEALTHY)
            
            # Verify _update_health_status was called for each service
            self.assertEqual(self.monitoring_service._update_health_status.call_count, 3)
    
    def test_check_system_health_with_unhealthy_component(self):
        """Test checking system health with an unhealthy component."""
        # Mock settings
        with mock.patch('modules.monitoring.services.monitoring_service.settings') as mock_settings:
            mock_settings.health_check_services = {
                "database": "postgresql://localhost:5432",
                "cache": "redis://localhost:6379",
                "api": "http://localhost:8000/health"
            }
            
            # Mock _update_health_status method
            self.monitoring_service._update_health_status = mock.MagicMock()
            
            # Mock a connection error for the cache service
            def side_effect(service_name, is_healthy, error_message=None):
                if service_name == "cache":
                    # Simulate an unhealthy cache
                    for component in self.monitoring_service.check_system_health().components:
                        if component.name == "cache":
                            component.status = HealthStatusEnum.UNHEALTHY
                            component.details = "Connection refused"
                    # Update overall status
                    self.monitoring_service.check_system_health().status = HealthStatusEnum.UNHEALTHY
            
            self.monitoring_service._update_health_status.side_effect = side_effect
            
            # Call the method
            result = self.monitoring_service.check_system_health()
            
            # Verify results
            self.assertIsInstance(result, HealthCheckResponse)
            self.assertEqual(len(result.components), 3)
            
            # Check if at least one component is unhealthy
            unhealthy_components = [c for c in result.components if c.status == HealthStatusEnum.UNHEALTHY]
            self.assertTrue(len(unhealthy_components) > 0)
    
    def test_get_component_status(self):
        """Test getting component status."""
        # Mock SystemHealthStatus
        from modules.monitoring.models import SystemHealthStatus
        mock_health_status = mock.MagicMock(spec=SystemHealthStatus)
        mock_health_status.component_name = "database"
        mock_health_status.status = HealthStatusEnum.HEALTHY.value
        mock_health_status.details = "Database is healthy"
        mock_health_status.timestamp = datetime.utcnow()
        
        # Mock query chain
        mock_query = mock.MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_health_status
        
        self.db.query.return_value = mock_query
        
        # Call the method
        result = self.monitoring_service.get_component_status("database")
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "database")
        self.assertEqual(result.status, HealthStatusEnum.HEALTHY)
        self.assertEqual(result.details, "Database is healthy")
    
    def test_get_component_status_not_found(self):
        """Test getting component status for a non-existent component."""
        # Mock query chain
        mock_query = mock.MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        
        self.db.query.return_value = mock_query
        
        # Call the method
        result = self.monitoring_service.get_component_status("non_existent")
        
        # Verify results
        self.assertIsNone(result)
    
    def test_get_component_metrics(self):
        """Test getting component metrics."""
        # Mock metrics result
        mock_metrics = mock.MagicMock()
        mock_metrics.items = [
            {"id": str(uuid.uuid4()), "value": 85.5, "timestamp": datetime.utcnow().isoformat()},
            {"id": str(uuid.uuid4()), "value": 90.2, "timestamp": datetime.utcnow().isoformat()}
        ]
        
        self.monitoring_service.metrics_service.search_metrics.return_value = mock_metrics
        
        # Call the method
        result = self.monitoring_service.get_component_metrics(
            component_name="database",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            metric_type=MetricTypeEnum.CPU,
            limit=10
        )
        
        # Verify results
        self.assertEqual(len(result), 2)
        self.monitoring_service.metrics_service.search_metrics.assert_called_once()
        
        # Verify the search parameters
        call_args = self.monitoring_service.metrics_service.search_metrics.call_args[0][0]
        self.assertEqual(call_args["service_name"], "database")
        self.assertEqual(call_args["metric_type"], MetricTypeEnum.CPU.value)
        self.assertEqual(call_args["limit"], 10)
    
    def test_get_service_logs(self):
        """Test getting service logs."""
        # Mock logs result
        mock_logs = mock.MagicMock()
        mock_logs.items = [
            {"id": str(uuid.uuid4()), "message": "Log 1", "timestamp": datetime.utcnow().isoformat()},
            {"id": str(uuid.uuid4()), "message": "Log 2", "timestamp": datetime.utcnow().isoformat()}
        ]
        
        self.monitoring_service.logging_service.search_logs.return_value = mock_logs
        
        # Call the method
        result = self.monitoring_service.get_service_logs(
            service_name="auth_service",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            log_level=LogLevelEnum.ERROR,
            limit=10
        )
        
        # Verify results
        self.assertEqual(len(result), 2)
        self.monitoring_service.logging_service.search_logs.assert_called_once()
        
        # Verify the search parameters
        call_args = self.monitoring_service.logging_service.search_logs.call_args[0]
        self.assertEqual(call_args[0], "auth_service")  # service_name
        self.assertEqual(call_args[3], LogLevelEnum.ERROR.value)  # log_level
        self.assertEqual(call_args[4], 10)  # limit
    
    def test_update_health_status(self):
        """Test updating health status."""
        # Mock SystemHealthStatus
        from modules.monitoring.models import SystemHealthStatus
        
        # Call the method
        component_name = "database"
        is_healthy = True
        error_message = None
        
        with mock.patch.object(self.monitoring_service, '_update_health_status', wraps=self.monitoring_service._update_health_status) as wrapped_method:
            # We need to mock the actual implementation since it's a private method
            # and we want to verify it works correctly
            
            # Call the method through check_system_health to trigger _update_health_status
            with mock.patch('modules.monitoring.services.monitoring_service.settings') as mock_settings:
                mock_settings.health_check_services = {
                    "database": "postgresql://localhost:5432"
                }
                
                self.monitoring_service.check_system_health()
                
                # Verify _update_health_status was called
                wrapped_method.assert_called_with("database", True)
    
    def test_generate_service_health_report(self):
        """Test generating a service health report."""
        # Mock SystemHealthStatus
        from modules.monitoring.models import SystemHealthStatus
        
        # Mock query results for health status
        mock_health_statuses = [
            mock.MagicMock(spec=SystemHealthStatus),
            mock.MagicMock(spec=SystemHealthStatus)
        ]
        
        # Configure mocks
        for i, status in enumerate(mock_health_statuses):
            status.component_name = "auth_service"
            status.status = HealthStatusEnum.HEALTHY.value if i == 0 else HealthStatusEnum.UNHEALTHY.value
            status.timestamp = datetime.utcnow() - timedelta(hours=i)
        
        # Mock query chain for health status
        mock_health_query = mock.MagicMock()
        mock_health_query.filter.return_value = mock_health_query
        mock_health_query.filter_by.return_value = mock_health_query
        mock_health_query.all.return_value = mock_health_statuses
        
        # Mock metrics service for response time
        self.monitoring_service.metrics_service.get_average_metric.return_value = 150.5
        
        # Mock logging service for error count
        self.monitoring_service.logging_service.count_logs.return_value = 5
        
        # Configure db.query to return different query objects based on the argument
        def query_side_effect(model):
            if model == SystemHealthStatus:
                return mock_health_query
            return mock.MagicMock()
            
        self.db.query.side_effect = query_side_effect
        
        # Call the method
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        
        result = self.monitoring_service.generate_service_health_report(
            service_name="auth_service",
            start_time=start_time,
            end_time=end_time
        )
        
        # Verify results
        self.assertEqual(result.service_name, "auth_service")
        self.assertEqual(result.status, HealthStatusEnum.HEALTHY)  # Most recent status
        self.assertGreaterEqual(result.uptime_percentage, 0)
        self.assertLessEqual(result.uptime_percentage, 100)
        self.assertEqual(result.average_response_time, 150.5)
        self.assertEqual(result.error_count, 5)
        self.assertEqual(result.start_time, start_time)
        self.assertEqual(result.end_time, end_time)


if __name__ == "__main__":
    unittest.main()
