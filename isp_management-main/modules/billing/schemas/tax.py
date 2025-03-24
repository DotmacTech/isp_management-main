from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TaxRateBase(BaseModel):
    """Base model for tax rate data."""
    name: str
    description: Optional[str] = None
    rate: Decimal
    country: str
    region: Optional[str] = None
    is_default: bool = False


class TaxRateCreate(TaxRateBase):
    """Model for creating a new tax rate."""
    pass


class TaxRateUpdate(BaseModel):
    """Model for updating a tax rate."""
    name: Optional[str] = None
    description: Optional[str] = None
    rate: Optional[Decimal] = None
    country: Optional[str] = None
    region: Optional[str] = None
    is_default: Optional[bool] = None


class TaxRateResponse(TaxRateBase):
    """Response model for tax rate."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaxExemptionBase(BaseModel):
    """Base model for tax exemption data."""
    tax_rate_id: int
    exemption_certificate: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class TaxExemptionCreate(TaxExemptionBase):
    """Model for creating a new tax exemption."""
    user_id: int


class TaxExemptionResponse(TaxExemptionBase):
    """Response model for tax exemption."""
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxCalculationRequest(BaseModel):
    """Request model for tax calculation."""
    amount: Decimal
    country: str
    region: Optional[str] = None
    user_id: Optional[int] = None


class TaxDetail(BaseModel):
    """Detail of a tax calculation."""
    tax_rate_id: int
    name: str
    rate: Decimal
    amount: Decimal


class TaxCalculationResponse(BaseModel):
    """Response model for tax calculation."""
    taxable_amount: Decimal
    total_tax: Decimal
    tax_details: List[TaxDetail]
    country: str
    region: Optional[str] = None
