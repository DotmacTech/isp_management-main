from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from modules.billing.models import DiscountType, DiscountStatus


class DiscountBase(BaseModel):
    """Base model for discount data."""
    name: str
    description: Optional[str] = None
    discount_type: DiscountType
    amount: Decimal
    is_percentage: bool = True
    code: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    max_uses: Optional[int] = None
    max_uses_per_user: Optional[int] = None
    min_order_amount: Optional[Decimal] = None
    applicable_plans: Optional[str] = None


class DiscountCreate(DiscountBase):
    """Model for creating a new discount."""
    status: DiscountStatus = DiscountStatus.ACTIVE


class DiscountUpdate(BaseModel):
    """Model for updating a discount."""
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    amount: Optional[Decimal] = None
    is_percentage: Optional[bool] = None
    code: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    max_uses: Optional[int] = None
    max_uses_per_user: Optional[int] = None
    min_order_amount: Optional[Decimal] = None
    status: Optional[DiscountStatus] = None
    applicable_plans: Optional[str] = None


class DiscountResponse(DiscountBase):
    """Response model for discount."""
    id: int
    status: DiscountStatus
    times_used: Optional[int] = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiscountUsageBase(BaseModel):
    """Base model for discount usage data."""
    discount_id: int
    amount: Decimal
    user_id: Optional[int] = None
    invoice_id: Optional[int] = None


class DiscountUsageCreate(DiscountUsageBase):
    """Model for creating a new discount usage record."""
    pass


class DiscountUsageResponse(DiscountUsageBase):
    """Response model for discount usage."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountValidationRequest(BaseModel):
    """Request model for discount validation."""
    code: str
    user_id: Optional[int] = None
    amount: Optional[Decimal] = None
    plan_id: Optional[int] = None


class DiscountValidationResponse(BaseModel):
    """Response model for discount validation."""
    valid: bool
    reason: Optional[str] = None
    discount_id: Optional[int] = None
    discount_name: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    is_percentage: Optional[bool] = None


class DiscountCalculationRequest(BaseModel):
    """Request model for discount calculation."""
    discount_id: int
    base_amount: Decimal


class DiscountCalculationResponse(BaseModel):
    """Response model for discount calculation."""
    discount_id: int
    discount_name: str
    discount_code: Optional[str] = None
    base_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    is_percentage: bool
    percentage_or_amount: Decimal
