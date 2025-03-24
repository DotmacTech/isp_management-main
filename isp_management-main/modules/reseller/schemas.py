from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict

class ResellerStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"
    TERMINATED = "terminated"

class CommissionType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"

class ResellerTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

class ResellerBase(BaseModel):
    user_id: int
    company_name: str
    contact_person: str
    email: EmailStr
    phone: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    status: ResellerStatus = ResellerStatus.PENDING_APPROVAL
    tier: ResellerTier = ResellerTier.BRONZE
    commission_type: CommissionType = CommissionType.PERCENTAGE
    commission_rate: float = Field(ge=0, le=100)  # Percentage between 0 and 100
    credit_limit: float = 0.0
    notes: Optional[str] = None

    @field_validator('commission_rate')
    @classmethod
    def validate_commission_rate(cls, v, info):
        if 'commission_type' in info.data and info.data['commission_type'] == CommissionType.PERCENTAGE:
            if v < 0 or v > 100:
                raise ValueError('Commission rate must be between 0 and 100 for percentage type')
        return v

class ResellerCreate(ResellerBase):
    pass

class ResellerResponse(ResellerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    current_balance: float
    total_customers: int
    total_revenue: float
    
    model_config = ConfigDict(from_attributes=True)

class ResellerCustomerBase(BaseModel):
    reseller_id: int
    customer_id: int
    notes: Optional[str] = None

class ResellerCustomerCreate(ResellerCustomerBase):
    pass

class ResellerCustomerResponse(ResellerCustomerBase):
    id: int
    created_at: datetime
    customer_name: str
    customer_email: str
    
    model_config = ConfigDict(from_attributes=True)

class ResellerTransactionType(str, Enum):
    COMMISSION = "commission"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    WITHDRAWAL = "withdrawal"

class ResellerTransactionBase(BaseModel):
    reseller_id: int
    amount: float
    transaction_type: ResellerTransactionType
    description: str
    reference_id: Optional[str] = None  # e.g., invoice ID, payment ID

class ResellerTransactionCreate(ResellerTransactionBase):
    pass

class ResellerTransactionResponse(ResellerTransactionBase):
    id: int
    created_at: datetime
    balance_after: float
    
    model_config = ConfigDict(from_attributes=True)

class ResellerCommissionRuleBase(BaseModel):
    reseller_id: int
    tariff_plan_id: int
    commission_type: CommissionType
    commission_rate: float
    min_customers: Optional[int] = None  # For tiered commission
    max_customers: Optional[int] = None  # For tiered commission

class ResellerCommissionRuleCreate(ResellerCommissionRuleBase):
    pass

class ResellerCommissionRuleResponse(ResellerCommissionRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ResellerSearch(BaseModel):
    query: str
    status: Optional[ResellerStatus] = None
    tier: Optional[ResellerTier] = None
    limit: int = 10
    offset: int = 0

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    reseller: Dict[str, Any]

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ResellerProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None

class ResellerDashboardStats(BaseModel):
    total_customers: int
    active_customers: int
    total_revenue: float
    current_balance: float
    recent_transactions: List[Dict[str, Any]]
    commission_summary: Dict[str, Any]

class ResellerPasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class ResellerCustomerSummary(BaseModel):
    id: int
    name: str
    email: str
    status: str
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: datetime

class ResellerCustomerList(BaseModel):
    customers: List[ResellerCustomerSummary]
    total: int
    page: int
    page_size: int

class CommissionCalculationRequest(BaseModel):
    reseller_id: int
    start_date: datetime
    end_date: datetime
    include_details: bool = False

class CommissionCalculationResponse(BaseModel):
    reseller_id: int
    period_start: datetime
    period_end: datetime
    total_commission: float
    commission_by_plan: Dict[str, float]
    commission_details: Optional[List[Dict[str, Any]]] = None

class CommissionPaymentRequest(BaseModel):
    reseller_id: int
    amount: float
    payment_method: str
    payment_reference: Optional[str] = None
    notes: Optional[str] = None

class TierBenefits(BaseModel):
    tier: ResellerTier
    description: str
    commission_multiplier: float
    features: List[str]
    requirements: Dict[str, Any]

class ResellerHierarchyType(str, Enum):
    DIRECT = "direct"
    MASTER = "master"
    SUB_RESELLER = "sub_reseller"

class ResellerHierarchyCreate(BaseModel):
    parent_reseller_id: int
    child_reseller_id: int
    relationship_type: ResellerHierarchyType
    commission_share_percentage: float = Field(ge=0, le=100)
    notes: Optional[str] = None

class ResellerHierarchyResponse(ResellerHierarchyCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ResellerPortalSettings(BaseModel):
    dashboard_widgets: List[str]
    notification_preferences: Dict[str, bool]
    display_preferences: Dict[str, Any]

class ResellerNotificationType(str, Enum):
    COMMISSION_EARNED = "commission_earned"
    NEW_CUSTOMER = "new_customer"
    CUSTOMER_SUBSCRIPTION_CHANGED = "customer_subscription_changed"
    PAYMENT_RECEIVED = "payment_received"
    TIER_CHANGED = "tier_changed"
    SYSTEM_ANNOUNCEMENT = "system_announcement"

class ResellerNotification(BaseModel):
    id: int
    reseller_id: int
    notification_type: ResellerNotificationType
    title: str
    message: str
    is_read: bool = False
    created_at: datetime
    data: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)

class ResellerInvoice(BaseModel):
    id: int
    reseller_id: int
    amount: float
    status: str
    due_date: datetime
    created_at: datetime
    items: List[Dict[str, Any]]
    
    model_config = ConfigDict(from_attributes=True)

class ResellerCommissionRuleUpdate(BaseModel):
    commission_type: Optional[CommissionType] = None
    commission_rate: Optional[float] = None
    min_customers: Optional[int] = None
    max_customers: Optional[int] = None

class ResellerCommissionTracking(BaseModel):
    reseller_id: int
    commission_rule_id: int
    commission_amount: float
    commission_date: datetime
    description: str

class ResellerPortalSettingsUpdate(BaseModel):
    dashboard_widgets: Optional[List[str]] = None
    notification_preferences: Optional[Dict[str, bool]] = None
    display_preferences: Optional[Dict[str, Any]] = None

class ResellerNotificationUpdate(BaseModel):
    notification_type: Optional[ResellerNotificationType] = None
    title: Optional[str] = None
    message: Optional[str] = None
    is_read: Optional[bool] = None
