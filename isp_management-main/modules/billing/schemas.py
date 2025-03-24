"""
Billing module schemas.

This module defines the Pydantic schemas for billing operations.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

# Import from the properly structured package
from modules.billing.api.schemas import (
    SubscriptionBase, SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate,
    SubscriptionPeriod, SubscriptionStatus, MonthlyReportRequestSchema
)

# Add alias for MonthlyReportRequestSchema
MonthlyReportRequest = MonthlyReportRequestSchema

class InvoiceBase(BaseModel):
    """Base schema for invoice data."""
    user_id: int = Field(..., description="User ID the invoice belongs to")
    amount: Decimal = Field(..., description="Total invoice amount")
    due_date: datetime = Field(..., description="Due date for payment")
    description: str = Field(..., description="Invoice description")
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(InvoiceBase):
    """Schema for creating a new invoice."""
    pass


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response data."""
    id: int = Field(..., description="Unique identifier for the invoice")
    status: str = Field(..., description="Payment status (paid, unpaid, cancelled)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class OverdueInvoiceResponse(InvoiceResponse):
    """Schema for overdue invoice response data."""
    days_overdue: int = Field(..., description="Number of days the invoice is overdue")
    
    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    """Base schema for payment data."""
    invoice_id: int = Field(..., description="ID of the invoice being paid")
    amount: Decimal = Field(..., description="Payment amount")
    payment_method: str = Field(..., description="Payment method used")
    
    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(PaymentBase):
    """Schema for creating a new payment."""
    pass


class PaymentResponse(PaymentBase):
    """Schema for payment response data."""
    id: int = Field(..., description="Unique identifier for the payment")
    status: str = Field(..., description="Payment status (processed, pending, failed)")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Re-export the schemas
__all__ = [
    'InvoiceBase', 'InvoiceCreate', 'InvoiceResponse',
    'PaymentCreate', 'PaymentResponse',
    'SubscriptionBase', 'SubscriptionCreate', 'SubscriptionResponse', 'SubscriptionUpdate',
    'SubscriptionPeriod', 'SubscriptionStatus',
    'OverdueInvoiceResponse',
    'MonthlyReportRequest'
]
