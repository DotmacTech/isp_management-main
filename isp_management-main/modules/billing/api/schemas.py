"""
Billing Module API Schemas

This module defines Pydantic models for billing-related data validation,
serialization and documentation.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from enum import Enum


class DiscountBaseSchema(BaseModel):
    """Base model for discount information."""
    name: str = Field(..., description="Name of the discount")
    percentage: Decimal = Field(..., description="Discount percentage value")
    description: Optional[str] = Field(None, description="Optional description of the discount")


class DiscountCreateSchema(DiscountBaseSchema):
    """Schema for creating a new discount."""
    pass


class DiscountResponseSchema(DiscountBaseSchema):
    """Schema for discount response data."""
    id: int = Field(..., description="Unique identifier for the discount")
    created_at: datetime = Field(..., description="When the discount was created")
    updated_at: Optional[datetime] = Field(None, description="When the discount was last updated")

    model_config = ConfigDict(from_attributes=True)


class PaymentBaseSchema(BaseModel):
    """Base model for payment information."""
    invoice_id: int = Field(..., description="ID of the invoice this payment is for")
    amount: Decimal = Field(..., description="Payment amount")
    payment_method: str = Field(..., description="Method of payment")
    transaction_id: Optional[str] = Field(None, description="External transaction ID if applicable")
    notes: Optional[str] = Field(None, description="Additional notes about the payment")


class PaymentCreateSchema(PaymentBaseSchema):
    """Schema for creating a new payment."""
    pass


class PaymentResponseSchema(PaymentBaseSchema):
    """Schema for payment response data."""
    id: int = Field(..., description="Unique identifier for the payment")
    created_at: datetime = Field(..., description="When the payment was created")
    status: str = Field(..., description="Status of the payment")

    model_config = ConfigDict(from_attributes=True)


class TaxRateBaseSchema(BaseModel):
    """Base model for tax rate information."""
    name: str = Field(..., description="Name of the tax rate")
    rate: Decimal = Field(..., description="Tax rate percentage")
    description: Optional[str] = Field(None, description="Optional description of the tax rate")
    is_compound: bool = Field(False, description="Whether this tax is applied after other taxes")


class TaxRateCreateSchema(TaxRateBaseSchema):
    """Schema for creating a new tax rate."""
    pass


class TaxRateResponseSchema(TaxRateBaseSchema):
    """Schema for tax rate response data."""
    id: int = Field(..., description="Unique identifier for the tax rate")
    created_at: datetime = Field(..., description="When the tax rate was created")
    updated_at: Optional[datetime] = Field(None, description="When the tax rate was last updated")

    model_config = ConfigDict(from_attributes=True)


class CreditNoteBaseSchema(BaseModel):
    """Base model for credit note information."""
    invoice_id: int = Field(..., description="ID of the related invoice")
    amount: Decimal = Field(..., description="Amount of the credit note")
    reason: str = Field(..., description="Reason for issuing the credit note")
    notes: Optional[str] = Field(None, description="Additional notes about the credit note")


class CreditNoteCreateSchema(CreditNoteBaseSchema):
    """Schema for creating a new credit note."""
    pass


class CreditNoteResponseSchema(CreditNoteBaseSchema):
    """Schema for credit note response data."""
    id: int = Field(..., description="Unique identifier for the credit note")
    created_at: datetime = Field(..., description="When the credit note was created")
    updated_at: Optional[datetime] = Field(None, description="When the credit note was last updated")
    status: str = Field(..., description="Status of the credit note")

    model_config = ConfigDict(from_attributes=True)


class InvoiceItemBaseSchema(BaseModel):
    """Base model for invoice item information."""
    description: str = Field(..., description="Description of the item")
    quantity: int = Field(1, description="Quantity of items")
    unit_price: Decimal = Field(..., description="Price per unit")
    discount: Optional[Decimal] = Field(None, description="Discount applied to this item")
    tax_rate: Optional[Decimal] = Field(None, description="Tax rate applied to this item")


class InvoiceItemCreateSchema(InvoiceItemBaseSchema):
    """Schema for creating a new invoice item."""
    pass


class InvoiceItemResponseSchema(InvoiceItemBaseSchema):
    """Schema for invoice item response data."""
    id: int = Field(..., description="Unique identifier for the invoice item")
    subtotal: Decimal = Field(..., description="Subtotal for this item (quantity * unit_price)")
    discount_amount: Decimal = Field(0, description="Amount of discount applied to this item")
    tax_amount: Decimal = Field(0, description="Amount of tax applied to this item")
    total: Decimal = Field(..., description="Total amount for this item after discounts and taxes")

    model_config = ConfigDict(from_attributes=True)


class InvoiceBaseSchema(BaseModel):
    """Base model for invoice information."""
    user_id: int = Field(..., description="ID of the user this invoice belongs to")
    due_date: datetime = Field(..., description="Due date for payment")
    notes: Optional[str] = Field(None, description="Additional notes about the invoice")
    payment_terms: Optional[str] = Field(None, description="Payment terms for this invoice")


class InvoiceCreateSchema(InvoiceBaseSchema):
    """Schema for creating a new invoice."""
    items: List[InvoiceItemCreateSchema] = Field(..., description="Items included in this invoice")
    discount_ids: Optional[List[int]] = Field(None, description="IDs of discounts to apply")
    tax_rate_ids: Optional[List[int]] = Field(None, description="IDs of tax rates to apply")


class InvoiceResponseSchema(InvoiceBaseSchema):
    """Schema for invoice response data."""
    id: int = Field(..., description="Unique identifier for the invoice")
    invoice_number: str = Field(..., description="Generated invoice number")
    created_at: datetime = Field(..., description="When the invoice was created")
    updated_at: Optional[datetime] = Field(None, description="When the invoice was last updated")
    status: str = Field(..., description="Status of the invoice")
    subtotal: Decimal = Field(..., description="Subtotal amount before discounts and taxes")
    discount_amount: Decimal = Field(0, description="Total amount of discounts applied")
    tax_amount: Decimal = Field(0, description="Total amount of taxes applied")
    total: Decimal = Field(..., description="Total amount after discounts and taxes")
    items: List[InvoiceItemResponseSchema] = Field(..., description="Items included in this invoice")

    model_config = ConfigDict(from_attributes=True)


class DiscountDetailSchema(BaseModel):
    """Schema for discount details within an invoice."""
    id: int
    name: str
    description: Optional[str]
    percentage: Decimal
    amount: Decimal


class TaxDetailSchema(BaseModel):
    """Schema for tax details within an invoice."""
    id: int
    name: str
    rate: Decimal
    amount: Decimal
    is_compound: bool = False


class CreditNoteDetailSchema(BaseModel):
    """Schema for credit note details within an invoice."""
    id: int
    amount: float
    date_issued: datetime
    reason: str
    status: str


class InvoiceDetailResponseSchema(BaseModel):
    """Detailed schema for invoice response."""
    invoice: InvoiceResponseSchema
    discounts: List[DiscountResponseSchema] = Field([], description="Discounts applied to this invoice")
    taxes: List[TaxRateResponseSchema] = Field([], description="Tax rates applied to this invoice")
    credit_notes: List[CreditNoteResponseSchema] = Field([], description="Credit notes for this invoice")
    payment_history: List[Dict[str, Any]] = Field([], description="Payment history for this invoice")
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceDetailsResponseSchema(BaseModel):
    """Complete detailed schema for invoice response including all related data."""
    id: int
    invoice_number: str
    customer_id: int
    customer_name: str
    issue_date: datetime
    due_date: datetime
    status: str
    subtotal: float
    discount_total: float
    tax_total: float
    credit_note_total: float
    total: float
    line_items: List[Dict[str, Any]]
    discounts: List[DiscountDetailSchema]
    taxes: List[TaxDetailSchema]
    credit_notes: List[CreditNoteDetailSchema]
    payment_history: List[Dict[str, Any]]
    notes: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class OverdueInvoiceResponseSchema(BaseModel):
    """Schema for overdue invoice response data."""
    invoice_id: int = Field(..., description="Unique identifier for the invoice")
    user_id: int = Field(..., description="ID of the user this invoice belongs to")
    amount: Decimal = Field(..., description="Total amount of the invoice")
    due_date: datetime = Field(..., description="Due date for payment")
    days_overdue: int = Field(..., description="Number of days the invoice is overdue")
    
    model_config = ConfigDict(from_attributes=True)


class MonthlyReportRequestSchema(BaseModel):
    """Schema for requesting a monthly billing report."""
    year: int = Field(..., description="Year for the report", ge=2000, le=2100)
    month: int = Field(..., description="Month for the report (1-12)", ge=1, le=12)
    customer_id: Optional[int] = Field(None, description="Optional customer ID to filter report")
    include_details: bool = Field(False, description="Whether to include detailed breakdowns")
    report_format: str = Field("pdf", description="Report format (pdf, csv, excel)")

    @field_validator('month')
    def validate_month(cls, v):
        """Validate month value."""
        if v < 1 or v > 12:
            raise ValueError("Month must be between 1 and 12")
        return v


# Subscription schemas
class SubscriptionPeriod(str, Enum):
    """Enum for subscription billing periods."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    BIANNUAL = "biannual"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    """Enum for subscription status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PENDING = "pending"
    EXPIRED = "expired"


class SubscriptionBase(BaseModel):
    """Base schema for subscription data."""
    user_id: int = Field(..., description="ID of the user the subscription belongs to")
    plan_id: int = Field(..., description="ID of the plan the user is subscribed to")
    billing_day: int = Field(..., description="Day of the month for billing", ge=1, le=31)
    period: SubscriptionPeriod = Field(SubscriptionPeriod.MONTHLY, description="Subscription period")
    auto_renew: bool = Field(True, description="Whether the subscription auto-renews")
    price_override: Optional[Decimal] = Field(None, description="Override price (if different from plan)")
    discount_id: Optional[int] = Field(None, description="ID of applied discount")
    start_date: datetime = Field(..., description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    notes: Optional[str] = Field(None, description="Additional notes")

    model_config = ConfigDict(from_attributes=True)

    @field_validator('billing_day')
    def validate_billing_day(cls, v):
        """Validate billing day."""
        if v < 1 or v > 31:
            raise ValueError("Billing day must be between 1 and 31")
        return v


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription."""
    pass


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription response data."""
    id: int = Field(..., description="Unique identifier for the subscription")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    next_billing_date: datetime = Field(..., description="Next billing date")
    plan_name: str = Field(..., description="Name of the subscribed plan")
    current_period_start: datetime = Field(..., description="Start of current billing period")
    current_period_end: datetime = Field(..., description="End of current billing period")

    model_config = ConfigDict(from_attributes=True)


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    plan_id: Optional[int] = Field(None, description="ID of the new plan")
    billing_day: Optional[int] = Field(None, description="New billing day", ge=1, le=31)
    period: Optional[SubscriptionPeriod] = Field(None, description="New subscription period")
    auto_renew: Optional[bool] = Field(None, description="Whether the subscription auto-renews")
    price_override: Optional[Decimal] = Field(None, description="Override price")
    discount_id: Optional[int] = Field(None, description="ID of applied discount")
    notes: Optional[str] = Field(None, description="Additional notes")

    model_config = ConfigDict(from_attributes=True)
