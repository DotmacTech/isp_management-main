"""
Tests for the AnnouncementService in the Communications module.

This module contains tests for the announcement functionality of the
ISP Management Platform's Communications module.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

# Import directly from the communications module
from modules.communications import AnnouncementService
from modules.communications.models import Announcement, AnnouncementType
from modules.communications.schemas import AnnouncementCreate, AnnouncementUpdate
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
def announcement_data():
    """Create test announcement data."""
    return AnnouncementCreate(
        title="Test Announcement",
        content="This is a test announcement",
        announcement_type=AnnouncementType.GENERAL,
        is_public=True,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=7),
        targeted_recipient_ids=[2, 3]
    )


@pytest.mark.asyncio
async def test_create_announcement(mock_db, mock_background_tasks, mock_webhook_service, announcement_data):
    """Test creating a new announcement."""
    # Set up the mock database
    mock_announcement = MagicMock()
    mock_announcement.id = 1
    mock_announcement.title = announcement_data.title
    mock_announcement.content = announcement_data.content
    mock_announcement.announcement_type = announcement_data.announcement_type
    mock_announcement.is_public = announcement_data.is_public
    mock_announcement.is_active = True
    mock_announcement.start_date = announcement_data.start_date
    mock_announcement.end_date = announcement_data.end_date
    mock_announcement.created_by = 1
    mock_announcement.created_at = datetime.utcnow()
    mock_announcement.updated_at = datetime.utcnow()
    mock_announcement.targeted_recipients = []
    
    # Configure the db add and commit methods
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    
    # Configure the Announcement model creation mock
    with patch('modules.communications.models.Announcement', return_value=mock_announcement):
        # Call the create_announcement method
        result = await AnnouncementService.create_announcement(
            db=mock_db,
            announcement_data=announcement_data,
            created_by=1,
            background_tasks=mock_background_tasks
        )
        
        # Assertions
        assert result is mock_announcement
        assert result.title == announcement_data.title
        assert result.content == announcement_data.content
        assert result.announcement_type == announcement_data.announcement_type
        assert result.is_public == announcement_data.is_public
        assert result.is_active is True
        assert result.start_date == announcement_data.start_date
        assert result.end_date == announcement_data.end_date
        assert result.created_by == 1
        
        # Verify db interactions
        mock_db.add.assert_called_once()
        assert mock_db.commit.call_count >= 1
        assert mock_db.refresh.call_count >= 1
        
        # Verify background task was added for webhook
        mock_background_tasks.add_task.assert_called_with(
            WebhookService.trigger_event,
            "announcement.created",
            {
                "announcement_id": mock_announcement.id,
                "title": mock_announcement.title,
                "announcement_type": mock_announcement.announcement_type.value,
                "is_public": mock_announcement.is_public,
                "created_at": mock_announcement.created_at.isoformat()
            }
        )


@pytest.mark.asyncio
async def test_trigger_announcement_webhook(mock_db, mock_webhook_service):
    """Test triggering a webhook for an announcement event."""
    # Set up the mock announcement
    mock_announcement = MagicMock()
    mock_announcement.id = 1
    mock_announcement.title = "Test Announcement"
    mock_announcement.announcement_type = AnnouncementType.GENERAL
    mock_announcement.is_public = True
    mock_announcement.created_at = datetime.utcnow()
    
    # Create a test background tasks object
    mock_background_tasks = MagicMock()
    
    # Mock the get_announcement method
    with patch.object(AnnouncementService, 'get_announcement', new_callable=AsyncMock, return_value=mock_announcement):
        # Call the create_announcement method with mocked background_tasks
        # This will trigger the webhook in the background
        announcement_data = AnnouncementCreate(
            title="Test Announcement",
            content="Test content",
            announcement_type=AnnouncementType.GENERAL,
            is_public=True
        )
        
        # Mock the db add and commit methods
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Mock the Announcement model creation
        with patch('modules.communications.models.Announcement', return_value=mock_announcement):
            await AnnouncementService.create_announcement(
                db=mock_db,
                announcement_data=announcement_data,
                created_by=1,
                background_tasks=mock_background_tasks
            )
            
            # Verify background task was added with the correct parameters
            mock_background_tasks.add_task.assert_called_once()
            call_args = mock_background_tasks.add_task.call_args
            
            # Check that the first argument is WebhookService.trigger_event
            assert call_args[0][0] == WebhookService.trigger_event
            
            # Check that the second argument is the event type
            assert call_args[0][1] == "announcement.created"
            
            # Check that the payload contains the expected fields
            payload = call_args[0][2]
            assert payload["announcement_id"] == mock_announcement.id
            assert payload["title"] == mock_announcement.title
            assert payload["announcement_type"] == mock_announcement.announcement_type.value
            assert payload["is_public"] == mock_announcement.is_public
            assert "created_at" in payload


@pytest.mark.asyncio
async def test_get_announcement(mock_db):
    """Test retrieving an announcement by ID."""
    # Set up the mock announcement
    mock_announcement = MagicMock()
    mock_announcement.id = 1
    mock_announcement.is_public = False
    mock_announcement.created_by = 1
    mock_announcement.announcement_type = AnnouncementType.GENERAL
    
    # Configure the db query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_announcement
    
    # Test getting announcement as creator
    result = await AnnouncementService.get_announcement(mock_db, announcement_id=1, user_id=1)
    assert result is mock_announcement
    
    # Test getting announcement as targeted recipient
    mock_announcement.targeted_recipients = [MagicMock(id=2)]
    result = await AnnouncementService.get_announcement(mock_db, announcement_id=1, user_id=2)
    assert result is mock_announcement
    
    # Test getting public announcement
    mock_announcement.is_public = True
    result = await AnnouncementService.get_announcement(mock_db, announcement_id=1, user_id=3)
    assert result is mock_announcement
    
    # Test trying to get private announcement without permission
    mock_announcement.is_public = False
    mock_announcement.targeted_recipients = [MagicMock(id=2)]
    result = await AnnouncementService.get_announcement(mock_db, announcement_id=1, user_id=3)
    assert result is None


@pytest.mark.asyncio
async def test_update_announcement(mock_db, mock_background_tasks):
    """Test updating an announcement."""
    # Set up the mock announcement
    mock_announcement = MagicMock()
    mock_announcement.id = 1
    mock_announcement.created_by = 1
    mock_announcement.title = "Original Title"
    mock_announcement.content = "Original Content"
    mock_announcement.is_active = True
    mock_announcement.announcement_type = AnnouncementType.GENERAL
    mock_announcement.is_public = True
    mock_announcement.created_at = datetime.utcnow()
    mock_announcement.updated_at = datetime.utcnow()
    
    # Configure the db query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_announcement
    
    # Create update data
    update_data = AnnouncementUpdate(
        title="Updated Title",
        content="Updated Content",
        is_active=False
    )
    
    # Test updating announcement
    result = await AnnouncementService.update_announcement(
        db=mock_db,
        announcement_id=1,
        update_data=update_data,
        user_id=1,
        background_tasks=mock_background_tasks
    )
    
    assert result is mock_announcement
    assert result.title == "Updated Title"
    assert result.content == "Updated Content"
    assert result.is_active is False
    mock_db.commit.assert_called_once()
    
    # Verify background task was added for webhook
    mock_background_tasks.add_task.assert_called_with(
        WebhookService.trigger_event,
        "announcement.updated",
        {
            "announcement_id": mock_announcement.id,
            "title": "Updated Title",
            "announcement_type": mock_announcement.announcement_type.value,
            "is_public": mock_announcement.is_public,
            "is_active": False,
            "created_at": mock_announcement.created_at.isoformat(),
            "updated_at": mock_announcement.updated_at.isoformat()
        }
    )
    
    # Test trying to update announcement without permission
    mock_db.reset_mock()
    mock_background_tasks.reset_mock()
    
    result = await AnnouncementService.update_announcement(
        db=mock_db,
        announcement_id=1,
        update_data=update_data,
        user_id=2,
        background_tasks=mock_background_tasks
    )
    
    assert result is None
    mock_db.commit.assert_not_called()
    mock_background_tasks.add_task.assert_not_called()


@pytest.mark.asyncio
async def test_delete_announcement(mock_db):
    """Test deleting an announcement."""
    # Set up the mock announcement
    mock_announcement = MagicMock()
    mock_announcement.id = 1
    mock_announcement.created_by = 1
    
    # Configure the db query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_announcement
    
    # Test deleting announcement
    result = await AnnouncementService.delete_announcement(mock_db, announcement_id=1, user_id=1)
    
    assert result is True
    mock_db.delete.assert_called_once_with(mock_announcement)
    mock_db.commit.assert_called_once()
    
    # Test trying to delete announcement without permission
    mock_db.reset_mock()
    
    result = await AnnouncementService.delete_announcement(mock_db, announcement_id=1, user_id=2)
    
    assert result is False
    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()
