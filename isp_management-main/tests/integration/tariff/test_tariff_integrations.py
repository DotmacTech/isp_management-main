"""
Integration tests for the Tariff Enforcement Module's RADIUS and Billing integrations.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import asyncio
import json
import pytest
import httpx
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

# Import the modules after conftest.py has set up the mock modules
from modules.tariff.radius_integration import RadiusIntegration
from modules.tariff.billing_integration import BillingIntegration


@pytest.mark.asyncio
async def test_radius_integration_apply_policy():
    """Test applying a RADIUS policy to a user."""
    radius = RadiusIntegration(
        api_url="http://radius-api.example.com",
        api_key="test-radius-key",
        timeout=10.0
    )
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "Policy applied successfully"
        }
        mock_request.return_value = mock_response
        
        result = await radius.apply_policy(username="testuser", policy_id=101)
        
        assert result["status"] == "success"
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert "testuser" in json.loads(call_kwargs["content"])
        assert 101 in json.loads(call_kwargs["content"]).values()


@pytest.mark.asyncio
async def test_radius_integration_update_bandwidth():
    """Test updating bandwidth limits for a user."""
    radius = RadiusIntegration(
        api_url="http://radius-api.example.com",
        api_key="test-radius-key",
        timeout=10.0
    )
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "Bandwidth updated successfully"
        }
        mock_request.return_value = mock_response
        
        result = await radius.update_bandwidth(
            username="testuser",
            download_speed=50,
            upload_speed=10
        )
        
        assert result["status"] == "success"
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert "testuser" in json.loads(call_kwargs["content"])
        assert 50 in json.loads(call_kwargs["content"]).values()
        assert 10 in json.loads(call_kwargs["content"]).values()


@pytest.mark.asyncio
async def test_radius_integration_throttle_user():
    """Test throttling a user's bandwidth."""
    radius = RadiusIntegration(
        api_url="http://radius-api.example.com",
        api_key="test-radius-key",
        timeout=10.0
    )
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "User throttled successfully"
        }
        mock_request.return_value = mock_response
        
        result = await radius.throttle_user(
            username="testuser",
            download_speed=5,
            upload_speed=2,
            reason="data_cap_exceeded"
        )
        
        assert result["status"] == "success"
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert "testuser" in json.loads(call_kwargs["content"])
        assert 5 in json.loads(call_kwargs["content"]).values()
        assert 2 in json.loads(call_kwargs["content"]).values()
        assert "data_cap_exceeded" in json.loads(call_kwargs["content"]).values()


@pytest.mark.asyncio
async def test_billing_integration_create_invoice_item():
    """Test creating an invoice item."""
    billing = BillingIntegration(
        api_url="http://billing-api.example.com",
        api_key="test-billing-key",
        timeout=10.0
    )
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "invoice_item_id": 123,
            "amount": 29.99
        }
        mock_request.return_value = mock_response
        
        result = await billing.create_invoice_item(
            user_id=123,
            amount=Decimal("29.99"),
            description="Monthly subscription - Test Plan"
        )
        
        assert result["status"] == "success"
        assert result["invoice_item_id"] == 123
        assert result["amount"] == 29.99
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert 123 in json.loads(call_kwargs["content"]).values()
        assert "29.99" in json.loads(call_kwargs["content"]).values()
        assert "Monthly subscription" in json.loads(call_kwargs["content"]).values()


@pytest.mark.asyncio
async def test_billing_integration_calculate_prorated_amount():
    """Test calculating a prorated amount for a plan change."""
    billing = BillingIntegration(
        api_url="http://billing-api.example.com",
        api_key="test-billing-key",
        timeout=10.0
    )
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "prorated_refund": 15.00,
            "prorated_charge": 30.00,
            "net_charge": 15.00
        }
        mock_request.return_value = mock_response
        
        result = await billing.calculate_prorated_amount(
            user_id=123,
            old_plan_id=1,
            new_plan_id=2,
            change_date=datetime.now()
        )
        
        assert "prorated_refund" in result
        assert "prorated_charge" in result
        assert "net_charge" in result
        assert result["prorated_refund"] == 15.00
        assert result["prorated_charge"] == 30.00
        assert result["net_charge"] == 15.00
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling_radius_integration():
    """Test error handling in the RADIUS integration."""
    radius = RadiusIntegration(
        api_url="http://radius-api.example.com",
        api_key="test-radius-key",
        timeout=10.0
    )
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "status": "error",
            "message": "Internal server error"
        }
        mock_request.return_value = mock_response
        
        # Test error handling when applying a policy
        with pytest.raises(Exception) as excinfo:
            await radius.apply_policy(username="testuser", policy_id=101)
        
        assert "RADIUS API error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_error_handling_billing_integration():
    """Test error handling in the Billing integration."""
    billing = BillingIntegration(
        api_url="http://billing-api.example.com",
        api_key="test-billing-key",
        timeout=10.0
    )
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "status": "error",
            "message": "Internal server error"
        }
        mock_request.return_value = mock_response
        
        # Test error handling when creating an invoice item
        with pytest.raises(Exception) as excinfo:
            await billing.create_invoice_item(
                user_id=123,
                amount=Decimal("29.99"),
                description="Monthly subscription - Test Plan"
            )
        
        assert "Billing API error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_connection_timeout_handling():
    """Test handling of connection timeouts."""
    radius = RadiusIntegration(
        api_url="http://radius-api.example.com",
        api_key="test-radius-key",
        timeout=1.0
    )
    
    with patch("httpx.AsyncClient.request", side_effect=httpx.TimeoutException("Connection timed out")):
        # Test timeout handling when applying a policy
        with pytest.raises(Exception) as excinfo:
            await radius.apply_policy(username="testuser", policy_id=101)
        
        assert "timed out" in str(excinfo.value)
