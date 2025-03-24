"""
Test module for the Mobile Service in the Field Services Module.
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session
from modules.field_services.models import (
    Technician, TechnicianStatusEnum, Job, JobStatusEnum, JobPriorityEnum, JobTypeEnum,
    JobHistory, TechnicianInventory, InventoryTransaction, InventoryTransactionTypeEnum
)
from modules.field_services.schemas import (
    MobileSyncRequest, MobileSyncResponse, MobileJobUpdate,
    MobileLocationUpdate, MobileInventoryUsage
)
from modules.field_services.services import MobileService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mobile_service(mock_db):
    """Create a MobileService instance with a mock database."""
    return MobileService(mock_db)


@pytest.fixture
def sample_technician():
    """Create a sample Technician instance for testing."""
    technician = Technician(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="123-456-7890",
        status=TechnicianStatusEnum.AVAILABLE,
        current_location_lat=40.7128,
        current_location_lon=-74.0060,
        last_location_update=datetime.utcnow() - timedelta(hours=1)
    )
    return technician


@pytest.fixture
def sample_job():
    """Create a sample Job instance for testing."""
    job = Job(
        id=1,
        title="Fix Router Connection",
        description="Customer reporting intermittent connection issues",
        customer_id=1,
        job_type=JobTypeEnum.INSTALLATION,
        status=JobStatusEnum.ASSIGNED,
        priority=JobPriorityEnum.MEDIUM,
        technician_id=1,
        estimated_duration_minutes=60,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=1),
        scheduled_end_time=datetime.utcnow() + timedelta(hours=2),
        location_lat=40.7128,
        location_lon=-74.0060,
        location_address="123 Main St, New York, NY 10001",
        created_at=datetime.utcnow() - timedelta(days=1),
        updated_at=datetime.utcnow() - timedelta(hours=2)
    )
    return job


@pytest.fixture
def sample_sync_request():
    """Create a sample MobileSyncRequest for testing."""
    return MobileSyncRequest(
        technician_id=1,
        last_sync_time=datetime.utcnow() - timedelta(hours=1),
        job_updates=[
            MobileJobUpdate(
                job_id=1,
                status="IN_PROGRESS",
                notes="Started working on the router installation",
                timestamp=datetime.utcnow(),
                actual_start_time=datetime.utcnow()
            )
        ],
        location_update=MobileLocationUpdate(
            latitude=40.7130,
            longitude=-74.0065,
            timestamp=datetime.utcnow()
        ),
        inventory_usage=[
            MobileInventoryUsage(
                inventory_id=1,
                quantity=2,
                job_id=1,
                timestamp=datetime.utcnow()
            )
        ]
    )


class TestMobileService:
    """Test cases for the MobileService class."""

    def test_sync_technician_data(self, mobile_service, mock_db, sample_technician, sample_job, sample_sync_request):
        """Test synchronizing data between mobile app and backend."""
        # Arrange
        technician_id = 1
        
        # Mock technician query
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_technician,  # For technician query
            sample_job,         # For job query
        ]
        
        # Mock job updates processing
        with patch.object(mobile_service, '_process_job_updates') as mock_process_jobs:
            mock_process_jobs.return_value = [sample_job]
            
            # Mock technician location update
            with patch.object(mobile_service, '_update_technician_location') as mock_update_location:
                mock_update_location.return_value = None
                
                # Mock inventory usage processing
                with patch.object(mobile_service, '_process_inventory_usage') as mock_process_inventory:
                    mock_process_inventory.return_value = None
                    
                    # Mock data retrieval
                    with patch.object(mobile_service, '_get_technician_jobs') as mock_get_jobs:
                        mock_get_jobs.return_value = [
                            {
                                "id": 1,
                                "title": "Fix Router Connection",
                                "status": "IN_PROGRESS",
                                "customer_id": 1,
                                "links": []
                            }
                        ]
                        
                        with patch.object(mobile_service, '_get_technician_notifications') as mock_get_notifications:
                            mock_get_notifications.return_value = [
                                {
                                    "id": 1,
                                    "title": "New Job Assigned",
                                    "message": "You have been assigned to job #1",
                                    "is_read": False,
                                    "links": []
                                }
                            ]
                            
                            with patch.object(mobile_service, '_get_technician_inventory') as mock_get_inventory:
                                mock_get_inventory.return_value = [
                                    {
                                        "inventory_id": 1,
                                        "inventory_name": "Router",
                                        "quantity": 5,
                                        "links": []
                                    }
                                ]
                                
                                # Mock sync hash generation
                                with patch.object(mobile_service, '_generate_sync_hash') as mock_generate_hash:
                                    mock_generate_hash.return_value = "test_hash_123"
                                    
                                    # Act
                                    result = mobile_service.sync_technician_data(technician_id, sample_sync_request)
        
        # Assert
        assert result.technician_id == technician_id
        assert result.sync_hash == "test_hash_123"
        assert len(result.jobs) == 1
        assert len(result.notifications) == 1
        assert len(result.inventory) == 1
        assert len(result.updated_job_ids) == 1
        assert result.updated_job_ids[0] == 1
        
        # Verify method calls
        mock_process_jobs.assert_called_once_with(technician_id, sample_sync_request.job_updates)
        mock_update_location.assert_called_once_with(technician_id, sample_sync_request.location_update)
        mock_process_inventory.assert_called_once_with(technician_id, sample_sync_request.inventory_usage)
        mock_get_jobs.assert_called_once_with(technician_id, sample_sync_request.last_sync_time)
        mock_get_notifications.assert_called_once_with(technician_id, sample_sync_request.last_sync_time)
        mock_get_inventory.assert_called_once_with(technician_id, sample_sync_request.last_sync_time)
        mock_generate_hash.assert_called_once()

    def test_process_job_updates(self, mobile_service, mock_db, sample_job):
        """Test processing job updates from mobile app."""
        # Arrange
        technician_id = 1
        job_updates = [
            MobileJobUpdate(
                job_id=1,
                status="IN_PROGRESS",
                notes="Started working on the router installation",
                timestamp=datetime.utcnow(),
                actual_start_time=datetime.utcnow()
            )
        ]
        
        # Mock job query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_job
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Act
        result = mobile_service._process_job_updates(technician_id, job_updates)
        
        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].status == JobStatusEnum.IN_PROGRESS
        assert result[0].actual_start_time is not None
        assert "Started working on the router installation" in result[0].notes
        assert mock_db.add.called  # Should add a JobHistory entry
        assert mock_db.commit.called

    def test_update_technician_location(self, mobile_service, mock_db, sample_technician):
        """Test updating technician location from mobile app."""
        # Arrange
        technician_id = 1
        location_update = MobileLocationUpdate(
            latitude=40.7130,
            longitude=-74.0065,
            timestamp=datetime.utcnow()
        )
        
        # Mock technician query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_technician
        mock_db.commit.return_value = None
        
        # Act
        mobile_service._update_technician_location(technician_id, location_update)
        
        # Assert
        assert sample_technician.current_location_lat == 40.7130
        assert sample_technician.current_location_lon == -74.0065
        assert sample_technician.last_location_update is not None
        assert mock_db.commit.called

    def test_process_inventory_usage(self, mobile_service, mock_db):
        """Test processing inventory usage from mobile app."""
        # Arrange
        technician_id = 1
        inventory_usage = [
            MobileInventoryUsage(
                inventory_id=1,
                quantity=2,
                job_id=1,
                timestamp=datetime.utcnow()
            )
        ]
        
        # Create a mock technician inventory
        tech_inventory = TechnicianInventory(
            technician_id=technician_id,
            inventory_id=1,
            quantity=5
        )
        
        # Mock inventory query
        mock_db.query.return_value.filter.return_value.first.return_value = tech_inventory
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Act
        mobile_service._process_inventory_usage(technician_id, inventory_usage)
        
        # Assert
        assert tech_inventory.quantity == 3  # 5 - 2 = 3
        assert mock_db.add.called  # Should add an InventoryTransaction
        assert mock_db.commit.called

    def test_get_technician_jobs(self, mobile_service, mock_db, sample_job):
        """Test getting jobs assigned to a technician for mobile sync."""
        # Arrange
        technician_id = 1
        last_sync_time = datetime.utcnow() - timedelta(hours=1)
        
        # Mock job query with join load
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.all.return_value = [sample_job]
        
        # Create a mock customer
        customer = MagicMock()
        customer.name = "Test Customer"
        customer.phone = "555-123-4567"
        
        # Attach customer to job
        sample_job.customer = customer
        
        # Act
        result = mobile_service._get_technician_jobs(technician_id, last_sync_time)
        
        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["title"] == "Fix Router Connection"
        assert result[0]["customer_name"] == "Test Customer"
        assert result[0]["customer_phone"] == "555-123-4567"
        assert "links" in result[0]

    def test_generate_sync_hash(self, mobile_service):
        """Test generating a hash for data verification."""
        # Arrange
        jobs = [{"id": 1, "title": "Fix Router"}]
        notifications = [{"id": 1, "title": "New Job"}]
        inventory = [{"inventory_id": 1, "quantity": 5}]
        
        # Create expected hash
        data_string = json.dumps({
            "jobs": jobs,
            "notifications": notifications,
            "inventory": inventory
        }, default=str)
        expected_hash = hashlib.sha256(data_string.encode()).hexdigest()
        
        # Act
        result = mobile_service._generate_sync_hash(jobs, notifications, inventory)
        
        # Assert
        assert result == expected_hash

    def test_get_offline_data_package(self, mobile_service, mock_db, sample_technician):
        """Test getting a complete data package for offline use."""
        # Arrange
        technician_id = 1
        
        # Mock technician query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_technician
        
        # Mock data retrieval
        with patch.object(mobile_service, '_get_technician_jobs') as mock_get_jobs:
            mock_get_jobs.return_value = [
                {
                    "id": 1,
                    "title": "Fix Router Connection",
                    "status": "ASSIGNED",
                    "customer_id": 1,
                    "links": []
                }
            ]
            
            with patch.object(mobile_service, '_get_technician_inventory') as mock_get_inventory:
                mock_get_inventory.return_value = [
                    {
                        "inventory_id": 1,
                        "inventory_name": "Router",
                        "quantity": 5,
                        "links": []
                    }
                ]
                
                # Act
                result = mobile_service.get_offline_data_package(technician_id)
        
        # Assert
        assert result["technician_id"] == technician_id
        assert "package_time" in result
        assert "package_hash" in result
        assert len(result["jobs"]) == 1
        assert len(result["inventory"]) == 1
        assert "reference_data" in result
        assert "links" in result
