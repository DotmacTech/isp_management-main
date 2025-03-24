import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend_core.main import app
from backend_core.models import (
    User, Invoice, Payment, Discount, InvoiceDiscount, 
    CreditNote, CreditNoteApplication, TaxRate, InvoiceTax
)
from modules.billing.services import BillingService
from modules.billing.schemas import (
    DiscountCreate, CreditNoteCreate, TaxRateCreate, InvoiceCreate
)


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def db_session(monkeypatch):
    # This would be replaced with a proper test database setup
    from backend_core.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    # First, try to find an existing test user
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    if user:
        # Clean up any existing related records for this user's invoices
        for invoice in db_session.query(Invoice).filter(Invoice.user_id == user.id).all():
            db_session.query(InvoiceDiscount).filter(InvoiceDiscount.invoice_id == invoice.id).delete()
            db_session.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice.id).delete()
            db_session.query(CreditNoteApplication).filter(CreditNoteApplication.invoice_id == invoice.id).delete()
        # Now we can safely delete the invoices
        db_session.query(Invoice).filter(Invoice.user_id == user.id).delete()
        db_session.commit()
        return user
        
    # If no user exists, create a new one
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpassword",
        is_active=True,
        role="customer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for test user."""
    from backend_core.auth_service import create_access_token
    access_token = create_access_token({
        "sub": test_user.username,
        "id": test_user.id,
        "role": test_user.role
    })
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_invoice(db_session, test_user):
    # First, clean up any existing related records for this user's invoices
    for invoice in db_session.query(Invoice).filter(Invoice.user_id == test_user.id).all():
        db_session.query(InvoiceDiscount).filter(InvoiceDiscount.invoice_id == invoice.id).delete()
        db_session.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice.id).delete()
        db_session.query(CreditNoteApplication).filter(CreditNoteApplication.invoice_id == invoice.id).delete()
    # Now we can safely delete the invoices
    db_session.query(Invoice).filter(Invoice.user_id == test_user.id).delete()
    db_session.commit()
    
    invoice = Invoice(
        user_id=test_user.id,
        amount=Decimal("100.00"),
        status="pending",
        due_date=datetime.utcnow() + timedelta(days=30),
        billing_country="GB"
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def test_discount(db_session):
    current_time = datetime.utcnow()
    discount = Discount(
        name="Test Discount",
        description="Test discount description",
        discount_type="fixed_amount",
        value=Decimal("10.00"),
        is_percentage=False,
        valid_from=current_time - timedelta(days=1),  # Make sure it's valid from yesterday
        valid_to=current_time + timedelta(days=30),   # Valid for next 30 days
        is_active=True
    )
    db_session.add(discount)
    db_session.commit()
    db_session.refresh(discount)
    return discount


@pytest.fixture
def test_credit_note(db_session, test_user):
    credit_note = CreditNote(
        user_id=test_user.id,
        amount=Decimal("50.00"),
        remaining_amount=Decimal("50.00"),
        reason="Test credit note",
        status="issued"
    )
    db_session.add(credit_note)
    db_session.commit()
    db_session.refresh(credit_note)
    return credit_note


@pytest.fixture
def test_tax_rate(db_session):
    # First, find all GB tax rates
    gb_tax_rates = db_session.query(TaxRate).filter(
        TaxRate.country == "GB",
        TaxRate.is_default == True
    ).all()
    
    # Delete invoice taxes referencing these tax rates
    for tax_rate in gb_tax_rates:
        db_session.query(InvoiceTax).filter(
            InvoiceTax.tax_rate_id == tax_rate.id
        ).delete()
    
    # Now delete the tax rates
    for tax_rate in gb_tax_rates:
        db_session.delete(tax_rate)
    
    db_session.commit()
    
    # Create our test tax rate
    tax_rate = TaxRate(
        name="VAT",
        description="Value Added Tax",
        rate=Decimal("20.00"),
        country="GB",
        region=None,
        is_default=True
    )
    db_session.add(tax_rate)
    db_session.commit()
    db_session.refresh(tax_rate)
    return tax_rate


class TestDiscountManagement:
    def test_create_discount(self, db_session):
        billing_service = BillingService(db_session)
        discount_data = DiscountCreate(
            name="New Discount",
            description="New discount description",
            discount_type="percentage",
            value=Decimal("15.00"),
            is_percentage=True,
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=30)
        )
        
        discount = billing_service.create_discount(discount_data)
        assert discount.name == "New Discount"
        assert discount.value == Decimal("15.00")
        assert discount.is_percentage is True
        
    def test_get_discount(self, db_session, test_discount):
        billing_service = BillingService(db_session)
        discount = billing_service.get_discount(test_discount.id)
        assert discount.id == test_discount.id
        assert discount.name == test_discount.name
        
    def test_get_active_discounts(self, db_session, test_discount):
        billing_service = BillingService(db_session)
        discounts = billing_service.get_active_discounts()
        assert len(discounts) >= 1
        assert any(d.id == test_discount.id for d in discounts)
        
    def test_apply_discount_to_invoice(self, db_session, test_invoice, test_discount):
        billing_service = BillingService(db_session)
        result = billing_service.apply_discount_to_invoice(test_invoice.id, test_discount.id)
        
        # Check that the discount was applied
        invoice_discount = db_session.query(InvoiceDiscount).filter(
            InvoiceDiscount.invoice_id == test_invoice.id,
            InvoiceDiscount.discount_id == test_discount.id
        ).first()
        
        assert invoice_discount is not None
        assert invoice_discount.amount == Decimal("10.00")  # Fixed discount value
        
        # Check that the invoice amount was updated
        updated_invoice = billing_service.get_invoice(test_invoice.id)
        assert updated_invoice.amount == Decimal("90.00")  # 100 - 10


class TestCreditNotes:
    def test_create_credit_note(self, db_session, test_user):
        billing_service = BillingService(db_session)
        credit_note_data = CreditNoteCreate(
            user_id=test_user.id,
            amount=Decimal("75.00"),
            reason="Test reason"
        )
        
        credit_note = billing_service.create_credit_note(credit_note_data)
        assert credit_note.user_id == test_user.id
        assert credit_note.amount == Decimal("75.00")
        assert credit_note.remaining_amount == Decimal("75.00")
        assert credit_note.status == "issued"
        
    def test_get_credit_note(self, db_session, test_credit_note):
        billing_service = BillingService(db_session)
        credit_note = billing_service.get_credit_note(test_credit_note.id)
        assert credit_note.id == test_credit_note.id
        assert credit_note.amount == test_credit_note.amount
        
    def test_get_user_credit_notes(self, db_session, test_user, test_credit_note):
        billing_service = BillingService(db_session)
        credit_notes = billing_service.get_user_credit_notes(test_user.id)
        assert len(credit_notes) >= 1
        assert any(cn.id == test_credit_note.id for cn in credit_notes)
        
    def test_apply_credit_note_to_invoice(self, db_session, test_invoice, test_credit_note):
        billing_service = BillingService(db_session)
        result = billing_service.apply_credit_note_to_invoice(
            test_credit_note.id, test_invoice.id, Decimal("30.00")
        )
        
        # Check that the credit note application was created
        application = db_session.query(CreditNoteApplication).filter(
            CreditNoteApplication.credit_note_id == test_credit_note.id,
            CreditNoteApplication.invoice_id == test_invoice.id
        ).first()
        
        assert application is not None
        assert application.amount == Decimal("30.00")
        
        # Check that the credit note remaining amount was updated
        updated_credit_note = billing_service.get_credit_note(test_credit_note.id)
        assert updated_credit_note.remaining_amount == Decimal("20.00")  # 50 - 30
        
        # Check that the invoice amount reflects the credit note application
        updated_invoice = billing_service.get_invoice(test_invoice.id)
        assert updated_invoice.amount == Decimal("70.00")  # 100 - 30


class TestTaxCalculation:
    def test_create_tax_rate(self, db_session):
        billing_service = BillingService(db_session)
        tax_rate_data = TaxRateCreate(
            name="GST",
            description="Goods and Services Tax",
            rate=Decimal("10.00"),
            country="AU",
            region=None
        )
        
        tax_rate = billing_service.create_tax_rate(tax_rate_data)
        assert tax_rate.name == "GST"
        assert tax_rate.rate == Decimal("10.00")
        assert tax_rate.country == "AU"
        
    def test_get_tax_rate(self, db_session, test_tax_rate):
        billing_service = BillingService(db_session)
        tax_rate = billing_service.get_tax_rate(test_tax_rate.id)
        assert tax_rate.id == test_tax_rate.id
        assert tax_rate.name == test_tax_rate.name
        
    def test_calculate_invoice_taxes(self, db_session, test_invoice, test_tax_rate):
        billing_service = BillingService(db_session)
        
        # Calculate taxes for the invoice
        tax_details = billing_service.calculate_invoice_taxes(test_invoice.id)
        
        # Verify tax calculations
        assert tax_details is not None
        assert len(tax_details) == 1
        
        tax_detail = tax_details[0]
        assert tax_detail.tax_rate_id == test_tax_rate.id
        assert tax_detail.tax_amount == Decimal("20.00")  # 20% of 100.00
        

class TestInvoiceDetails:
    def test_get_invoice_details(self, db_session, test_invoice, test_discount, test_tax_rate, auth_headers):
        # Apply discount to invoice
        billing_service = BillingService(db_session)
        billing_service.apply_discount_to_invoice(test_invoice.id, test_discount.id)

        # Calculate taxes
        billing_service.calculate_invoice_taxes(test_invoice.id)

        # Test the API endpoint
        client = TestClient(app)
        response = client.get(f"/api/billing/invoices/{test_invoice.id}/details", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_invoice.id
        assert len(data["discounts"]) > 0
        assert len(data["taxes"]) > 0
