"""
Tests for the monitoring models in the monitoring module.

This module contains tests for the Pydantic models used in the monitoring module,
ensuring that they are compatible with Pydantic v2.
"""

import unittest
from datetime import datetime, timedelta
import uuid
import json

from modules.monitoring.models.monitoring_models import (
    LogLevel, HealthStatusEnum, MetricTypeEnum, LogLevelEnum,
    ServiceLogBase, ServiceLogCreate, ServiceLogUpdate, ServiceLogInDB,
    ServiceLogResponse, LogSearchParams, LogSearchResult,
    HealthCheckComponentStatus, HealthCheckResponse, ServiceHealthReport
)


class TestMonitoringModels(unittest.TestCase):
    """Test cases for the monitoring models."""

    def test_log_level_enum(self):
        """Test the LogLevel enum."""
        self.assertEqual(LogLevel.DEBUG, "debug")
        self.assertEqual(LogLevel.INFO, "info")
        self.assertEqual(LogLevel.WARNING, "warning")
        self.assertEqual(LogLevel.ERROR, "error")
        self.assertEqual(LogLevel.CRITICAL, "critical")

    def test_health_status_enum(self):
        """Test the HealthStatusEnum."""
        self.assertEqual(HealthStatusEnum.HEALTHY, "healthy")
        self.assertEqual(HealthStatusEnum.DEGRADED, "degraded")
        self.assertEqual(HealthStatusEnum.UNHEALTHY, "unhealthy")
        self.assertEqual(HealthStatusEnum.MAINTENANCE, "maintenance")
        self.assertEqual(HealthStatusEnum.UNKNOWN, "unknown")

    def test_metric_type_enum(self):
        """Test the MetricTypeEnum."""
        self.assertEqual(MetricTypeEnum.CPU, "cpu")
        self.assertEqual(MetricTypeEnum.MEMORY, "memory")
        self.assertEqual(MetricTypeEnum.DISK, "disk")
        self.assertEqual(MetricTypeEnum.NETWORK, "network")
        self.assertEqual(MetricTypeEnum.LATENCY, "latency")
        self.assertEqual(MetricTypeEnum.THROUGHPUT, "throughput")
        self.assertEqual(MetricTypeEnum.ERROR_RATE, "error_rate")
        self.assertEqual(MetricTypeEnum.CUSTOM, "custom")

    def test_service_log_base(self):
        """Test the ServiceLogBase model."""
        # Create a ServiceLogBase instance
        log_base = ServiceLogBase(
            endpoint_id=str(uuid.uuid4()),
            status="success",
            response_time=150.5,
            status_code="200",
            error_message=None,
            details={"method": "GET", "path": "/api/users"}
        )
        
        # Verify fields
        self.assertIsNotNone(log_base.endpoint_id)
        self.assertEqual(log_base.status, "success")
        self.assertEqual(log_base.response_time, 150.5)
        self.assertEqual(log_base.status_code, "200")
        self.assertIsNone(log_base.error_message)
        self.assertEqual(log_base.details, {"method": "GET", "path": "/api/users"})
        
        # Test model_dump (Pydantic v2 method)
        log_dict = log_base.model_dump()
        self.assertIsInstance(log_dict, dict)
        self.assertEqual(log_dict["status"], "success")
        self.assertEqual(log_dict["response_time"], 150.5)
        
        # Test JSON serialization
        log_json = log_base.model_dump_json()
        log_dict_from_json = json.loads(log_json)
        self.assertEqual(log_dict_from_json["status"], "success")
        self.assertEqual(log_dict_from_json["response_time"], 150.5)

    def test_service_log_create(self):
        """Test the ServiceLogCreate model."""
        # Create a ServiceLogCreate instance
        log_create = ServiceLogCreate(
            endpoint_id=str(uuid.uuid4()),
            status="success",
            response_time=150.5,
            status_code="200",
            error_message=None,
            details={"method": "GET", "path": "/api/users"}
        )
        
        # Verify fields
        self.assertIsNotNone(log_create.endpoint_id)
        self.assertEqual(log_create.status, "success")
        self.assertEqual(log_create.response_time, 150.5)
        
        # Test model_dump (Pydantic v2 method)
        log_dict = log_create.model_dump()
        self.assertIsInstance(log_dict, dict)
        self.assertEqual(log_dict["status"], "success")

    def test_service_log_update(self):
        """Test the ServiceLogUpdate model."""
        # Create a ServiceLogUpdate instance
        log_update = ServiceLogUpdate(
            status="updated",
            response_time=200.5,
            elasticsearch_synced=True
        )
        
        # Verify fields
        self.assertEqual(log_update.status, "updated")
        self.assertEqual(log_update.response_time, 200.5)
        self.assertTrue(log_update.elasticsearch_synced)
        
        # Test model_dump (Pydantic v2 method)
        log_dict = log_update.model_dump()
        self.assertIsInstance(log_dict, dict)
        self.assertEqual(log_dict["status"], "updated")
        self.assertTrue(log_dict["elasticsearch_synced"])
        
        # Test with some fields missing
        log_update_partial = ServiceLogUpdate(status="updated")
        self.assertEqual(log_update_partial.status, "updated")
        self.assertIsNone(log_update_partial.response_time)
        self.assertIsNone(log_update_partial.elasticsearch_synced)

    def test_service_log_in_db(self):
        """Test the ServiceLogInDB model."""
        # Create a ServiceLogInDB instance
        now = datetime.utcnow()
        log_in_db = ServiceLogInDB(
            id=str(uuid.uuid4()),
            endpoint_id=str(uuid.uuid4()),
            status="success",
            response_time=150.5,
            status_code="200",
            error_message=None,
            details={"method": "GET", "path": "/api/users"},
            created_at=now,
            elasticsearch_synced=True
        )
        
        # Verify fields
        self.assertIsNotNone(log_in_db.id)
        self.assertIsNotNone(log_in_db.endpoint_id)
        self.assertEqual(log_in_db.status, "success")
        self.assertEqual(log_in_db.created_at, now)
        self.assertTrue(log_in_db.elasticsearch_synced)
        
        # Test model_dump (Pydantic v2 method)
        log_dict = log_in_db.model_dump()
        self.assertIsInstance(log_dict, dict)
        self.assertEqual(log_dict["status"], "success")
        self.assertTrue(log_dict["elasticsearch_synced"])

    def test_log_search_params(self):
        """Test the LogSearchParams model."""
        # Create a LogSearchParams instance
        now = datetime.utcnow()
        search_params = LogSearchParams(
            service_names=["auth_service", "user_service"],
            log_levels=[LogLevel.ERROR, LogLevel.INFO],
            start_time=now - timedelta(days=1),
            end_time=now,
            trace_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            user_id=123,
            message_contains="error",
            request_path="/api/users",
            use_elasticsearch=True,
            offset=0,
            limit=50
        )
        
        # Verify fields
        self.assertEqual(search_params.service_names, ["auth_service", "user_service"])
        self.assertEqual(search_params.log_levels, [LogLevel.ERROR, LogLevel.INFO])
        self.assertEqual(search_params.start_time, now - timedelta(days=1))
        self.assertEqual(search_params.end_time, now)
        self.assertEqual(search_params.message_contains, "error")
        self.assertEqual(search_params.limit, 50)
        
        # Test model_dump (Pydantic v2 method)
        params_dict = search_params.model_dump()
        self.assertIsInstance(params_dict, dict)
        self.assertEqual(params_dict["service_names"], ["auth_service", "user_service"])
        self.assertEqual(params_dict["message_contains"], "error")

    def test_log_search_result(self):
        """Test the LogSearchResult model."""
        # Create sample logs
        now = datetime.utcnow()
        logs = [
            ServiceLogResponse(
                id=str(uuid.uuid4()),
                endpoint_id=str(uuid.uuid4()),
                status="success",
                response_time=150.5,
                status_code="200",
                error_message=None,
                details={"method": "GET", "path": "/api/users"},
                created_at=now,
                elasticsearch_synced=True
            ),
            ServiceLogResponse(
                id=str(uuid.uuid4()),
                endpoint_id=str(uuid.uuid4()),
                status="error",
                response_time=450.2,
                status_code="500",
                error_message="Internal server error",
                details={"method": "POST", "path": "/api/users"},
                created_at=now,
                elasticsearch_synced=True
            )
        ]
        
        # Create a LogSearchResult instance
        search_result = LogSearchResult(logs=logs, total=2)
        
        # Verify fields
        self.assertEqual(len(search_result.logs), 2)
        self.assertEqual(search_result.total, 2)
        self.assertEqual(search_result.logs[0].status, "success")
        self.assertEqual(search_result.logs[1].status, "error")
        
        # Test model_dump (Pydantic v2 method)
        result_dict = search_result.model_dump()
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(len(result_dict["logs"]), 2)
        self.assertEqual(result_dict["total"], 2)

    def test_health_check_component_status(self):
        """Test the HealthCheckComponentStatus model."""
        # Create a HealthCheckComponentStatus instance
        component_status = HealthCheckComponentStatus(
            name="database",
            status=HealthStatusEnum.HEALTHY,
            details="Database is healthy and responding within expected time"
        )
        
        # Verify fields
        self.assertEqual(component_status.name, "database")
        self.assertEqual(component_status.status, HealthStatusEnum.HEALTHY)
        self.assertEqual(component_status.details, "Database is healthy and responding within expected time")
        
        # Test model_dump (Pydantic v2 method)
        status_dict = component_status.model_dump()
        self.assertIsInstance(status_dict, dict)
        self.assertEqual(status_dict["name"], "database")
        self.assertEqual(status_dict["status"], "healthy")

    def test_health_check_response(self):
        """Test the HealthCheckResponse model."""
        # Create component statuses
        components = [
            HealthCheckComponentStatus(
                name="database",
                status=HealthStatusEnum.HEALTHY,
                details="Database is healthy"
            ),
            HealthCheckComponentStatus(
                name="cache",
                status=HealthStatusEnum.HEALTHY,
                details="Cache is healthy"
            ),
            HealthCheckComponentStatus(
                name="api",
                status=HealthStatusEnum.DEGRADED,
                details="API is experiencing high latency"
            )
        ]
        
        # Create a HealthCheckResponse instance
        now = datetime.utcnow()
        health_check = HealthCheckResponse(
            status=HealthStatusEnum.DEGRADED,
            timestamp=now,
            components=components
        )
        
        # Verify fields
        self.assertEqual(health_check.status, HealthStatusEnum.DEGRADED)
        self.assertEqual(health_check.timestamp, now)
        self.assertEqual(len(health_check.components), 3)
        self.assertEqual(health_check.components[0].name, "database")
        self.assertEqual(health_check.components[2].status, HealthStatusEnum.DEGRADED)
        
        # Test model_dump (Pydantic v2 method)
        health_dict = health_check.model_dump()
        self.assertIsInstance(health_dict, dict)
        self.assertEqual(health_dict["status"], "degraded")
        self.assertEqual(len(health_dict["components"]), 3)

    def test_service_health_report(self):
        """Test the ServiceHealthReport model."""
        # Create a ServiceHealthReport instance
        now = datetime.utcnow()
        health_report = ServiceHealthReport(
            service_name="auth_service",
            status=HealthStatusEnum.HEALTHY,
            uptime_percentage=99.95,
            average_response_time=120.5,
            error_count=5,
            outage_count=1,
            total_outage_duration=300,
            start_time=now - timedelta(days=7),
            end_time=now
        )
        
        # Verify fields
        self.assertEqual(health_report.service_name, "auth_service")
        self.assertEqual(health_report.status, HealthStatusEnum.HEALTHY)
        self.assertEqual(health_report.uptime_percentage, 99.95)
        self.assertEqual(health_report.average_response_time, 120.5)
        self.assertEqual(health_report.error_count, 5)
        self.assertEqual(health_report.outage_count, 1)
        self.assertEqual(health_report.total_outage_duration, 300)
        
        # Test model_dump (Pydantic v2 method)
        report_dict = health_report.model_dump()
        self.assertIsInstance(report_dict, dict)
        self.assertEqual(report_dict["service_name"], "auth_service")
        self.assertEqual(report_dict["status"], "healthy")
        self.assertEqual(report_dict["uptime_percentage"], 99.95)


if __name__ == "__main__":
    unittest.main()
