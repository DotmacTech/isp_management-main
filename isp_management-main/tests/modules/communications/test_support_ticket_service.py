"""
Tests for the SupportTicketService in the Communications module.

This module contains tests for the support ticket functionality of the
ISP Management Platform's Communications module.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

# Import directly from the communications module
from modules.communications import SupportTicketService
from modules.communications.models import SupportTicket, TicketResponse, TicketStatus, TicketPriority, TicketCategory
from modules.communications.schemas import SupportTicketCreate, SupportTicketUpdate, TicketResponseCreate
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
def ticket_data():
    """Create test support ticket data."""
    return SupportTicketCreate(
        subject="Internet Connection Issue",
        description="My internet connection keeps dropping every 30 minutes",
        category=TicketCategory.TECHNICAL,
        priority=TicketPriority.HIGH,
        attachments=[]
    )


@pytest.fixture
def ticket_response_data():
    """Create test ticket response data."""
    return TicketResponseCreate(
        response_text="We're investigating your issue. Please try resetting your router.",
        is_internal=False,
        attachments=[]
    )


@pytest.mark.asyncio
async def test_create_ticket(mock_db, mock_background_tasks, mock_webhook_service, ticket_data):
    """Test creating a new support ticket."""
    # Set up the mock ticket
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.subject = ticket_data.subject
    mock_ticket.description = ticket_data.description
    mock_ticket.category = ticket_data.category
    mock_ticket.priority = ticket_data.priority
    mock_ticket.status = TicketStatus.OPEN
    mock_ticket.created_by = 1
    mock_ticket.ticket_number = "TKT-10001"
    mock_ticket.created_at = datetime.utcnow()
    mock_ticket.updated_at = datetime.utcnow()
    mock_ticket.attachments = []
    
    # Configure the db add and commit methods
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    
    # Configure the SupportTicket model creation mock
    with patch('modules.communications.models.SupportTicket', return_value=mock_ticket):
        # Call the create_ticket method
        result = await SupportTicketService.create_ticket(
            db=mock_db,
            ticket_data=ticket_data,
            user_id=1,
            background_tasks=mock_background_tasks
        )
        
        # Assertions
        assert result is mock_ticket
        assert result.subject == ticket_data.subject
        assert result.description == ticket_data.description
        assert result.category == ticket_data.category
        assert result.priority == ticket_data.priority
        assert result.status == TicketStatus.OPEN
        assert result.created_by == 1
        
        # Verify db interactions
        mock_db.add.assert_called_once()
        assert mock_db.commit.call_count >= 1
        assert mock_db.refresh.call_count >= 1
        
        # Verify background task was added for webhook
        mock_background_tasks.add_task.assert_called_once()
        call_args = mock_background_tasks.add_task.call_args
        
        # Check that the first argument is WebhookService.trigger_event
        assert call_args[0][0] == WebhookService.trigger_event
        
        # Check that the event type is "ticket.created"
        assert call_args[0][1] == "ticket.created"
        
        # Check that the payload contains the expected fields
        payload = call_args[0][2]
        assert "ticket_id" in payload
        assert payload["ticket_id"] == mock_ticket.id
        assert "subject" in payload
        assert "user_id" in payload
        assert "category" in payload
        assert "priority" in payload
        assert "status" in payload


@pytest.mark.asyncio
async def test_trigger_ticket_webhook(mock_db, mock_webhook_service):
    """Test triggering a webhook for a ticket event."""
    # Set up the mock ticket
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.ticket_number = "TKT-10001"
    mock_ticket.subject = "Internet Connection Issue"
    mock_ticket.status = TicketStatus.OPEN
    mock_ticket.priority = TicketPriority.HIGH
    mock_ticket.category = TicketCategory.TECHNICAL
    mock_ticket.created_by = 1
    mock_ticket.assigned_to = None
    mock_ticket.created_at = datetime.utcnow()
    
    # Mock the get_ticket method
    with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=mock_ticket):
        # Call the _trigger_ticket_webhook method
        await SupportTicketService._trigger_ticket_webhook(mock_db, mock_ticket.id, "ticket.created")
        
        # Verify webhook service was called
        mock_webhook_service.assert_called_once()
        call_args = mock_webhook_service.call_args
        
        # Check that the first argument is the event type
        assert call_args[1]["event_type"] == "ticket.created"
        
        # Check that the payload contains the expected fields
        payload = call_args[1]["payload"]
        assert "id" in payload
        assert payload["id"] == mock_ticket.id
        assert "subject" in payload
        assert "status" in payload
        assert "priority" in payload
        assert "category" in payload
        assert "created_by" in payload


@pytest.mark.asyncio
async def test_get_ticket(mock_db):
    """Test retrieving a ticket by ID."""
    # Set up the mock ticket
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.created_by = 1
    mock_ticket.assigned_to = 2
    
    # Configure the db query for the ticket
    mock_db.query.return_value.filter.return_value.first.return_value = mock_ticket
    
    # Test getting ticket as creator
    result = await SupportTicketService.get_ticket(mock_db, ticket_id=1, user_id=1)
    assert result is mock_ticket
    
    # Test getting ticket as assignee
    result = await SupportTicketService.get_ticket(mock_db, ticket_id=1, user_id=2)
    assert result is mock_ticket
    
    # Test getting ticket as admin
    # Mock the User query to return a staff user
    mock_staff_user = MagicMock()
    mock_staff_user.is_staff = True
    
    # Configure the db query to return the ticket and then the staff user
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_ticket, mock_staff_user]
    
    result = await SupportTicketService.get_ticket(mock_db, ticket_id=1, user_id=3)
    assert result is mock_ticket
    
    # Test trying to get ticket without permission
    # Reset the mock
    mock_db.reset_mock()
    
    # Mock the User query to return a non-staff user
    mock_non_staff_user = MagicMock()
    mock_non_staff_user.is_staff = False
    
    # Configure the db query to return the ticket and then the non-staff user
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_ticket, mock_non_staff_user]
    
    result = await SupportTicketService.get_ticket(mock_db, ticket_id=1, user_id=3)
    assert result is None


@pytest.mark.asyncio
async def test_update_ticket_status(mock_db, mock_background_tasks):
    """Test updating a ticket's status."""
    # Set up the mock ticket
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.created_by = 1
    mock_ticket.assigned_to = 2
    mock_ticket.status = TicketStatus.OPEN
    
    # Mock the User query to return a staff user
    mock_staff_user = MagicMock()
    mock_staff_user.is_staff = True
    
    # Configure the db query to return a staff user when queried
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_staff_user]
    
    # Test updating ticket status
    with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=mock_ticket):
        result = await SupportTicketService.update_ticket_status(
            db=mock_db,
            ticket_id=1,
            status=TicketStatus.IN_PROGRESS,
            user_id=2,
            background_tasks=mock_background_tasks
        )
        
        assert result is mock_ticket
        assert result.status == TicketStatus.IN_PROGRESS
        mock_db.commit.assert_called_once()
        
        # Verify background task was added for webhook
        mock_background_tasks.add_task.assert_called_once()
        call_args = mock_background_tasks.add_task.call_args
        
        # Check that the first argument is SupportTicketService._trigger_ticket_webhook
        assert call_args[0][0] == SupportTicketService._trigger_ticket_webhook
        
        # Check that the db parameter is passed
        assert call_args[0][1] == mock_db
        
        # Check that the ticket_id is passed
        assert call_args[0][2] == 1
        
        # Check that the event type is "ticket.status_updated"
        assert call_args[0][3] == "ticket.status_updated"
    
    # Test trying to update status without permission
    mock_db.reset_mock()
    mock_background_tasks.reset_mock()
    
    # Mock the User query to return a non-staff user
    mock_non_staff_user = MagicMock()
    mock_non_staff_user.is_staff = False
    
    # Configure the db query to return a non-staff user when queried
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_non_staff_user]
    
    # Mock the get_ticket method to return None for unauthorized user
    with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=None):
        result = await SupportTicketService.update_ticket_status(
            db=mock_db,
            ticket_id=1,
            status=TicketStatus.IN_PROGRESS,
            user_id=3,
            background_tasks=mock_background_tasks
        )
        
        assert result is None
        mock_db.commit.assert_not_called()
        mock_background_tasks.add_task.assert_not_called()


@pytest.mark.asyncio
async def test_add_ticket_response(mock_db, mock_background_tasks, ticket_response_data):
    """Test adding a response to a ticket."""
    # Set up the mock ticket
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.created_by = 1
    mock_ticket.assigned_to = 2
    mock_ticket.status = TicketStatus.OPEN
    
    # Set up the mock response
    mock_response = MagicMock()
    mock_response.id = 1
    mock_response.ticket_id = 1
    mock_response.responder_id = 2
    mock_response.response_text = ticket_response_data.response_text
    mock_response.is_internal = ticket_response_data.is_internal
    mock_response.created_at = datetime.utcnow()
    mock_response.updated_at = datetime.utcnow()
    
    # Configure the db query for the ticket
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_ticket]
    
    # Configure the TicketResponse model creation mock
    with patch('modules.communications.models.TicketResponse', return_value=mock_response):
        # Mock the get_ticket method
        with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=mock_ticket):
            # Test adding response as assignee
            result = await SupportTicketService.add_ticket_response(
                db=mock_db,
                ticket_id=1,
                response_data=ticket_response_data,
                user_id=2,
                background_tasks=mock_background_tasks
            )
            
            assert result is mock_response
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            
            # Verify background task was added for webhook
            mock_background_tasks.add_task.assert_called_once()
            call_args = mock_background_tasks.add_task.call_args
            
            # Check that the first argument is WebhookService.trigger_event
            assert call_args[0][0] == WebhookService.trigger_event
            
            # Check that the event type is "ticket.response_added"
            assert call_args[0][1] == "ticket.response_added"
            
            # Check that the payload contains the expected fields
            payload = call_args[0][2]
            assert "ticket_id" in payload
            assert "response_id" in payload
            assert "responder_id" in payload
            assert "is_internal" in payload
    
    # Test adding response as customer
    mock_db.reset_mock()
    mock_background_tasks.reset_mock()
    
    with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=mock_ticket):
        with patch('modules.communications.models.TicketResponse', return_value=mock_response):
            result = await SupportTicketService.add_ticket_response(
                db=mock_db,
                ticket_id=1,
                response_data=ticket_response_data,
                user_id=1,
                background_tasks=mock_background_tasks
            )
            
            assert result is mock_response
    
    # Test trying to add response without permission
    mock_db.reset_mock()
    mock_background_tasks.reset_mock()
    
    # Mock the User query to return a non-staff user
    mock_non_staff_user = MagicMock()
    mock_non_staff_user.is_staff = False
    
    # Configure the db query to return a non-staff user when queried
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_ticket, mock_non_staff_user]
    
    # Mock the get_ticket method to return None for unauthorized user
    with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=None):
        result = await SupportTicketService.add_ticket_response(
            db=mock_db,
            ticket_id=1,
            response_data=ticket_response_data,
            user_id=3,
            background_tasks=mock_background_tasks
        )
        
        assert result is None
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_assign_ticket(mock_db, mock_background_tasks):
    """Test assigning a ticket to an agent."""
    # Set up the mock ticket
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.assigned_to = None
    mock_ticket.status = TicketStatus.OPEN
    
    # Mock the User query to return a staff user
    mock_staff_user = MagicMock()
    mock_staff_user.is_staff = True
    
    # Configure the db query to return a staff user when queried
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_staff_user, mock_staff_user]
    
    # Test assigning ticket as admin
    with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=mock_ticket):
        result = await SupportTicketService.assign_ticket(
            db=mock_db,
            ticket_id=1,
            staff_id=2,
            assigner_id=1,
            background_tasks=mock_background_tasks
        )
        
        assert result is mock_ticket
        assert result.assigned_to == 2
        assert result.status == TicketStatus.IN_PROGRESS
        mock_db.commit.assert_called_once()
        
        # Verify background task was added for webhook
        mock_background_tasks.add_task.assert_called_once()
        call_args = mock_background_tasks.add_task.call_args
        
        # Check that the first argument is SupportTicketService._trigger_ticket_webhook
        assert call_args[0][0] == SupportTicketService._trigger_ticket_webhook
        
        # Check that the db parameter is passed
        assert call_args[0][1] == mock_db
        
        # Check that the ticket_id is passed
        assert call_args[0][2] == 1
        
        # Check that the event type is "ticket.assigned"
        assert call_args[0][3] == "ticket.assigned"
    
    # Test trying to assign ticket without permission
    mock_db.reset_mock()
    mock_background_tasks.reset_mock()
    
    # Mock the User query to return a non-staff user
    mock_non_staff_user = MagicMock()
    mock_non_staff_user.is_staff = False
    
    # Configure the db query to return a non-staff user when queried
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_non_staff_user]
    
    # Mock the get_ticket method to return None for unauthorized user
    with patch.object(SupportTicketService, 'get_ticket', new_callable=AsyncMock, return_value=None):
        result = await SupportTicketService.assign_ticket(
            db=mock_db,
            ticket_id=1,
            staff_id=2,
            assigner_id=3,
            background_tasks=mock_background_tasks
        )
        
        assert result is None
        mock_db.commit.assert_not_called()
        mock_background_tasks.add_task.assert_not_called()
