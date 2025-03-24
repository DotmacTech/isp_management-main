from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, 
    Integer, JSON, Numeric, String, Text, Table
)
from sqlalchemy.orm import relationship

from backend_core.database import Base


class BillingCycle(str, Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class PaymentMethod(str, Enum):
    """Payment method options"""
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    EWALLET = "ewallet"
    CASH = "cash"
    CHECK = "check"
    CRYPTO = "crypto"
    OTHER = "other"


class PaymentStatus(str, Enum):
    """Payment status options"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"


class InvoiceStatus(str, Enum):
    """Invoice status options"""
    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class SubscriptionStatus(str, Enum):
    """Subscription status options"""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIAL = "trial"
    EXPIRED = "expired"


class DiscountType(str, Enum):
    """Discount type options"""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    TIERED = "tiered"


class RecurringBillingProfile(Base):
    """Model for recurring billing profiles"""
    __tablename__ = "recurring_billing_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String(128), nullable=False)
    billing_cycle = Column(String(20), default=BillingCycle.MONTHLY)
    next_billing_date = Column(DateTime, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)
    grace_period_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="recurring_billing_profiles")
    subscriptions = relationship("Subscription", back_populates="billing_profile")


class Subscription(Base):
    """Model for subscriptions"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    billing_profile_id = Column(Integer, ForeignKey("recurring_billing_profiles.id"), nullable=True)
    plan_id = Column(Integer, ForeignKey("tariff_plans.id"))
    status = Column(String(20), default=SubscriptionStatus.ACTIVE)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    trial_end_date = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    pause_start = Column(DateTime, nullable=True)
    pause_end = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("TariffPlan")
    billing_profile = relationship("RecurringBillingProfile", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")


class InvoiceTemplate(Base):
    """Model for invoice templates"""
    __tablename__ = "invoice_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    template_html = Column(Text, nullable=False)
    css_styles = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    creator = relationship("User")


class PaymentGatewayConfig(Base):
    """Model for payment gateway configurations"""
    __tablename__ = "payment_gateway_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    gateway_type = Column(String(50), nullable=False)  # stripe, paypal, etc.
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    config = Column(JSON, nullable=False)  # API keys, endpoints, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = relationship("PaymentTransaction", back_populates="gateway")


class PaymentTransaction(Base):
    """Model for payment transactions"""
    __tablename__ = "payment_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    gateway_id = Column(Integer, ForeignKey("payment_gateway_configs.id"))
    transaction_id = Column(String(255), unique=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default=PaymentStatus.PENDING)
    gateway_response = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payment = relationship("Payment", back_populates="transactions")
    gateway = relationship("PaymentGatewayConfig", back_populates="transactions")
    refunds = relationship("Refund", back_populates="transaction")


class Refund(Base):
    """Model for refunds"""
    __tablename__ = "refunds"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"))
    transaction_id = Column(Integer, ForeignKey("payment_transactions.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    refund_transaction_id = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payment = relationship("Payment", back_populates="refunds")
    transaction = relationship("PaymentTransaction", back_populates="refunds")
    creator = relationship("User")


class PaymentReminder(Base):
    """Model for payment reminders"""
    __tablename__ = "payment_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    reminder_type = Column(String(20))  # upcoming, overdue, etc.
    days_offset = Column(Integer)  # days before/after due date
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="reminders")


class UsageRecord(Base):
    """Model for usage-based billing records"""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # GB, minutes, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50))  # radius, api, manual, etc.
    billed = Column(Boolean, default=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription")
    invoice = relationship("Invoice")


class TieredPricing(Base):
    """Model for tiered pricing"""
    __tablename__ = "tiered_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("tariff_plans.id"))
    tier_start = Column(Float, nullable=False)
    tier_end = Column(Float, nullable=True)  # Null means unlimited
    unit_price = Column(Numeric(10, 4), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = relationship("TariffPlan")


class InvoiceItem(Base):
    """Model for invoice line items"""
    __tablename__ = "invoice_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    description = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="items")


class TaxExemption(Base):
    """Model for tax exemptions"""
    __tablename__ = "tax_exemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tax_rate_id = Column(Integer, ForeignKey("tax_rates.id"))
    exemption_certificate = Column(String(128), nullable=True)
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    tax_rate = relationship("TaxRate")


class FinancialTransaction(Base):
    """Model for financial transactions (for accounting purposes)"""
    __tablename__ = "financial_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String(50))  # invoice, payment, refund, credit_note, etc.
    reference_id = Column(Integer)  # ID of the related entity
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    description = Column(Text, nullable=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    accounting_code = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


class AccountingIntegration(Base):
    """Model for accounting software integrations"""
    __tablename__ = "accounting_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    integration_type = Column(String(50))  # quickbooks, xero, etc.
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BillingAuditLog(Base):
    """Model for billing-specific audit logs"""
    __tablename__ = "billing_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50))  # invoice, payment, subscription, etc.
    entity_id = Column(Integer)
    action = Column(String(50))  # create, update, delete, etc.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    changes = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
