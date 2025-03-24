"""
Pytest configuration for Field Services Module tests.

This file contains shared fixtures and configuration for testing
the Field Services Module.
"""

import pytest
import sys
import importlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session, declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum, ForeignKey, Float
from modules.field_services.models import (
    JobStatusEnum, JobPriorityEnum, JobTypeEnum,
    TechnicianStatusEnum,
    NotificationTypeEnum, NotificationPriorityEnum,
    InventoryStatusEnum, InventoryType, InventoryTransactionTypeEnum
)

# Create a mock Base for testing
MockBase = declarative_base()

# Mock models to avoid circular imports and relationship issues
class MockUser(MockBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MockCustomer(MockBase):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MockTechnician(MockBase):
    __tablename__ = "field_technicians"
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone = Column(String)
    status = Column(Enum(TechnicianStatusEnum))
    skills = Column(String)  # JSON string in real model
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationship
    jobs = relationship("MockJob", back_populates="technician")


class MockJob(MockBase):
    __tablename__ = "field_jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(Text)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    technician_id = Column(Integer, ForeignKey("field_technicians.id"))
    status = Column(Enum(JobStatusEnum))
    priority = Column(Enum(JobPriorityEnum))
    job_type = Column(Enum(JobTypeEnum))
    estimated_duration_minutes = Column(Integer)
    scheduled_start_time = Column(DateTime)
    scheduled_end_time = Column(DateTime)
    actual_start_time = Column(DateTime)
    actual_end_time = Column(DateTime)
    sla_deadline = Column(DateTime)
    location_lat = Column(Float)
    location_lon = Column(Float)
    location_address = Column(String)
    required_skills = Column(String)  # JSON string in real model
    required_equipment = Column(String)  # JSON string in real model
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationships
    technician = relationship("MockTechnician", back_populates="jobs")
    customer = relationship("MockCustomer")
    notifications = relationship("MockTechnicianNotification", back_populates="job")
    job_history = relationship("MockJobHistory", back_populates="job")


class MockTechnicianNotification(MockBase):
    __tablename__ = "field_technician_notifications"
    id = Column(Integer, primary_key=True)
    technician_id = Column(Integer, ForeignKey("field_technicians.id"))
    title = Column(String)
    message = Column(Text)
    notification_type = Column(Enum(NotificationTypeEnum))
    priority = Column(Enum(NotificationPriorityEnum))
    job_id = Column(Integer, ForeignKey("field_jobs.id"))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    expiry_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationship
    job = relationship("MockJob", back_populates="notifications")


class MockJobHistory(MockBase):
    __tablename__ = "field_job_history"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("field_jobs.id"))
    status_from = Column(Enum(JobStatusEnum))
    status_to = Column(Enum(JobStatusEnum))
    notes = Column(Text)
    changed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Add relationship
    job = relationship("MockJob", back_populates="job_history")


# Setup mock relationships to avoid SQLAlchemy mapper errors
@pytest.fixture(scope="session", autouse=True)
def setup_mock_relationships():
    """
    Setup mock relationships for testing to avoid SQLAlchemy mapper errors.
    """
    # This is a no-op fixture since we've defined the relationships directly in the classes
    pass


@pytest.fixture
def mock_db():
    """
    Create a mock database session for testing.
    """
    db = MagicMock(spec=Session)
    
    # Configure query method to return a query mock
    query_mock = MagicMock()
    db.query.return_value = query_mock
    
    # Configure filter method to return the query mock for chaining
    query_mock.filter.return_value = query_mock
    query_mock.filter_by.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.outerjoin.return_value = query_mock
    query_mock.options.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.all.return_value = []
    query_mock.first.return_value = None
    query_mock.count.return_value = 0
    
    return db


@pytest.fixture
def sample_notification_data():
    """Sample data for creating a notification."""
    return {
        "technician_id": 1,
        "title": "Test Notification",
        "message": "This is a test notification",
        "notification_type": "JOB_ASSIGNMENT",
        "priority": "HIGH",
        "job_id": 1,
        "expiry_date": datetime.utcnow() + timedelta(days=1)
    }


@pytest.fixture
def sample_notification():
    """Create a sample TechnicianNotification instance for testing."""
    current_time = datetime.utcnow()
    notification = MockTechnicianNotification(
        id=1,
        technician_id=1,
        title="Test Notification",
        message="This is a test notification",
        notification_type=NotificationTypeEnum.JOB_ASSIGNMENT,
        priority=NotificationPriorityEnum.HIGH,
        job_id=1,
        is_read=False,
        read_at=None,
        expiry_date=current_time + timedelta(days=1),
        created_at=current_time,
        updated_at=current_time
    )
    return notification


@pytest.fixture
def sample_customer():
    """Create a sample customer for testing."""
    customer = MockCustomer()
    customer.id = 1
    customer.name = "Test Customer"
    customer.email = "customer@example.com"
    customer.phone = "123-456-7890"
    customer.address = "123 Main St, New York, NY 10001"
    customer.created_at = datetime.utcnow() - timedelta(days=30)
    customer.updated_at = datetime.utcnow() - timedelta(days=15)
    return customer


@pytest.fixture
def sample_technician():
    """Create a sample technician for testing."""
    technician = MockTechnician()
    technician.id = 1
    technician.first_name = "John"
    technician.last_name = "Doe"
    technician.email = "john.doe@example.com"
    technician.phone = "123-456-7890"
    technician.status = TechnicianStatusEnum.AVAILABLE
    technician.skills = '["networking", "installation", "troubleshooting"]'
    technician.created_at = datetime.utcnow() - timedelta(days=30)
    technician.updated_at = datetime.utcnow() - timedelta(days=15)
    return technician


@pytest.fixture
def sample_job_data():
    """
    Sample job data for testing.
    """
    return {
        "title": "Fix Internet Connection",
        "description": "Customer reporting intermittent connection issues",
        "customer_id": 1,
        "job_type": "installation",  # lowercase to match schema enum
        "priority": "medium",  # lowercase to match schema enum
        "status": "pending",  # lowercase to match schema enum
        "estimated_duration_minutes": 60,
        "scheduled_start_time": datetime.utcnow() + timedelta(days=1),
        "scheduled_end_time": datetime.utcnow() + timedelta(days=1, hours=1),
        "location_lat": 37.7749,
        "location_lon": -122.4194,
        "location_address": "123 Main St, San Francisco, CA 94105",
        "required_skills": ["networking", "troubleshooting"],
        "required_equipment": ["router", "cable_tester"]
    }


@pytest.fixture
def sample_job(sample_job_data):
    """
    Sample job for testing.
    """
    job = MockJob(
        id=1,
        title=sample_job_data["title"],
        description=sample_job_data["description"],
        customer_id=sample_job_data["customer_id"],
        technician_id=None,
        status=JobStatusEnum.PENDING,
        priority=JobPriorityEnum.MEDIUM,
        job_type=JobTypeEnum.INSTALLATION,
        estimated_duration_minutes=sample_job_data["estimated_duration_minutes"],
        scheduled_start_time=sample_job_data["scheduled_start_time"],
        scheduled_end_time=sample_job_data["scheduled_end_time"],
        actual_start_time=None,
        actual_end_time=None,
        sla_deadline=datetime.utcnow() + timedelta(days=2),
        location_lat=sample_job_data["location_lat"],
        location_lon=sample_job_data["location_lon"],
        location_address=sample_job_data["location_address"],
        required_skills=str(sample_job_data["required_skills"]),
        required_equipment=str(sample_job_data["required_equipment"]),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Add mock methods for testing
    job._to_response = MagicMock(return_value={
        "id": 1,
        "title": sample_job_data["title"],
        "description": sample_job_data["description"],
        "customer_id": sample_job_data["customer_id"],
        "technician_id": None,
        "status": "pending",  # lowercase to match schema enum
        "priority": "medium",  # lowercase to match schema enum
        "job_type": "installation",  # lowercase to match schema enum
        "estimated_duration_minutes": sample_job_data["estimated_duration_minutes"],
        "scheduled_start_time": sample_job_data["scheduled_start_time"],
        "scheduled_end_time": sample_job_data["scheduled_end_time"],
        "actual_start_time": None,
        "actual_end_time": None,
        "sla_deadline": datetime.utcnow() + timedelta(days=2),
        "location_lat": sample_job_data["location_lat"],
        "location_lon": sample_job_data["location_lon"],
        "location_address": sample_job_data["location_address"],
        "required_skills": sample_job_data["required_skills"],
        "required_equipment": sample_job_data["required_equipment"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": 1,
        "updated_by": 1,
        "notes": None,
        "sla_status": "within_sla"
    })
    
    return job


@pytest.fixture
def notification_service(mock_db):
    """Create a notification service for testing."""
    from modules.field_services.services.notification_service import NotificationService
    return NotificationService(mock_db)
