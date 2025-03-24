"""
Discount schemas for the billing module.

This module provides Pydantic models for discount-related operations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator


class DiscountType(str, Enum):
    """Types of discounts that can be applied."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_MONTHS = "free_months"
    SIGNUP_CREDIT = "signup_credit"
    REFERRAL = "referral"
    LOYALTY = "loyalty"
    PROMOTIONAL = "promotional"
    CUSTOM = "custom"


class DiscountStatus(str, Enum):
    """Status of a discount."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    PENDING = "pending"
    USED = "used"
    ARCHIVED = "archived"


class DiscountBase(BaseModel):
    """Base schema for discount data."""
    name: str = Field(..., description="Discount name")
    description: Optional[str] = Field(None, description="Discount description")
    discount_type: DiscountType = Field(..., description="Type of discount")
    value: Decimal = Field(..., description="Discount value (percentage or fixed amount)")
    max_uses: Optional[int] = Field(None, description="Maximum number of times this discount can be used")
    valid_from: Optional[datetime] = Field(None, description="Start date of validity")
    valid_until: Optional[datetime] = Field(None, description="End date of validity")
    min_order_value: Optional[Decimal] = Field(None, description="Minimum order value for discount to apply")
    max_discount_amount: Optional[Decimal] = Field(None, description="Maximum discount amount (for percentage discounts)")
    is_stackable: bool = Field(False, description="Whether this discount can be combined with others")
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator('value')
    def validate_value(cls, value, info):
        """Validate discount value based on type."""
        discount_type = info.data.get('discount_type')
        if discount_type == DiscountType.PERCENTAGE and (value <= 0 or value > 100):
            raise ValueError('Percentage discount must be between 0 and 100')
        if discount_type != DiscountType.PERCENTAGE and value <= 0:
            raise ValueError('Fixed amount discount must be greater than 0')
        return value


class DiscountCreate(DiscountBase):
    """Schema for creating a new discount."""
    code: str = Field(..., description="Unique discount code")


class DiscountUpdate(BaseModel):
    """Schema for updating a discount."""
    name: Optional[str] = Field(None, description="Discount name")
    description: Optional[str] = Field(None, description="Discount description")
    discount_type: Optional[DiscountType] = Field(None, description="Type of discount")
    value: Optional[Decimal] = Field(None, description="Discount value (percentage or fixed amount)")
    code: Optional[str] = Field(None, description="Unique discount code")
    max_uses: Optional[int] = Field(None, description="Maximum number of times this discount can be used")
    valid_from: Optional[datetime] = Field(None, description="Start date of validity")
    valid_until: Optional[datetime] = Field(None, description="End date of validity")
    min_order_value: Optional[Decimal] = Field(None, description="Minimum order value for discount to apply")
    max_discount_amount: Optional[Decimal] = Field(None, description="Maximum discount amount (for percentage discounts)")
    is_stackable: Optional[bool] = Field(None, description="Whether this discount can be combined with others")
    status: Optional[DiscountStatus] = Field(None, description="Status of the discount")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountResponse(DiscountBase):
    """Schema for discount response data."""
    id: int = Field(..., description="Unique identifier for the discount")
    code: str = Field(..., description="Unique discount code")
    status: DiscountStatus = Field(..., description="Status of the discount")
    uses_count: int = Field(0, description="Number of times this discount has been used")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountUsageBase(BaseModel):
    """Base schema for discount usage data."""
    discount_id: int = Field(..., description="Discount ID")
    user_id: int = Field(..., description="User ID")
    invoice_id: Optional[int] = Field(None, description="Invoice ID where discount was applied")
    applied_amount: Decimal = Field(..., description="Amount of discount applied")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountUsageCreate(DiscountUsageBase):
    """Schema for creating a discount usage record."""
    pass


class DiscountUsageResponse(DiscountUsageBase):
    """Schema for discount usage response data."""
    id: int = Field(..., description="Unique identifier for the usage record")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountValidationRequest(BaseModel):
    """Schema for discount validation request."""
    code: str = Field(..., description="Discount code to validate")
    user_id: int = Field(..., description="User ID attempting to use discount")
    order_amount: Decimal = Field(..., description="Order amount before discount")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountValidationResponse(BaseModel):
    """Schema for discount validation response."""
    is_valid: bool = Field(..., description="Whether discount is valid")
    discount_id: Optional[int] = Field(None, description="Discount ID if valid")
    discount_amount: Optional[Decimal] = Field(None, description="Calculated discount amount")
    reason: Optional[str] = Field(None, description="Reason if discount is invalid")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountCalculationRequest(BaseModel):
    """Schema for discount calculation request."""
    discount_id: int = Field(..., description="Discount ID")
    order_amount: Decimal = Field(..., description="Order amount before discount")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountCalculationResponse(BaseModel):
    """Schema for discount calculation response."""
    discount_amount: Decimal = Field(..., description="Calculated discount amount")
    final_amount: Decimal = Field(..., description="Final amount after discount")
    
    model_config = ConfigDict(from_attributes=True)


class DiscountDetail(BaseModel):
    """Detailed discount information for invoice."""
    id: int = Field(..., description="Discount ID")
    name: str = Field(..., description="Discount name")
    code: str = Field(..., description="Discount code")
    discount_type: DiscountType = Field(..., description="Type of discount")
    value: Decimal = Field(..., description="Original discount value")
    applied_amount: Decimal = Field(..., description="Amount of discount applied")
    
    model_config = ConfigDict(from_attributes=True)

# Backward compatibility aliases with Schema suffix
DiscountCreateSchema = DiscountCreate
DiscountUpdateSchema = DiscountUpdate
DiscountResponseSchema = DiscountResponse
DiscountUsageCreateSchema = DiscountUsageCreate
DiscountUsageResponseSchema = DiscountUsageResponse
DiscountValidationRequestSchema = DiscountValidationRequest
DiscountValidationResponseSchema = DiscountValidationResponse
DiscountCalculationRequestSchema = DiscountCalculationRequest
DiscountCalculationResponseSchema = DiscountCalculationResponse
DiscountDetailSchema = DiscountDetail
