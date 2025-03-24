"""
Test module for the Job Service in the Field Services Module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, ANY
from sqlalchemy.orm import Session

from modules.field_services.services.job_service import JobService
from modules.field_services.schemas import (
    JobCreate, JobUpdate, JobResponse, JobFilterParams,
    JobStatus, JobPriority, JobType
)
from modules.field_services.models import (
    JobStatusEnum, JobPriorityEnum, JobTypeEnum,
    NotificationTypeEnum
)
from tests.field_services.conftest import (
    MockJob, MockTechnician, MockTechnicianNotification, MockJobHistory
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def job_service(mock_db):
    """Create a JobService instance with a mock database."""
    return JobService(mock_db)


@pytest.fixture
def sample_job_data():
    """Create sample job data for testing."""
    return {
        "title": "Fix Router Connection",
        "description": "Customer reporting intermittent connection issues",
        "customer_id": 1,
        "job_type": JobTypeEnum.INSTALLATION,
        "status": JobStatusEnum.PENDING,
        "priority": JobPriorityEnum.MEDIUM,
        "estimated_duration_minutes": 60,
        "scheduled_start_time": datetime.utcnow() + timedelta(days=1),
        "scheduled_end_time": datetime.utcnow() + timedelta(days=1, hours=1),
        "location_lat": 40.7128,
        "location_lon": -74.0060,
        "location_address": "123 Main St, New York, NY 10001",
        "required_skills": ["networking", "router_configuration"],
        "required_equipment": ["router", "cables", "laptop"]
    }


@pytest.fixture
def sample_job():
    """Create a sample Job instance for testing."""
    job = MockJob(
        id=1,
        title="Fix Router Connection",
        description="Customer reporting intermittent connection issues",
        customer_id=1,
        job_type=JobTypeEnum.INSTALLATION,
        status=JobStatusEnum.PENDING,
        priority=JobPriorityEnum.MEDIUM,
        estimated_duration_minutes=60,
        scheduled_start_time=datetime.utcnow() + timedelta(days=1),
        scheduled_end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        location_lat=40.7128,
        location_lon=-74.0060,
        location_address="123 Main St, New York, NY 10001",
        required_skills=["networking", "router_configuration"],
        required_equipment=["router", "cables", "laptop"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    return job


@pytest.fixture
def sample_job_filter_params():
    """Create sample job filter parameters for testing."""
    return {
        "status": "pending",
        "technician_id": None,
        "customer_id": 1,
        "priority": "medium",
        "page": 1,
        "page_size": 20
    }


class TestJobService:
    """Test cases for the JobService class."""

    def test_create_job(self, job_service, sample_job_data):
        """Test creating a new job."""
        # Arrange
        job_create = JobCreate(**sample_job_data)
        
        # Create a mock response for _to_response
        mock_response = {
            "id": 1,
            "title": job_create.title,
            "description": job_create.description,
            "customer_id": job_create.customer_id,
            "technician_id": job_create.technician_id,
            "status": job_create.status,
            "priority": job_create.priority,
            "job_type": job_create.job_type,
            "estimated_duration_minutes": job_create.estimated_duration_minutes,
            "scheduled_start_time": job_create.scheduled_start_time,
            "scheduled_end_time": job_create.scheduled_end_time,
            "actual_start_time": None,
            "actual_end_time": None,
            "sla_deadline": None,
            "location_lat": job_create.location_lat,
            "location_lon": job_create.location_lon,
            "location_address": job_create.location_address,
            "required_skills": job_create.required_skills,
            "required_equipment": job_create.required_equipment,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": 1,
            "updated_by": None,
            "notes": None,
            "sla_status": "on_track",
            "links": []
        }
        
        # Patch the Job model to use our mock
        with patch('modules.field_services.services.job_service.Job', MockJob), \
             patch('modules.field_services.services.job_service.JobHistory', MockJobHistory), \
             patch.object(job_service, '_to_response', return_value=JobResponse(**mock_response)), \
             patch.object(job_service, '_calculate_sla_deadline'):
            
            # Configure mock_db
            job_service.db.add = MagicMock()
            job_service.db.commit = MagicMock()
            job_service.db.refresh = MagicMock()
            
            # Act
            result = job_service.create_job(job_create, user_id=1)
            
            # Assert
            job_service.db.add.assert_called_once()
            job_service.db.commit.assert_called_once()
            job_service.db.refresh.assert_called_once()
            assert result is not None

    def test_get_job_by_id(self, job_service, sample_job):
        """Test retrieving a job by ID."""
        # Arrange
        job_id = 1
        
        # Create a mock response for _to_response
        mock_response = {
            "id": 1,
            "title": "Test Job",
            "description": "Test Description",
            "customer_id": 1,
            "technician_id": None,
            "status": "pending",
            "priority": "medium",
            "job_type": "installation",
            "estimated_duration_minutes": 60,
            "scheduled_start_time": datetime.utcnow(),
            "scheduled_end_time": datetime.utcnow() + timedelta(hours=1),
            "actual_start_time": None,
            "actual_end_time": None,
            "sla_deadline": datetime.utcnow() + timedelta(days=1),
            "location_lat": 37.7749,
            "location_lon": -122.4194,
            "location_address": "123 Main St",
            "required_skills": ["networking"],
            "required_equipment": ["router"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": 1,
            "updated_by": None,
            "notes": None,
            "sla_status": "on_track",
            "links": []
        }
        
        # Patch the internal Job model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.job_service.Job', MockJob), \
             patch('modules.field_services.services.job_service.joinedload', MagicMock()), \
             patch.object(job_service, '_to_response', return_value=JobResponse(**mock_response)), \
             patch.object(job_service, '_calculate_sla_status', return_value="on_track"):
            
            # Configure mock_db to return sample_job
            mock_query = MagicMock()
            mock_filter = MagicMock()
            
            mock_query.filter.return_value = mock_filter
            mock_filter.first.return_value = sample_job
            job_service.db.query.return_value = mock_query
            
            # Act
            result = job_service.get_job_by_id(job_id)
            
            # Assert
            job_service.db.query.assert_called_once()
            assert result is not None

    def test_get_job_not_found(self, job_service):
        """Test retrieving a non-existent job."""
        # Arrange
        job_id = 999
        
        # Patch the internal Job model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.job_service.Job', MockJob), \
             patch('modules.field_services.services.job_service.joinedload', MagicMock()):
            
            # Configure mock_db to return None
            mock_query = MagicMock()
            mock_filter = MagicMock()
            
            mock_query.filter.return_value = mock_filter
            mock_filter.first.return_value = None
            job_service.db.query.return_value = mock_query
            
            # Act
            result = job_service.get_job_by_id(job_id)
            
            # Assert
            job_service.db.query.assert_called_once()
            assert result is None

    def test_update_job(self, job_service, sample_job):
        """Test updating a job."""
        # Arrange
        job_id = 1
        update_data = JobUpdate(title="Updated Job Title", priority="high")
        
        # Create a mock response for _to_response
        mock_response = {
            "id": 1,
            "title": "Updated Job Title",
            "description": "Test Description",
            "customer_id": 1,
            "technician_id": None,
            "status": "pending",
            "priority": "high",
            "job_type": "installation",
            "estimated_duration_minutes": 60,
            "scheduled_start_time": datetime.utcnow(),
            "scheduled_end_time": datetime.utcnow() + timedelta(hours=1),
            "actual_start_time": None,
            "actual_end_time": None,
            "sla_deadline": datetime.utcnow() + timedelta(days=1),
            "location_lat": 37.7749,
            "location_lon": -122.4194,
            "location_address": "123 Main St",
            "required_skills": ["networking"],
            "required_equipment": ["router"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": 1,
            "updated_by": 1,
            "notes": None,
            "sla_status": "on_track",
            "links": []
        }
        
        # Patch the Job model and get_job_by_id method
        with patch('modules.field_services.services.job_service.Job', MockJob), \
             patch.object(job_service, '_to_response', return_value=JobResponse(**mock_response)), \
             patch.object(job_service, '_calculate_sla_deadline'):
            
            # Mock get_job_by_id to return sample_job
            mock_get_job = MagicMock(return_value=sample_job)
            job_service.get_job_by_id = mock_get_job
            
            # Configure mock_db
            job_service.db.commit.return_value = None
            
            # Act
            result = job_service.update_job(job_id, update_data, user_id=1)
            
            # Assert
            job_service.db.commit.assert_called_once()
            assert result is not None

    def test_delete_job(self, job_service, sample_job):
        """Test deleting a job."""
        # Arrange
        job_id = 1
        
        # Patch the Job model and get_job_by_id method
        with patch('modules.field_services.services.job_service.Job', MockJob):
            
            # Mock get_job_by_id to return sample_job
            mock_get_job = MagicMock(return_value=sample_job)
            job_service.get_job_by_id = mock_get_job
            
            # Configure mock_db
            job_service.db.delete.return_value = None
            job_service.db.commit.return_value = None
            
            # Act
            result = job_service.delete_job(job_id)
            
            # Assert
            job_service.db.delete.assert_called_once_with(sample_job)
            job_service.db.commit.assert_called_once()
            assert result is True

    def test_assign_job_to_technician(self, job_service, sample_job, sample_technician):
        """Test assigning a job to a technician."""
        # Arrange
        job_id = 1
        technician_id = 1
        
        # Create a mock response for _to_response
        mock_response = {
            "id": 1,
            "title": "Test Job",
            "description": "Test Description",
            "customer_id": 1,
            "technician_id": 1,
            "status": "assigned",
            "priority": "medium",
            "job_type": "installation",
            "estimated_duration_minutes": 60,
            "scheduled_start_time": datetime.utcnow(),
            "scheduled_end_time": datetime.utcnow() + timedelta(hours=1),
            "actual_start_time": None,
            "actual_end_time": None,
            "sla_deadline": datetime.utcnow() + timedelta(days=1),
            "location_lat": 37.7749,
            "location_lon": -122.4194,
            "location_address": "123 Main St",
            "required_skills": ["networking"],
            "required_equipment": ["router"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": 1,
            "updated_by": 1,
            "notes": None,
            "sla_status": "on_track",
            "links": []
        }
        
        # Patch the Job model and get_job_by_id method
        with patch('modules.field_services.services.job_service.Job', MockJob), \
             patch('modules.field_services.services.job_service.JobHistory', MockJobHistory), \
             patch.object(job_service, '_to_response', return_value=JobResponse(**mock_response)):
            
            # Mock get_job_by_id to return sample_job
            mock_get_job = MagicMock(return_value=sample_job)
            job_service.get_job_by_id = mock_get_job
            
            # Configure mock_db
            job_service.db.add.return_value = None
            job_service.db.commit.return_value = None
            
            # Act
            result = job_service.assign_job_to_technician(job_id, technician_id, user_id=1)
            
            # Assert
            job_service.db.commit.assert_called_once()
            assert result is not None
            assert sample_job.technician_id == technician_id
            assert sample_job.status == JobStatusEnum.ASSIGNED

    def test_get_jobs(self, job_service, sample_job):
        """Test retrieving jobs with filtering."""
        # Arrange
        status = "pending"
        technician_id = None
        customer_id = 1
        
        # Create a mock response for _to_response
        mock_response = {
            "id": 1,
            "title": "Test Job",
            "description": "Test Description",
            "customer_id": 1,
            "technician_id": None,
            "status": "pending",
            "priority": "medium",
            "job_type": "installation",
            "estimated_duration_minutes": 60,
            "scheduled_start_time": datetime.utcnow(),
            "scheduled_end_time": datetime.utcnow() + timedelta(hours=1),
            "actual_start_time": None,
            "actual_end_time": None,
            "sla_deadline": datetime.utcnow() + timedelta(days=1),
            "location_lat": 37.7749,
            "location_lon": -122.4194,
            "location_address": "123 Main St",
            "required_skills": ["networking"],
            "required_equipment": ["router"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": 1,
            "updated_by": None,
            "notes": None,
            "sla_status": "on_track",
            "links": []
        }
        
        # Patch the Job model
        with patch('modules.field_services.services.job_service.Job', MockJob), \
             patch('modules.field_services.services.job_service.joinedload', MagicMock()), \
             patch.object(job_service, '_to_response', return_value=JobResponse(**mock_response)):
            
            # Configure mock_db
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_count = MagicMock(return_value=1)
            mock_order_by = MagicMock()
            mock_offset = MagicMock()
            mock_limit = MagicMock()
            mock_all = MagicMock(return_value=[sample_job])
            
            mock_query.options.return_value = mock_query
            mock_query.filter.return_value = mock_filter
            mock_filter.count.return_value = mock_count
            mock_filter.order_by.return_value = mock_order_by
            mock_order_by.offset.return_value = mock_offset
            mock_offset.limit.return_value = mock_limit
            mock_limit.all.return_value = [sample_job]
            
            job_service.db.query.return_value = mock_query
            
            # Act
            result, total = job_service.get_jobs(
                status=status,
                technician_id=technician_id,
                customer_id=customer_id
            )
            
            # Assert
            job_service.db.query.assert_called_once()
            assert len(result) == 1

    def test_calculate_sla_deadline(self, job_service, sample_job):
        """Test calculating SLA deadline."""
        # Arrange
        # Patch the SLADefinition model
        with patch('modules.field_services.services.job_service.SLADefinition', MagicMock()):
            # Configure mock_db
            mock_query = MagicMock()
            mock_filter = MagicMock()
            
            mock_query.filter.return_value = mock_filter
            mock_filter.first.return_value = None  # No SLA definition found, use defaults
            job_service.db.query.return_value = mock_query
            
            # Act
            job_service._calculate_sla_deadline(sample_job)
            
            # Assert
            job_service.db.query.assert_called_once()
            assert sample_job.sla_deadline is not None

    def test_calculate_sla_status(self, job_service, sample_job):
        """Test calculating SLA status."""
        # Arrange
        # Set up different scenarios
        
        # 1. Completed job within SLA
        sample_job.status = JobStatusEnum.COMPLETED
        sample_job.actual_end_time = datetime.utcnow() - timedelta(hours=1)
        sample_job.sla_deadline = datetime.utcnow()
        
        # Act
        result = job_service._calculate_sla_status(sample_job)
        
        # Assert
        assert result == "met"
        
        # 2. In-progress job with time remaining
        sample_job.status = JobStatusEnum.IN_PROGRESS
        sample_job.actual_end_time = None
        sample_job.sla_deadline = datetime.utcnow() + timedelta(days=1)
        
        # Act
        result = job_service._calculate_sla_status(sample_job)
        
        # Assert
        assert result == "on_track"
