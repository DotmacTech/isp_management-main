"""
Integration tests for the billing module caching implementation.
These tests verify that the caching system works correctly with the billing service.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from backend_core.cache import (
    redis_client,
    get_cached_tax_rate, cache_tax_rate, invalidate_tax_rate_cache,
    get_cached_active_discounts, cache_active_discounts, invalidate_active_discounts_cache,
    get_cached_invoice_details, cache_invoice_details, invalidate_invoice_cache,
    get_cached_user_credit_notes, cache_user_credit_notes, invalidate_user_credit_notes_cache
)
from modules.billing.services import BillingService
from backend_core.models import (
    Invoice, Payment, Discount, InvoiceDiscount, 
    CreditNote, CreditNoteApplication, TaxRate, InvoiceTax
)


@pytest.fixture(scope="function")
def clear_redis():
    """Clear Redis before and after each test."""
    redis_client.flushdb()
    yield
    redis_client.flushdb()


@pytest.fixture
def billing_service(db_session):
    """Create a billing service for testing."""
    return BillingService(db_session)


@pytest.fixture
def sample_tax_rate(db_session):
    """Create a sample tax rate for testing."""
    tax_rate = TaxRate(
        name="Test VAT",
        description="Test Value Added Tax",
        rate=Decimal("20.00"),
        country="GB",
        region="",
        is_default=True
    )
    db_session.add(tax_rate)
    db_session.commit()
    return tax_rate


@pytest.fixture
def sample_discount(db_session):
    """Create a sample discount for testing."""
    now = datetime.utcnow()
    discount = Discount(
        name="Test Discount",
        description="Test discount for caching",
        discount_type="percentage",
        value=Decimal("10.00"),
        is_percentage=True,
        is_active=True,
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=30)
    )
    db_session.add(discount)
    db_session.commit()
    return discount


@pytest.fixture
def sample_invoice(db_session, sample_user):
    """Create a sample invoice for testing."""
    invoice = Invoice(
        user_id=sample_user.id,
        amount=Decimal("100.00"),
        status="unpaid",
        due_date=datetime.utcnow() + timedelta(days=30),
        billing_country="GB"
    )
    db_session.add(invoice)
    db_session.commit()
    return invoice


@pytest.fixture
def sample_credit_note(db_session, sample_user, sample_invoice):
    """Create a sample credit note for testing."""
    credit_note = CreditNote(
        user_id=sample_user.id,
        amount=Decimal("50.00"),
        remaining_amount=Decimal("50.00"),
        reason="Test credit note",
        reference_invoice_id=sample_invoice.id,
        status="issued"
    )
    db_session.add(credit_note)
    db_session.commit()
    return credit_note


class TestTaxRateCacheIntegration:
    """Test tax rate caching integration with billing service."""

    def test_get_applicable_tax_rate_uses_cache(self, billing_service, sample_tax_rate, clear_redis):
        """Test that get_applicable_tax_rate uses and updates the cache."""
        country = sample_tax_rate.country
        region = sample_tax_rate.region or ""
        
        # First call should miss cache and query database
        with patch('isp_management.backend_core.cache.get_cached_tax_rate', wraps=get_cached_tax_rate) as mock_get_cache:
            with patch('isp_management.backend_core.cache.cache_tax_rate', wraps=cache_tax_rate) as mock_set_cache:
                # First call - should be a cache miss
                result1 = billing_service.get_applicable_tax_rate(country, region)
                
                # Verify cache was checked
                mock_get_cache.assert_called_once_with(country, region)
                
                # Verify result was cached
                mock_set_cache.assert_called_once()
                
                # Second call - should be a cache hit
                result2 = billing_service.get_applicable_tax_rate(country, region)
                
                # Verify results are the same
                assert result1.id == result2.id
                assert result1.rate == result2.rate
    
    def test_tax_rate_cache_invalidation(self, billing_service, sample_tax_rate, db_session, clear_redis):
        """Test that tax rate cache is invalidated when tax rates are updated."""
        country = sample_tax_rate.country
        region = sample_tax_rate.region or ""
        
        # First call to cache the tax rate
        billing_service.get_applicable_tax_rate(country, region)
        
        # Verify tax rate is in cache
        cached_data = get_cached_tax_rate(country, region)
        assert cached_data is not None
        assert cached_data["id"] == sample_tax_rate.id
        
        # Update tax rate
        sample_tax_rate.rate = Decimal("25.00")
        db_session.commit()
        
        # Invalidate cache
        invalidate_tax_rate_cache(country, region)
        
        # Verify cache was invalidated
        cached_data = get_cached_tax_rate(country, region)
        assert cached_data is None
        
        # Next call should get updated rate
        updated_rate = billing_service.get_applicable_tax_rate(country, region)
        assert updated_rate.rate == Decimal("25.00")


class TestActiveDiscountsCacheIntegration:
    """Test active discounts caching integration with billing service."""

    def test_get_active_discounts_uses_cache(self, billing_service, sample_discount, clear_redis):
        """Test that get_active_discounts uses and updates the cache."""
        # First call should miss cache and query database
        with patch('isp_management.backend_core.cache.get_cached_active_discounts', wraps=get_cached_active_discounts) as mock_get_cache:
            with patch('isp_management.backend_core.cache.cache_active_discounts', wraps=cache_active_discounts) as mock_set_cache:
                # First call - should be a cache miss
                result1 = billing_service.get_active_discounts()
                
                # Verify cache was checked
                mock_get_cache.assert_called_once()
                
                # Verify result was cached
                mock_set_cache.assert_called_once()
                
                # Second call - should be a cache hit
                result2 = billing_service.get_active_discounts()
                
                # Verify results are the same
                assert len(result1) == len(result2)
                assert result1[0].id == result2[0].id
    
    def test_active_discounts_cache_invalidation(self, billing_service, sample_discount, db_session, clear_redis):
        """Test that active discounts cache is invalidated when discounts are updated."""
        # First call to cache the active discounts
        discounts = billing_service.get_active_discounts()
        assert len(discounts) == 1
        
        # Verify discounts are in cache
        cached_data = get_cached_active_discounts()
        assert cached_data is not None
        assert len(cached_data) == 1
        
        # Create a new discount
        new_discount = Discount(
            name="New Discount",
            description="New discount for testing",
            discount_type="fixed",
            value=Decimal("5.00"),
            is_percentage=False,
            is_active=True,
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(new_discount)
        db_session.commit()
        
        # Invalidate cache
        invalidate_active_discounts_cache()
        
        # Verify cache was invalidated
        cached_data = get_cached_active_discounts()
        assert cached_data is None
        
        # Next call should get updated discounts
        updated_discounts = billing_service.get_active_discounts()
        assert len(updated_discounts) == 2


class TestInvoiceDetailsCacheIntegration:
    """Test invoice details caching integration with billing service."""

    def test_get_invoice_details_uses_cache(self, billing_service, sample_invoice, clear_redis):
        """Test that get_invoice_details uses and updates the cache."""
        invoice_id = sample_invoice.id
        
        # First call should miss cache and query database
        with patch('isp_management.backend_core.cache.get_cached_invoice_details', wraps=get_cached_invoice_details) as mock_get_cache:
            with patch('isp_management.backend_core.cache.cache_invoice_details', wraps=cache_invoice_details) as mock_set_cache:
                # First call - should be a cache miss
                result1 = billing_service.get_invoice_details(invoice_id)
                
                # Verify cache was checked
                mock_get_cache.assert_called_once_with(invoice_id)
                
                # Verify result was cached
                mock_set_cache.assert_called_once()
                
                # Second call - should be a cache hit
                result2 = billing_service.get_invoice_details(invoice_id)
                
                # Verify results are the same
                assert result1["id"] == result2["id"]
                assert result1["status"] == result2["status"]
    
    def test_invoice_cache_invalidation_on_payment(self, billing_service, sample_invoice, db_session, clear_redis):
        """Test that invoice cache is invalidated when a payment is processed."""
        invoice_id = sample_invoice.id
        
        # First call to cache the invoice details
        billing_service.get_invoice_details(invoice_id)
        
        # Verify invoice details are in cache
        cached_data = get_cached_invoice_details(invoice_id)
        assert cached_data is not None
        assert cached_data["id"] == invoice_id
        
        # Process a payment
        payment_data = MagicMock()
        payment_data.invoice_id = invoice_id
        payment_data.amount = Decimal("50.00")
        payment_data.payment_method = "credit_card"
        payment_data.transaction_id = "test_transaction"
        
        # Mock the get_invoice method to return our sample invoice
        with patch.object(billing_service, 'get_invoice', return_value=sample_invoice):
            # Process the payment
            billing_service.process_payment(payment_data)
        
        # Verify cache was invalidated
        cached_data = get_cached_invoice_details(invoice_id)
        assert cached_data is None


class TestUserCreditNotesCacheIntegration:
    """Test user credit notes caching integration with billing service."""

    def test_get_user_credit_notes_uses_cache(self, billing_service, sample_credit_note, clear_redis):
        """Test that get_user_credit_notes uses and updates the cache."""
        user_id = sample_credit_note.user_id
        
        # First call should miss cache and query database
        with patch('isp_management.backend_core.cache.get_cached_user_credit_notes', wraps=get_cached_user_credit_notes) as mock_get_cache:
            with patch('isp_management.backend_core.cache.cache_user_credit_notes', wraps=cache_user_credit_notes) as mock_set_cache:
                # First call - should be a cache miss
                result1 = billing_service.get_user_credit_notes(user_id)
                
                # Verify cache was checked
                mock_get_cache.assert_called_once_with(user_id)
                
                # Verify result was cached
                mock_set_cache.assert_called_once()
                
                # Second call - should be a cache hit
                result2 = billing_service.get_user_credit_notes(user_id)
                
                # Verify results are the same
                assert len(result1) == len(result2)
                assert result1[0].id == result2[0].id
    
    def test_user_credit_notes_cache_invalidation(self, billing_service, sample_credit_note, sample_invoice, db_session, clear_redis):
        """Test that user credit notes cache is invalidated when a credit note is applied."""
        user_id = sample_credit_note.user_id
        
        # First call to cache the user credit notes
        credit_notes = billing_service.get_user_credit_notes(user_id)
        assert len(credit_notes) == 1
        
        # Verify credit notes are in cache
        cached_data = get_cached_user_credit_notes(user_id)
        assert cached_data is not None
        assert len(cached_data) == 1
        
        # Apply credit note to invoice
        with patch.object(billing_service, 'get_invoice', return_value=sample_invoice):
            with patch.object(billing_service, 'get_credit_note', return_value=sample_credit_note):
                billing_service.apply_credit_note_to_invoice(
                    credit_note_id=sample_credit_note.id,
                    invoice_id=sample_invoice.id,
                    amount=Decimal("25.00")
                )
        
        # Verify cache was invalidated
        cached_data = get_cached_user_credit_notes(user_id)
        assert cached_data is None
        
        # Next call should get updated credit notes
        updated_credit_notes = billing_service.get_user_credit_notes(user_id)
        assert len(updated_credit_notes) == 1
        assert updated_credit_notes[0].remaining_amount == Decimal("25.00")


@pytest.mark.parametrize("redis_available", [True, False])
def test_cache_fallback_behavior(redis_available, billing_service, sample_invoice, clear_redis):
    """Test that the system falls back to database queries when Redis is unavailable."""
    invoice_id = sample_invoice.id
    
    # Mock Redis availability
    if not redis_available:
        with patch('isp_management.backend_core.cache.redis_client.get', side_effect=Exception("Redis connection error")):
            with patch('isp_management.backend_core.cache.redis_client.setex', side_effect=Exception("Redis connection error")):
                # Should still work despite Redis errors
                result = billing_service.get_invoice_details(invoice_id)
                assert result is not None
                assert result["id"] == invoice_id
    else:
        # Normal operation with Redis available
        result = billing_service.get_invoice_details(invoice_id)
        assert result is not None
        assert result["id"] == invoice_id


def test_cache_serialization_deserialization(billing_service, sample_invoice, clear_redis):
    """Test that complex types like Decimal are properly serialized and deserialized."""
    invoice_id = sample_invoice.id
    
    # Add a discount to the invoice
    discount = Discount(
        name="Test Discount",
        description="Test discount for serialization",
        discount_type="percentage",
        value=Decimal("15.00"),
        is_percentage=True,
        is_active=True,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_to=datetime.utcnow() + timedelta(days=30)
    )
    
    # Create invoice details with Decimal values
    invoice_details = {
        "id": invoice_id,
        "user_id": sample_invoice.user_id,
        "status": sample_invoice.status,
        "subtotal": Decimal("100.00"),
        "total_discount": Decimal("15.00"),
        "total_tax": Decimal("17.00"),
        "total": Decimal("102.00"),
        "discounts": [
            {
                "id": 1,
                "name": "Test Discount",
                "amount": Decimal("15.00")
            }
        ],
        "taxes": [
            {
                "id": 1,
                "name": "VAT",
                "rate": Decimal("20.00"),
                "amount": Decimal("17.00")
            }
        ]
    }
    
    # Cache the invoice details
    cache_invoice_details(invoice_id, invoice_details)
    
    # Retrieve from cache
    cached_details = get_cached_invoice_details(invoice_id)
    
    # Verify decimal values are properly handled
    assert cached_details is not None
    assert cached_details["subtotal"] == "100.00"
    assert cached_details["total_discount"] == "15.00"
    assert cached_details["discounts"][0]["amount"] == "15.00"
    assert cached_details["taxes"][0]["rate"] == "20.00"
