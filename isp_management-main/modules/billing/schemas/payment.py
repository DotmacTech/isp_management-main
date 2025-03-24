"""
Payment schemas for the billing module.

This module contains Pydantic schema models for payments, payment transactions, and refunds.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict

from modules.billing.models import (
    PaymentMethod,
    PaymentStatus,
)


class PaymentBase(BaseModel):
    """Base schema for payment operations."""
    payment_reference: Optional[str] = Field(None, description="Unique payment reference number")
    invoice_id: int = Field(..., description="ID of the invoice being paid")
    user_id: int = Field(..., description="ID of the user making the payment")
    amount: Decimal = Field(..., description="Payment amount", ge=0)
    payment_method: PaymentMethod = Field(..., description="Method of payment")
    notes: Optional[str] = Field(None, description="Additional notes about the payment")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "payment_reference": "PAY-20230715-001",
                "invoice_id": 123,
                "user_id": 456,
                "amount": "150.75",
                "payment_method": "credit_card",
                "notes": "Payment for July services"
            }
        }
    )


class PaymentCreate(PaymentBase):
    """Schema for creating a new payment."""
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway: Optional[str] = Field(None, description="Payment gateway used")
    gateway_response: Optional[Dict[str, Any]] = Field(None, description="Response from payment gateway")


class PaymentUpdate(BaseModel):
    """Schema for updating an existing payment."""
    status: Optional[PaymentStatus] = Field(None, description="Updated payment status")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway_response: Optional[Dict[str, Any]] = Field(None, description="Response from payment gateway")
    notes: Optional[str] = Field(None, description="Additional notes about the payment")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "completed",
                "transaction_id": "txn_12345abcde",
                "notes": "Payment confirmed by gateway"
            }
        }
    )


class PaymentResponse(PaymentBase):
    """Schema for payment response."""
    id: int = Field(..., description="Payment ID")
    status: PaymentStatus = Field(..., description="Payment status")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway: Optional[str] = Field(None, description="Payment gateway used")
    payment_date: datetime = Field(..., description="Date and time of payment")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PaymentMethodStats(BaseModel):
    """Statistics for a specific payment method."""
    payment_method: str = Field(..., description="Payment method name")
    count: int = Field(..., description="Number of payments using this method")
    total_amount: Decimal = Field(..., description="Total amount of payments using this method")
    percentage: float = Field(..., description="Percentage of all payments using this method")
    average_payment: Decimal = Field(..., description="Average payment amount for this method")
    success_rate: float = Field(..., description="Percentage of successful payments using this method")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "payment_method": "credit_card",
                "count": 150,
                "total_amount": "25000.75",
                "percentage": 62.5,
                "average_payment": "166.67",
                "success_rate": 98.2
            }
        }
    )


class PaymentMethodsStatsResponse(BaseModel):
    """Response schema for payment methods statistics."""
    time_period: str = Field(..., description="Time period for the statistics")
    total_payments: int = Field(..., description="Total number of payments in the period")
    total_amount: Decimal = Field(..., description="Total amount of all payments")
    methods: List[PaymentMethodStats] = Field(..., description="Statistics for each payment method")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "time_period": "2023-01-01 to 2023-03-31",
                "total_payments": 240,
                "total_amount": "40000.00",
                "methods": [
                    {
                        "payment_method": "credit_card",
                        "count": 150,
                        "total_amount": "25000.75",
                        "percentage": 62.5,
                        "average_payment": "166.67",
                        "success_rate": 98.2
                    },
                    {
                        "payment_method": "bank_transfer",
                        "count": 90,
                        "total_amount": "15000.25",
                        "percentage": 37.5,
                        "average_payment": "166.67",
                        "success_rate": 99.1
                    }
                ]
            }
        }
    )


class PaymentTransactionBase(BaseModel):
    """Base schema for payment transaction operations."""
    payment_id: int = Field(..., description="ID of the associated payment")
    transaction_type: str = Field(..., description="Type of transaction")
    amount: Decimal = Field(..., description="Transaction amount", ge=0)
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "payment_id": 123,
                "transaction_type": "authorization",
                "amount": "150.75"
            }
        }
    )


class PaymentTransactionCreate(PaymentTransactionBase):
    """Schema for creating a new payment transaction."""
    status: str = Field("pending", description="Transaction status")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway: Optional[str] = Field(None, description="Payment gateway used")
    gateway_response: Optional[Dict[str, Any]] = Field(None, description="Response from payment gateway")
    error_message: Optional[str] = Field(None, description="Error message if transaction failed")


class PaymentTransactionUpdate(BaseModel):
    """Schema for updating an existing payment transaction."""
    status: Optional[str] = Field(None, description="Updated transaction status")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway_response: Optional[Dict[str, Any]] = Field(None, description="Response from payment gateway")
    error_message: Optional[str] = Field(None, description="Error message if transaction failed")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "transaction_id": "txn_12345abcde"
            }
        }
    )


class PaymentTransactionResponse(PaymentTransactionBase):
    """Schema for payment transaction response."""
    id: int = Field(..., description="Transaction ID")
    status: str = Field(..., description="Transaction status")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway: Optional[str] = Field(None, description="Payment gateway used")
    error_message: Optional[str] = Field(None, description="Error message if transaction failed")
    processor_response_code: Optional[str] = Field(None, description="Response code from payment processor")
    transaction_date: datetime = Field(..., description="Date and time of transaction")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class RefundBase(BaseModel):
    """Base schema for refund operations."""
    payment_id: int = Field(..., description="ID of the payment to refund")
    credit_note_id: Optional[int] = Field(None, description="ID of the associated credit note if any")
    amount: Decimal = Field(..., description="Refund amount", ge=0)
    refund_method: str = Field(..., description="Method used for the refund")
    reason: Optional[str] = Field(None, description="Reason for the refund")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "payment_id": 123,
                "amount": "50.25",
                "refund_method": "original_payment",
                "reason": "Service cancellation"
            }
        }
    )


class RefundCreate(RefundBase):
    """Schema for creating a new refund."""
    refund_reference: Optional[str] = Field(None, description="Unique refund reference number")
    notes: Optional[str] = Field(None, description="Additional notes about the refund")
    processed_by_user_id: Optional[int] = Field(None, description="ID of the user processing the refund")


class RefundUpdate(BaseModel):
    """Schema for updating an existing refund."""
    status: Optional[str] = Field(None, description="Updated refund status")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway_response: Optional[Dict[str, Any]] = Field(None, description="Response from payment gateway")
    notes: Optional[str] = Field(None, description="Additional notes about the refund")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "completed",
                "transaction_id": "ref_12345abcde",
                "notes": "Refund processed successfully"
            }
        }
    )


class RefundResponse(RefundBase):
    """Schema for refund response."""
    id: int = Field(..., description="Refund ID")
    refund_reference: str = Field(..., description="Unique refund reference number")
    status: str = Field(..., description="Refund status")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    gateway: Optional[str] = Field(None, description="Payment gateway used")
    refund_date: datetime = Field(..., description="Date and time of refund")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    notes: Optional[str] = Field(None, description="Additional notes about the refund")


class PaymentGatewayConfigBase(BaseModel):
    """Base schema for payment gateway configuration."""
    name: str = Field(..., description="Name of the payment gateway configuration")
    gateway_type: str = Field(..., description="Type of payment gateway")
    is_active: bool = Field(True, description="Whether the gateway is active")
    is_default: bool = Field(False, description="Whether this is the default gateway")
    environment: str = Field("sandbox", description="Environment (sandbox or production)")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "Stripe Production",
                "gateway_type": "stripe",
                "is_active": True,
                "is_default": True,
                "environment": "production"
            }
        }
    )


class PaymentGatewayConfigCreate(PaymentGatewayConfigBase):
    """Schema for creating a new payment gateway configuration."""
    credentials: Dict[str, str] = Field(..., description="Credentials for gateway authentication")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Additional configuration parameters")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for gateway callbacks")
    webhook_secret: Optional[str] = Field(None, description="Secret for webhook verification")
    tenant_id: Optional[int] = Field(None, description="ID of the tenant if not global")
    is_global: bool = Field(False, description="Whether this configuration is global")
    description: Optional[str] = Field(None, description="Description of the payment gateway configuration")


class PaymentGatewayConfigUpdate(BaseModel):
    """Schema for updating an existing payment gateway configuration."""
    name: Optional[str] = Field(None, description="Name of the payment gateway configuration")
    is_active: Optional[bool] = Field(None, description="Whether the gateway is active")
    is_default: Optional[bool] = Field(None, description="Whether this is the default gateway")
    credentials: Optional[Dict[str, str]] = Field(None, description="Credentials for gateway authentication")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Additional configuration parameters")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for gateway callbacks")
    webhook_secret: Optional[str] = Field(None, description="Secret for webhook verification")
    description: Optional[str] = Field(None, description="Description of the payment gateway configuration")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Stripe Production Updated",
                "is_active": True,
                "is_default": True
            }
        }
    )


class PaymentGatewayConfigResponse(PaymentGatewayConfigBase):
    """Schema for payment gateway configuration response."""
    id: int = Field(..., description="Configuration ID")
    credentials: Dict[str, str] = Field(..., description="Credentials for gateway authentication")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Additional configuration parameters")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for gateway callbacks")
    tenant_id: Optional[int] = Field(None, description="ID of the tenant if not global")
    is_global: bool = Field(..., description="Whether this configuration is global")
    description: Optional[str] = Field(None, description="Description of the payment gateway configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
