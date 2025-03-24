"""
Schemas for the reseller module.

This package contains schemas for the reseller module.
"""

from enum import Enum
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, EmailStr


class ResellerStatus(str, Enum):
    """Status of a reseller account."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    PENDING = "pending"


class ResellerTier(str, Enum):
    """Tier level of a reseller."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class CommissionType(str, Enum):
    """Type of commission calculation."""
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class ResellerBase(BaseModel):
    """Base schema for reseller data."""
    name: str = Field(..., description="Reseller company name")
    contact_person: str = Field(..., description="Name of primary contact person")
    email: EmailStr = Field(..., description="Primary email for contact")
    phone: str = Field(..., description="Contact phone number")
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/Zip code")
    tax_id: Optional[str] = Field(None, description="Tax ID or business registration number")
    tier: ResellerTier = Field(ResellerTier.BRONZE, description="Reseller tier level")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerCreate(ResellerBase):
    """Schema for creating a new reseller."""
    password: str = Field(..., description="Initial password for reseller account")


class ResellerResponse(ResellerBase):
    """Schema for reseller response data."""
    id: int = Field(..., description="Unique identifier for the reseller")
    status: ResellerStatus = Field(..., description="Status of reseller account")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    customer_count: int = Field(0, description="Number of customers managed by this reseller")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerProfileUpdate(BaseModel):
    """Schema for updating reseller profile data."""
    name: Optional[str] = Field(None, description="Reseller company name")
    contact_person: Optional[str] = Field(None, description="Name of primary contact person")
    email: Optional[EmailStr] = Field(None, description="Primary email for contact")
    phone: Optional[str] = Field(None, description="Contact phone number")
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/Zip code")
    tax_id: Optional[str] = Field(None, description="Tax ID or business registration number")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerCustomerBase(BaseModel):
    """Base schema for reseller customers."""
    customer_id: int = Field(..., description="ID of the customer assigned to the reseller")
    reseller_id: int = Field(..., description="ID of the reseller managing this customer")
    notes: Optional[str] = Field(None, description="Additional notes about this customer relationship")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerCustomerCreate(BaseModel):
    """Schema for creating a new reseller-customer relationship."""
    customer_id: int = Field(..., description="ID of the customer to assign to the reseller")
    notes: Optional[str] = Field(None, description="Additional notes about this customer relationship")


class ResellerCustomerResponse(ResellerCustomerBase):
    """Schema for reseller customer response data."""
    id: int = Field(..., description="Unique identifier for this reseller-customer relationship")
    created_at: datetime = Field(..., description="Relationship creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerTransactionType(str, Enum):
    """Type of reseller transaction."""
    COMMISSION = "commission"
    BONUS = "bonus"
    ADJUSTMENT = "adjustment"
    WITHDRAWAL = "withdrawal"


class ResellerTransactionBase(BaseModel):
    """Base schema for reseller transactions."""
    reseller_id: int = Field(..., description="ID of the reseller")
    amount: Decimal = Field(..., description="Transaction amount")
    type: ResellerTransactionType = Field(..., description="Type of transaction")
    reference_id: Optional[str] = Field(None, description="Reference ID (e.g., invoice number)")
    description: str = Field(..., description="Transaction description")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerTransactionCreate(ResellerTransactionBase):
    """Schema for creating a new reseller transaction."""
    pass


class ResellerTransactionResponse(ResellerTransactionBase):
    """Schema for reseller transaction response data."""
    id: int = Field(..., description="Unique identifier for the transaction")
    created_at: datetime = Field(..., description="Transaction timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerCommissionRuleBase(BaseModel):
    """Base schema for reseller commission rules."""
    reseller_id: int = Field(..., description="ID of the reseller this rule applies to")
    product_id: Optional[int] = Field(None, description="ID of the product this rule applies to (None for all)")
    service_id: Optional[int] = Field(None, description="ID of the service this rule applies to (None for all)")
    commission_type: CommissionType = Field(..., description="Type of commission calculation")
    commission_value: Decimal = Field(..., description="Commission value (percentage or fixed amount)")
    min_order_value: Optional[Decimal] = Field(None, description="Minimum order value to qualify")
    start_date: datetime = Field(..., description="Rule effective start date")
    end_date: Optional[datetime] = Field(None, description="Rule effective end date (None for never)")
    description: Optional[str] = Field(None, description="Rule description")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerCommissionRuleCreate(ResellerCommissionRuleBase):
    """Schema for creating a new reseller commission rule."""
    pass


class ResellerCommissionRuleResponse(ResellerCommissionRuleBase):
    """Schema for reseller commission rule response data."""
    id: int = Field(..., description="Unique identifier for the commission rule")
    created_at: datetime = Field(..., description="Rule creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(True, description="Whether this rule is currently active")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerSearch(BaseModel):
    """Schema for searching resellers."""
    keyword: Optional[str] = Field(None, description="Search keyword")
    status: Optional[ResellerStatus] = Field(None, description="Filter by status")
    tier: Optional[ResellerTier] = Field(None, description="Filter by tier")
    country: Optional[str] = Field(None, description="Filter by country")
    min_customers: Optional[int] = Field(None, description="Minimum number of customers")
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    
    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")
    
    model_config = ConfigDict(from_attributes=True)
