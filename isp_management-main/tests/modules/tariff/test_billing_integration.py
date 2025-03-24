"""
Tests for the Billing integration in the Tariff Enforcement Module.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from modules.tariff.billing_integration import BillingIntegration


@pytest.fixture
def billing_integration():
    """Fixture for BillingIntegration instance."""
    with patch('modules.tariff.billing_integration.settings') as mock_settings:
        mock_settings.BILLING_API_URL = "http://billing-api.test"
        mock_settings.BILLING_API_KEY = "test-api-key"
        mock_settings.BILLING_API_TIMEOUT = 5.0
        
        integration = BillingIntegration()
        yield integration


@pytest.mark.asyncio
async def test_create_invoice_item_success(billing_integration):
    """Test creating an invoice item successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "id": "inv_item_123",
        "user_id": 1,
        "amount": 50.00,
        "description": "Test charge",
        "type": "tariff_plan"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await billing_integration.create_invoice_item(
            user_id=1,
            amount=Decimal('50.00'),
            description="Test charge",
            item_type="tariff_plan",
            metadata={"plan_id": 123}
        )
        
        # Verify the result
        assert result["id"] == "inv_item_123"
        assert result["user_id"] == 1
        assert result["amount"] == 50.00
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            "http://billing-api.test/invoice-items",
            headers=billing_integration.headers,
            json={
                "user_id": 1,
                "amount": 50.0,
                "description": "Test charge",
                "type": "tariff_plan",
                "metadata": {"plan_id": 123}
            }
        )


@pytest.mark.asyncio
async def test_create_invoice_item_http_error(billing_integration):
    """Test creating an invoice item with HTTP error."""
    # Mock the httpx AsyncClient
    mock_error = httpx.HTTPStatusError(
        "Error",
        request=MagicMock(),
        response=MagicMock()
    )
    mock_error.response.status_code = 400
    mock_error.response.text = "Invalid amount"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=mock_error
        )
        
        # Verify that HTTPException is raised
        with pytest.raises(HTTPException) as excinfo:
            await billing_integration.create_invoice_item(
                user_id=1,
                amount=Decimal('-50.00'),  # Negative amount causing error
                description="Test charge",
                item_type="tariff_plan"
            )
        
        assert excinfo.value.status_code == 400
        assert "Invalid amount" in excinfo.value.detail


@pytest.mark.asyncio
async def test_calculate_prorated_amount(billing_integration):
    """Test calculating prorated amounts correctly."""
    # Test case 1: Full month
    amount1 = await billing_integration.calculate_prorated_amount(
        plan_price=Decimal('30.00'),
        days_used=30,
        days_in_cycle=30
    )
    assert amount1 == Decimal('30.00')
    
    # Test case 2: Half month
    amount2 = await billing_integration.calculate_prorated_amount(
        plan_price=Decimal('30.00'),
        days_used=15,
        days_in_cycle=30
    )
    assert amount2 == Decimal('15.00')
    
    # Test case 3: One day
    amount3 = await billing_integration.calculate_prorated_amount(
        plan_price=Decimal('30.00'),
        days_used=1,
        days_in_cycle=30
    )
    assert amount3 == Decimal('1.00')
    
    # Test case 4: Zero days (edge case)
    amount4 = await billing_integration.calculate_prorated_amount(
        plan_price=Decimal('30.00'),
        days_used=0,
        days_in_cycle=30
    )
    assert amount4 == Decimal('0.00')
    
    # Test case 5: Zero days in cycle (edge case)
    amount5 = await billing_integration.calculate_prorated_amount(
        plan_price=Decimal('30.00'),
        days_used=15,
        days_in_cycle=0
    )
    assert amount5 == Decimal('0.00')


@pytest.mark.asyncio
async def test_handle_plan_change_success(billing_integration):
    """Test handling a plan change successfully."""
    # Mock the create_invoice_item method
    billing_integration.create_invoice_item = AsyncMock()
    billing_integration.calculate_prorated_amount = AsyncMock(side_effect=[
        Decimal('10.00'),  # Credit for old plan
        Decimal('20.00')   # Charge for new plan
    ])
    
    # Test data
    user_id = 1
    previous_plan = {
        "id": 101,
        "name": "Basic Plan",
        "price": "30.00"
    }
    new_plan = {
        "id": 102,
        "name": "Premium Plan",
        "price": "60.00"
    }
    effective_date = datetime(2023, 1, 15)
    cycle_start = datetime(2023, 1, 1)
    cycle_end = datetime(2023, 1, 31)
    
    result = await billing_integration.handle_plan_change(
        user_id=user_id,
        previous_plan=previous_plan,
        new_plan=new_plan,
        effective_date=effective_date,
        current_cycle_start=cycle_start,
        current_cycle_end=cycle_end
    )
    
    # Verify the result
    assert result["prorated_credit"] == 10.0
    assert result["prorated_charge"] == 20.0
    assert result["days_used"] == 14
    assert result["days_remaining"] == 16
    assert result["days_in_cycle"] == 30
    
    # Verify the method calls
    assert billing_integration.create_invoice_item.call_count == 2
    
    # First call should be for the credit
    credit_call_args = billing_integration.create_invoice_item.call_args_list[0][1]
    assert credit_call_args["user_id"] == 1
    assert credit_call_args["amount"] == -Decimal('10.00')  # Negative for credit
    assert "Prorated credit" in credit_call_args["description"]
    assert credit_call_args["item_type"] == "tariff_plan_credit"
    
    # Second call should be for the charge
    charge_call_args = billing_integration.create_invoice_item.call_args_list[1][1]
    assert charge_call_args["user_id"] == 1
    assert charge_call_args["amount"] == Decimal('20.00')
    assert "Prorated charge" in charge_call_args["description"]
    assert charge_call_args["item_type"] == "tariff_plan_charge"


@pytest.mark.asyncio
async def test_charge_overage_fee_success(billing_integration):
    """Test charging an overage fee successfully."""
    # Mock the create_invoice_item method
    billing_integration.create_invoice_item = AsyncMock(return_value={
        "id": "inv_item_456",
        "user_id": 1,
        "amount": 25.00,
        "description": "Data overage fee for Premium Plan (5000 MB)",
        "type": "data_overage"
    })
    
    result = await billing_integration.charge_overage_fee(
        user_id=1,
        plan_name="Premium Plan",
        overage_mb=5000,
        rate_per_mb=Decimal('0.005')
    )
    
    # Verify the result
    assert result["user_id"] == 1
    assert result["overage_mb"] == 5000
    assert result["rate_per_mb"] == 0.005
    assert result["overage_fee"] == 25.0
    assert result["invoice_item_id"] == "inv_item_456"
    
    # Verify the method call
    billing_integration.create_invoice_item.assert_called_once_with(
        user_id=1,
        amount=Decimal('25.00'),
        description="Data overage fee for Premium Plan (5000 MB)",
        item_type="data_overage",
        metadata={
            "overage_mb": 5000,
            "rate_per_mb": 0.005,
            "plan_name": "Premium Plan"
        }
    )


@pytest.mark.asyncio
async def test_get_user_billing_info_success(billing_integration):
    """Test getting user billing info successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "user_id": 1,
        "payment_method": "credit_card",
        "card_last4": "4242",
        "billing_address": "123 Test St",
        "billing_cycle": "monthly",
        "next_invoice_date": "2023-02-01"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        result = await billing_integration.get_user_billing_info(1)
        
        # Verify the result
        assert result["user_id"] == 1
        assert result["payment_method"] == "credit_card"
        assert result["card_last4"] == "4242"
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
            "http://billing-api.test/users/1/billing-info",
            headers=billing_integration.headers
        )


@pytest.mark.asyncio
async def test_get_user_invoices_success(billing_integration):
    """Test getting user invoices successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "invoices": [
            {
                "id": "inv_123",
                "user_id": 1,
                "amount": 30.00,
                "status": "paid",
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "id": "inv_456",
                "user_id": 1,
                "amount": 30.00,
                "status": "pending",
                "created_at": "2023-02-01T00:00:00Z"
            }
        ],
        "total": 2
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        result = await billing_integration.get_user_invoices(1, limit=5)
        
        # Verify the result
        assert len(result["invoices"]) == 2
        assert result["invoices"][0]["id"] == "inv_123"
        assert result["invoices"][1]["id"] == "inv_456"
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
            "http://billing-api.test/users/1/invoices",
            headers=billing_integration.headers,
            params={"limit": 5}
        )


@pytest.mark.asyncio
async def test_sync_billing_cycle_success(billing_integration):
    """Test syncing billing cycle successfully."""
    # Mock the httpx AsyncClient
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "status": "success",
        "message": "Billing cycle synchronized",
        "next_billing_date": "2023-02-01T00:00:00Z"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        cycle_start = datetime(2023, 1, 1)
        cycle_end = datetime(2023, 1, 31)
        
        result = await billing_integration.sync_billing_cycle(
            user_id=1,
            tariff_plan_id=101,
            cycle_start=cycle_start,
            cycle_end=cycle_end
        )
        
        # Verify the result
        assert result["status"] == "success"
        assert result["message"] == "Billing cycle synchronized"
        
        # Verify the API call
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            "http://billing-api.test/users/1/sync-billing-cycle",
            headers=billing_integration.headers,
            json={
                "tariff_plan_id": 101,
                "cycle_start": "2023-01-01T00:00:00",
                "cycle_end": "2023-01-31T00:00:00"
            }
        )


@pytest.mark.asyncio
async def test_calculate_next_billing_date(billing_integration):
    """Test calculating next billing date for different cycles."""
    # Test monthly cycle
    current_date = datetime(2023, 1, 15)
    next_date = await billing_integration.calculate_next_billing_date(
        current_date, "monthly"
    )
    assert next_date == datetime(2023, 2, 15)
    
    # Test quarterly cycle
    next_date = await billing_integration.calculate_next_billing_date(
        current_date, "quarterly"
    )
    assert next_date == datetime(2023, 4, 15)
    
    # Test biannual cycle
    next_date = await billing_integration.calculate_next_billing_date(
        current_date, "biannual"
    )
    assert next_date == datetime(2023, 7, 15)
    
    # Test annual cycle
    next_date = await billing_integration.calculate_next_billing_date(
        current_date, "annual"
    )
    assert next_date == datetime(2024, 1, 15)
    
    # Test unknown cycle (should default to monthly)
    next_date = await billing_integration.calculate_next_billing_date(
        current_date, "unknown"
    )
    assert next_date == datetime(2023, 2, 15)
    
    # Test month rollover (December to January)
    current_date = datetime(2023, 12, 15)
    next_date = await billing_integration.calculate_next_billing_date(
        current_date, "monthly"
    )
    assert next_date == datetime(2024, 1, 15)
