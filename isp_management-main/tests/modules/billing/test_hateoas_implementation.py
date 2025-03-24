"""
Tests for HATEOAS implementation in the Billing Module.

This module contains tests to verify that the billing API endpoints
correctly implement HATEOAS principles, including proper link generation
and resource relationships.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from modules.billing.services.billing_service import BillingService
from modules.billing.models.invoice import Invoice
from modules.billing.models.discount import Discount
from modules.billing.models.tax import Tax
from modules.billing.models.payment import Payment
from backend_core.auth_service import get_current_user, get_current_active_user, get_current_user_role


@pytest.fixture
def mock_billing_service():
    """Create a mock billing service for testing."""
    with patch("modules.billing.api.endpoints.BillingService") as mock_service:
        # Mock invoice data
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.user_id = 1
        mock_invoice.amount = 100.0
        mock_invoice.status = "pending"
        mock_invoice.due_date = "2025-04-01"
        mock_invoice.created_at = "2025-03-01"
        
        # Mock invoice list
        mock_invoices = [
            mock_invoice,
            MagicMock(id=2, user_id=1, amount=150.0, status="paid", due_date="2025-03-01", created_at="2025-02-01")
        ]
        
        # Mock discounts
        mock_discount = MagicMock(id=1, invoice_id=1, amount=10.0, description="Early payment discount")
        
        # Mock taxes
        mock_tax = MagicMock(id=1, invoice_id=1, amount=20.0, description="VAT")
        
        # Mock payments
        mock_payment = MagicMock(id=1, invoice_id=1, amount=50.0, status="completed", payment_date="2025-03-15")
        
        # Setup mock service methods
        mock_service_instance = mock_service.return_value
        mock_service_instance.get_invoice.return_value = mock_invoice
        mock_service_instance.get_user_invoices.return_value = mock_invoices
        mock_service_instance.get_invoice_discounts.return_value = [mock_discount]
        mock_service_instance.get_invoice_taxes.return_value = [mock_tax]
        mock_service_instance.get_invoice_payments.return_value = [mock_payment]
        
        yield mock_service_instance


@pytest.fixture
def mock_auth_dependencies():
    """Mock authentication dependencies for testing."""
    with patch("backend_core.auth_service.get_current_user") as mock_get_user:
        # Create a mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.role = "admin"
        
        # Setup the mock to return our mock user
        mock_get_user.return_value = mock_user
        
        yield mock_get_user


class TestBillingHATEOAS:
    """Test cases for HATEOAS implementation in the billing module."""
    
    def test_get_invoice_hateoas_links(self, client: TestClient, mock_billing_service, mock_auth_dependencies):
        """Test that get_invoice endpoint includes proper HATEOAS links."""
        response = client.get("/api/v1/billing/invoices/1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that _links field exists
        assert "_links" in data
        links = data["_links"]
        
        # Check for required link relations
        assert "self" in links
        assert "payments" in links
        assert "pdf" in links
        assert "html" in links
        
        # Verify link structure
        assert links["self"]["href"].endswith("/billing/invoices/1")
        assert links["payments"]["href"].endswith("/billing/invoices/1/payments")
        assert links["pdf"]["href"].endswith("/billing/invoices/1/pdf")
        assert links["html"]["href"].endswith("/billing/invoices/1/html")
    
    def test_get_user_invoices_hateoas_links(self, client: TestClient, mock_billing_service, mock_auth_dependencies):
        """Test that get_user_invoices endpoint includes proper HATEOAS links."""
        response = client.get("/api/v1/billing/users/1/invoices")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that _links field exists at collection level
        assert "_links" in data
        collection_links = data["_links"]
        
        # Check for collection link relations
        assert "self" in collection_links
        assert collection_links["self"]["href"].endswith("/billing/users/1/invoices")
        
        # Check for pagination links if applicable
        if "next" in collection_links:
            assert collection_links["next"]["href"].endswith("page=2")
        
        # Check that each item has its own links
        assert "items" in data
        for item in data["items"]:
            assert "_links" in item
            item_links = item["_links"]
            assert "self" in item_links
            assert item_links["self"]["href"].endswith(f"/billing/invoices/{item['id']}")
    
    def test_get_invoice_details_hateoas_links(self, client: TestClient, mock_billing_service, mock_auth_dependencies):
        """Test that get_invoice_details endpoint includes proper HATEOAS links."""
        response = client.get("/api/v1/billing/invoices/1/details")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that _links field exists
        assert "_links" in data
        links = data["_links"]
        
        # Check for required link relations
        assert "self" in links
        assert "invoice" in links
        assert "payments" in links
        assert "discounts" in links
        assert "taxes" in links
        
        # Verify link structure
        assert links["self"]["href"].endswith("/billing/invoices/1/details")
        assert links["invoice"]["href"].endswith("/billing/invoices/1")
        assert links["payments"]["href"].endswith("/billing/invoices/1/payments")
        assert links["discounts"]["href"].endswith("/billing/invoices/1/discounts")
        assert links["taxes"]["href"].endswith("/billing/invoices/1/taxes")
        
        # Check embedded resources if present
        if "discounts" in data:
            for discount in data["discounts"]:
                assert "_links" in discount
                assert "self" in discount["_links"]
        
        if "taxes" in data:
            for tax in data["taxes"]:
                assert "_links" in tax
                assert "self" in tax["_links"]
    
    def test_create_invoice_hateoas_links(self, client: TestClient, mock_billing_service, mock_auth_dependencies):
        """Test that create_invoice endpoint includes proper HATEOAS links in response."""
        # Mock the create_invoice method to return an invoice with ID 3
        mock_billing_service.create_invoice.return_value = MagicMock(
            id=3, user_id=1, amount=200.0, status="pending", due_date="2025-05-01", created_at="2025-04-01"
        )
        
        # Create a new invoice
        invoice_data = {
            "user_id": 1,
            "amount": 200.0,
            "due_date": "2025-05-01",
            "items": [{"description": "Monthly subscription", "amount": 200.0}]
        }
        
        response = client.post("/api/v1/billing/invoices", json=invoice_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Check that _links field exists
        assert "_links" in data
        links = data["_links"]
        
        # Check for required link relations
        assert "self" in links
        assert "payments" in links
        assert "user" in links
        
        # Verify link structure
        assert links["self"]["href"].endswith("/billing/invoices/3")
        assert links["payments"]["href"].endswith("/billing/invoices/3/payments")
        assert links["user"]["href"].endswith("/users/1")
    
    def test_invoice_reminder_hateoas_links(self, client: TestClient, mock_billing_service, mock_auth_dependencies):
        """Test that invoice reminder endpoint includes proper HATEOAS links."""
        response = client.post("/api/v1/billing/invoices/1/reminder")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that _links field exists
        assert "_links" in data
        links = data["_links"]
        
        # Check for required link relations
        assert "self" in links
        assert "invoice" in links
        
        # Verify link structure
        assert links["self"]["href"].endswith("/billing/invoices/1/reminder")
        assert links["invoice"]["href"].endswith("/billing/invoices/1")


@pytest.mark.parametrize(
    "endpoint,expected_links",
    [
        ("/api/v1/billing/invoices/1", ["self", "payments", "pdf", "html"]),
        ("/api/v1/billing/invoices/1/details", ["self", "invoice", "payments", "discounts", "taxes"]),
        ("/api/v1/billing/users/1/invoices", ["self"]),
        ("/api/v1/billing/invoices/1/payments", ["self", "invoice"]),
        ("/api/v1/billing/invoices/1/discounts", ["self", "invoice"]),
        ("/api/v1/billing/invoices/1/taxes", ["self", "invoice"]),
    ]
)
def test_endpoint_hateoas_compliance(client: TestClient, mock_billing_service, mock_auth_dependencies, endpoint, expected_links):
    """Parametrized test to verify HATEOAS compliance across multiple endpoints."""
    response = client.get(endpoint)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check if this is a collection response
    if "items" in data and isinstance(data["items"], list):
        # Collection response
        assert "_links" in data
        for link in expected_links:
            assert link in data["_links"]
        
        # Check that each item has links
        for item in data["items"]:
            assert "_links" in item
            assert "self" in item["_links"]
    else:
        # Single resource response
        assert "_links" in data
        for link in expected_links:
            assert link in data["_links"]


def test_api_versioning_with_hateoas(client: TestClient, mock_billing_service, mock_auth_dependencies):
    """Test that API versioning works correctly with HATEOAS links."""
    # Test with explicit v1 version
    v1_response = client.get(
        "/api/v1/billing/invoices/1",
        headers={"Accept": "application/json"}
    )
    
    assert v1_response.status_code == 200
    assert "X-API-Version" in v1_response.headers
    assert v1_response.headers["X-API-Version"] == "1.0"
    
    # Test with v2 version (should still work as we've mounted the same routers)
    v2_response = client.get(
        "/api/v2/billing/invoices/1",
        headers={"Accept": "application/json"}
    )
    
    assert v2_response.status_code == 200
    assert "X-API-Version" in v2_response.headers
    assert v2_response.headers["X-API-Version"] == "2.0"
    
    # Verify HATEOAS links use the correct version in the URL
    v1_data = v1_response.json()
    v2_data = v2_response.json()
    
    assert "/api/v1/" in v1_data["_links"]["self"]["href"]
    assert "/api/v2/" in v2_data["_links"]["self"]["href"]
