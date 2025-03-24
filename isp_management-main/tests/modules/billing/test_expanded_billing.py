"""
Integration tests for the expanded billing module features.

This test suite covers the new features added to the billing module:
- Subscription management
- Tax management
- Discount management
- Financial reporting
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from isp_management.main import app
from backend_core.database import get_db
from backend_core.models import User
from modules.billing.models import (
    Invoice, Payment, Discount, TaxRate, TaxExemption,
    Subscription, SubscriptionPlan, RecurringBillingProfile, UsageRecord
)
from modules.billing.services.subscription_service import SubscriptionService
from modules.billing.services.tax_service import TaxService
from modules.billing.services.discount_service import DiscountService
from modules.billing.services.reporting_service import ReportingService


client = TestClient(app)


@pytest.fixture
def db_session(monkeypatch):
    """Return a SQLAlchemy session for testing."""
    # This would be replaced with a proper test database setup
    # For now, we'll just use the development database
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def test_admin_user(db_session):
    """Create a test admin user for testing."""
    user = User(
        email="admin@example.com",
        username="adminuser",
        full_name="Admin User",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def test_subscription_plan(db_session):
    """Create a test subscription plan for testing."""
    plan = SubscriptionPlan(
        name="Basic Plan",
        description="Basic internet service",
        price=Decimal("29.99"),
        billing_cycle="monthly",
        features=json.dumps(["10 Mbps", "100 GB data"]),
        is_active=True
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    yield plan
    db_session.delete(plan)
    db_session.commit()


@pytest.fixture
def test_tax_rate(db_session):
    """Create a test tax rate for testing."""
    tax_rate = TaxRate(
        name="Test VAT",
        description="Value Added Tax",
        rate=Decimal("0.20"),
        country="GB",
        is_default=True
    )
    db_session.add(tax_rate)
    db_session.commit()
    db_session.refresh(tax_rate)
    yield tax_rate
    db_session.delete(tax_rate)
    db_session.commit()


@pytest.fixture
def test_discount(db_session):
    """Create a test discount for testing."""
    discount = Discount(
        name="Test Discount",
        description="Test discount for new customers",
        discount_type="promotional",
        amount=Decimal("10.00"),
        is_percentage=True,
        code="NEWCUSTOMER",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=30),
        max_uses=100,
        status="active"
    )
    db_session.add(discount)
    db_session.commit()
    db_session.refresh(discount)
    yield discount
    db_session.delete(discount)
    db_session.commit()


class TestSubscriptionManagement:
    """Test cases for subscription management."""

    def test_create_subscription(self, db_session, test_user, test_subscription_plan):
        """Test creating a new subscription."""
        subscription_service = SubscriptionService(db_session)
        
        subscription = subscription_service.create_subscription({
            "user_id": test_user.id,
            "plan_id": test_subscription_plan.id,
            "start_date": datetime.now(),
            "billing_cycle": "monthly",
            "auto_renew": True
        })
        
        assert subscription is not None
        assert subscription.user_id == test_user.id
        assert subscription.plan_id == test_subscription_plan.id
        assert subscription.status == "active"
        
        # Clean up
        db_session.delete(subscription)
        db_session.commit()

    def test_cancel_subscription(self, db_session, test_user, test_subscription_plan):
        """Test cancelling a subscription."""
        subscription_service = SubscriptionService(db_session)
        
        # Create a subscription first
        subscription = subscription_service.create_subscription({
            "user_id": test_user.id,
            "plan_id": test_subscription_plan.id,
            "start_date": datetime.now(),
            "billing_cycle": "monthly",
            "auto_renew": True
        })
        
        # Cancel the subscription
        cancelled_subscription = subscription_service.cancel_subscription(
            subscription.id,
            "Testing cancellation"
        )
        
        assert cancelled_subscription is not None
        assert cancelled_subscription.status == "cancelled"
        assert cancelled_subscription.cancellation_reason == "Testing cancellation"
        
        # Clean up
        db_session.delete(subscription)
        db_session.commit()

    def test_pause_and_resume_subscription(self, db_session, test_user, test_subscription_plan):
        """Test pausing and resuming a subscription."""
        subscription_service = SubscriptionService(db_session)
        
        # Create a subscription first
        subscription = subscription_service.create_subscription({
            "user_id": test_user.id,
            "plan_id": test_subscription_plan.id,
            "start_date": datetime.now(),
            "billing_cycle": "monthly",
            "auto_renew": True
        })
        
        # Pause the subscription
        paused_subscription = subscription_service.pause_subscription(
            subscription.id,
            30,  # Pause for 30 days
            "Testing pause"
        )
        
        assert paused_subscription is not None
        assert paused_subscription.status == "paused"
        assert paused_subscription.pause_reason == "Testing pause"
        assert paused_subscription.pause_until is not None
        
        # Resume the subscription
        resumed_subscription = subscription_service.resume_subscription(subscription.id)
        
        assert resumed_subscription is not None
        assert resumed_subscription.status == "active"
        assert resumed_subscription.pause_until is None
        
        # Clean up
        db_session.delete(subscription)
        db_session.commit()

    def test_change_subscription_plan(self, db_session, test_user, test_subscription_plan):
        """Test changing a subscription plan."""
        subscription_service = SubscriptionService(db_session)
        
        # Create a subscription first
        subscription = subscription_service.create_subscription({
            "user_id": test_user.id,
            "plan_id": test_subscription_plan.id,
            "start_date": datetime.now(),
            "billing_cycle": "monthly",
            "auto_renew": True
        })
        
        # Create another plan
        new_plan = SubscriptionPlan(
            name="Premium Plan",
            description="Premium internet service",
            price=Decimal("49.99"),
            billing_cycle="monthly",
            features=json.dumps(["50 Mbps", "500 GB data"]),
            is_active=True
        )
        db_session.add(new_plan)
        db_session.commit()
        db_session.refresh(new_plan)
        
        # Change the subscription plan
        updated_subscription = subscription_service.change_plan(
            subscription.id,
            new_plan.id,
            True  # Prorate
        )
        
        assert updated_subscription is not None
        assert updated_subscription.plan_id == new_plan.id
        assert updated_subscription.previous_plan_id == test_subscription_plan.id
        
        # Clean up
        db_session.delete(subscription)
        db_session.delete(new_plan)
        db_session.commit()


class TestTaxManagement:
    """Test cases for tax management."""

    def test_create_tax_rate(self, db_session):
        """Test creating a new tax rate."""
        tax_service = TaxService(db_session)
        
        tax_rate = tax_service.create_tax_rate({
            "name": "GST",
            "description": "Goods and Services Tax",
            "rate": Decimal("0.10"),
            "country": "AU",
            "is_default": True
        })
        
        assert tax_rate is not None
        assert tax_rate.name == "GST"
        assert tax_rate.rate == Decimal("0.10")
        assert tax_rate.country == "AU"
        
        # Clean up
        db_session.delete(tax_rate)
        db_session.commit()

    def test_create_tax_exemption(self, db_session, test_user, test_tax_rate):
        """Test creating a tax exemption for a user."""
        tax_service = TaxService(db_session)
        
        exemption = tax_service.create_tax_exemption({
            "user_id": test_user.id,
            "tax_rate_id": test_tax_rate.id,
            "exemption_certificate": "EXEMPT-123",
            "valid_from": datetime.now(),
            "valid_to": datetime.now() + timedelta(days=365)
        })
        
        assert exemption is not None
        assert exemption.user_id == test_user.id
        assert exemption.tax_rate_id == test_tax_rate.id
        assert exemption.exemption_certificate == "EXEMPT-123"
        
        # Clean up
        db_session.delete(exemption)
        db_session.commit()

    def test_calculate_tax(self, db_session, test_tax_rate):
        """Test calculating tax for an amount."""
        tax_service = TaxService(db_session)
        
        # Calculate tax for an amount in the UK
        tax_calculation = tax_service.calculate_tax(
            Decimal("100.00"),
            "GB",
            None,  # No region
            None   # No user (no exemptions)
        )
        
        assert tax_calculation is not None
        assert tax_calculation["taxable_amount"] == Decimal("100.00")
        assert tax_calculation["total_tax"] == Decimal("20.00")  # 20% VAT
        assert len(tax_calculation["tax_details"]) == 1
        assert tax_calculation["tax_details"][0]["rate"] == Decimal("0.20")


class TestDiscountManagement:
    """Test cases for discount management."""

    def test_create_discount(self, db_session):
        """Test creating a new discount."""
        discount_service = DiscountService(db_session)
        
        discount = discount_service.create_discount({
            "name": "Summer Sale",
            "description": "Summer promotion",
            "discount_type": "promotional",
            "amount": Decimal("15.00"),
            "is_percentage": True,
            "code": "SUMMER2025",
            "valid_from": datetime.now(),
            "valid_to": datetime.now() + timedelta(days=90),
            "max_uses": 500,
            "status": "active"
        })
        
        assert discount is not None
        assert discount.name == "Summer Sale"
        assert discount.amount == Decimal("15.00")
        assert discount.code == "SUMMER2025"
        
        # Clean up
        db_session.delete(discount)
        db_session.commit()

    def test_validate_discount_code(self, db_session, test_discount):
        """Test validating a discount code."""
        discount_service = DiscountService(db_session)
        
        # Validate a valid discount code
        validation = discount_service.validate_discount_code(
            "NEWCUSTOMER",
            None,  # No user ID
            Decimal("100.00"),  # Order amount
            None   # No plan ID
        )
        
        assert validation is not None
        assert validation["valid"] is True
        assert validation["discount_id"] == test_discount.id
        assert validation["discount_amount"] == Decimal("10.00")  # 10% of 100.00
        
        # Validate an invalid discount code
        invalid_validation = discount_service.validate_discount_code(
            "INVALID",
            None,
            Decimal("100.00"),
            None
        )
        
        assert invalid_validation is not None
        assert invalid_validation["valid"] is False

    def test_calculate_discount_amount(self, db_session, test_discount):
        """Test calculating discount amount."""
        discount_service = DiscountService(db_session)
        
        # Calculate discount amount
        calculation = discount_service.calculate_discount_amount(
            test_discount.id,
            Decimal("200.00")
        )
        
        assert calculation is not None
        assert calculation["discount_id"] == test_discount.id
        assert calculation["base_amount"] == Decimal("200.00")
        assert calculation["discount_amount"] == Decimal("20.00")  # 10% of 200.00
        assert calculation["final_amount"] == Decimal("180.00")


class TestFinancialReporting:
    """Test cases for financial reporting."""

    def test_get_revenue_summary(self, db_session, test_user):
        """Test getting a revenue summary."""
        reporting_service = ReportingService(db_session)
        
        # Create some test data
        invoice = Invoice(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            due_date=datetime.now() + timedelta(days=30),
            status="paid",
            created_at=datetime.now() - timedelta(days=5)
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        
        payment = Payment(
            invoice_id=invoice.id,
            user_id=test_user.id,
            amount=Decimal("100.00"),
            payment_method="credit_card",
            status="completed",
            created_at=datetime.now() - timedelta(days=3)
        )
        db_session.add(payment)
        db_session.commit()
        
        # Get revenue summary
        start_date = datetime.now() - timedelta(days=10)
        end_date = datetime.now()
        summary = reporting_service.get_revenue_summary(start_date, end_date)
        
        assert summary is not None
        assert summary["invoiced_amount"] >= 100.00
        assert summary["paid_amount"] >= 100.00
        
        # Clean up
        db_session.delete(payment)
        db_session.delete(invoice)
        db_session.commit()

    def test_get_subscription_metrics(self, db_session, test_user, test_subscription_plan):
        """Test getting subscription metrics."""
        subscription_service = SubscriptionService(db_session)
        reporting_service = ReportingService(db_session)
        
        # Create a subscription
        subscription = subscription_service.create_subscription({
            "user_id": test_user.id,
            "plan_id": test_subscription_plan.id,
            "start_date": datetime.now() - timedelta(days=10),
            "billing_cycle": "monthly",
            "auto_renew": True
        })
        
        # Get subscription metrics
        metrics = reporting_service.get_subscription_metrics()
        
        assert metrics is not None
        assert metrics["active_subscriptions"] >= 1
        assert metrics["monthly_recurring_revenue"] >= float(test_subscription_plan.price)
        
        # Clean up
        db_session.delete(subscription)
        db_session.commit()


def test_api_endpoints(client, monkeypatch, db_session, test_user, test_admin_user, test_subscription_plan, test_tax_rate, test_discount):
    """Test the API endpoints for the expanded billing module."""
    
    # Mock the authentication to use our test users
    def mock_get_current_user():
        return test_user
    
    def mock_get_current_admin_user():
        return test_admin_user
    
    monkeypatch.setattr("isp_management.backend_core.auth_service.get_current_user", mock_get_current_user)
    monkeypatch.setattr("isp_management.backend_core.auth_service.get_current_admin_user", mock_get_current_admin_user)
    
    # Test subscription endpoints
    subscription_data = {
        "user_id": test_user.id,
        "plan_id": test_subscription_plan.id,
        "start_date": datetime.now().isoformat(),
        "billing_cycle": "monthly",
        "auto_renew": True
    }
    
    response = client.post("/api/billing/subscriptions", json=subscription_data)
    assert response.status_code == 201
    subscription_id = response.json()["id"]
    
    response = client.get(f"/api/billing/subscriptions/{subscription_id}")
    assert response.status_code == 200
    assert response.json()["user_id"] == test_user.id
    
    # Test tax endpoints
    tax_rate_data = {
        "name": "Local Tax",
        "description": "Local sales tax",
        "rate": 0.05,
        "country": "US",
        "region": "NY",
        "is_default": False
    }
    
    response = client.post("/api/billing/tax-rates", json=tax_rate_data)
    assert response.status_code == 201
    tax_rate_id = response.json()["id"]
    
    response = client.get(f"/api/billing/tax-rates/{tax_rate_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Local Tax"
    
    # Test discount endpoints
    discount_data = {
        "name": "API Discount",
        "description": "Discount created via API",
        "discount_type": "promotional",
        "amount": 25.0,
        "is_percentage": True,
        "code": "API25",
        "valid_from": datetime.now().isoformat(),
        "valid_to": (datetime.now() + timedelta(days=30)).isoformat(),
        "max_uses": 50,
        "status": "active"
    }
    
    response = client.post("/api/billing/discounts", json=discount_data)
    assert response.status_code == 201
    discount_id = response.json()["id"]
    
    response = client.get(f"/api/billing/discounts/{discount_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "API Discount"
    
    # Test reporting endpoints
    date_range = {
        "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
        "end_date": datetime.now().isoformat()
    }
    
    response = client.post("/api/billing/reports/revenue-summary", json=date_range)
    assert response.status_code == 200
    
    # Clean up
    # The fixtures will clean up the test_user, test_admin_user, test_subscription_plan, test_tax_rate, and test_discount
    # We need to clean up the entities created in this test
    subscription = db_session.query(Subscription).filter_by(id=subscription_id).first()
    if subscription:
        db_session.delete(subscription)
    
    tax_rate = db_session.query(TaxRate).filter_by(id=tax_rate_id).first()
    if tax_rate:
        db_session.delete(tax_rate)
    
    discount = db_session.query(Discount).filter_by(id=discount_id).first()
    if discount:
        db_session.delete(discount)
    
    db_session.commit()
