#!/usr/bin/env python
"""
Integration test for service availability monitoring.

This script tests the integration of the service availability monitoring
components with the rest of the ISP Management Platform.
"""

import os
import sys
import unittest
import logging
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_service_monitoring_integration")

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variables for testing
os.environ["TESTING"] = "True"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ELASTICSEARCH_HOSTS"] = "http://localhost:9200"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SERVICE_CHECK_INTERVAL"] = "60"
os.environ["OUTAGE_DETECTION_THRESHOLD"] = "3"
os.environ["SERVICE_CHECK_TIMEOUT"] = "5"

# Import mock dependencies
try:
    from tests.mock_dependencies import setup_mock_dependencies
    mock_deps = setup_mock_dependencies()
    logger.info("Successfully set up mock dependencies")
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Running standalone tests instead...")
    from scripts.test_service_monitoring_core import TestServiceAvailabilityMonitoring
    logger.info("Running standalone service availability monitoring tests...")
    unittest.main(module='scripts.test_service_monitoring_core')
    sys.exit(0)

# Import required modules
try:
    # Import database models
    from backend_core.database import Base, get_engine, get_db
    from modules.monitoring.models.service_availability import (
        ServiceEndpoint, ServiceStatus, ServiceOutage, MaintenanceWindow,
        ProtocolType, StatusType, SeverityLevel
    )
    
    # Import services and collectors
    from modules.monitoring.services.availability_service import AvailabilityService
    from modules.monitoring.collectors.service_availability_collector import ServiceAvailabilityCollector
    
    logger.info("Successfully imported required modules")
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Running standalone tests instead...")
    from scripts.test_service_monitoring_core import TestServiceAvailabilityMonitoring
    logger.info("Running standalone service availability monitoring tests...")
    unittest.main(module='scripts.test_service_monitoring_core')
    sys.exit(0)

# Set up test database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create in-memory SQLite database
engine = create_engine("sqlite:///:memory:", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Create test data
def create_test_data():
    """Create test data for integration tests."""
    db = SessionLocal()
    try:
        # Create service endpoints
        endpoints = [
            ServiceEndpoint(
                id="http-endpoint-1",
                name="Example API",
                url="https://api.example.com/health",
                protocol=ProtocolType.HTTPS,
                check_interval=60,
                timeout=5,
                retries=3,
                expected_status_code=200,
                expected_pattern="healthy",
                is_active=True
            ),
            ServiceEndpoint(
                id="tcp-endpoint-1",
                name="Example Database",
                url="db.example.com:5432",
                protocol=ProtocolType.TCP,
                check_interval=60,
                timeout=5,
                retries=3,
                is_active=True
            ),
            ServiceEndpoint(
                id="icmp-endpoint-1",
                name="Example Server",
                url="server.example.com",
                protocol=ProtocolType.ICMP,
                check_interval=60,
                timeout=5,
                retries=3,
                is_active=True
            ),
            ServiceEndpoint(
                id="inactive-endpoint-1",
                name="Inactive Service",
                url="inactive.example.com",
                protocol=ProtocolType.HTTP,
                check_interval=60,
                timeout=5,
                retries=3,
                is_active=False
            )
        ]
        
        for endpoint in endpoints:
            db.add(endpoint)
        
        # Create maintenance window
        now = datetime.utcnow()
        maintenance_window = MaintenanceWindow(
            id="maintenance-1",
            endpoint_id="http-endpoint-1",
            name="Scheduled Maintenance",
            description="System upgrade",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            is_active=True
        )
        db.add(maintenance_window)
        
        # Create service statuses
        statuses = [
            ServiceStatus(
                id="status-1",
                endpoint_id="http-endpoint-1",
                status=StatusType.MAINTENANCE,
                response_time=0.5,
                timestamp=now - timedelta(minutes=5)
            ),
            ServiceStatus(
                id="status-2",
                endpoint_id="tcp-endpoint-1",
                status=StatusType.UP,
                response_time=0.1,
                timestamp=now - timedelta(minutes=5)
            ),
            ServiceStatus(
                id="status-3",
                endpoint_id="icmp-endpoint-1",
                status=StatusType.UP,
                response_time=0.05,
                timestamp=now - timedelta(minutes=5)
            )
        ]
        
        for status in statuses:
            db.add(status)
        
        # Create service outage
        outage = ServiceOutage(
            id="outage-1",
            endpoint_id="tcp-endpoint-1",
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(hours=23),
            severity=SeverityLevel.HIGH,
            description="Network issue",
            resolved=True,
            resolution_notes="Network issue resolved"
        )
        db.add(outage)
        
        db.commit()
        logger.info("Successfully created test data")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating test data: {e}")
        raise
    finally:
        db.close()


class TestServiceAvailabilityIntegration(unittest.TestCase):
    """Integration tests for service availability monitoring."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        # Create test data
        create_test_data()
        
        # Create services
        cls.db = SessionLocal()
        cls.availability_service = AvailabilityService(cls.db)
        cls.collector = ServiceAvailabilityCollector(cls.db)
    
    @classmethod
    def tearDownClass(cls):
        """Tear down test class."""
        cls.db.close()
    
    def setUp(self):
        """Set up test case."""
        # Create a new session for each test
        self.db = SessionLocal()
        self.availability_service = AvailabilityService(self.db)
        self.collector = ServiceAvailabilityCollector(self.db)
    
    def tearDown(self):
        """Tear down test case."""
        self.db.close()
    
    def test_get_all_endpoints(self):
        """Test getting all service endpoints."""
        endpoints = self.availability_service.get_all_endpoints()
        self.assertEqual(len(endpoints), 4)
        
        active_endpoints = self.availability_service.get_all_endpoints(active_only=True)
        self.assertEqual(len(active_endpoints), 3)
    
    def test_get_endpoint(self):
        """Test getting a specific service endpoint."""
        endpoint = self.availability_service.get_endpoint("http-endpoint-1")
        self.assertIsNotNone(endpoint)
        self.assertEqual(endpoint.name, "Example API")
        self.assertEqual(endpoint.protocol, ProtocolType.HTTPS)
    
    def test_create_endpoint(self):
        """Test creating a service endpoint."""
        endpoint_data = {
            "name": "New API",
            "url": "https://new-api.example.com/health",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 120,
            "timeout": 10,
            "retries": 5,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = self.availability_service.create_endpoint(endpoint_data)
        self.assertIsNotNone(endpoint)
        self.assertEqual(endpoint.name, "New API")
        self.assertEqual(endpoint.protocol, ProtocolType.HTTPS)
        self.assertEqual(endpoint.check_interval, 120)
    
    def test_update_endpoint(self):
        """Test updating a service endpoint."""
        update_data = {
            "name": "Updated API",
            "check_interval": 180,
            "timeout": 15
        }
        
        updated = self.availability_service.update_endpoint("http-endpoint-1", update_data)
        self.assertTrue(updated)
    
    def test_is_in_maintenance(self):
        """Test checking if a service is in maintenance."""
        in_maintenance = self.availability_service.is_in_maintenance("http-endpoint-1")
        self.assertTrue(in_maintenance)
        
        not_in_maintenance = self.availability_service.is_in_maintenance("tcp-endpoint-1")
        self.assertFalse(not_in_maintenance)
    
    def test_collect_all_services(self):
        """Test collecting all services."""
        # Mock the service checks to return successful responses
        with mock.patch.object(self.collector, '_check_http_service', return_value=(StatusType.UP, 0.5, None)), \
             mock.patch.object(self.collector, '_check_tcp_service', return_value=(StatusType.UP, 0.1, None)), \
             mock.patch.object(self.collector, '_check_icmp_service', return_value=(StatusType.UP, 0.05, None)):
            
            results = self.collector.collect_all_services()
            self.assertIsNotNone(results)
            self.assertEqual(len(results), 3)  # Only active endpoints


if __name__ == "__main__":
    unittest.main()
