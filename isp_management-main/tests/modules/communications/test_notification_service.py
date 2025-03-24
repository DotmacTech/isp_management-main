"""
Tests for the NotificationService in the Communications module.

This module contains tests for the notification functionality of the
ISP Management Platform's Communications module.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

# Import directly from the communications module
from modules.communications import NotificationService
from modules.communications.models import Notification, NotificationType, DeliveryMethod
from modules.communications.schemas import NotificationCreate
from modules.communications.webhooks import WebhookService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    
    # Mock the User model
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    
    # Configure db.query to return appropriate mock objects
    db.query.return_value.filter.return_value.first.return_value = mock_user
    
    return db


@pytest.fixture
def mock_background_tasks():
    """Create a mock BackgroundTasks object."""
    return MagicMock(spec=BackgroundTasks)


@pytest.fixture
def mock_webhook_service():
    """Create a mock for the WebhookService."""
    with patch.object(WebhookService, 'trigger_event', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def notification_data():
    """Create test notification data."""
    return NotificationCreate(
        title="Test Notification",
        content="This is a test notification",
        notification_type=NotificationType.SYSTEM,
        is_actionable=True,
        action_url="https://example.com/actions/1",
        delivery_method=DeliveryMethod.IN_APP,
        recipient_ids=[2, 3],
        expires_at=datetime.utcnow().replace(hour=23, minute=59, second=59)
    )


@pytest.mark.asyncio
async def test_create_notification(mock_db, mock_background_tasks, mock_webhook_service, notification_data):
    """Test creating a new notification."""
    # Set up the mock database
    mock_notification = MagicMock()
    mock_notification.id = 1
    mock_notification.title = notification_data.title
    mock_notification.content = notification_data.content
    mock_notification.notification_type = notification_data.notification_type
    mock_notification.is_actionable = notification_data.is_actionable
    mock_notification.action_url = notification_data.action_url
    mock_notification.delivery_method = notification_data.delivery_method
    mock_notification.is_read = False
    mock_notification.read_at = None
    mock_notification.created_at = datetime.utcnow()
    mock_notification.expires_at = notification_data.expires_at
    mock_notification.recipients = []
    
    # Configure the db add and commit methods
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    
    # Configure the Notification model creation mock
    with patch('modules.communications.models.Notification', return_value=mock_notification):
        # Call the create_notification method
        result = await NotificationService.create_notification(
            db=mock_db,
            notification_data=notification_data,
            sender_id=1,
            background_tasks=mock_background_tasks
        )
        
        # Assertions
        assert result is mock_notification
        assert result.title == notification_data.title
        assert result.content == notification_data.content
        assert result.notification_type == notification_data.notification_type
        assert result.is_actionable == notification_data.is_actionable
        assert result.action_url == notification_data.action_url
        assert result.delivery_method == notification_data.delivery_method
        assert result.expires_at == notification_data.expires_at
        
        # Verify db interactions
        mock_db.add.assert_called_once()
        assert mock_db.commit.call_count >= 1
        assert mock_db.refresh.call_count >= 1
        
        # Verify background task was added for webhook
        mock_background_tasks.add_task.assert_called_once()
        call_args = mock_background_tasks.add_task.call_args
        
        # Check that the first argument is WebhookService.trigger_event
        assert call_args[0][0] == WebhookService.trigger_event
        
        # Check that the second argument is the event type
        assert call_args[0][1] == "notification.created"
        
        # Check that the payload contains the expected fields
        payload = call_args[0][2]
        assert payload["notification_id"] == mock_notification.id
        assert payload["title"] == mock_notification.title
        assert "notification_type" in payload
        assert "sender_id" in payload


@pytest.mark.asyncio
async def test_trigger_notification_webhook(mock_db, mock_webhook_service):
    """Test triggering a webhook for a notification event."""
    # Set up the mock notification
    mock_notification = MagicMock()
    mock_notification.id = 1
    mock_notification.title = "Test Notification"
    mock_notification.notification_type = NotificationType.SYSTEM
    mock_notification.sender_id = 1
    mock_notification.recipients = [MagicMock(id=2), MagicMock(id=3)]
    mock_notification.created_at = datetime.utcnow()
    
    # Mock the get_notification method
    with patch.object(NotificationService, 'get_notification', new_callable=AsyncMock, return_value=mock_notification):
        # Call the _trigger_notification_webhook method
        await NotificationService._trigger_notification_webhook(mock_db, mock_notification.id, "notification.created")
        
        # Verify webhook service was called
        mock_webhook_service.assert_called_once_with(
            event_type="notification.created",
            payload={
                "id": mock_notification.id,
                "sender_id": mock_notification.sender_id,
                "recipient_ids": [2, 3],
                "title": mock_notification.title,
                "notification_type": mock_notification.notification_type.value,
                "created_at": mock_notification.created_at.isoformat(),
                "event_type": "notification.created"
            }
        )


@pytest.mark.asyncio
async def test_get_notification(mock_db):
    """Test retrieving a notification by ID."""
    # Set up the mock notification
    mock_notification = MagicMock()
    mock_notification.id = 1
    
    # Configure the db query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_notification
    
    # Test getting notification as recipient
    mock_notification.recipients = [MagicMock(id=2)]
    result = await NotificationService.get_notification(mock_db, notification_id=1, user_id=2)
    assert result is mock_notification
    
    # Test trying to get notification without permission
    result = await NotificationService.get_notification(mock_db, notification_id=1, user_id=3)
    assert result is None


@pytest.mark.asyncio
async def test_mark_notification_as_read(mock_db):
    """Test marking a notification as read."""
    # Set up the mock notification
    mock_notification = MagicMock()
    mock_notification.id = 1
    mock_notification.is_read = False
    mock_notification.read_at = None
    mock_notification.recipients = [MagicMock(id=1)]
    
    # Configure the db query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_notification
    
    # Mock the get_notification method to return our mock_notification
    with patch.object(NotificationService, 'get_notification', new_callable=AsyncMock, return_value=mock_notification):
        # Test marking notification as read
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime.utcnow()
            mock_datetime.utcnow.return_value = mock_now
            
            result = await NotificationService.mark_as_read(mock_db, notification_id=1, user_id=1)
            
            assert result is mock_notification
            assert result.is_read is True
            assert result.read_at is not None
            mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_notification(mock_db):
    """Test deleting a notification."""
    # Set up the mock notification
    mock_notification = MagicMock()
    mock_notification.id = 1
    mock_notification.recipients = [MagicMock(id=1)]
    
    # Configure the db query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_notification
    
    # Test deleting notification
    result = await NotificationService.delete_notification(mock_db, notification_id=1, user_id=1)
    
    assert result is True
    mock_db.delete.assert_called_once_with(mock_notification)
    mock_db.commit.assert_called_once()
    
    # Test trying to delete notification without permission
    mock_notification.recipients = [MagicMock(id=2)]
    result = await NotificationService.delete_notification(mock_db, notification_id=1, user_id=3)
    
    assert result is False
