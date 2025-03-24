"""
Tests for the caching implementation in the billing module.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from backend_core.cache import (
    get_cached_tax_rate, cache_tax_rate,
    get_cached_active_discounts, cache_active_discounts,
    get_cached_invoice_details, cache_invoice_details, invalidate_invoice_cache,
    get_cached_user_credit_notes, cache_user_credit_notes, invalidate_user_credit_notes_cache
)
from modules.billing.services import BillingService


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('isp_management.backend_core.cache.redis_client') as mock_client:
        mock_client.get.return_value = None  # Default to cache miss
        yield mock_client


@pytest.fixture
def billing_service(db_session):
    """Create a billing service instance for testing."""
    return BillingService(db_session)


class TestTaxRateCache:
    """Test tax rate caching functionality."""

    def test_cache_tax_rate(self, mock_redis):
        """Test caching a tax rate."""
        country = "US"
        region = "CA"
        tax_rate = {"id": 1, "name": "California Sales Tax", "rate": 7.25}
        
        cache_tax_rate(country, region, tax_rate)
        
        # Verify Redis was called with correct parameters
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == f"tax_rate:{country}:{region}"
        assert "California Sales Tax" in args[2]  # Check serialized data

    def test_get_cached_tax_rate_hit(self, mock_redis):
        """Test retrieving a cached tax rate (cache hit)."""
        country = "US"
        region = "CA"
        tax_rate = {"id": 1, "name": "California Sales Tax", "rate": 7.25}
        
        # Set up mock to return cached data
        mock_redis.get.return_value = '{"id": 1, "name": "California Sales Tax", "rate": 7.25}'
        
        result = get_cached_tax_rate(country, region)
        
        # Verify Redis was called with correct parameters
        mock_redis.get.assert_called_once_with(f"tax_rate:{country}:{region}")
        assert result == tax_rate

    def test_get_cached_tax_rate_miss(self, mock_redis):
        """Test retrieving a cached tax rate (cache miss)."""
        country = "US"
        region = "CA"
        
        # Set up mock to return no data (cache miss)
        mock_redis.get.return_value = None
        
        result = get_cached_tax_rate(country, region)
        
        # Verify Redis was called with correct parameters
        mock_redis.get.assert_called_once_with(f"tax_rate:{country}:{region}")
        assert result is None


class TestActiveDiscountsCache:
    """Test active discounts caching functionality."""

    def test_cache_active_discounts(self, mock_redis):
        """Test caching active discounts."""
        discounts = [
            {"id": 1, "name": "Summer Sale", "value": 10, "is_percentage": True},
            {"id": 2, "name": "New Customer", "value": 5, "is_percentage": False}
        ]
        
        cache_active_discounts(discounts)
        
        # Verify Redis was called with correct parameters
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "active_discounts"
        assert "Summer Sale" in args[2]  # Check serialized data

    def test_get_cached_active_discounts_hit(self, mock_redis):
        """Test retrieving cached active discounts (cache hit)."""
        discounts = [
            {"id": 1, "name": "Summer Sale", "value": 10, "is_percentage": True},
            {"id": 2, "name": "New Customer", "value": 5, "is_percentage": False}
        ]
        
        # Set up mock to return cached data
        mock_redis.get.return_value = '[{"id": 1, "name": "Summer Sale", "value": 10, "is_percentage": true}, {"id": 2, "name": "New Customer", "value": 5, "is_percentage": false}]'
        
        result = get_cached_active_discounts()
        
        # Verify Redis was called with correct parameters
        mock_redis.get.assert_called_once_with("active_discounts")
        assert result == discounts


class TestInvoiceDetailsCache:
    """Test invoice details caching functionality."""

    def test_cache_invoice_details(self, mock_redis):
        """Test caching invoice details."""
        invoice_id = 123
        details = {
            "id": invoice_id,
            "user_id": 456,
            "amount": 100.00,
            "status": "unpaid",
            "discounts": [{"id": 1, "name": "Summer Sale", "amount": 10.00}],
            "taxes": [{"id": 1, "name": "VAT", "amount": 20.00}]
        }
        
        cache_invoice_details(invoice_id, details)
        
        # Verify Redis was called with correct parameters
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == f"invoice:{invoice_id}"
        assert "Summer Sale" in args[2]  # Check serialized data

    def test_invalidate_invoice_cache(self, mock_redis):
        """Test invalidating invoice cache."""
        invoice_id = 123
        
        invalidate_invoice_cache(invoice_id)
        
        # Verify Redis was called with correct parameters
        mock_redis.delete.assert_called_once_with(f"invoice:{invoice_id}")


class TestUserCreditNotesCache:
    """Test user credit notes caching functionality."""

    def test_cache_user_credit_notes(self, mock_redis):
        """Test caching user credit notes."""
        user_id = 456
        credit_notes = [
            {"id": 1, "amount": 50.00, "remaining_amount": 25.00, "status": "issued"},
            {"id": 2, "amount": 30.00, "remaining_amount": 30.00, "status": "issued"}
        ]
        
        cache_user_credit_notes(user_id, credit_notes)
        
        # Verify Redis was called with correct parameters
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == f"user_credit_notes:{user_id}"
        assert "remaining_amount" in args[2]  # Check serialized data

    def test_invalidate_user_credit_notes_cache(self, mock_redis):
        """Test invalidating user credit notes cache."""
        user_id = 456
        
        invalidate_user_credit_notes_cache(user_id)
        
        # Verify Redis was called with correct parameters
        mock_redis.delete.assert_called_once_with(f"user_credit_notes:{user_id}")


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for caching with the billing service."""
    
    @patch('isp_management.backend_core.cache.get_cached_tax_rate')
    @patch('isp_management.backend_core.cache.cache_tax_rate')
    def test_get_applicable_tax_rate_uses_cache(self, mock_cache_tax_rate, mock_get_cached_tax_rate, billing_service, db_session):
        """Test that get_applicable_tax_rate uses and updates the cache."""
        country = "US"
        region = "NY"
        
        # Set up mock to return no cached data first time
        mock_get_cached_tax_rate.return_value = None
        
        # Call the method - should hit database
        billing_service.get_applicable_tax_rate(country, region)
        
        # Verify cache was checked
        mock_get_cached_tax_rate.assert_called_once_with(country, region)
        
        # Verify result was cached
        assert mock_cache_tax_rate.called
    
    @patch('isp_management.backend_core.cache.get_cached_active_discounts')
    @patch('isp_management.backend_core.cache.cache_active_discounts')
    def test_get_active_discounts_uses_cache(self, mock_cache_active_discounts, mock_get_cached_active_discounts, billing_service):
        """Test that get_active_discounts uses and updates the cache."""
        # Set up mock to return no cached data first time
        mock_get_cached_active_discounts.return_value = None
        
        # Call the method - should hit database
        billing_service.get_active_discounts()
        
        # Verify cache was checked
        mock_get_cached_active_discounts.assert_called_once()
        
        # Verify result was cached
        assert mock_cache_active_discounts.called
    
    @patch('isp_management.backend_core.cache.invalidate_invoice_cache')
    def test_process_payment_invalidates_cache(self, mock_invalidate_invoice_cache, billing_service, db_session):
        """Test that process_payment invalidates the invoice cache."""
        # This test would need more setup with actual database records
        # For now, we'll just verify the mock is called in the right place
        
        # Create a mock payment_data
        payment_data = MagicMock()
        payment_data.invoice_id = 123
        
        # Mock the get_invoice method to avoid database lookup
        with patch.object(billing_service, 'get_invoice') as mock_get_invoice:
            mock_invoice = MagicMock()
            mock_invoice.status = "unpaid"
            mock_invoice.amount = Decimal("100.00")
            mock_invoice.payments = []
            mock_get_invoice.return_value = mock_invoice
            
            # Also mock db operations
            with patch.object(billing_service.db, 'add'), \
                 patch.object(billing_service.db, 'commit'), \
                 patch.object(billing_service.db, 'refresh'):
                
                # Call the method
                billing_service.process_payment(payment_data)
                
                # Verify cache was invalidated
                mock_invalidate_invoice_cache.assert_called_once_with(payment_data.invoice_id)
