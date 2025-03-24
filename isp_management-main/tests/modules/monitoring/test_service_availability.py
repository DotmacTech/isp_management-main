"""
Unit tests for service availability monitoring.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, ServiceOutage, MaintenanceWindow,
    ProtocolType, StatusType, SeverityLevel
)
from modules.monitoring.services.availability_service import AvailabilityService
from modules.monitoring.services.availability_service_outage import OutageManagementService
from modules.monitoring.collectors.service_availability_collector import (
    ServiceAvailabilityCollector,
    collect_service_availability,
    collect_specific_service_availability
)


class TestServiceEndpoint:
    """Tests for ServiceEndpoint model and related functionality."""

    def test_create_endpoint(self, db_session):
        """Test creating a service endpoint."""
        service = AvailabilityService(db_session)
        
        endpoint_data = {
            "id": "test-endpoint",
            "name": "Test Endpoint",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        assert endpoint.id == "test-endpoint"
        assert endpoint.name == "Test Endpoint"
        assert endpoint.url == "https://example.com"
        assert endpoint.protocol == ProtocolType.HTTPS
        assert endpoint.check_interval == 60
        assert endpoint.timeout == 5
        assert endpoint.retries == 3
        assert endpoint.expected_status_code == 200
        assert endpoint.is_active is True
        
        # Clean up
        db_session.delete(endpoint)
        db_session.commit()

    def test_update_endpoint(self, db_session):
        """Test updating a service endpoint."""
        service = AvailabilityService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-endpoint",
            "name": "Test Endpoint",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Update endpoint
        update_data = {
            "name": "Updated Test Endpoint",
            "url": "https://updated-example.com",
            "check_interval": 120,
            "is_active": False
        }
        
        updated_endpoint = service.update_endpoint(endpoint.id, update_data)
        
        assert updated_endpoint.id == "test-endpoint"
        assert updated_endpoint.name == "Updated Test Endpoint"
        assert updated_endpoint.url == "https://updated-example.com"
        assert updated_endpoint.protocol == ProtocolType.HTTPS  # Unchanged
        assert updated_endpoint.check_interval == 120
        assert updated_endpoint.timeout == 5  # Unchanged
        assert updated_endpoint.retries == 3  # Unchanged
        assert updated_endpoint.expected_status_code == 200  # Unchanged
        assert updated_endpoint.is_active is False
        
        # Clean up
        db_session.delete(updated_endpoint)
        db_session.commit()

    def test_delete_endpoint(self, db_session):
        """Test deleting a service endpoint."""
        service = AvailabilityService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-endpoint",
            "name": "Test Endpoint",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Delete endpoint
        result = service.delete_endpoint(endpoint.id)
        
        assert result is True
        
        # Verify endpoint is deleted
        deleted_endpoint = service.get_endpoint(endpoint.id)
        assert deleted_endpoint is None


class TestServiceStatus:
    """Tests for ServiceStatus model and related functionality."""

    def test_check_service_https(self, db_session):
        """Test checking an HTTPS service endpoint."""
        service = AvailabilityService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-https",
            "name": "Test HTTPS",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Mock requests.get
        with patch('modules.monitoring.services.availability_service.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response
            
            # Check service
            status = service.check_service(endpoint.id)
            
            assert status.endpoint_id == endpoint.id
            assert status.status == StatusType.UP
            assert status.response_time is not None
            assert status.error_message is None
        
        # Clean up
        db_session.delete(endpoint)
        db_session.commit()

    def test_check_service_http_failure(self, db_session):
        """Test checking an HTTP service endpoint that fails."""
        service = AvailabilityService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-http-fail",
            "name": "Test HTTP Fail",
            "url": "http://nonexistent-domain-123456.com",
            "protocol": ProtocolType.HTTP,
            "check_interval": 60,
            "timeout": 2,
            "retries": 1,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Mock requests.get to raise exception
        with patch('modules.monitoring.services.availability_service.requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")
            
            # Check service
            status = service.check_service(endpoint.id)
            
            assert status.endpoint_id == endpoint.id
            assert status.status == StatusType.DOWN
            assert status.response_time is None
            assert "Connection error" in status.error_message
        
        # Clean up
        db_session.delete(endpoint)
        db_session.commit()

    def test_check_service_tcp(self, db_session):
        """Test checking a TCP service endpoint."""
        service = AvailabilityService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-tcp",
            "name": "Test TCP",
            "url": "example.com:80",
            "protocol": ProtocolType.TCP,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Mock socket connection
        with patch('modules.monitoring.services.availability_service.socket.create_connection') as mock_connect:
            mock_socket = MagicMock()
            mock_connect.return_value = mock_socket
            
            # Check service
            status = service.check_service(endpoint.id)
            
            assert status.endpoint_id == endpoint.id
            assert status.status == StatusType.UP
            assert status.response_time is not None
            assert status.error_message is None
        
        # Clean up
        db_session.delete(endpoint)
        db_session.commit()


class TestServiceOutage:
    """Tests for ServiceOutage model and related functionality."""

    def test_create_outage(self, db_session):
        """Test creating a service outage."""
        service = AvailabilityService(db_session)
        outage_service = OutageManagementService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-outage",
            "name": "Test Outage",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Create outage
        outage_data = {
            "endpoint_id": endpoint.id,
            "severity": SeverityLevel.MAJOR,
            "description": "Test outage",
            "start_time": datetime.utcnow() - timedelta(minutes=30),
            "notification_channels": ["email"]
        }
        
        outage = outage_service.create_outage(outage_data)
        
        assert outage.endpoint_id == endpoint.id
        assert outage.severity == SeverityLevel.MAJOR
        assert outage.description == "Test outage"
        assert outage.resolved is False
        assert outage.resolved_at is None
        assert outage.resolution_notes is None
        
        # Clean up
        db_session.delete(outage)
        db_session.delete(endpoint)
        db_session.commit()

    def test_resolve_outage(self, db_session):
        """Test resolving a service outage."""
        service = AvailabilityService(db_session)
        outage_service = OutageManagementService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-outage",
            "name": "Test Outage",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Create outage
        outage_data = {
            "endpoint_id": endpoint.id,
            "severity": SeverityLevel.MAJOR,
            "description": "Test outage",
            "start_time": datetime.utcnow() - timedelta(minutes=30),
            "notification_channels": ["email"]
        }
        
        outage = outage_service.create_outage(outage_data)
        
        # Resolve outage
        resolution_notes = "Fixed the issue"
        resolved_outage = outage_service.resolve_outage(outage.id, resolution_notes)
        
        assert resolved_outage.endpoint_id == endpoint.id
        assert resolved_outage.resolved is True
        assert resolved_outage.resolved_at is not None
        assert resolved_outage.resolution_notes == resolution_notes
        
        # Clean up
        db_session.delete(outage)
        db_session.delete(endpoint)
        db_session.commit()

    def test_outage_detection(self, db_session):
        """Test outage detection based on consecutive failures."""
        service = AvailabilityService(db_session)
        outage_service = OutageManagementService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-outage-detection",
            "name": "Test Outage Detection",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Create multiple failure statuses
        for i in range(5):
            status = ServiceStatus(
                id=str(uuid.uuid4()),
                endpoint_id=endpoint.id,
                status=StatusType.DOWN,
                timestamp=datetime.utcnow() - timedelta(minutes=5-i),
                error_message="Simulated failure for testing",
                elasticsearch_synced=False
            )
            db_session.add(status)
        
        db_session.commit()
        
        # Process potential outages
        outage_service.process_potential_outages(endpoint_id=endpoint.id)
        
        # Check if outage was created
        outages = outage_service.get_active_outages(endpoint_id=endpoint.id)
        
        assert len(outages) == 1
        assert outages[0].endpoint_id == endpoint.id
        assert outages[0].resolved is False
        
        # Clean up
        db_session.delete(outages[0])
        db_session.delete(endpoint)
        db_session.commit()


class TestMaintenanceWindow:
    """Tests for MaintenanceWindow model and related functionality."""

    def test_create_maintenance_window(self, db_session):
        """Test creating a maintenance window."""
        service = AvailabilityService(db_session)
        outage_service = OutageManagementService(db_session)
        
        # Create endpoints
        endpoint1_data = {
            "id": "test-maintenance-1",
            "name": "Test Maintenance 1",
            "url": "https://example1.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint2_data = {
            "id": "test-maintenance-2",
            "name": "Test Maintenance 2",
            "url": "https://example2.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint1 = service.create_endpoint(endpoint1_data)
        endpoint2 = service.create_endpoint(endpoint2_data)
        
        # Create maintenance window
        window_data = {
            "endpoint_ids": [endpoint1.id, endpoint2.id],
            "start_time": datetime.utcnow() - timedelta(minutes=15),
            "end_time": datetime.utcnow() + timedelta(hours=1),
            "description": "Test maintenance window",
            "created_by": "test_user"
        }
        
        window = outage_service.create_maintenance_window(window_data)
        
        assert window.description == "Test maintenance window"
        assert window.created_by == "test_user"
        assert window.is_active() is True
        assert len(window.endpoints) == 2
        
        # Clean up
        db_session.delete(window)
        db_session.delete(endpoint1)
        db_session.delete(endpoint2)
        db_session.commit()

    def test_is_in_maintenance(self, db_session):
        """Test checking if an endpoint is in maintenance."""
        service = AvailabilityService(db_session)
        outage_service = OutageManagementService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-in-maintenance",
            "name": "Test In Maintenance",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Create maintenance window
        window_data = {
            "endpoint_ids": [endpoint.id],
            "start_time": datetime.utcnow() - timedelta(minutes=15),
            "end_time": datetime.utcnow() + timedelta(hours=1),
            "description": "Test maintenance window",
            "created_by": "test_user"
        }
        
        window = outage_service.create_maintenance_window(window_data)
        
        # Check if endpoint is in maintenance
        is_in_maintenance = outage_service.is_in_maintenance(endpoint.id)
        
        assert is_in_maintenance is True
        
        # Clean up
        db_session.delete(window)
        db_session.delete(endpoint)
        db_session.commit()


class TestServiceAvailabilityCollector:
    """Tests for ServiceAvailabilityCollector."""

    def test_collect_service(self, db_session):
        """Test collecting availability data for a specific service."""
        service = AvailabilityService(db_session)
        
        # Create endpoint
        endpoint_data = {
            "id": "test-collector",
            "name": "Test Collector",
            "url": "https://example.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint = service.create_endpoint(endpoint_data)
        
        # Mock check_service
        with patch('modules.monitoring.services.availability_service.AvailabilityService.check_service') as mock_check:
            mock_status = MagicMock()
            mock_status.status = StatusType.UP
            mock_status.response_time = 100.0
            mock_check.return_value = mock_status
            
            # Collect service data
            collector = ServiceAvailabilityCollector(db_session)
            result = collector.collect_service(endpoint.id)
            
            assert result["endpoint_id"] == endpoint.id
            assert result["status"] == StatusType.UP.value
            assert result["response_time"] == 100.0
            assert result["success"] is True
            assert result["error"] is None
        
        # Clean up
        db_session.delete(endpoint)
        db_session.commit()

    def test_collect_all_services(self, db_session):
        """Test collecting availability data for all services."""
        service = AvailabilityService(db_session)
        
        # Create endpoints
        endpoint1_data = {
            "id": "test-collector-1",
            "name": "Test Collector 1",
            "url": "https://example1.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint2_data = {
            "id": "test-collector-2",
            "name": "Test Collector 2",
            "url": "https://example2.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        }
        
        endpoint1 = service.create_endpoint(endpoint1_data)
        endpoint2 = service.create_endpoint(endpoint2_data)
        
        # Mock check_service
        with patch('modules.monitoring.services.availability_service.AvailabilityService.check_service') as mock_check:
            mock_status = MagicMock()
            mock_status.status = StatusType.UP
            mock_status.response_time = 100.0
            mock_check.return_value = mock_status
            
            # Collect all services data
            collector = ServiceAvailabilityCollector(db_session)
            result = collector.collect_all_services()
            
            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert result["in_maintenance"] == 0
            assert result["by_status"][StatusType.UP.value] == 2
        
        # Clean up
        db_session.delete(endpoint1)
        db_session.delete(endpoint2)
        db_session.commit()


import pytest
import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, ANY
from sqlalchemy.orm import Session

from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, ServiceOutage, MaintenanceWindow,
    ProtocolType, StatusType, SeverityLevel
)
from modules.monitoring.collectors.service_availability_collector import (
    ServiceAvailabilityCollector,
    collect_service_availability,
    collect_specific_service_availability
)
from modules.monitoring.routes.service_availability import router
from modules.monitoring.tasks.service_availability_tasks import (
    check_service_availability_task,
    sync_service_statuses_to_elasticsearch_task
)


@pytest.fixture
def mock_elasticsearch_client():
    """Mock ElasticsearchClient for testing."""
    with patch("modules.monitoring.collectors.service_availability_collector.ElasticsearchClient") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def sample_service_endpoints(db: Session):
    """Create sample service endpoints for testing."""
    endpoints = [
        ServiceEndpoint(
            id="test-http-service",
            name="Test HTTP Service",
            url="http://example.com/health",
            protocol=ProtocolType.HTTP,
            check_interval=60,
            timeout=5,
            retries=3,
            expected_status_code=200,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ServiceEndpoint(
            id="test-https-service",
            name="Test HTTPS Service",
            url="https://example.com/health",
            protocol=ProtocolType.HTTPS,
            check_interval=60,
            timeout=5,
            retries=3,
            expected_status_code=200,
            expected_response_pattern='"status":"UP"',
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ServiceEndpoint(
            id="test-tcp-service",
            name="Test TCP Service",
            url="example.com:80",
            protocol=ProtocolType.TCP,
            check_interval=60,
            timeout=5,
            retries=3,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ServiceEndpoint(
            id="test-udp-service",
            name="Test UDP Service",
            url="example.com:53",
            protocol=ProtocolType.UDP,
            check_interval=60,
            timeout=5,
            retries=3,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ServiceEndpoint(
            id="test-dns-service",
            name="Test DNS Service",
            url="example.com",
            protocol=ProtocolType.DNS,
            check_interval=60,
            timeout=5,
            retries=3,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ServiceEndpoint(
            id="test-icmp-service",
            name="Test ICMP Service",
            url="example.com",
            protocol=ProtocolType.ICMP,
            check_interval=60,
            timeout=5,
            retries=3,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ServiceEndpoint(
            id="inactive-service",
            name="Inactive Service",
            url="http://inactive.example.com",
            protocol=ProtocolType.HTTP,
            check_interval=60,
            timeout=5,
            retries=3,
            is_active=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    
    for endpoint in endpoints:
        db.add(endpoint)
    
    db.commit()
    
    for endpoint in endpoints:
        db.refresh(endpoint)
    
    yield endpoints
    
    # Clean up
    for endpoint in endpoints:
        db.delete(endpoint)
    
    db.commit()


@pytest.fixture
def sample_maintenance_window(db: Session, sample_service_endpoints):
    """Create a sample maintenance window for testing."""
    # Create maintenance window
    start_time = datetime.utcnow() - timedelta(hours=1)
    end_time = datetime.utcnow() + timedelta(hours=1)
    
    window = MaintenanceWindow(
        id=str(uuid.uuid4()),
        description="Scheduled maintenance for testing",
        start_time=start_time,
        end_time=end_time,
        created_by="test-user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(window)
    db.commit()
    db.refresh(window)
    
    # Add HTTP service to maintenance window
    http_endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTP)
    window.endpoints.append(http_endpoint)
    
    db.commit()
    db.refresh(window)
    
    yield window
    
    # Clean up
    db.delete(window)
    db.commit()


class TestServiceAvailabilityCollector:
    """Test the ServiceAvailabilityCollector class."""
    
    @patch("modules.monitoring.collectors.service_availability_collector.requests.get")
    def test_check_http_service_up(self, mock_get, db, sample_service_endpoints):
        """Test checking an HTTP service that is up."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"UP"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UP
        assert status.response_time is not None
        assert status.error_message is None
        assert mock_get.called
        mock_get.assert_called_with(
            endpoint.url,
            timeout=endpoint.timeout,
            verify=True
        )
    
    @patch("modules.monitoring.collectors.service_availability_collector.requests.get")
    def test_check_http_service_down(self, mock_get, db, sample_service_endpoints):
        """Test checking an HTTP service that is down."""
        # Setup
        mock_get.side_effect = Exception("Connection refused")
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.DOWN
        assert status.response_time is None
        assert "Connection refused" in status.error_message
        assert mock_get.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.requests.get")
    def test_check_http_service_degraded(self, mock_get, db, sample_service_endpoints):
        """Test checking an HTTP service that is degraded (wrong status code)."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.DEGRADED
        assert status.response_time is not None
        assert "Expected status code 200, got 500" in status.error_message
        assert mock_get.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.requests.get")
    def test_check_https_service_with_pattern_match(self, mock_get, db, sample_service_endpoints):
        """Test checking an HTTPS service with pattern matching."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"UP","version":"1.0"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTPS)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UP
        assert status.response_time is not None
        assert status.error_message is None
        assert mock_get.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.requests.get")
    def test_check_https_service_with_pattern_mismatch(self, mock_get, db, sample_service_endpoints):
        """Test checking an HTTPS service with pattern mismatch."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"DOWN","version":"1.0"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTPS)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.DEGRADED
        assert status.response_time is not None
        assert "Expected response pattern not found" in status.error_message
        assert mock_get.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.socket.socket")
    def test_check_tcp_service_up(self, mock_socket, db, sample_service_endpoints):
        """Test checking a TCP service that is up."""
        # Setup
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.TCP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UP
        assert status.response_time is not None
        assert status.error_message is None
        assert mock_socket_instance.connect_ex.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.socket.socket")
    def test_check_tcp_service_down(self, mock_socket, db, sample_service_endpoints):
        """Test checking a TCP service that is down."""
        # Setup
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect_ex.return_value = 1  # Connection refused
        mock_socket.return_value = mock_socket_instance
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.TCP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.DOWN
        assert status.response_time is None
        assert "Connection failed" in status.error_message
        assert mock_socket_instance.connect_ex.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.socket.socket")
    def test_check_udp_service_up(self, mock_socket, db, sample_service_endpoints):
        """Test checking a UDP service that is up."""
        # Setup
        mock_socket_instance = MagicMock()
        mock_socket_instance.recv.return_value = b'response data'
        mock_socket.return_value = mock_socket_instance
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.UDP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UP
        assert status.response_time is not None
        assert status.error_message is None
        assert mock_socket_instance.sendto.called
        assert mock_socket_instance.recv.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.socket.socket")
    def test_check_udp_service_down(self, mock_socket, db, sample_service_endpoints):
        """Test checking a UDP service that is down."""
        # Setup
        mock_socket_instance = MagicMock()
        mock_socket_instance.recv.side_effect = Exception("Timeout")
        mock_socket.return_value = mock_socket_instance
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.UDP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.DOWN
        assert status.response_time is None
        assert "Timeout" in status.error_message
        assert mock_socket_instance.sendto.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.socket.gethostbyname")
    def test_check_dns_service_up(self, mock_gethostbyname, db, sample_service_endpoints):
        """Test checking a DNS service that is up."""
        # Setup
        mock_gethostbyname.return_value = "93.184.216.34"  # example.com IP
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.DNS)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UP
        assert status.response_time is not None
        assert status.error_message is None
        assert mock_gethostbyname.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.socket.gethostbyname")
    def test_check_dns_service_down(self, mock_gethostbyname, db, sample_service_endpoints):
        """Test checking a DNS service that is down."""
        # Setup
        mock_gethostbyname.side_effect = Exception("DNS resolution failed")
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.DNS)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.DOWN
        assert status.response_time is None
        assert "DNS resolution failed" in status.error_message
        assert mock_gethostbyname.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.subprocess.run")
    def test_check_icmp_service_up(self, mock_run, db, sample_service_endpoints):
        """Test checking an ICMP service that is up."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "64 bytes from 93.184.216.34: icmp_seq=1 ttl=56 time=11.632 ms"
        mock_run.return_value = mock_process
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.ICMP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UP
        assert status.response_time is not None
        assert status.error_message is None
        assert mock_run.called
    
    @patch("modules.monitoring.collectors.service_availability_collector.subprocess.run")
    def test_check_icmp_service_down(self, mock_run, db, sample_service_endpoints):
        """Test checking an ICMP service that is down."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Request timeout for icmp_seq 0"
        mock_run.return_value = mock_process
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.ICMP)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.DOWN
        assert status.response_time is None
        assert "Ping failed" in status.error_message
        assert mock_run.called
    
    def test_check_inactive_service(self, db, sample_service_endpoints):
        """Test checking an inactive service."""
        # Setup
        endpoint = next(e for e in sample_service_endpoints if not e.is_active)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UNKNOWN
        assert status.response_time is None
        assert "Service is inactive" in status.error_message
    
    def test_check_service_in_maintenance(self, db, sample_service_endpoints, sample_maintenance_window):
        """Test checking a service that is in maintenance."""
        # Setup
        endpoint = next(e for e in sample_maintenance_window.endpoints)
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        
        # Verify
        assert status.endpoint_id == endpoint.id
        assert status.status == StatusType.UNKNOWN
        assert status.response_time is None
        assert "Service is in maintenance" in status.error_message
    
    @patch("modules.monitoring.collectors.service_availability_collector.requests.get")
    def test_detect_outage_new(self, mock_get, db, sample_service_endpoints):
        """Test detecting a new outage."""
        # Setup
        mock_get.side_effect = Exception("Connection refused")
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTP)
        collector = ServiceAvailabilityCollector(db)
        
        # Create previous DOWN statuses
        for _ in range(3):  # 3 consecutive failures
            status = ServiceStatus(
                id=str(uuid.uuid4()),
                endpoint_id=endpoint.id,
                status=StatusType.DOWN,
                timestamp=datetime.utcnow() - timedelta(minutes=5),
                error_message="Connection refused",
                elasticsearch_synced=True
            )
            db.add(status)
        
        db.commit()
        
        # Execute
        status = collector.check_service(endpoint)
        collector.process_service_status(status)
        
        # Verify
        outages = db.query(ServiceOutage).filter_by(endpoint_id=endpoint.id, resolved=False).all()
        assert len(outages) == 1
        assert outages[0].severity == SeverityLevel.MAJOR
        assert outages[0].description.startswith("Service outage detected")
        assert "Connection refused" in outages[0].description
    
    @patch("modules.monitoring.collectors.service_availability_collector.requests.get")
    def test_resolve_outage(self, mock_get, db, sample_service_endpoints):
        """Test resolving an existing outage."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"UP"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response
        
        endpoint = next(e for e in sample_service_endpoints if e.protocol == ProtocolType.HTTP)
        
        # Create an active outage
        outage = ServiceOutage(
            id=str(uuid.uuid4()),
            endpoint_id=endpoint.id,
            severity=SeverityLevel.MAJOR,
            description="Service outage detected: Connection refused",
            start_time=datetime.utcnow() - timedelta(hours=1),
            resolved=False,
            elasticsearch_synced=True,
            created_at=datetime.utcnow() - timedelta(hours=1),
            updated_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.add(outage)
        db.commit()
        
        collector = ServiceAvailabilityCollector(db)
        
        # Execute
        status = collector.check_service(endpoint)
        collector.process_service_status(status)
        
        # Verify
        db.refresh(outage)
        assert outage.resolved
        assert outage.resolved_at is not None
        assert outage.resolution_notes is not None
    
    def test_collect_service_availability_function(self, db, sample_service_endpoints, mock_elasticsearch_client):
        """Test the collect_service_availability function."""
        # Setup
        with patch.object(ServiceAvailabilityCollector, "check_service") as mock_check:
            with patch.object(ServiceAvailabilityCollector, "process_service_status") as mock_process:
                # Mock the check_service method to return a status
                mock_status = MagicMock()
                mock_status.endpoint_id = sample_service_endpoints[0].id
                mock_status.status = StatusType.UP
                mock_check.return_value = mock_status
                
                # Execute
                collect_service_availability(db)
                
                # Verify
                # Should be called once for each active service
                active_endpoints = [e for e in sample_service_endpoints if e.is_active]
                assert mock_check.call_count == len(active_endpoints)
                assert mock_process.call_count == len(active_endpoints)
    
    def test_collect_specific_service_availability_function(self, db, sample_service_endpoints, mock_elasticsearch_client):
        """Test the collect_specific_service_availability function."""
        # Setup
        with patch.object(ServiceAvailabilityCollector, "check_service") as mock_check:
            with patch.object(ServiceAvailabilityCollector, "process_service_status") as mock_process:
                # Mock the check_service method to return a status
                mock_status = MagicMock()
                mock_status.endpoint_id = sample_service_endpoints[0].id
                mock_status.status = StatusType.UP
                mock_check.return_value = mock_status
                
                # Execute
                endpoint_id = sample_service_endpoints[0].id
                collect_specific_service_availability(db, endpoint_id)
                
                # Verify
                mock_check.assert_called_once()
                mock_process.assert_called_once()


class TestServiceAvailabilityTasks:
    """Test the service availability Celery tasks."""
    
    @patch("modules.monitoring.tasks.service_availability_tasks.collect_service_availability")
    def test_check_service_availability_task(self, mock_collect, db):
        """Test the check_service_availability_task."""
        # Execute
        check_service_availability_task()
        
        # Verify
        mock_collect.assert_called_once_with(ANY)
    
    @patch("modules.monitoring.tasks.service_availability_tasks.ElasticsearchClient")
    def test_sync_service_statuses_to_elasticsearch_task(self, mock_es_client, db, sample_service_endpoints):
        """Test the sync_service_statuses_to_elasticsearch_task."""
        # Setup
        mock_client_instance = MagicMock()
        mock_es_client.return_value = mock_client_instance
        
        # Create some unsynced statuses
        statuses = []
        for endpoint in sample_service_endpoints[:2]:
            status = ServiceStatus(
                id=str(uuid.uuid4()),
                endpoint_id=endpoint.id,
                status=StatusType.UP,
                response_time=0.1,
                timestamp=datetime.utcnow(),
                elasticsearch_synced=False
            )
            db.add(status)
            statuses.append(status)
        
        # Create an unsynced outage
        outage = ServiceOutage(
            id=str(uuid.uuid4()),
            endpoint_id=sample_service_endpoints[0].id,
            severity=SeverityLevel.MAJOR,
            description="Test outage",
            start_time=datetime.utcnow() - timedelta(hours=1),
            resolved=True,
            resolved_at=datetime.utcnow(),
            resolution_notes="Test resolution",
            elasticsearch_synced=False,
            created_at=datetime.utcnow() - timedelta(hours=1),
            updated_at=datetime.utcnow()
        )
        db.add(outage)
        
        db.commit()
        
        # Execute
        sync_service_statuses_to_elasticsearch_task()
        
        # Verify
        mock_client_instance.bulk_index.assert_called()
        
        # Check that statuses are marked as synced
        for status in statuses:
            db.refresh(status)
            assert status.elasticsearch_synced
        
        # Check that outage is marked as synced
        db.refresh(outage)
        assert outage.elasticsearch_synced


class TestServiceAvailabilityRoutes:
    """Test the service availability API routes."""
    
    # Add API route tests here
