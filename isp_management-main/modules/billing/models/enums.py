"""
Billing module enum classes.

This module contains all enum classes used in the billing module for consistent
type definitions across models, services, and API schemas.
"""

from enum import StrEnum


class BillingCycle(StrEnum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class PaymentMethod(StrEnum):
    """Payment method options"""
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    EWALLET = "ewallet"
    CASH = "cash"
    CHECK = "check"
    CRYPTO = "crypto"
    OTHER = "other"


class PaymentStatus(StrEnum):
    """Payment status options"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"


class InvoiceStatus(StrEnum):
    """Invoice status options"""
    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class SubscriptionStatus(StrEnum):
    """Subscription status options"""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIAL = "trial"
    EXPIRED = "expired"


class DiscountType(StrEnum):
    """Discount type options"""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    TIERED = "tiered"


class DiscountStatus(StrEnum):
    """Discount status options"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
