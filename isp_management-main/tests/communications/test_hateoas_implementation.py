"""
Tests for HATEOAS implementation in the Communications module.

This module contains tests to verify that the HATEOAS links are correctly
implemented in the Communications API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import json


def test_messages_endpoint_hateoas(client, test_user):
    """Test that the messages endpoint returns proper HATEOAS links."""
    # Authenticate as test user
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "password123"}
    )
    token = response.json()["access_token"]
    
    # Get messages with authentication
    response = client.get(
        "/api/v1/communications/messages",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/communications/messages"
    
    # If there are messages, check for item links
    if "items" in data and len(data["items"]) > 0:
        message = data["items"][0]
        assert "_links" in message
        assert "self" in message["_links"]
        assert "delete" in message["_links"]
        assert "mark_as_read" in message["_links"]


def test_notifications_endpoint_hateoas(client, test_user):
    """Test that the notifications endpoint returns proper HATEOAS links."""
    # Authenticate as test user
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "password123"}
    )
    token = response.json()["access_token"]
    
    # Get notifications with authentication
    response = client.get(
        "/api/v1/communications/notifications",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/communications/notifications"
    
    # If there are notifications, check for item links
    if "items" in data and len(data["items"]) > 0:
        notification = data["items"][0]
        assert "_links" in notification
        assert "self" in notification["_links"]
        assert "mark_as_read" in notification["_links"]


def test_announcements_endpoint_hateoas(client, test_admin):
    """Test that the announcements endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get announcements with authentication
    response = client.get(
        "/api/v1/communications/announcements",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/communications/announcements"
    assert "create" in data["_links"]
    
    # If there are announcements, check for item links
    if "items" in data and len(data["items"]) > 0:
        announcement = data["items"][0]
        assert "_links" in announcement
        assert "self" in announcement["_links"]
        assert "update" in announcement["_links"]
        assert "delete" in announcement["_links"]


def test_support_tickets_endpoint_hateoas(client, test_user):
    """Test that the support tickets endpoint returns proper HATEOAS links."""
    # Authenticate as test user
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "password123"}
    )
    token = response.json()["access_token"]
    
    # Get support tickets with authentication
    response = client.get(
        "/api/v1/communications/support-tickets",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/communications/support-tickets"
    assert "create" in data["_links"]
    
    # If there are support tickets, check for item links
    if "items" in data and len(data["items"]) > 0:
        ticket = data["items"][0]
        assert "_links" in ticket
        assert "self" in ticket["_links"]
        assert "update" in ticket["_links"]
        assert "close" in ticket["_links"]
        assert "add_comment" in ticket["_links"]
