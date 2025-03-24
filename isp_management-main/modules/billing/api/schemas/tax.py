"""
Tax schemas for the billing module.

This module provides Pydantic models for tax-related operations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class TaxType(str, Enum):
    """Types of taxes applied to invoices."""
    VALUE_ADDED = "value_added"
    SALES = "sales"
    GOODS_AND_SERVICES = "goods_and_services"
    CONSUMPTION = "consumption"
    EXCISE = "excise"
    CUSTOM = "custom"


class TaxStatus(str, Enum):
    """Status of a tax rule."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ARCHIVED = "archived"


class TaxDetail(BaseModel):
    """Detailed tax information for a specific line item or invoice."""
    tax_rate_id: int = Field(..., description="ID of the tax rate applied")
    name: str = Field(..., description="Name of the tax")
    rate: Decimal = Field(..., description="Tax rate as decimal", ge=0, le=1)
    amount: Decimal = Field(..., description="Calculated tax amount")
    
    model_config = ConfigDict(from_attributes=True)


class TaxRateBase(BaseModel):
    """Base schema for tax rate data."""
    name: str = Field(..., description="Tax name")
    description: Optional[str] = Field(None, description="Tax description")
    rate: Decimal = Field(..., description="Tax rate as decimal", ge=0, le=1)
    type: TaxType = Field(..., description="Type of tax")
    country_code: str = Field(..., description="Country code (ISO)")
    region_code: Optional[str] = Field(None, description="Region/State/Province code")
    is_default: bool = Field(False, description="Whether this is the default tax rate")
    
    model_config = ConfigDict(from_attributes=True)


class TaxRateCreate(TaxRateBase):
    """Schema for creating a new tax rate."""
    pass


class TaxRateUpdate(BaseModel):
    """Schema for updating a tax rate."""
    name: Optional[str] = Field(None, description="Tax name")
    description: Optional[str] = Field(None, description="Tax description")
    rate: Optional[Decimal] = Field(None, description="Tax rate as decimal", ge=0, le=1)
    type: Optional[TaxType] = Field(None, description="Type of tax")
    country_code: Optional[str] = Field(None, description="Country code (ISO)")
    region_code: Optional[str] = Field(None, description="Region/State/Province code")
    is_default: Optional[bool] = Field(None, description="Whether this is the default tax rate")
    status: Optional[TaxStatus] = Field(None, description="Status of the tax rate")
    
    model_config = ConfigDict(from_attributes=True)


class TaxRateResponse(TaxRateBase):
    """Schema for tax rate response data."""
    id: int = Field(..., description="Unique identifier for the tax rate")
    status: TaxStatus = Field(..., description="Status of the tax rate")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class TaxExemptionBase(BaseModel):
    """Base schema for tax exemption data."""
    user_id: int = Field(..., description="User ID this exemption belongs to")
    tax_id: int = Field(..., description="Tax ID this exemption applies to")
    exemption_number: str = Field(..., description="Tax exemption certificate number")
    expiration_date: Optional[datetime] = Field(None, description="Expiration date of exemption")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    model_config = ConfigDict(from_attributes=True)


class TaxExemptionCreate(TaxExemptionBase):
    """Schema for creating a new tax exemption."""
    pass


class TaxExemptionResponse(TaxExemptionBase):
    """Schema for tax exemption response data."""
    id: int = Field(..., description="Unique identifier for the exemption")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class TaxCalculationRequest(BaseModel):
    """Schema for tax calculation request."""
    user_id: int = Field(..., description="User ID for tax calculation")
    country_code: str = Field(..., description="Country code (ISO)")
    region_code: Optional[str] = Field(None, description="Region/State/Province code")
    total_amount: Decimal = Field(..., description="Total amount before tax")
    items: List[dict] = Field([], description="Line items for detailed tax calculation")
    
    model_config = ConfigDict(from_attributes=True)


class TaxCalculationResponse(BaseModel):
    """Schema for tax calculation response."""
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    tax_amount: Decimal = Field(..., description="Total tax amount")
    total: Decimal = Field(..., description="Total including tax")
    tax_details: List[TaxDetail] = Field([], description="Detailed breakdown of taxes")
    
    model_config = ConfigDict(from_attributes=True)


# Backward compatibility aliases with Schema suffix
TaxRateCreateSchema = TaxRateCreate
TaxRateUpdateSchema = TaxRateUpdate
TaxRateResponseSchema = TaxRateResponse
TaxExemptionCreateSchema = TaxExemptionCreate
TaxExemptionResponseSchema = TaxExemptionResponse
TaxCalculationRequestSchema = TaxCalculationRequest
TaxCalculationResponseSchema = TaxCalculationResponse
TaxDetailSchema = TaxDetail
