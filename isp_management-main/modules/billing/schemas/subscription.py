from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from modules.billing.models import BillingCycle, SubscriptionStatus


class RecurringBillingProfileBase(BaseModel):
    """Base model for recurring billing profile data."""
    name: str
    billing_cycle: BillingCycle
    amount: Decimal
    currency: str = "USD"
    is_active: bool = True
    auto_renew: bool = True
    grace_period_days: Optional[int] = 0


class RecurringBillingProfileCreate(RecurringBillingProfileBase):
    """Model for creating a new recurring billing profile."""
    user_id: int
    next_billing_date: datetime


class RecurringBillingProfileUpdate(BaseModel):
    """Model for updating a recurring billing profile."""
    name: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    next_billing_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    auto_renew: Optional[bool] = None
    grace_period_days: Optional[int] = None


class RecurringBillingProfileResponse(RecurringBillingProfileBase):
    """Response model for recurring billing profile."""
    id: int
    user_id: int
    next_billing_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionBase(BaseModel):
    """Base model for subscription data."""
    plan_id: int
    status: Optional[SubscriptionStatus] = SubscriptionStatus.ACTIVE
    billing_cycle: Optional[BillingCycle] = BillingCycle.MONTHLY
    auto_renew: Optional[bool] = True


class SubscriptionCreate(SubscriptionBase):
    """Model for creating a new subscription."""
    user_id: int
    start_date: Optional[datetime] = None
    trial_days: Optional[int] = None
    billing_profile_id: Optional[int] = None
    create_billing_profile: Optional[bool] = False
    currency: Optional[str] = "USD"


class SubscriptionUpdate(BaseModel):
    """Model for updating a subscription."""
    plan_id: Optional[int] = None
    status: Optional[SubscriptionStatus] = None
    billing_cycle: Optional[BillingCycle] = None
    auto_renew: Optional[bool] = None
    current_period_end: Optional[datetime] = None
    billing_profile_id: Optional[int] = None


class SubscriptionResponse(SubscriptionBase):
    """Response model for subscription."""
    id: int
    user_id: int
    start_date: datetime
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    pause_start: Optional[datetime] = None
    pause_end: Optional[datetime] = None
    billing_profile_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UsageRecordBase(BaseModel):
    """Base model for usage record data."""
    quantity: float
    unit: str = "unit"
    source: Optional[str] = None


class UsageRecordCreate(UsageRecordBase):
    """Model for creating a new usage record."""
    subscription_id: int
    timestamp: Optional[datetime] = None


class UsageRecordResponse(UsageRecordBase):
    """Response model for usage record."""
    id: int
    subscription_id: int
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionStatistics(BaseModel):
    """Statistics about subscriptions."""
    total_active: int
    total_trial: int
    total_cancelled: int
    total_paused: int
    monthly_recurring_revenue: float
    annual_recurring_revenue: float
    average_subscription_age_days: float


class SubscriptionPlanChange(BaseModel):
    """Model for changing a subscription plan."""
    new_plan_id: int
    prorate: bool = True
