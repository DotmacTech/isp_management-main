"""
Schemas for the billing API.

This module contains Pydantic models for the billing API.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

# Import subscription schemas
from .subscription import (
    SubscriptionPeriod,
    SubscriptionStatus,
    SubscriptionBase,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionHistoryEntry,
    SubscriptionWithHistory
)

# Monthly report request schema
class MonthlyReportRequestSchema(BaseModel):
    """Request schema for generating monthly billing reports."""
    year: int = Field(..., description="Year for the report", ge=2000, le=2100)
    month: int = Field(..., description="Month for the report", ge=1, le=12)
    
    model_config = ConfigDict(from_attributes=True)


# Discount schemas
class DiscountType(str, Enum):
    """Enum for discount types."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class DiscountBaseSchema(BaseModel):
    """Base schema for discount data."""
    name: str = Field(..., description="Discount name")
    description: Optional[str] = Field(None, description="Discount description")
    discount_type: DiscountType = Field(..., description="Type of discount")
    value: Decimal = Field(..., description="Discount value", ge=0)
    is_active: bool = Field(True, description="Whether the discount is active")
    valid_from: datetime = Field(..., description="Start date of validity")
    valid_to: Optional[datetime] = Field(None, description="End date of validity")
    applicable_plans: Optional[List[int]] = Field(None, description="List of applicable plan IDs")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountCreateSchema(DiscountBaseSchema):
    """Schema for creating a new discount."""
    pass


class DiscountResponseSchema(DiscountBaseSchema):
    """Schema for discount response data."""
    id: int = Field(..., description="Unique identifier for the discount")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountUpdateSchema(BaseModel):
    """Schema for updating a discount."""
    name: Optional[str] = Field(None, description="Discount name")
    type: Optional[DiscountType] = Field(None, description="Discount type")
    value: Optional[Decimal] = Field(None, description="Discount value", ge=0)
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    is_active: Optional[bool] = Field(None, description="Whether the discount is active")
    max_uses: Optional[int] = Field(None, description="Maximum number of uses", ge=0)
    description: Optional[str] = Field(None, description="Description")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountDetailSchema(DiscountResponseSchema):
    """Schema for detailed discount information."""
    current_uses: int = Field(0, description="Current number of uses")
    remaining_uses: Optional[int] = Field(None, description="Remaining uses available")
    is_expired: bool = Field(False, description="Whether the discount is expired")
    products: List[int] = Field([], description="IDs of products this discount applies to")
    services: List[int] = Field([], description="IDs of services this discount applies to")
    
    model_config = ConfigDict(from_attributes=True)


# Credit note schemas
class CreditNoteReason(str, Enum):
    """Enum for credit note reasons."""
    SERVICE_ISSUE = "service_issue"
    BILLING_ERROR = "billing_error"
    GOODWILL = "goodwill"
    CANCELLATION = "cancellation"
    OTHER = "other"


class CreditNoteBaseSchema(BaseModel):
    """Base schema for credit note data."""
    invoice_id: int = Field(..., description="ID of the related invoice")
    amount: Decimal = Field(..., description="Credit note amount", ge=0)
    reason: CreditNoteReason = Field(..., description="Reason for credit note")
    description: str = Field(..., description="Detailed description")
    
    model_config = ConfigDict(from_attributes=True)


class CreditNoteCreateSchema(CreditNoteBaseSchema):
    """Schema for creating a new credit note."""
    pass


class CreditNoteResponseSchema(CreditNoteBaseSchema):
    """Schema for credit note response data."""
    id: int = Field(..., description="Unique identifier for the credit note")
    credit_note_number: str = Field(..., description="Credit note number")
    status: str = Field(..., description="Status of the credit note")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class CreditNoteDetailSchema(CreditNoteResponseSchema):
    """Schema for detailed credit note information."""
    invoice_number: Optional[str] = Field(None, description="Original invoice number if this credit note is tied to an invoice")
    applied_amount: Decimal = Field(0, description="Amount already applied from this credit note")
    remaining_amount: Decimal = Field(..., description="Remaining amount that can be applied")
    refunded_amount: Optional[Decimal] = Field(None, description="Amount refunded to customer")
    applied_to: List[Dict[str, Any]] = Field([], description="List of invoices/transactions this credit note has been applied to")
    audit_trail: List[Dict[str, Any]] = Field([], description="Audit trail of actions taken on this credit note")
    
    model_config = ConfigDict(from_attributes=True)


# Tax rate schemas
class TaxRateBaseSchema(BaseModel):
    """Base schema for tax rate data."""
    name: str = Field(..., description="Tax name (e.g., VAT, GST)")
    rate: Decimal = Field(..., description="Tax rate percentage", ge=0, le=100)
    country_code: Optional[str] = Field(None, description="ISO country code")
    region: Optional[str] = Field(None, description="Region or state")
    is_default: bool = Field(False, description="Whether this is the default tax rate")
    description: Optional[str] = Field(None, description="Tax description")
    
    model_config = ConfigDict(from_attributes=True)


class TaxRateCreateSchema(TaxRateBaseSchema):
    """Schema for creating a new tax rate."""
    pass


class TaxRateResponseSchema(TaxRateBaseSchema):
    """Schema for tax rate response data."""
    id: int = Field(..., description="Unique identifier for the tax rate")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class TaxRateUpdateSchema(BaseModel):
    """Schema for updating a tax rate."""
    name: Optional[str] = Field(None, description="Tax name")
    rate: Optional[Decimal] = Field(None, description="Tax rate percentage", ge=0, le=100)
    country_code: Optional[str] = Field(None, description="ISO country code")
    region: Optional[str] = Field(None, description="Region or state")
    is_default: Optional[bool] = Field(None, description="Whether this is the default tax rate")
    description: Optional[str] = Field(None, description="Tax description")
    
    model_config = ConfigDict(from_attributes=True)


class TaxDetailSchema(TaxRateResponseSchema):
    """Schema for detailed tax rate information."""
    usage_count: int = Field(0, description="Number of times this tax rate has been used")
    regions_applied: List[str] = Field([], description="Regions where this tax rate is applied")
    last_applied: Optional[datetime] = Field(None, description="Last time this tax rate was applied")
    is_regulatory_compliant: bool = Field(True, description="Whether this tax rate complies with regulations")
    
    model_config = ConfigDict(from_attributes=True)


# Invoice detail schemas
class InvoiceItemSchema(BaseModel):
    """Schema for invoice item data."""
    id: Optional[int] = Field(None, description="Item ID")
    invoice_id: Optional[int] = Field(None, description="Invoice ID this item belongs to")
    description: str = Field(..., description="Item description")
    quantity: Decimal = Field(..., description="Quantity", ge=0)
    unit_price: Decimal = Field(..., description="Unit price", ge=0)
    amount: Decimal = Field(..., description="Total amount", ge=0)
    tax_rate: Optional[Decimal] = Field(None, description="Tax rate percentage", ge=0)
    tax_amount: Optional[Decimal] = Field(None, description="Tax amount", ge=0)
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceCreateSchema(BaseModel):
    """Schema for creating a new invoice."""
    user_id: int = Field(..., description="User ID the invoice belongs to")
    amount: Decimal = Field(..., description="Total invoice amount", ge=0)
    tax_amount: Decimal = Field(0, description="Total tax amount", ge=0)
    subtotal: Decimal = Field(..., description="Subtotal before tax", ge=0)
    due_date: datetime = Field(..., description="Due date for payment")
    description: str = Field(..., description="Invoice description")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    notes: Optional[str] = Field(None, description="Additional notes")
    items: List[InvoiceItemSchema] = Field([], description="Invoice items")
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceResponseSchema(BaseModel):
    """Schema for invoice response data."""
    id: int = Field(..., description="Unique identifier for the invoice")
    invoice_number: str = Field(..., description="Invoice number")
    user_id: int = Field(..., description="User ID the invoice belongs to")
    amount: Decimal = Field(..., description="Total invoice amount")
    tax_amount: Decimal = Field(..., description="Total tax amount")
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    status: str = Field(..., description="Payment status (paid, unpaid, cancelled)")
    due_date: datetime = Field(..., description="Due date for payment")
    issue_date: datetime = Field(..., description="Issue date")
    description: str = Field(..., description="Invoice description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceDetailResponseSchema(BaseModel):
    """Schema for detailed invoice response data."""
    id: int = Field(..., description="Unique identifier for the invoice")
    invoice_number: str = Field(..., description="Invoice number")
    user_id: int = Field(..., description="User ID the invoice belongs to")
    amount: Decimal = Field(..., description="Total invoice amount")
    tax_amount: Decimal = Field(..., description="Total tax amount")
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    status: str = Field(..., description="Payment status (paid, unpaid, cancelled)")
    due_date: datetime = Field(..., description="Due date for payment")
    issue_date: datetime = Field(..., description="Issue date")
    description: str = Field(..., description="Invoice description")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    notes: Optional[str] = Field(None, description="Additional notes")
    items: List[InvoiceItemSchema] = Field([], description="Invoice items")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Add an alias for backward compatibility
InvoiceDetailsResponseSchema = InvoiceDetailResponseSchema


class OverdueInvoiceResponseSchema(BaseModel):
    """Schema for overdue invoice response data."""
    id: int = Field(..., description="Unique identifier for the invoice")
    invoice_number: str = Field(..., description="Invoice number")
    user_id: int = Field(..., description="User ID the invoice belongs to")
    amount: Decimal = Field(..., description="Total invoice amount")
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    due_date: datetime = Field(..., description="Due date for payment")
    days_overdue: int = Field(..., description="Number of days the invoice is overdue")
    last_reminder_sent: Optional[datetime] = Field(None, description="Timestamp of last reminder sent")
    reminder_count: int = Field(0, description="Number of reminders sent")
    
    model_config = ConfigDict(from_attributes=True)


# Payment schemas
class PaymentMethod(str, Enum):
    """Enum for payment methods."""
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    CASH = "cash"
    OTHER = "other"


class PaymentStatus(str, Enum):
    """Enum for payment status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentCreateSchema(BaseModel):
    """Schema for creating a new payment."""
    user_id: int = Field(..., description="User ID this payment belongs to")
    invoice_id: Optional[int] = Field(None, description="Invoice ID this payment is for")
    amount: Decimal = Field(..., description="Payment amount", gt=0)
    method: PaymentMethod = Field(..., description="Payment method")
    reference: Optional[str] = Field(None, description="Payment reference")
    notes: Optional[str] = Field(None, description="Additional notes")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    
    model_config = ConfigDict(from_attributes=True)


class PaymentResponseSchema(BaseModel):
    """Schema for payment response data."""
    id: int = Field(..., description="Unique identifier for the payment")
    user_id: int = Field(..., description="User ID this payment belongs to")
    invoice_id: Optional[int] = Field(None, description="Invoice ID this payment is for")
    amount: Decimal = Field(..., description="Payment amount")
    method: PaymentMethod = Field(..., description="Payment method")
    status: PaymentStatus = Field(..., description="Payment status")
    reference: Optional[str] = Field(None, description="Payment reference")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Discount type enum
class DiscountType(str, Enum):
    """Enum for discount types."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


# Export all schemas
__all__ = [
    'SubscriptionPeriod',
    'SubscriptionStatus',
    'SubscriptionBase',
    'SubscriptionCreate',
    'SubscriptionResponse',
    'SubscriptionUpdate',
    'MonthlyReportRequestSchema',
    'DiscountType',
    'DiscountBaseSchema',
    'DiscountCreateSchema',
    'DiscountResponseSchema',
    'DiscountUpdateSchema',
    'DiscountDetailSchema',
    'CreditNoteReason',
    'CreditNoteBaseSchema',
    'CreditNoteCreateSchema',
    'CreditNoteResponseSchema',
    'CreditNoteDetailSchema',
    'TaxRateBaseSchema',
    'TaxRateCreateSchema',
    'TaxRateResponseSchema',
    'TaxRateUpdateSchema',
    'TaxDetailSchema',
    'InvoiceItemSchema',
    'InvoiceCreateSchema',
    'InvoiceResponseSchema',
    'InvoiceDetailResponseSchema',
    'InvoiceDetailsResponseSchema',
    'OverdueInvoiceResponseSchema',
    'PaymentMethod',
    'PaymentStatus',
    'PaymentCreateSchema',
    'PaymentResponseSchema'
]
