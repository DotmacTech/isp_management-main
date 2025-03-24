"""
Tests for the billing module template service.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from modules.billing.template_service import (
    render_invoice_template,
    render_invoice_reminder_email,
    render_monthly_billing_report,
    get_cached_template,
    cache_template,
    invalidate_template_cache
)

# Sample test data
@pytest.fixture
def invoice_context():
    """Sample invoice context for testing."""
    return {
        "invoice": {
            "id": 12345,
            "amount": Decimal("150.00"),
            "status": "unpaid",
            "created_at": datetime.now(),
            "due_date": datetime.now() + timedelta(days=30),
            "subtotal": Decimal("140.00")
        },
        "customer": {
            "id": 1001,
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "address": "123 Main St\nAnytown, CA 12345",
            "phone": "555-123-4567"
        },
        "invoice_items": [
            {
                "description": "Internet Service - Basic Plan",
                "period_start": datetime.now(),
                "period_end": datetime.now() + timedelta(days=30),
                "quantity": 1,
                "unit_price": Decimal("100.00"),
                "amount": Decimal("100.00")
            },
            {
                "description": "Equipment Rental - Router",
                "period_start": datetime.now(),
                "period_end": datetime.now() + timedelta(days=30),
                "quantity": 1,
                "unit_price": Decimal("40.00"),
                "amount": Decimal("40.00")
            }
        ],
        "discounts": [
            {
                "name": "Loyalty Discount",
                "amount": Decimal("10.00")
            }
        ],
        "taxes": [
            {
                "name": "Sales Tax",
                "rate": Decimal("10.00"),
                "amount": Decimal("20.00")
            }
        ],
        "payments": [],
        "balance_due": Decimal("150.00"),
        "payment_methods": ["Credit Card", "Bank Transfer", "PayPal"],
        "payment_account_number": "XXXX-XXXX-XXXX-1234",
        "payment_terms": "Net 30",
        "company_name": "ISP Management",
        "company_address": "456 Business Ave\nCorporate City, CA 54321",
        "company_email": "billing@example.com",
        "company_phone": "555-987-6543",
        "company_website": "www.example.com",
        "company_logo_url": "https://example.com/logo.png"
    }

@pytest.fixture
def reminder_context():
    """Sample reminder context for testing."""
    return {
        "invoice": {
            "id": 12345,
            "amount": Decimal("150.00"),
            "status": "overdue",
            "created_at": datetime.now() - timedelta(days=45),
            "due_date": datetime.now() - timedelta(days=15),
            "balance_due": Decimal("150.00")
        },
        "customer": {
            "id": 1001,
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "address": "123 Main St\nAnytown, CA 12345",
            "phone": "555-123-4567"
        },
        "days_overdue": 15,
        "payment_link": "https://billing.example.com/invoices/12345/pay"
    }

@pytest.fixture
def report_context():
    """Sample report context for testing."""
    return {
        "month_name": "January",
        "year": 2023,
        "generation_date": datetime.now(),
        "total_revenue": Decimal("5000.00"),
        "invoice_count": 50,
        "payment_count": 45,
        "outstanding_amount": Decimal("750.00"),
        "revenue_categories": [
            {"name": "Internet Services", "amount": Decimal("3500.00"), "percentage": 70},
            {"name": "Equipment Rental", "amount": Decimal("1000.00"), "percentage": 20},
            {"name": "Installation Fees", "amount": Decimal("500.00"), "percentage": 10}
        ],
        "payment_methods": [
            {"name": "Credit Card", "amount": Decimal("3000.00"), "percentage": 60, "count": 30},
            {"name": "Bank Transfer", "amount": Decimal("1500.00"), "percentage": 30, "count": 10},
            {"name": "PayPal", "amount": Decimal("500.00"), "percentage": 10, "count": 5}
        ],
        "invoice_statuses": [
            {"name": "Paid", "amount": Decimal("4250.00"), "percentage": 85, "count": 40},
            {"name": "Unpaid", "amount": Decimal("500.00"), "percentage": 10, "count": 7},
            {"name": "Overdue", "amount": Decimal("250.00"), "percentage": 5, "count": 3}
        ],
        "top_customers": [
            {
                "name": "John Doe",
                "revenue": Decimal("500.00"),
                "invoice_count": 5,
                "average_invoice": Decimal("100.00")
            },
            {
                "name": "Jane Smith",
                "revenue": Decimal("450.00"),
                "invoice_count": 3,
                "average_invoice": Decimal("150.00")
            }
        ],
        "revenue_chart_url": "https://charts.example.com/revenue/2023/1"
    }

# Mock Redis for testing
@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('isp_management.modules.billing.template_service.redis') as mock_redis:
        yield mock_redis

# Tests for template rendering
def test_render_invoice_template(invoice_context):
    """Test rendering an invoice template."""
    html = render_invoice_template(invoice_context)
    
    # Basic assertions to verify the template was rendered correctly
    assert html is not None
    assert isinstance(html, str)
    assert "INVOICE" in html
    assert f"#{invoice_context['invoice']['id']}" in html
    assert invoice_context['customer']['full_name'] in html
    assert "Internet Service - Basic Plan" in html

def test_render_invoice_reminder_email(reminder_context):
    """Test rendering an invoice reminder email."""
    html = render_invoice_reminder_email(reminder_context)
    
    # Basic assertions to verify the template was rendered correctly
    assert html is not None
    assert isinstance(html, str)
    assert "Invoice Reminder" in html
    assert f"#{reminder_context['invoice']['id']}" in html
    assert reminder_context['customer']['full_name'] in html
    assert f"{reminder_context['days_overdue']} days" in html
    assert reminder_context['payment_link'] in html

def test_render_monthly_billing_report(report_context):
    """Test rendering a monthly billing report."""
    html = render_monthly_billing_report(report_context)
    
    # Basic assertions to verify the template was rendered correctly
    assert html is not None
    assert isinstance(html, str)
    assert "Monthly Billing Report" in html
    assert report_context['month_name'] in html
    assert str(report_context['year']) in html
    assert "Internet Services" in html
    assert "Credit Card" in html
    assert "John Doe" in html

# Tests for template caching
def test_get_cached_template_hit(mock_redis):
    """Test retrieving a cached template (cache hit)."""
    # Setup mock to return a cached template
    mock_redis.get.return_value = "Cached HTML content"
    
    # Call the function
    cached_template = get_cached_template("invoice", {"id": 12345})
    
    # Verify the result
    assert cached_template == "Cached HTML content"
    mock_redis.get.assert_called_once()

def test_get_cached_template_miss(mock_redis):
    """Test retrieving a cached template (cache miss)."""
    # Setup mock to return None (cache miss)
    mock_redis.get.return_value = None
    
    # Call the function
    cached_template = get_cached_template("invoice", {"id": 12345})
    
    # Verify the result
    assert cached_template is None
    mock_redis.get.assert_called_once()

def test_cache_template(mock_redis):
    """Test caching a rendered template."""
    # Call the function
    cache_template("invoice", {"id": 12345}, "HTML content")
    
    # Verify Redis was called with the correct arguments
    mock_redis.set.assert_called_once()
    # The first argument should be the cache key
    assert "template:invoice:" in mock_redis.set.call_args[0][0]
    # The second argument should be the HTML content
    assert mock_redis.set.call_args[0][1] == "HTML content"

def test_invalidate_template_cache(mock_redis):
    """Test invalidating the template cache."""
    # Call the function
    invalidate_template_cache()
    
    # Verify Redis was called to delete keys matching the pattern
    mock_redis.delete.assert_called()

# Integration tests
def test_invoice_template_with_caching(invoice_context, mock_redis):
    """Test the full invoice template rendering with caching."""
    # Setup mock to return None (cache miss)
    mock_redis.get.return_value = None
    
    # First call should render the template and cache it
    html1 = render_invoice_template(invoice_context)
    
    # Verify the template was cached
    mock_redis.set.assert_called_once()
    
    # Setup mock to return the cached template
    mock_redis.get.return_value = html1
    
    # Second call should retrieve from cache
    html2 = render_invoice_template(invoice_context)
    
    # Verify the results are the same
    assert html1 == html2

# Error handling tests
def test_render_invoice_template_missing_context():
    """Test rendering an invoice template with missing context."""
    with pytest.raises(KeyError):
        render_invoice_template({})  # Empty context

def test_render_invoice_template_invalid_context():
    """Test rendering an invoice template with invalid context."""
    with pytest.raises(KeyError):
        render_invoice_template({"invoice": {}})  # Missing required fields
