"""
Tests for the service availability models in the monitoring module.

This module contains tests for the models used in service availability monitoring,
ensuring that they function correctly and are compatible with Pydantic v2.
"""

import unittest
from datetime import datetime, timedelta
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from modules.monitoring.models.service_availability import (
    ProtocolType, StatusType, SeverityLevel, NotificationType,
    ServiceEndpoint, ServiceStatus, ServiceOutage, ServiceAlert, MaintenanceWindow,
    generate_uuid
)


class TestServiceAvailabilityModels(unittest.TestCase):
    """Test cases for the service availability models."""

    def setUp(self):
        """Set up test environment."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        
        # Create all tables
        from backend_core.database import Base
        Base.metadata.create_all(self.engine)
        
        # Create session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        
    def tearDown(self):
        """Clean up after tests."""
        self.db.close()
    
    def test_generate_uuid(self):
        """Test UUID generation function."""
        uuid_str = generate_uuid()
        self.assertIsInstance(uuid_str, str)
        # Verify it's a valid UUID
        try:
            uuid_obj = uuid.UUID(uuid_str)
            self.assertEqual(str(uuid_obj), uuid_str)
        except ValueError:
            self.fail("generate_uuid() did not return a valid UUID string")
    
    def test_protocol_type_enum(self):
        """Test the ProtocolType enum."""
        self.assertEqual(ProtocolType.HTTP.value, "http")
        self.assertEqual(ProtocolType.HTTPS.value, "https")
        self.assertEqual(ProtocolType.TCP.value, "tcp")
        self.assertEqual(ProtocolType.UDP.value, "udp")
        self.assertEqual(ProtocolType.ICMP.value, "icmp")
        self.assertEqual(ProtocolType.DNS.value, "dns")
        self.assertEqual(ProtocolType.RADIUS.value, "radius")
        self.assertEqual(ProtocolType.CUSTOM.value, "custom")
    
    def test_status_type_enum(self):
        """Test the StatusType enum."""
        self.assertEqual(StatusType.UP.value, "up")
        self.assertEqual(StatusType.DOWN.value, "down")
        self.assertEqual(StatusType.DEGRADED.value, "degraded")
        self.assertEqual(StatusType.MAINTENANCE.value, "maintenance")
        self.assertEqual(StatusType.UNKNOWN.value, "unknown")
    
    def test_severity_level_enum(self):
        """Test the SeverityLevel enum."""
        self.assertEqual(SeverityLevel.CRITICAL.value, "critical")
        self.assertEqual(SeverityLevel.HIGH.value, "high")
        self.assertEqual(SeverityLevel.MEDIUM.value, "medium")
        self.assertEqual(SeverityLevel.LOW.value, "low")
    
    def test_notification_type_enum(self):
        """Test the NotificationType enum."""
        self.assertEqual(NotificationType.EMAIL.value, "email")
        self.assertEqual(NotificationType.SMS.value, "sms")
        self.assertEqual(NotificationType.SLACK.value, "slack")
        self.assertEqual(NotificationType.WEBHOOK.value, "webhook")
        self.assertEqual(NotificationType.PAGERDUTY.value, "pagerduty")
    
    def test_service_endpoint_model(self):
        """Test the ServiceEndpoint model."""
        # Create a service endpoint
        endpoint = ServiceEndpoint(
            id=generate_uuid(),
            name="Test API",
            description="Test API endpoint",
            url="https://api.example.com",
            protocol=ProtocolType.HTTPS,
            port=443,
            check_interval=60,
            timeout=5,
            retries=3,
            expected_status_code=200,
            expected_response_pattern=None,
            is_active=True
        )
        
        # Add to database
        self.db.add(endpoint)
        self.db.commit()
        
        # Retrieve from database
        db_endpoint = self.db.query(ServiceEndpoint).filter_by(name="Test API").first()
        
        # Verify attributes
        self.assertIsNotNone(db_endpoint)
        self.assertEqual(db_endpoint.name, "Test API")
        self.assertEqual(db_endpoint.description, "Test API endpoint")
        self.assertEqual(db_endpoint.url, "https://api.example.com")
        self.assertEqual(db_endpoint.protocol, ProtocolType.HTTPS)
        self.assertEqual(db_endpoint.port, 443)
        self.assertEqual(db_endpoint.check_interval, 60)
        self.assertEqual(db_endpoint.timeout, 5)
        self.assertEqual(db_endpoint.retries, 3)
        self.assertEqual(db_endpoint.expected_status_code, 200)
        self.assertIsNone(db_endpoint.expected_response_pattern)
        self.assertTrue(db_endpoint.is_active)
        self.assertIsInstance(db_endpoint.created_at, datetime)
        self.assertIsInstance(db_endpoint.updated_at, datetime)
    
    def test_service_status_model(self):
        """Test the ServiceStatus model."""
        # Create a service endpoint first
        endpoint = ServiceEndpoint(
            id=generate_uuid(),
            name="Status Test API",
            url="https://status.example.com",
            protocol=ProtocolType.HTTPS
        )
        self.db.add(endpoint)
        self.db.commit()
        
        # Create a service status
        status = ServiceStatus(
            id=generate_uuid(),
            endpoint_id=endpoint.id,
            status=StatusType.UP,
            response_time=0.345,
            status_message="Service is up and running",
            elasticsearch_synced=False
        )
        
        # Add to database
        self.db.add(status)
        self.db.commit()
        
        # Retrieve from database
        db_status = self.db.query(ServiceStatus).filter_by(endpoint_id=endpoint.id).first()
        
        # Verify attributes
        self.assertIsNotNone(db_status)
        self.assertEqual(db_status.endpoint_id, endpoint.id)
        self.assertEqual(db_status.status, StatusType.UP)
        self.assertAlmostEqual(db_status.response_time, 0.345)
        self.assertEqual(db_status.status_message, "Service is up and running")
        self.assertFalse(db_status.elasticsearch_synced)
        self.assertIsInstance(db_status.timestamp, datetime)
        
        # Test relationship
        self.assertEqual(db_status.endpoint.id, endpoint.id)
        self.assertEqual(db_status.endpoint.name, "Status Test API")
    
    def test_service_outage_model(self):
        """Test the ServiceOutage model."""
        # Create a service endpoint first
        endpoint = ServiceEndpoint(
            id=generate_uuid(),
            name="Outage Test API",
            url="https://outage.example.com",
            protocol=ProtocolType.HTTPS
        )
        self.db.add(endpoint)
        self.db.commit()
        
        # Create a service outage
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow() - timedelta(hours=1)
        duration = int((end_time - start_time).total_seconds())
        
        outage = ServiceOutage(
            id=generate_uuid(),
            endpoint_id=endpoint.id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            severity=SeverityLevel.HIGH,
            affected_customers=150,
            resolution_notes="Fixed network connectivity issue",
            elasticsearch_synced=False
        )
        
        # Add to database
        self.db.add(outage)
        self.db.commit()
        
        # Retrieve from database
        db_outage = self.db.query(ServiceOutage).filter_by(endpoint_id=endpoint.id).first()
        
        # Verify attributes
        self.assertIsNotNone(db_outage)
        self.assertEqual(db_outage.endpoint_id, endpoint.id)
        self.assertEqual(db_outage.start_time, start_time)
        self.assertEqual(db_outage.end_time, end_time)
        self.assertEqual(db_outage.duration, duration)
        self.assertEqual(db_outage.severity, SeverityLevel.HIGH)
        self.assertEqual(db_outage.affected_customers, 150)
        self.assertEqual(db_outage.resolution_notes, "Fixed network connectivity issue")
        self.assertFalse(db_outage.elasticsearch_synced)
        
        # Test relationship
        self.assertEqual(db_outage.endpoint.id, endpoint.id)
        self.assertEqual(db_outage.endpoint.name, "Outage Test API")
    
    def test_service_alert_model(self):
        """Test the ServiceAlert model."""
        # Create a service endpoint first
        endpoint = ServiceEndpoint(
            id=generate_uuid(),
            name="Alert Test API",
            url="https://alert.example.com",
            protocol=ProtocolType.HTTPS
        )
        self.db.add(endpoint)
        self.db.commit()
        
        # Create a service outage
        outage = ServiceOutage(
            id=generate_uuid(),
            endpoint_id=endpoint.id,
            start_time=datetime.utcnow() - timedelta(hours=1),
            severity=SeverityLevel.CRITICAL
        )
        self.db.add(outage)
        self.db.commit()
        
        # Create a service alert
        alert = ServiceAlert(
            id=generate_uuid(),
            outage_id=outage.id,
            notification_type=NotificationType.EMAIL,
            recipients="admin@example.com,ops@example.com",
            message="Critical service outage detected",
            delivered=True,
            delivery_time=datetime.utcnow()
        )
        
        # Add to database
        self.db.add(alert)
        self.db.commit()
        
        # Retrieve from database
        db_alert = self.db.query(ServiceAlert).filter_by(outage_id=outage.id).first()
        
        # Verify attributes
        self.assertIsNotNone(db_alert)
        self.assertEqual(db_alert.outage_id, outage.id)
        self.assertEqual(db_alert.notification_type, NotificationType.EMAIL)
        self.assertEqual(db_alert.recipients, "admin@example.com,ops@example.com")
        self.assertEqual(db_alert.message, "Critical service outage detected")
        self.assertTrue(db_alert.delivered)
        self.assertIsInstance(db_alert.delivery_time, datetime)
        self.assertIsInstance(db_alert.alert_time, datetime)
        
        # Test relationship
        self.assertEqual(db_alert.outage.id, outage.id)
        self.assertEqual(db_alert.outage.endpoint_id, endpoint.id)
    
    def test_maintenance_window_model(self):
        """Test the MaintenanceWindow model."""
        # Create a maintenance window
        start_time = datetime.utcnow() + timedelta(days=1)
        end_time = start_time + timedelta(hours=4)
        
        window = MaintenanceWindow(
            id=generate_uuid(),
            name="Scheduled Network Maintenance",
            description="Upgrading network equipment",
            start_time=start_time,
            end_time=end_time,
            affected_services="api,auth,billing",
            created_by="admin"
        )
        
        # Add to database
        self.db.add(window)
        self.db.commit()
        
        # Retrieve from database
        db_window = self.db.query(MaintenanceWindow).filter_by(name="Scheduled Network Maintenance").first()
        
        # Verify attributes
        self.assertIsNotNone(db_window)
        self.assertEqual(db_window.name, "Scheduled Network Maintenance")
        self.assertEqual(db_window.description, "Upgrading network equipment")
        self.assertEqual(db_window.start_time, start_time)
        self.assertEqual(db_window.end_time, end_time)
        self.assertEqual(db_window.affected_services, "api,auth,billing")
        self.assertEqual(db_window.created_by, "admin")
        self.assertIsInstance(db_window.created_at, datetime)
        self.assertIsInstance(db_window.updated_at, datetime)
        
        # Test is_active method
        self.assertFalse(db_window.is_active())  # Should be false since it's in the future
        
        # Test affects_service method
        self.assertTrue(db_window.affects_service("api"))
        self.assertTrue(db_window.affects_service("auth"))
        self.assertTrue(db_window.affects_service("billing"))
        self.assertFalse(db_window.affects_service("monitoring"))


if __name__ == "__main__":
    unittest.main()
