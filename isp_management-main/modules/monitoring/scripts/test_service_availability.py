#!/usr/bin/env python
"""
Test script for service availability monitoring.

This script tests the service availability monitoring features by:
1. Creating test service endpoints
2. Checking their status
3. Simulating outages
4. Creating maintenance windows
5. Testing the outage management system

Usage:
    python test_service_availability.py

Environment Variables:
    DATABASE_URL: Database connection string
    ELASTICSEARCH_HOSTS: Elasticsearch hosts (comma-separated)
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime, timedelta
import uuid
import random

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/isp_management")

# Create database engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_test_endpoints(db: Session, count: int = 5) -> list:
    """Create test service endpoints."""
    logger.info(f"Creating {count} test service endpoints")
    
    service = AvailabilityService(db)
    endpoints = []
    
    # Create HTTP endpoints (these should succeed)
    for i in range(count - 2):
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
    endpoint_id = f"test-service-fail"
    
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
    endpoint_id = f"test-service-tcp"
    
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
    
    return endpoints


def check_service_statuses(db: Session, endpoints: list):
    """Check the status of service endpoints."""
    logger.info("Checking service statuses")
    
    service = AvailabilityService(db)
    
    for endpoint in endpoints:
        logger.info(f"Checking endpoint: {endpoint.id}")
        result = collect_specific_service_availability(db, endpoint.id)
        logger.info(f"Result: {result}")
        
        # Get latest status
        status = service.get_latest_status(endpoint.id)
        if status:
            logger.info(f"Status: {status.status.value}, Response Time: {status.response_time}ms")
        else:
            logger.info("No status found")
    
    # Check all services at once
    logger.info("Checking all services")
    result = collect_service_availability(db)
    logger.info(f"All services result: {result}")


def create_test_outage(db: Session, endpoint_id: str):
    """Create a test outage for a service endpoint."""
    logger.info(f"Creating test outage for endpoint: {endpoint_id}")
    
    outage_service = OutageManagementService(db)
    
    # Create outage
    outage = outage_service.create_outage({
        "endpoint_id": endpoint_id,
        "severity": SeverityLevel.MAJOR,
        "description": "Test outage created by test script",
        "start_time": datetime.utcnow() - timedelta(minutes=30),
        "notification_channels": ["email"]
    })
    
    logger.info(f"Created outage: {outage.id}")
    
    return outage


def create_test_maintenance_window(db: Session, endpoint_ids: list):
    """Create a test maintenance window."""
    logger.info("Creating test maintenance window")
    
    outage_service = OutageManagementService(db)
    
    # Create maintenance window
    window = outage_service.create_maintenance_window({
        "endpoint_ids": endpoint_ids,
        "start_time": datetime.utcnow() - timedelta(minutes=15),
        "end_time": datetime.utcnow() + timedelta(hours=1),
        "description": "Test maintenance window created by test script",
        "created_by": "test_script"
    })
    
    logger.info(f"Created maintenance window: {window.id}")
    
    return window


def test_outage_detection(db: Session, endpoint_id: str):
    """Test the outage detection system."""
    logger.info(f"Testing outage detection for endpoint: {endpoint_id}")
    
    service = AvailabilityService(db)
    outage_service = OutageManagementService(db)
    
    # Get endpoint
    endpoint = service.get_endpoint(endpoint_id)
    if not endpoint:
        logger.error(f"Endpoint not found: {endpoint_id}")
        return
    
    # Create multiple failure statuses
    for i in range(5):
        status = ServiceStatus(
            id=str(uuid.uuid4()),
            endpoint_id=endpoint_id,
            status=StatusType.DOWN,
            response_time=None,
            timestamp=datetime.utcnow() - timedelta(minutes=5-i),
            error_message="Simulated failure for testing",
            elasticsearch_synced=False
        )
        db.add(status)
    
    db.commit()
    logger.info("Created 5 failure statuses")
    
    # Process potential outages
    logger.info("Processing potential outages")
    outage_service.process_potential_outages(endpoint_id=endpoint_id)
    
    # Check if outage was created
    outages = outage_service.get_active_outages(endpoint_id=endpoint_id)
    if outages:
        logger.info(f"Outage detected: {outages[0].id}")
    else:
        logger.warning("No outage detected")


def test_outage_resolution(db: Session, endpoint_id: str):
    """Test the outage resolution system."""
    logger.info(f"Testing outage resolution for endpoint: {endpoint_id}")
    
    service = AvailabilityService(db)
    outage_service = OutageManagementService(db)
    
    # Get active outages
    outages = outage_service.get_active_outages(endpoint_id=endpoint_id)
    if not outages:
        logger.warning("No active outages found")
        return
    
    outage = outages[0]
    logger.info(f"Found active outage: {outage.id}")
    
    # Create success status
    status = ServiceStatus(
        id=str(uuid.uuid4()),
        endpoint_id=endpoint_id,
        status=StatusType.UP,
        response_time=100.0,
        timestamp=datetime.utcnow(),
        elasticsearch_synced=False
    )
    db.add(status)
    db.commit()
    logger.info("Created success status")
    
    # Check for resolved outages
    logger.info("Checking for resolved outages")
    outage_service.check_for_resolved_outages(endpoint_id=endpoint_id)
    
    # Check if outage was resolved
    outage = outage_service.get_outage(outage.id)
    if outage and outage.resolved:
        logger.info(f"Outage resolved: {outage.id}")
    else:
        logger.warning("Outage not resolved")


def test_elasticsearch_sync(db: Session):
    """Test syncing service statuses to Elasticsearch."""
    logger.info("Testing Elasticsearch sync")
    
    # Sync statuses
    result = sync_service_statuses_to_elasticsearch(db)
    
    logger.info(f"Sync result: {result}")


def cleanup_test_data(db: Session):
    """Clean up test data."""
    logger.info("Cleaning up test data")
    
    service = AvailabilityService(db)
    outage_service = OutageManagementService(db)
    
    # Delete test endpoints
    for i in range(5):
        endpoint_id = f"test-service-{i+1}"
        service.delete_endpoint(endpoint_id)
        logger.info(f"Deleted endpoint: {endpoint_id}")
    
    # Delete failing endpoint
    service.delete_endpoint("test-service-fail")
    logger.info("Deleted endpoint: test-service-fail")
    
    # Delete TCP endpoint
    service.delete_endpoint("test-service-tcp")
    logger.info("Deleted endpoint: test-service-tcp")
    
    # Delete maintenance windows
    windows = outage_service.get_maintenance_windows()[0]
    for window in windows:
        if "test script" in window.description.lower():
            outage_service.delete_maintenance_window(window.id)
            logger.info(f"Deleted maintenance window: {window.id}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test service availability monitoring")
    parser.add_argument("--cleanup-only", action="store_true", help="Only clean up test data")
    args = parser.parse_args()
    
    # Create database session
    db = SessionLocal()
    
    try:
        if args.cleanup_only:
            cleanup_test_data(db)
            return
        
        # Create test endpoints
        endpoints = create_test_endpoints(db)
        
        # Check service statuses
        check_service_statuses(db, endpoints)
        
        # Create test outage
        outage = create_test_outage(db, endpoints[0].id)
        
        # Create test maintenance window
        window = create_test_maintenance_window(db, [endpoint.id for endpoint in endpoints[:2]])
        
        # Test outage detection
        test_outage_detection(db, endpoints[2].id)
        
        # Test outage resolution
        test_outage_resolution(db, endpoints[2].id)
        
        # Test Elasticsearch sync
        test_elasticsearch_sync(db)
        
        # Wait for user input before cleanup
        input("Press Enter to clean up test data...")
        
        # Clean up test data
        cleanup_test_data(db)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
