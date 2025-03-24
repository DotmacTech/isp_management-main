"""
Tests for service availability monitoring.

This module tests the service availability monitoring features by:
1. Creating test service endpoints
2. Checking their status
3. Simulating outages
4. Creating maintenance windows
5. Testing the outage management system
"""

import pytest
import logging
from datetime import datetime, timedelta

from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, ServiceOutage, MaintenanceWindow,
    ProtocolType, StatusType, SeverityLevel
)
from modules.monitoring.services.availability_service import AvailabilityService
from modules.monitoring.services.availability_service_outage import OutageManagementService
from modules.monitoring.collectors.service_availability_collector import (
    collect_service_availability,
    collect_specific_service_availability,
    sync_service_statuses_to_elasticsearch
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_service_availability")


@pytest.fixture
def test_endpoints(db_session):
    """Create test service endpoints."""
    logger.info("Creating test service endpoints")
    
    service = AvailabilityService(db_session)
    endpoints = []
    
    # Create HTTP endpoints (these should succeed)
    for i in range(3):
        endpoint_id = f"test-service-{i+1}"
        
        # Delete if exists
        existing = service.get_endpoint(endpoint_id)
        if existing:
            service.delete_endpoint(endpoint_id)
        
        # Create new endpoint
        endpoint = service.create_endpoint({
            "id": endpoint_id,
            "name": f"Test Service {i+1}",
            "url": "https://www.google.com",
            "protocol": ProtocolType.HTTPS,
            "check_interval": 60,
            "timeout": 5,
            "retries": 3,
            "expected_status_code": 200,
            "is_active": True
        })
        
        endpoints.append(endpoint)
        logger.info(f"Created endpoint: {endpoint.id} ({endpoint.name})")
    
    # Create one endpoint that will fail (invalid URL)
    endpoint_id = "test-service-fail"
    
    # Delete if exists
    existing = service.get_endpoint(endpoint_id)
    if existing:
        service.delete_endpoint(endpoint_id)
    
    # Create new endpoint
    endpoint = service.create_endpoint({
        "id": endpoint_id,
        "name": "Test Service (Failing)",
        "url": "https://invalid-url-that-will-fail.example.com",
        "protocol": ProtocolType.HTTPS,
        "check_interval": 60,
        "timeout": 2,
        "retries": 1,
        "expected_status_code": 200,
        "is_active": True
    })
    
    endpoints.append(endpoint)
    logger.info(f"Created endpoint: {endpoint.id} ({endpoint.name})")
    
    # Create one TCP endpoint
    endpoint_id = "test-service-tcp"
    
    # Delete if exists
    existing = service.get_endpoint(endpoint_id)
    if existing:
        service.delete_endpoint(endpoint_id)
    
    # Create new endpoint
    endpoint = service.create_endpoint({
        "id": endpoint_id,
        "name": "Test Service (TCP)",
        "url": "google.com:443",
        "protocol": ProtocolType.TCP,
        "check_interval": 60,
        "timeout": 5,
        "retries": 3,
        "is_active": True
    })
    
    endpoints.append(endpoint)
    logger.info(f"Created endpoint: {endpoint.id} ({endpoint.name})")
    
    yield endpoints
    
    # Clean up test data
    for endpoint in endpoints:
        service.delete_endpoint(endpoint.id)


def test_service_status_collection(db_session, test_endpoints):
    """Test collecting service status."""
    logger.info("Testing service status collection")
    
    service = AvailabilityService(db_session)
    
    for endpoint in test_endpoints:
        logger.info(f"Checking endpoint: {endpoint.id}")
        result = collect_specific_service_availability(db_session, endpoint.id)
        
        # Get latest status
        status = service.get_latest_status(endpoint.id)
        if status:
            logger.info(f"Status: {status.status.value}, Response Time: {status.response_time}ms")
            assert status.status is not None
        else:
            logger.info("No status found")
    
    # Check all services at once
    logger.info("Checking all services")
    result = collect_service_availability(db_session)
    assert result is not None


def test_outage_management(db_session, test_endpoints):
    """Test outage management."""
    logger.info("Testing outage management")
    
    outage_service = OutageManagementService(db_session)
    endpoint_id = test_endpoints[0].id
    
    # Create outage
    outage = outage_service.create_outage({
        "endpoint_id": endpoint_id,
        "severity": SeverityLevel.MAJOR,
        "description": "Test outage created by test script",
        "start_time": datetime.utcnow() - timedelta(minutes=30),
        "notification_channels": ["email"]
    })
    
    logger.info(f"Created outage: {outage.id}")
    assert outage.id is not None
    assert outage.endpoint_id == endpoint_id
    
    # Test outage resolution
    outage_service.resolve_outage(outage.id, "Test resolution")
    resolved_outage = outage_service.get_outage(outage.id)
    assert resolved_outage.end_time is not None
    assert resolved_outage.resolution == "Test resolution"


def test_maintenance_window(db_session, test_endpoints):
    """Test maintenance window creation and management."""
    logger.info("Testing maintenance window")
    
    outage_service = OutageManagementService(db_session)
    endpoint_ids = [endpoint.id for endpoint in test_endpoints[:2]]
    
    # Create maintenance window
    window = outage_service.create_maintenance_window({
        "endpoint_ids": endpoint_ids,
        "start_time": datetime.utcnow() - timedelta(minutes=15),
        "end_time": datetime.utcnow() + timedelta(hours=1),
        "description": "Test maintenance window created by test script",
        "created_by": "test_script"
    })
    
    logger.info(f"Created maintenance window: {window.id}")
    assert window.id is not None
    
    # Get maintenance window
    window = outage_service.get_maintenance_window(window.id)
    assert window is not None
    assert len(window.endpoints) == len(endpoint_ids)
    
    # Test that endpoints are in maintenance mode
    for endpoint_id in endpoint_ids:
        is_in_maintenance = outage_service.is_endpoint_in_maintenance(endpoint_id)
        assert is_in_maintenance is True


def test_elasticsearch_sync(db_session, test_endpoints, monkeypatch):
    """Test syncing service statuses to Elasticsearch."""
    # Mock the Elasticsearch client to avoid actual ES calls
    class MockElasticsearchClient:
        def bulk_index(self, *args, **kwargs):
            return {"errors": False, "items": []}
    
    # Apply the mock
    monkeypatch.setattr(
        "modules.monitoring.collectors.service_availability_collector.ElasticsearchClient",
        lambda: MockElasticsearchClient()
    )
    
    # Collect some statuses first
    collect_service_availability(db_session)
    
    # Test sync to ES
    result = sync_service_statuses_to_elasticsearch(db_session)
    assert result is not None
