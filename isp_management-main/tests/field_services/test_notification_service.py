"""
Test module for the Notification Service in the Field Services Module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session
from tests.field_services.conftest import (
    MockTechnicianNotification, MockJob, MockTechnician
)
from modules.field_services.models import (
    NotificationTypeEnum, NotificationPriorityEnum,
    JobStatusEnum
)
from modules.field_services.schemas import (
    TechnicianNotificationCreate, TechnicianNotificationUpdate, TechnicianNotificationResponse
)
from modules.field_services.services import NotificationService


class TestNotificationService:
    """Test cases for the NotificationService class."""

    def test_create_notification(self, notification_service, mock_db, sample_notification_data):
        """Test creating a new notification."""
        # Arrange
        notification_create = TechnicianNotificationCreate(**sample_notification_data)
        
        # Patch the internal TechnicianNotification model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.TechnicianNotification', MockTechnicianNotification):
            # Mock the database operations
            mock_db.add.return_value = None
            mock_db.commit.return_value = None
            mock_db.refresh.side_effect = lambda x: setattr(x, 'id', 1)
            
            # Mock the _to_response method
            with patch.object(notification_service, '_to_response') as mock_to_response:
                current_time = datetime.utcnow()
                mock_to_response.return_value = TechnicianNotificationResponse(
                    id=1,
                    technician_id=notification_create.technician_id,
                    title=notification_create.title,
                    message=notification_create.message,
                    notification_type=notification_create.notification_type,
                    priority=notification_create.priority,
                    job_id=notification_create.job_id,
                    is_read=False,
                    read_at=None,
                    expiry_date=notification_create.expiry_date,
                    created_at=current_time,
                    updated_at=current_time,
                    links=[]
                )
                
                # Act
                result = notification_service.create_notification(notification_create)
                
                # Assert
                assert mock_db.add.called
                assert mock_db.commit.called
                assert mock_db.refresh.called
                assert result.id is not None
                assert result.title == sample_notification_data["title"]
                assert result.is_read is False

    def test_get_technician_notifications(self, notification_service, mock_db, sample_notification):
        """Test retrieving notifications for a technician."""
        # Arrange
        technician_id = 1
        
        # Patch the internal TechnicianNotification model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.TechnicianNotification', MockTechnicianNotification):
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [sample_notification]
            
            # Mock the _to_response method
            with patch.object(notification_service, '_to_response') as mock_to_response:
                current_time = datetime.utcnow()
                mock_to_response.return_value = TechnicianNotificationResponse(
                    id=sample_notification.id,
                    technician_id=sample_notification.technician_id,
                    title=sample_notification.title,
                    message=sample_notification.message,
                    notification_type=sample_notification.notification_type,
                    priority=sample_notification.priority,
                    job_id=sample_notification.job_id,
                    is_read=sample_notification.is_read,
                    read_at=sample_notification.read_at,
                    expiry_date=sample_notification.expiry_date,
                    created_at=current_time,
                    updated_at=current_time,
                    links=[]
                )
                
                # Act
                notifications, total = notification_service.get_technician_notifications(technician_id)
                
                # Assert
                assert mock_db.query.called
                assert len(notifications) == 1
                assert total == 1
                assert notifications[0].id == sample_notification.id
                assert notifications[0].title == sample_notification.title

    def test_get_technician_notifications_unread_only(self, notification_service, mock_db, sample_notification):
        """Test retrieving unread notifications for a technician."""
        # Arrange
        technician_id = 1
        unread_only = True
        
        # Patch the internal TechnicianNotification model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.TechnicianNotification', MockTechnicianNotification):
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [sample_notification]
            
            # Mock the _to_response method
            with patch.object(notification_service, '_to_response') as mock_to_response:
                current_time = datetime.utcnow()
                mock_to_response.return_value = TechnicianNotificationResponse(
                    id=sample_notification.id,
                    technician_id=sample_notification.technician_id,
                    title=sample_notification.title,
                    message=sample_notification.message,
                    notification_type=sample_notification.notification_type,
                    priority=sample_notification.priority,
                    job_id=sample_notification.job_id,
                    is_read=False,
                    read_at=None,
                    expiry_date=sample_notification.expiry_date,
                    created_at=current_time,
                    updated_at=current_time,
                    links=[]
                )
                
                # Act
                notifications, total = notification_service.get_technician_notifications(
                    technician_id, unread_only=unread_only
                )
                
                # Assert
                assert mock_db.query.called
                assert len(notifications) == 1
                assert total == 1
                assert notifications[0].id == sample_notification.id
                assert notifications[0].is_read is False

    def test_mark_notification_as_read(self, notification_service, mock_db, sample_notification):
        """Test marking a notification as read."""
        # Arrange
        notification_id = 1
        
        # Patch the internal TechnicianNotification model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.TechnicianNotification', MockTechnicianNotification):
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value = mock_query
            mock_query.first.return_value = sample_notification
            
            # Mock the _to_response method
            with patch.object(notification_service, '_to_response') as mock_to_response:
                current_time = datetime.utcnow()
                mock_to_response.return_value = TechnicianNotificationResponse(
                    id=sample_notification.id,
                    technician_id=sample_notification.technician_id,
                    title=sample_notification.title,
                    message=sample_notification.message,
                    notification_type=sample_notification.notification_type,
                    priority=sample_notification.priority,
                    job_id=sample_notification.job_id,
                    is_read=True,
                    read_at=current_time,
                    expiry_date=sample_notification.expiry_date,
                    created_at=current_time,
                    updated_at=current_time,
                    links=[]
                )
                
                # Act
                result = notification_service.mark_notification_as_read(notification_id)
                
                # Assert
                assert mock_db.query.called
                assert mock_db.commit.called
                assert result is not None
                assert result.is_read is True
                assert result.read_at is not None

    def test_mark_all_notifications_as_read(self, notification_service, mock_db):
        """Test marking all notifications as read for a technician."""
        # Arrange
        technician_id = 1
        
        # Patch the internal TechnicianNotification model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.TechnicianNotification', MockTechnicianNotification):
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value = mock_query
            mock_query.update.return_value = 5  # 5 notifications updated
            
            # Act
            result = notification_service.mark_all_notifications_as_read(technician_id)
            
            # Assert
            assert mock_db.query.called
            assert mock_db.commit.called
            assert result == 5

    def test_delete_notification(self, notification_service, mock_db, sample_notification):
        """Test deleting a notification."""
        # Arrange
        notification_id = 1
        
        # Patch the internal TechnicianNotification model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.TechnicianNotification', MockTechnicianNotification):
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value = mock_query
            mock_query.first.return_value = sample_notification
            
            # Act
            result = notification_service.delete_notification(notification_id)
            
            # Assert
            assert mock_db.query.called
            assert mock_db.delete.called
            assert mock_db.commit.called
            assert result is True

    def test_create_job_assigned_notification(self, notification_service, mock_db, sample_job):
        """Test creating a notification for a job assignment."""
        # Arrange
        job_id = 1
        technician_id = 1
        
        # Patch the internal Job model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.Job', MockJob):
            # Configure mock_db to return our sample_job
            mock_db.query.return_value.filter.return_value.first.return_value = sample_job
            
            # Mock the create_notification method
            with patch.object(notification_service, 'create_notification') as mock_create:
                current_time = datetime.utcnow()
                mock_create.return_value = TechnicianNotificationResponse(
                    id=1,
                    technician_id=technician_id,
                    title="New Job Assigned",
                    message=f"You have been assigned to job: {sample_job.title}. Please review the details and confirm.",
                    notification_type=NotificationTypeEnum.JOB_ASSIGNMENT,
                    priority=NotificationPriorityEnum.HIGH,
                    job_id=job_id,
                    is_read=False,
                    read_at=None,
                    expiry_date=sample_job.scheduled_end_time,
                    created_at=current_time,
                    updated_at=current_time,
                    links=[]
                )
                
                # Act
                result = notification_service.create_job_assigned_notification(job_id, technician_id)
                
                # Assert
                assert mock_db.query.called
                assert mock_create.called
                assert result.id is not None
                assert result.technician_id == technician_id
                assert result.job_id == job_id
                assert result.notification_type.value == NotificationTypeEnum.JOB_ASSIGNMENT.value

    def test_create_sla_alert_notifications(self, notification_service, mock_db, sample_job):
        """Test creating notifications for jobs approaching SLA deadlines."""
        # Arrange
        
        # Patch the internal Job model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.Job', MockJob):
            # Configure mock_db to return our sample_job
            mock_db.query.return_value.filter.return_value.all.return_value = [sample_job]
            
            # Mock the create_notification method
            with patch.object(notification_service, 'create_notification') as mock_create:
                current_time = datetime.utcnow()
                mock_create.return_value = TechnicianNotificationResponse(
                    id=1,
                    technician_id=sample_job.technician_id,
                    title="SLA Alert",
                    message=f"Job '{sample_job.title}' is approaching its SLA deadline. Only 120 minutes remaining.",
                    notification_type=NotificationTypeEnum.SLA_ALERT,
                    priority=NotificationPriorityEnum.HIGH,
                    job_id=sample_job.id,
                    is_read=False,
                    read_at=None,
                    expiry_date=sample_job.sla_deadline,
                    created_at=current_time,
                    updated_at=current_time,
                    links=[]
                )
                
                # Act
                results = notification_service.create_sla_alert_notifications()
                
                # Assert
                assert mock_db.query.called
                assert mock_create.called
                assert len(results) == 1
                assert results[0].id is not None
                assert results[0].notification_type.value == NotificationTypeEnum.SLA_ALERT.value

    def test_get_notification_statistics(self, notification_service, mock_db):
        """Test getting notification statistics for a technician."""
        # Arrange
        technician_id = 1
        
        # Patch the internal TechnicianNotification model to avoid SQLAlchemy issues
        with patch('modules.field_services.services.notification_service.TechnicianNotification', MockTechnicianNotification):
            # Mock query for unread count
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 5
            
            # Mock query for type counts
            type_counts = [
                (NotificationTypeEnum.JOB_ASSIGNMENT, 2),
                (NotificationTypeEnum.JOB_UPDATE, 1),
                (NotificationTypeEnum.SLA_ALERT, 2)
            ]
            
            # Mock query for priority counts
            priority_counts = [
                (NotificationPriorityEnum.HIGH, 3),
                (NotificationPriorityEnum.MEDIUM, 2)
            ]
            
            # Configure the mock to return different results for different queries
            mock_db.query.side_effect = lambda *args: mock_query
            
            # Configure group_by to return a mock that will return type_counts or priority_counts
            mock_query.group_by.side_effect = lambda col: {
                MockTechnicianNotification.notification_type: MagicMock(all=lambda: type_counts),
                MockTechnicianNotification.priority: MagicMock(all=lambda: priority_counts)
            }.get(col, mock_query)
            
            # Act
            result = notification_service.get_notification_statistics(technician_id)
            
            # Assert
            assert mock_db.query.called
            assert result["technician_id"] == technician_id
            assert result["total_unread"] == 5
            assert "by_type" in result
            assert "by_priority" in result
