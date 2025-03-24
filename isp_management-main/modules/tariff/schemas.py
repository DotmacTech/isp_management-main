from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict

class TariffPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    billing_cycle: str = "monthly"  # monthly, quarterly, yearly
    download_speed: int  # in kbps
    upload_speed: int    # in kbps
    data_cap: Optional[int] = None  # in bytes, None means unlimited
    fup_threshold: Optional[int] = None  # in bytes, threshold for Fair Usage Policy
    throttle_speed_download: Optional[int] = None  # in kbps after FUP
    throttle_speed_upload: Optional[int] = None    # in kbps after FUP
    time_restrictions: Optional[Dict[str, Any]] = None  # JSON for time-based restrictions
    features: Optional[Dict[str, Any]] = None  # JSON for additional features
    radius_policy_id: Optional[int] = None
    throttled_radius_policy_id: Optional[int] = None
    is_active: bool = True

    @field_validator('billing_cycle')
    @classmethod
    def validate_billing_cycle(cls, v):
        if v not in ["monthly", "quarterly", "yearly"]:
            raise ValueError('billing_cycle must be one of: monthly, quarterly, yearly')
        return v


class TariffPlanCreate(TariffPlanBase):
    pass


class TariffPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    billing_cycle: Optional[str] = None
    download_speed: Optional[int] = None
    upload_speed: Optional[int] = None
    data_cap: Optional[int] = None
    fup_threshold: Optional[int] = None
    throttle_speed_download: Optional[int] = None
    throttle_speed_upload: Optional[int] = None
    time_restrictions: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None
    radius_policy_id: Optional[int] = None
    throttled_radius_policy_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator('billing_cycle')
    @classmethod
    def validate_billing_cycle(cls, v):
        if v is not None and v not in ["monthly", "quarterly", "yearly"]:
            raise ValueError('billing_cycle must be one of: monthly, quarterly, yearly')
        return v


class TariffPlanResponse(TariffPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserTariffPlanBase(BaseModel):
    user_id: int
    tariff_plan_id: int
    status: str = "active"  # active, suspended, cancelled
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None


class UserTariffPlanCreate(UserTariffPlanBase):
    pass


class UserTariffPlanUpdate(BaseModel):
    status: Optional[str] = None
    end_date: Optional[datetime] = None
    data_used: Optional[int] = None
    is_throttled: Optional[bool] = None
    throttled_at: Optional[datetime] = None


class UserTariffPlanResponse(UserTariffPlanBase):
    id: int
    current_cycle_start: datetime
    current_cycle_end: Optional[datetime]
    data_used: int
    is_throttled: bool
    throttled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUsageRecordBase(BaseModel):
    user_tariff_plan_id: int
    download_bytes: int = 0
    upload_bytes: int = 0
    total_bytes: int = 0
    source: str  # radius, netflow, etc.
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserUsageRecordCreate(UserUsageRecordBase):
    pass


class UserUsageRecordResponse(UserUsageRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TariffPolicyActionBase(BaseModel):
    tariff_plan_id: int
    trigger_type: str  # data_cap, fup, time_restriction
    threshold_value: Optional[int] = None
    action_type: str  # notify, throttle, block, charge
    action_params: Optional[Dict[str, Any]] = None
    notification_template_id: Optional[int] = None
    is_active: bool = True


class TariffPolicyActionCreate(TariffPolicyActionBase):
    pass


class TariffPolicyActionUpdate(BaseModel):
    trigger_type: Optional[str] = None
    threshold_value: Optional[int] = None
    action_type: Optional[str] = None
    action_params: Optional[Dict[str, Any]] = None
    notification_template_id: Optional[int] = None
    is_active: Optional[bool] = None


class TariffPolicyActionResponse(TariffPolicyActionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TariffPlanChangeBase(BaseModel):
    user_id: int
    new_plan_id: int
    previous_plan_id: Optional[int] = None
    change_type: str  # upgrade, downgrade, initial
    effective_date: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None


class TariffPlanChangeCreate(TariffPlanChangeBase):
    pass


class TariffPlanChangeUpdate(BaseModel):
    status: Optional[str] = None
    processed_at: Optional[datetime] = None
    prorated_credit: Optional[Decimal] = None
    prorated_charge: Optional[Decimal] = None
    notes: Optional[str] = None


class TariffPlanChangeResponse(TariffPlanChangeBase):
    id: int
    requested_at: datetime
    status: str
    processed_at: Optional[datetime]
    prorated_credit: Optional[Decimal]
    prorated_charge: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationTemplateBase(BaseModel):
    name: str
    subject: str
    body: str
    template_type: str  # email, sms, in-app
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    template_type: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsageCheckRequest(BaseModel):
    user_id: int
    session_id: Optional[str] = None
    download_bytes: int = 0
    upload_bytes: int = 0


class UsageCheckResponse(BaseModel):
    user_id: int
    tariff_plan_id: int
    plan_name: str
    status: str  # ok, throttled, blocked
    current_usage: int  # in bytes
    data_cap: Optional[int] = None  # in bytes
    percentage_used: float
    actions_triggered: List[Dict[str, Any]] = []
    message: Optional[str] = None


class BandwidthPolicyResponse(BaseModel):
    user_id: int
    download_speed: int  # in kbps
    upload_speed: int    # in kbps
    is_throttled: bool
    session_timeout: Optional[int] = None  # in seconds
    additional_attributes: Optional[Dict[str, Any]] = None
