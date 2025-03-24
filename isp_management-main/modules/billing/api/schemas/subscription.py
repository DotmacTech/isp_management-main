from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class SubscriptionPeriod(str, Enum):
    """Enum for subscription periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    """Enum for subscription status."""
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"


class SubscriptionBase(BaseModel):
    """Base schema for subscriptions."""
    user_id: int = Field(..., description="User ID this subscription belongs to")
    service_id: int = Field(..., description="Service ID this subscription is for")
    period: SubscriptionPeriod = Field(..., description="Subscription period")
    auto_renew: bool = Field(True, description="Whether to auto-renew the subscription")
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription."""
    start_date: datetime = Field(..., description="Subscription start date")
    price: Decimal = Field(..., description="Price per period", gt=0)
    
    model_config = ConfigDict(from_attributes=True)


# Create an alias for backward compatibility
SubscriptionCreateSchema = SubscriptionCreate


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    service_id: Optional[int] = Field(None, description="Service ID this subscription is for")
    period: Optional[SubscriptionPeriod] = Field(None, description="Subscription period")
    auto_renew: Optional[bool] = Field(None, description="Whether to auto-renew the subscription")
    price: Optional[Decimal] = Field(None, description="Price per period", gt=0)
    status: Optional[SubscriptionStatus] = Field(None, description="Subscription status")
    
    model_config = ConfigDict(from_attributes=True)


# Create an alias for backward compatibility
SubscriptionUpdateSchema = SubscriptionUpdate


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription response data."""
    id: int = Field(..., description="Unique identifier for the subscription")
    status: SubscriptionStatus = Field(..., description="Current status")
    start_date: datetime = Field(..., description="When the subscription started")
    end_date: Optional[datetime] = Field(None, description="When the subscription ends/ended")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    next_billing_date: datetime = Field(..., description="Next billing date")
    price: Decimal = Field(..., description="Current price per period")
    
    model_config = ConfigDict(from_attributes=True)


# Create an alias for backward compatibility
SubscriptionResponseSchema = SubscriptionResponse


class SubscriptionHistoryEntry(BaseModel):
    """Schema for subscription history entry."""
    id: int = Field(..., description="History entry ID")
    subscription_id: int = Field(..., description="Subscription ID")
    previous_status: SubscriptionStatus = Field(..., description="Previous subscription status")
    new_status: SubscriptionStatus = Field(..., description="New subscription status")
    change_reason: str = Field(..., description="Reason for the status change")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionWithHistory(BaseModel):
    """Schema for subscription with history entries."""
    subscription: SubscriptionResponse
    history: List[SubscriptionHistoryEntry] = Field([], description="History of changes")
    
    model_config = ConfigDict(from_attributes=True)


# Recurring Billing Profile schemas
class RecurringBillingProfileBase(BaseModel):
    """Base schema for recurring billing profiles."""
    user_id: int = Field(..., description="User ID this profile belongs to")
    payment_method_id: int = Field(..., description="Payment method ID to use for billing")
    is_default: bool = Field(False, description="Whether this is the default profile")
    
    model_config = ConfigDict(from_attributes=True)


class RecurringBillingProfileCreate(RecurringBillingProfileBase):
    """Schema for creating a new recurring billing profile."""
    pass


# Create an alias for backward compatibility
RecurringBillingProfileCreateSchema = RecurringBillingProfileCreate


class RecurringBillingProfileResponse(RecurringBillingProfileBase):
    """Schema for recurring billing profile response data."""
    id: int = Field(..., description="Unique identifier for the profile")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Create an alias for backward compatibility
RecurringBillingProfileResponseSchema = RecurringBillingProfileResponse


# Usage Record schemas
class UsageRecordBase(BaseModel):
    """Base schema for usage records."""
    subscription_id: int = Field(..., description="Subscription ID this usage is for")
    quantity: int = Field(..., description="Usage quantity", gt=0)
    usage_date: datetime = Field(..., description="Date of usage")
    description: Optional[str] = Field(None, description="Usage description")
    
    model_config = ConfigDict(from_attributes=True)


class UsageRecordCreate(UsageRecordBase):
    """Schema for creating a new usage record."""
    pass


# Create an alias for backward compatibility
UsageRecordCreateSchema = UsageRecordCreate


class UsageRecordResponse(UsageRecordBase):
    """Schema for usage record response data."""
    id: int = Field(..., description="Unique identifier for the usage record")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# Create an alias for backward compatibility
UsageRecordResponseSchema = UsageRecordResponse


# Subscription Plan Change schema
class SubscriptionPlanChange(BaseModel):
    """Schema for changing subscription plan."""
    new_plan_id: int = Field(..., description="ID of the new plan")
    effective_date: datetime = Field(..., description="When the change should take effect")
    prorate: bool = Field(True, description="Whether to prorate charges for the billing period")
    
    model_config = ConfigDict(from_attributes=True)


# Create an alias for backward compatibility
SubscriptionPlanChangeSchema = SubscriptionPlanChange
