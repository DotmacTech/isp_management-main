"""
Tests for HATEOAS implementation in the Monitoring module.

This module contains tests to verify that the HATEOAS links are correctly
implemented in the Monitoring API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import json


def test_health_check_endpoint_hateoas(client, test_admin, mock_monitoring_service):
    """Test that the health check endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get system health with authentication
    response = client.get(
        "/api/v1/monitoring/health",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for self link
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/monitoring/health"
    
    # Check for related links
    assert "metrics" in data["_links"]
    assert "alerts" in data["_links"]


def test_metrics_endpoint_hateoas(client, test_admin, mock_monitoring_service):
    """Test that the metrics endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get metrics with authentication
    response = client.get(
        "/api/v1/monitoring/metrics",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/monitoring/metrics"
    
    # Check for related links
    assert "health" in data["_links"]
    assert "record" in data["_links"]


def test_alerts_endpoint_hateoas(client, test_admin, mock_monitoring_service):
    """Test that the alerts endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get active alerts with authentication
    response = client.get(
        "/api/v1/monitoring/alerts",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/monitoring/alerts"
    assert "create" in data["_links"]
    
    # If there are alerts, check for item links
    if "items" in data and len(data["items"]) > 0:
        alert = data["items"][0]
        assert "_links" in alert
        assert "self" in alert["_links"]
        assert "update" in alert["_links"]
        assert "resolve" in alert["_links"]
        assert "delete" in alert["_links"]


def test_alert_configurations_endpoint_hateoas(client, test_admin):
    """Test that the alert configurations endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get alert configurations with authentication
    response = client.get(
        "/api/v1/monitoring/alert-configurations",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/monitoring/alert-configurations"
    assert "create" in data["_links"]
    
    # If there are configurations, check for item links
    if "items" in data and len(data["items"]) > 0:
        config = data["items"][0]
        assert "_links" in config
        assert "self" in config["_links"]
        assert "update" in config["_links"]
        assert "delete" in config["_links"]


def test_alert_history_endpoint_hateoas(client, test_admin):
    """Test that the alert history endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get alert history with authentication
    response = client.get(
        "/api/v1/monitoring/alert-history",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/monitoring/alert-history"
    
    # If there are history items, check for item links
    if "items" in data and len(data["items"]) > 0:
        history_item = data["items"][0]
        assert "_links" in history_item
        assert "self" in history_item["_links"]
        assert "alert" in history_item["_links"]


def test_reports_endpoint_hateoas(client, test_admin):
    """Test that the reports endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get reports with authentication
    response = client.get(
        "/api/v1/monitoring/reports",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/monitoring/reports"
    assert "generate" in data["_links"]
    
    # If there are reports, check for item links
    if "items" in data and len(data["items"]) > 0:
        report = data["items"][0]
        assert "_links" in report
        assert "self" in report["_links"]
        assert "download" in report["_links"]
        assert "delete" in report["_links"]


def test_dashboards_endpoint_hateoas(client, test_admin):
    """Test that the dashboards endpoint returns proper HATEOAS links."""
    # Authenticate as admin user
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    
    # Get dashboards with authentication
    response = client.get(
        "/api/v1/monitoring/dashboards",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert response is successful
    assert response.status_code == 200
    
    # Check that the response contains _links
    data = response.json()
    assert "_links" in data
    
    # Check for collection links
    assert "self" in data["_links"]
    assert data["_links"]["self"]["href"] == "/api/v1/monitoring/dashboards"
    assert "create" in data["_links"]
    
    # If there are dashboards, check for item links
    if "items" in data and len(data["items"]) > 0:
        dashboard = data["items"][0]
        assert "_links" in dashboard
        assert "self" in dashboard["_links"]
        assert "update" in dashboard["_links"]
        assert "delete" in dashboard["_links"]
        assert "widgets" in dashboard["_links"]
