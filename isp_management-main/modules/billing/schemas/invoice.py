"""
Invoice schemas for the billing module.

This module defines Pydantic models for invoice operations.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator

from modules.billing.models.enums import InvoiceStatus


# Base Invoice Schema
class InvoiceBase(BaseModel):
    """Base schema for invoice data."""
    customer_id: int = Field(..., description="ID of the customer")
    subscription_id: Optional[int] = Field(None, description="ID of the related subscription")
    due_date: datetime = Field(..., description="Due date for the invoice")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Creation Schema
class InvoiceCreate(InvoiceBase):
    """Schema for creating a new invoice."""
    items: List[Dict[str, Any]] = Field(..., description="Line items for the invoice")
    status: str = Field(InvoiceStatus.DRAFT, description="Initial status of the invoice")


# Invoice Update Schema
class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice."""
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Item Schema
class InvoiceItemBase(BaseModel):
    """Base schema for invoice item data."""
    invoice_id: int = Field(..., description="ID of the parent invoice")
    description: str = Field(..., description="Item description")
    quantity: int = Field(1, description="Quantity of items")
    unit_price: Decimal = Field(..., description="Price per unit")
    tax_rate: Optional[Decimal] = Field(None, description="Tax rate as decimal")
    discount_amount: Optional[Decimal] = Field(None, description="Discount amount")
    
    model_config = ConfigDict(from_attributes=True)
    
    @model_validator(mode='after')
    def calculate_total(self) -> 'InvoiceItemBase':
        """Calculate the total price for this item."""
        base_total = self.quantity * self.unit_price
        if hasattr(self, 'discount_amount') and self.discount_amount:
            base_total -= self.discount_amount
        if hasattr(self, 'tax_rate') and self.tax_rate:
            self.tax_amount = base_total * self.tax_rate
            base_total += self.tax_amount
        self.total = base_total
        return self


# Invoice Item Creation Schema
class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating a new invoice item."""
    pass


# Invoice Response Schema
class InvoiceResponse(InvoiceBase):
    """Schema for invoice response data."""
    id: int
    invoice_number: str
    created_at: datetime
    updated_at: datetime
    status: str
    total_amount: Decimal
    remaining_amount: Decimal
    items: List[Any] = []
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Detail Response Schema
class InvoiceDetailResponse(InvoiceResponse):
    """Detailed invoice response with additional data."""
    payment_history: List[Dict[str, Any]] = Field([], description="Payment history for this invoice")
    customer_info: Dict[str, Any] = Field(..., description="Customer information")
    
    model_config = ConfigDict(from_attributes=True)


# Multiple Invoices Response Schema
class InvoiceDetailsResponse(BaseModel):
    """Response schema for multiple invoices with pagination."""
    invoices: List[InvoiceResponse]
    total: int
    page: int
    per_page: int
    pages: int
    
    model_config = ConfigDict(from_attributes=True)


# Overdue Invoice Response Schema
class OverdueInvoiceResponse(InvoiceResponse):
    """Schema for overdue invoice response."""
    days_overdue: int = Field(..., description="Days the invoice is overdue")
    late_fee: Optional[Decimal] = Field(None, description="Late fee applied")
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Filter Params
class InvoiceFilterParams(BaseModel):
    """Schema for invoice filtering parameters."""
    user_id: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    is_overdue: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


# Proforma Invoice Creation Schema
class ProformaInvoiceCreate(BaseModel):
    """Schema for creating a proforma invoice."""
    user_id: int
    items: List[InvoiceItemCreate]
    due_date: date
    notes: Optional[str] = None
    billing_country: str
    currency: str = "USD"
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Template Schema
class InvoiceTemplateBase(BaseModel):
    """Base schema for invoice template data."""
    name: str = Field(..., description="Template name")
    header: str = Field(..., description="Header content")
    footer: Optional[str] = Field(None, description="Footer content")
    logo_url: Optional[str] = Field(None, description="URL to company logo")
    theme_color: Optional[str] = Field("#000000", description="Primary theme color (hex)")
    is_default: bool = Field(False, description="Whether this is the default template")
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Template Creation Schema
class InvoiceTemplateCreate(InvoiceTemplateBase):
    """Schema for creating a new invoice template."""
    pass


# Invoice Template Update Schema
class InvoiceTemplateUpdate(BaseModel):
    """Schema for updating an invoice template."""
    name: Optional[str] = None
    header: Optional[str] = None
    footer: Optional[str] = None
    logo_url: Optional[str] = None
    theme_color: Optional[str] = None
    is_default: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


# Invoice Template Response Schema
class InvoiceTemplateResponse(InvoiceTemplateBase):
    """Schema for invoice template response data."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Credit Note Schemas
class CreditNoteBase(BaseModel):
    """Base schema for credit note data."""
    invoice_id: int = Field(..., description="ID of the related invoice")
    amount: Decimal = Field(..., description="Credit amount")
    reason: str = Field(..., description="Reason for issuing credit")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_by: int = Field(..., description="ID of the user who created this")
    
    model_config = ConfigDict(from_attributes=True)


class CreditNoteCreate(CreditNoteBase):
    """Schema for creating a new credit note."""
    pass


class CreditNoteUpdate(BaseModel):
    """Schema for updating a credit note."""
    amount: Optional[Decimal] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class CreditNoteResponse(CreditNoteBase):
    """Schema for credit note response data."""
    id: int
    issued_date: datetime
    status: str
    voided_date: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Payment Reminder Schemas
class PaymentReminderBase(BaseModel):
    """Base schema for payment reminder data."""
    invoice_id: int = Field(..., description="ID of the invoice")
    reminder_date: datetime = Field(..., description="Date when reminder should be sent")
    message: str = Field(..., description="Reminder message content")
    is_sent: bool = Field(False, description="Whether the reminder has been sent")
    
    model_config = ConfigDict(from_attributes=True)


class PaymentReminderCreate(PaymentReminderBase):
    """Schema for creating a new payment reminder."""
    pass


class PaymentReminderUpdate(BaseModel):
    """Schema for updating a payment reminder."""
    reminder_date: Optional[datetime] = None
    message: Optional[str] = None
    is_sent: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


class PaymentReminderResponse(PaymentReminderBase):
    """Schema for payment reminder response data."""
    id: int
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# For backward compatibility
InvoiceSchema = InvoiceResponse
InvoiceItemSchema = InvoiceItemCreate
InvoiceTemplateSchema = InvoiceTemplateResponse
CreditNoteSchema = CreditNoteResponse
PaymentReminderSchema = PaymentReminderResponse
InvoiceCreateSchema = InvoiceCreate
InvoiceResponseSchema = InvoiceResponse
InvoiceDetailResponseSchema = InvoiceDetailResponse
InvoiceDetailsResponseSchema = InvoiceDetailsResponse
OverdueInvoiceResponseSchema = OverdueInvoiceResponse
CreditNoteDetailSchema = CreditNoteCreate
