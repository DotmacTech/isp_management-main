"""
Tests for webhook and external service functionality in the Communications module.

This module contains tests for webhook registration, triggering, and external service integration.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
import httpx
from unittest.mock import patch, AsyncMock
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend_core.main import app
from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user
from modules.communications import models, schemas
from modules.communications.webhooks import WebhookService
from modules.communications.external_services import ExternalServiceManager
from modules.communications.services import MessageService, NotificationService, SupportTicketService

# Test client setup
client = TestClient(app)

# Mock user for authentication
mock_user = models.User(
    id=1,
    username="testadmin",
    email="admin@example.com",
    role="admin",
    is_active=True
)

# Override dependency
@pytest.fixture
def override_get_current_user():
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    yield
    app.dependency_overrides = {}

# Test database session
@pytest.fixture
def test_db():
    # This would typically use a test database
    # For simplicity, we'll use the same get_db function
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


class TestWebhooks:
    """Tests for webhook functionality."""
    
    def test_register_webhook(self, test_db, override_get_current_user):
        """Test webhook registration."""
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["message.created", "notification.created"],
            "is_active": True,
            "secret": "test_secret",
            "headers": {"X-Custom-Header": "Value"},
            "description": "Test webhook for unit tests"
        }
        
        response = client.post("/api/communications/webhooks/", json=webhook_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == webhook_data["name"]
        assert data["url"] == webhook_data["url"]
        assert data["events"] == webhook_data["events"]
        assert data["is_active"] == webhook_data["is_active"]
        
        # Clean up
        webhook_id = data["id"]
        test_db.query(models.Webhook).filter(models.Webhook.id == webhook_id).delete()
        test_db.commit()
    
    def test_get_webhooks(self, test_db, override_get_current_user):
        """Test retrieving webhooks."""
        # Create a test webhook
        webhook = models.Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["message.created"],
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(webhook)
        test_db.commit()
        
        response = client.get("/api/communications/webhooks/")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0
        
        # Clean up
        test_db.delete(webhook)
        test_db.commit()
    
    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_trigger_webhook(self, mock_post, test_db):
        """Test triggering a webhook."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = json.dumps({"status": "success"})
        mock_post.return_value = mock_response
        
        # Create a test webhook
        webhook = models.Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["message.created"],
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(webhook)
        test_db.commit()
        
        # Trigger the webhook
        payload = {"message_id": 1, "content": "Test message"}
        result = await WebhookService.trigger_event(
            db=test_db,
            event="message.created",
            payload=payload
        )
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check that a log was created
        log = test_db.query(models.WebhookLog).filter(
            models.WebhookLog.webhook_id == webhook.id
        ).first()
        
        assert log is not None
        assert log.event == "message.created"
        assert log.success is True
        
        # Clean up
        test_db.delete(log)
        test_db.delete(webhook)
        test_db.commit()


class TestExternalServices:
    """Tests for external service functionality."""
    
    def test_register_external_service(self, test_db, override_get_current_user):
        """Test external service registration."""
        service_data = {
            "name": "Test SMS Service",
            "service_type": "sms",
            "provider": "twilio",
            "config": {
                "account_sid": "test_sid",
                "auth_token": "test_token",
                "from_number": "+1234567890"
            },
            "is_active": True,
            "description": "Test SMS service for unit tests"
        }
        
        response = client.post("/api/communications/external-services/", json=service_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == service_data["name"]
        assert data["service_type"] == service_data["service_type"]
        assert data["provider"] == service_data["provider"]
        assert data["is_active"] == service_data["is_active"]
        
        # Clean up
        service_id = data["id"]
        test_db.query(models.ExternalService).filter(models.ExternalService.id == service_id).delete()
        test_db.commit()
    
    def test_get_external_services(self, test_db, override_get_current_user):
        """Test retrieving external services."""
        # Create a test service
        service = models.ExternalService(
            name="Test Email Service",
            service_type="email",
            provider="sendgrid",
            config={"api_key": "test_key", "from_email": "test@example.com"},
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(service)
        test_db.commit()
        
        response = client.get("/api/communications/external-services/")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0
        
        # Clean up
        test_db.delete(service)
        test_db.commit()
    
    @patch("isp_management.modules.communications.external_services.ExternalServiceManager.send_message")
    @pytest.mark.asyncio
    async def test_send_message_via_external_service(self, mock_send, test_db, override_get_current_user):
        """Test sending a message via an external service."""
        # Mock response
        mock_send.return_value = True
        
        # Create a test service
        service = models.ExternalService(
            name="Test SMS Service",
            service_type="sms",
            provider="twilio",
            config={"account_sid": "test_sid", "auth_token": "test_token", "from_number": "+1234567890"},
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(service)
        test_db.commit()
        
        # Create a test message
        message_data = {
            "recipient_id": 2,
            "subject": "Test SMS",
            "content": "This is a test SMS message",
            "delivery_method": "SMS",
            "priority": "NORMAL"
        }
        
        response = client.post("/api/communications/messages/", json=message_data)
        assert response.status_code == 200
        
        # Verify that the send method was called
        mock_send.assert_called_once()
        
        # Clean up
        message_id = response.json()["id"]
        test_db.query(models.Message).filter(models.Message.id == message_id).delete()
        test_db.delete(service)
        test_db.commit()


class TestIntegration:
    """Integration tests for webhooks and external services."""
    
    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_message_creation_triggers_webhook(self, mock_post, test_db):
        """Test that creating a message triggers a webhook."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = json.dumps({"status": "success"})
        mock_post.return_value = mock_response
        
        # Create a test webhook
        webhook = models.Webhook(
            name="Message Webhook",
            url="https://example.com/webhook",
            events=["message.created"],
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(webhook)
        test_db.commit()
        
        # Create a message
        message_data = schemas.MessageCreate(
            recipient_id=2,
            subject="Test Message",
            content="This is a test message",
            delivery_method=models.DeliveryMethod.IN_APP,
            priority=models.Priority.NORMAL
        )
        
        background_tasks = BackgroundTasks()
        message = await MessageService.create_message(
            db=test_db,
            message_data=message_data,
            sender_id=mock_user.id,
            background_tasks=background_tasks
        )
        
        # Execute background tasks
        for task in background_tasks.tasks:
            await task()
        
        # Verify webhook was called
        mock_post.assert_called_once()
        
        # Check that a log was created
        log = test_db.query(models.WebhookLog).filter(
            models.WebhookLog.webhook_id == webhook.id,
            models.WebhookLog.event == "message.created"
        ).first()
        
        assert log is not None
        assert log.success is True
        
        # Clean up
        test_db.query(models.Message).filter(models.Message.id == message.id).delete()
        test_db.delete(log)
        test_db.delete(webhook)
        test_db.commit()
    
    @patch("isp_management.modules.communications.external_services.ExternalServiceManager.send_notification")
    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_notification_with_webhook_and_external_service(self, mock_post, mock_send, test_db):
        """Test creating a notification that triggers both a webhook and external service."""
        # Mock responses
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = json.dumps({"status": "success"})
        mock_post.return_value = mock_response
        mock_send.return_value = True
        
        # Create a test webhook
        webhook = models.Webhook(
            name="Notification Webhook",
            url="https://example.com/webhook",
            events=["notification.created"],
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(webhook)
        
        # Create a test service
        service = models.ExternalService(
            name="Test Push Service",
            service_type="push",
            provider="firebase",
            config={"api_key": "test_key"},
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(service)
        test_db.commit()
        
        # Create a notification
        notification_data = schemas.NotificationCreate(
            recipient_id=2,
            title="Test Notification",
            content="This is a test notification",
            notification_type=models.NotificationType.PUSH,
            priority=models.Priority.HIGH
        )
        
        background_tasks = BackgroundTasks()
        notification = await NotificationService.create_notification(
            db=test_db,
            notification_data=notification_data,
            sender_id=mock_user.id,
            background_tasks=background_tasks
        )
        
        # Execute background tasks
        for task in background_tasks.tasks:
            await task()
        
        # Verify webhook was called
        mock_post.assert_called_once()
        
        # Verify external service was called
        mock_send.assert_called_once()
        
        # Clean up
        test_db.query(models.Notification).filter(models.Notification.id == notification.id).delete()
        test_db.query(models.WebhookLog).filter(models.WebhookLog.webhook_id == webhook.id).delete()
        test_db.delete(webhook)
        test_db.delete(service)
        test_db.commit()
    
    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_support_ticket_workflow_with_webhooks(self, mock_post, test_db):
        """Test the support ticket workflow with webhooks."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = json.dumps({"status": "success"})
        mock_post.return_value = mock_response
        
        # Create test webhooks for different ticket events
        webhook_created = models.Webhook(
            name="Ticket Created Webhook",
            url="https://example.com/webhook/created",
            events=["ticket.created"],
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(webhook_created)
        
        webhook_updated = models.Webhook(
            name="Ticket Updated Webhook",
            url="https://example.com/webhook/updated",
            events=["ticket.updated"],
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(webhook_updated)
        
        webhook_response = models.Webhook(
            name="Ticket Response Webhook",
            url="https://example.com/webhook/response",
            events=["ticket.response_added"],
            is_active=True,
            created_by=mock_user.id
        )
        test_db.add(webhook_response)
        test_db.commit()
        
        # 1. Create a ticket
        ticket_data = schemas.SupportTicketCreate(
            subject="Test Ticket",
            description="This is a test ticket",
            category=models.TicketCategory.TECHNICAL,
            priority=models.Priority.HIGH,
            attachments=[]
        )
        
        background_tasks = BackgroundTasks()
        ticket = await SupportTicketService.create_ticket(
            db=test_db,
            ticket_data=ticket_data,
            customer_id=mock_user.id,
            background_tasks=background_tasks
        )
        
        # Execute background tasks
        for task in background_tasks.tasks:
            await task()
        
        # Verify webhook was called for ticket creation
        assert mock_post.call_count == 1
        
        # 2. Update the ticket
        update_data = schemas.SupportTicketUpdate(
            status=models.TicketStatus.IN_PROGRESS,
            priority=models.Priority.NORMAL
        )
        
        background_tasks = BackgroundTasks()
        updated_ticket = await SupportTicketService.update_ticket(
            db=test_db,
            ticket_id=ticket.id,
            ticket_data=update_data,
            user_id=mock_user.id,
            background_tasks=background_tasks
        )
        
        # Execute background tasks
        for task in background_tasks.tasks:
            await task()
        
        # Verify webhook was called for ticket update
        assert mock_post.call_count == 2
        
        # 3. Add a response to the ticket
        response_data = schemas.TicketResponseCreate(
            content="This is a test response",
            is_internal=False,
            attachments=[]
        )
        
        background_tasks = BackgroundTasks()
        ticket_response = await SupportTicketService.add_response(
            db=test_db,
            ticket_id=ticket.id,
            response_data=response_data,
            responder_id=mock_user.id,
            background_tasks=background_tasks
        )
        
        # Execute background tasks
        for task in background_tasks.tasks:
            await task()
        
        # Verify webhooks were called for response added and ticket updated
        assert mock_post.call_count == 4
        
        # Clean up
        test_db.query(models.TicketResponse).filter(models.TicketResponse.id == ticket_response.id).delete()
        test_db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket.id).delete()
        test_db.query(models.WebhookLog).delete()
        test_db.delete(webhook_created)
        test_db.delete(webhook_updated)
        test_db.delete(webhook_response)
        test_db.commit()
