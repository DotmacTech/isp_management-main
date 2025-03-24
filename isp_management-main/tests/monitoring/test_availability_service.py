"""
Tests for the availability service in the monitoring module.

This module contains tests for the AvailabilityService, ensuring that
service endpoint monitoring, status tracking, and outage detection work correctly.
"""

import unittest
from unittest import mock
from datetime import datetime, timedelta
import uuid
import requests
from sqlalchemy.orm import Session

from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, ServiceOutage, ServiceAlert, MaintenanceWindow,
    ProtocolType, StatusType, SeverityLevel, NotificationType,
    generate_uuid
)
from modules.monitoring.schemas.service_availability import (
    ServiceEndpointCreate, ServiceEndpointUpdate,
    ServiceStatusCreate, ServiceOutageCreate, ServiceAlertCreate,
    MaintenanceWindowCreate, MaintenanceWindowUpdate
)
from modules.monitoring.services.availability_service import AvailabilityService


class TestAvailabilityService(unittest.TestCase):
    """Test cases for the availability service."""

    def setUp(self):
        """Set up test environment."""
        # Mock database session
        self.db = mock.MagicMock(spec=Session)
        
        # Create availability service with mocked DB
        self.service = AvailabilityService(self.db)
        
        # Mock Elasticsearch client
        self.service.es_client = mock.MagicMock()
        
    def test_create_endpoint(self):
        """Test creating a service endpoint."""
        # Create endpoint data
        endpoint_data = ServiceEndpointCreate(
            id=generate_uuid(),
            name="Test API",
            description="Test API endpoint",
            url="https://api.example.com",
            protocol=ProtocolType.HTTPS,
            port=443,
            check_interval=60,
            timeout=5,
            retries=3,
            expected_status_code=200
        )
        
        # Call the service method
        result = self.service.create_endpoint(endpoint_data)
        
        # Verify the database operations
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        
        # Verify the result
        self.assertEqual(result.name, endpoint_data.name)
        self.assertEqual(result.url, endpoint_data.url)
        self.assertEqual(result.protocol, endpoint_data.protocol)
    
    def test_get_endpoint(self):
        """Test retrieving a service endpoint."""
        # Mock database query result
        endpoint_id = generate_uuid()
        mock_endpoint = mock.MagicMock(spec=ServiceEndpoint)
        mock_endpoint.id = endpoint_id
        mock_endpoint.name = "Test API"
        
        # Set up the mock query chain
        self.db.query.return_value.filter.return_value.first.return_value = mock_endpoint
        
        # Call the service method
        result = self.service.get_endpoint(endpoint_id)
        
        # Verify the result
        self.assertEqual(result.id, endpoint_id)
        self.assertEqual(result.name, "Test API")
    
    def test_update_endpoint(self):
        """Test updating a service endpoint."""
        # Mock database query result
        endpoint_id = generate_uuid()
        mock_endpoint = mock.MagicMock(spec=ServiceEndpoint)
        mock_endpoint.id = endpoint_id
        mock_endpoint.name = "Test API"
        
        # Set up the mock query chain
        self.db.query.return_value.filter.return_value.first.return_value = mock_endpoint
        
        # Create update data
        update_data = ServiceEndpointUpdate(
            name="Updated API",
            check_interval=120
        )
        
        # Call the service method
        result = self.service.update_endpoint(endpoint_id, update_data)
        
        # Verify the database operations
        self.db.commit.assert_called_once()
        
        # Verify the result
        self.assertEqual(mock_endpoint.name, "Updated API")
        self.assertEqual(mock_endpoint.check_interval, 120)
    
    def test_delete_endpoint(self):
        """Test deleting a service endpoint."""
        # Mock database query result
        endpoint_id = generate_uuid()
        mock_endpoint = mock.MagicMock(spec=ServiceEndpoint)
        mock_endpoint.id = endpoint_id
        
        # Set up the mock query chain
        self.db.query.return_value.filter.return_value.first.return_value = mock_endpoint
        
        # Call the service method
        result = self.service.delete_endpoint(endpoint_id)
        
        # Verify the database operations
        self.db.delete.assert_called_once_with(mock_endpoint)
        self.db.commit.assert_called_once()
        
        # Verify the result
        self.assertTrue(result)
    
    def test_list_endpoints(self):
        """Test listing service endpoints."""
        # Mock database query result
        mock_endpoints = [
            mock.MagicMock(spec=ServiceEndpoint),
            mock.MagicMock(spec=ServiceEndpoint)
        ]
        mock_endpoints[0].id = generate_uuid()
        mock_endpoints[0].name = "API 1"
        mock_endpoints[1].id = generate_uuid()
        mock_endpoints[1].name = "API 2"
        
        # Set up the mock query chain
        self.db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_endpoints
        self.db.query.return_value.filter.return_value.count.return_value = len(mock_endpoints)
        
        # Call the service method
        result, total = self.service.list_endpoints(skip=0, limit=10)
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(total, 2)
        self.assertEqual(result[0].name, "API 1")
        self.assertEqual(result[1].name, "API 2")
    
    @mock.patch('modules.monitoring.services.availability_service.requests.get')
    def test_check_http_endpoint_up(self, mock_get):
        """Test checking an HTTP endpoint that is up."""
        # Mock the HTTP response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.345
        mock_get.return_value = mock_response
        
        # Create endpoint
        endpoint = ServiceEndpoint(
            id=generate_uuid(),
            name="HTTP Test",
            url="https://api.example.com",
            protocol=ProtocolType.HTTPS,
            expected_status_code=200
        )
        
        # Call the method
        status, response_time, message = self.service._check_http_endpoint(endpoint)
        
        # Verify the result
        self.assertEqual(status, StatusType.UP)
        self.assertEqual(response_time, 0.345)
        self.assertEqual(message, "Service is up and running")
        
        # Verify the HTTP request was made correctly
        mock_get.assert_called_once_with(
            "https://api.example.com",
            timeout=5,
            verify=True
        )
    
    @mock.patch('modules.monitoring.services.availability_service.requests.get')
    def test_check_http_endpoint_down(self, mock_get):
        """Test checking an HTTP endpoint that is down."""
        # Mock the HTTP response to raise an exception
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Create endpoint
        endpoint = ServiceEndpoint(
            id=generate_uuid(),
            name="HTTP Test Down",
            url="https://down.example.com",
            protocol=ProtocolType.HTTPS,
            expected_status_code=200
        )
        
        # Call the method
        status, response_time, message = self.service._check_http_endpoint(endpoint)
        
        # Verify the result
        self.assertEqual(status, StatusType.DOWN)
        self.assertIsNone(response_time)
        self.assertEqual(message, "Connection refused")
    
    @mock.patch('modules.monitoring.services.availability_service.socket.socket')
    def test_check_tcp_endpoint_up(self, mock_socket):
        """Test checking a TCP endpoint that is up."""
        # Mock the socket operations
        mock_socket_instance = mock.MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Create endpoint
        endpoint = ServiceEndpoint(
            id=generate_uuid(),
            name="TCP Test",
            url="tcp.example.com",
            protocol=ProtocolType.TCP,
            port=22
        )
        
        # Call the method with mocked time.time() to simulate response time
        with mock.patch('modules.monitoring.services.availability_service.time.time', side_effect=[0, 0.123]):
            status, response_time, message = self.service._check_tcp_endpoint(endpoint)
        
        # Verify the result
        self.assertEqual(status, StatusType.UP)
        self.assertEqual(response_time, 0.123)
        self.assertEqual(message, "Service is up and running")
        
        # Verify the socket operations
        mock_socket_instance.connect.assert_called_once_with(("tcp.example.com", 22))
        mock_socket_instance.close.assert_called_once()
    
    def test_record_service_status(self):
        """Test recording a service status."""
        # Mock endpoint
        endpoint_id = generate_uuid()
        mock_endpoint = mock.MagicMock(spec=ServiceEndpoint)
        mock_endpoint.id = endpoint_id
        
        # Create status data
        status_data = ServiceStatusCreate(
            endpoint_id=endpoint_id
        )
        
        # Call the service method
        self.service.record_service_status(
            status_data,
            status=StatusType.UP,
            response_time=0.345,
            status_message="Service is up and running"
        )
        
        # Verify the database operations
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        
        # Verify Elasticsearch indexing
        self.service.es_client.index_service_status.assert_called_once()
    
    def test_detect_outage(self):
        """Test detecting a service outage."""
        # Mock endpoint
        endpoint_id = generate_uuid()
        mock_endpoint = mock.MagicMock(spec=ServiceEndpoint)
        mock_endpoint.id = endpoint_id
        mock_endpoint.name = "Outage Test"
        
        # Mock recent status checks
        mock_statuses = [
            mock.MagicMock(spec=ServiceStatus),
            mock.MagicMock(spec=ServiceStatus),
            mock.MagicMock(spec=ServiceStatus)
        ]
        for status in mock_statuses:
            status.status = StatusType.DOWN
        
        # Set up the mock query chain
        self.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_statuses
        
        # Mock that no active outage exists
        self.db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        # Call the service method
        result = self.service.detect_outage(mock_endpoint)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify the database operations (creating a new outage)
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
    
    def test_resolve_outage(self):
        """Test resolving a service outage."""
        # Mock endpoint
        endpoint_id = generate_uuid()
        mock_endpoint = mock.MagicMock(spec=ServiceEndpoint)
        mock_endpoint.id = endpoint_id
        
        # Mock active outage
        outage_id = generate_uuid()
        mock_outage = mock.MagicMock(spec=ServiceOutage)
        mock_outage.id = outage_id
        mock_outage.start_time = datetime.utcnow() - timedelta(hours=1)
        mock_outage.end_time = None
        
        # Set up the mock query chain
        self.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_outage
        
        # Call the service method
        result = self.service.resolve_outage(
            mock_endpoint,
            resolution_notes="Fixed network connectivity issue"
        )
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify the outage was updated
        self.assertIsNotNone(mock_outage.end_time)
        self.assertIsNotNone(mock_outage.duration)
        self.assertEqual(mock_outage.resolution_notes, "Fixed network connectivity issue")
        
        # Verify the database operations
        self.db.commit.assert_called_once()
        
        # Verify Elasticsearch indexing
        self.service.es_client.update_service_outage.assert_called_once()
    
    def test_create_maintenance_window(self):
        """Test creating a maintenance window."""
        # Create maintenance window data
        start_time = datetime.utcnow() + timedelta(days=1)
        end_time = start_time + timedelta(hours=4)
        
        window_data = MaintenanceWindowCreate(
            name="Scheduled Network Maintenance",
            description="Upgrading network equipment",
            start_time=start_time,
            end_time=end_time,
            affected_services="api,auth,billing",
            created_by="admin"
        )
        
        # Call the service method
        result = self.service.create_maintenance_window(window_data)
        
        # Verify the database operations
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        
        # Verify the result
        self.assertEqual(result.name, window_data.name)
        self.assertEqual(result.start_time, window_data.start_time)
        self.assertEqual(result.end_time, window_data.end_time)
    
    def test_check_maintenance_status(self):
        """Test checking if a service is in maintenance."""
        # Mock endpoint
        endpoint_id = generate_uuid()
        mock_endpoint = mock.MagicMock(spec=ServiceEndpoint)
        mock_endpoint.id = endpoint_id
        mock_endpoint.name = "API Service"
        
        # Mock active maintenance window
        now = datetime.utcnow()
        mock_window = mock.MagicMock(spec=MaintenanceWindow)
        mock_window.start_time = now - timedelta(hours=1)
        mock_window.end_time = now + timedelta(hours=1)
        mock_window.affected_services = "api,auth"
        mock_window.is_active.return_value = True
        mock_window.affects_service.return_value = True
        
        # Set up the mock query chain
        self.db.query.return_value.filter.return_value.all.return_value = [mock_window]
        
        # Call the service method
        result = self.service.check_maintenance_status(mock_endpoint)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify the window's methods were called
        mock_window.is_active.assert_called_once()
        mock_window.affects_service.assert_called_once_with("API Service")


if __name__ == "__main__":
    unittest.main()
