"""
Reseller API Schemas

This module defines Pydantic models for reseller API data validation,
serialization and documentation.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from enum import Enum


class ResellerStatus(str, Enum):
    """Enum for reseller status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"
    TERMINATED = "terminated"


class CommissionType(str, Enum):
    """Enum for commission type."""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"


class ResellerTier(str, Enum):
    """Enum for reseller tier."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class ResellerBase(BaseModel):
    """Base model for reseller information."""
    user_id: int = Field(..., description="Associated user ID")
    company_name: str = Field(..., description="Company name of the reseller")
    contact_person: str = Field(..., description="Contact person name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    address: Optional[str] = Field(None, description="Physical address")
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    status: ResellerStatus = Field(ResellerStatus.PENDING_APPROVAL, description="Current status")
    tier: ResellerTier = Field(ResellerTier.BRONZE, description="Reseller tier")
    commission_type: CommissionType = Field(CommissionType.PERCENTAGE, description="Commission calculation type")
    commission_rate: float = Field(..., ge=0, le=100, description="Commission rate")
    credit_limit: float = Field(0.0, description="Credit limit for the reseller")
    notes: Optional[str] = Field(None, description="Additional notes")

    @field_validator('commission_rate')
    def validate_commission_rate(cls, v, info):
        """Validate commission rate based on commission type."""
        commission_type = info.data.get('commission_type')
        if commission_type == CommissionType.PERCENTAGE and v > 100:
            raise ValueError("Percentage commission cannot exceed 100%")
        return v


class ResellerCreate(ResellerBase):
    """Schema for creating a new reseller."""
    pass


class ResellerResponse(ResellerBase):
    """Schema for reseller response data."""
    id: int = Field(..., description="Unique identifier for the reseller")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    current_balance: float = Field(..., description="Current account balance")
    total_customers: int = Field(..., description="Total number of customers")
    total_revenue: float = Field(..., description="Total revenue generated")

    model_config = ConfigDict(from_attributes=True)


class ResellerProfileBaseSchema(BaseModel):
    """Base model for reseller profile information."""
    name: str = Field(..., description="Name of the reseller")
    email: EmailStr = Field(..., description="Email of the reseller")
    phone: Optional[str] = Field(None, description="Phone number of the reseller")
    address: Optional[str] = Field(None, description="Address of the reseller")
    commission_rate: Decimal = Field(..., description="Commission rate for the reseller")
    description: Optional[str] = Field(None, description="Description of the reseller")


class ResellerCustomerBase(BaseModel):
    """Base model for reseller-customer relationship."""
    reseller_id: int = Field(..., description="ID of the reseller")
    customer_id: int = Field(..., description="ID of the customer")
    notes: Optional[str] = Field(None, description="Additional notes about the relationship")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerCustomerCreate(ResellerCustomerBase):
    """Schema for creating a new reseller-customer relationship."""
    pass


class ResellerCustomerResponse(ResellerCustomerBase):
    """Schema for reseller-customer relationship response."""
    id: int = Field(..., description="Unique identifier for the relationship")
    created_at: datetime = Field(..., description="Creation timestamp")
    customer_name: str = Field(..., description="Name of the customer")
    customer_email: str = Field(..., description="Email of the customer")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerTransactionType(str, Enum):
    """Enum for reseller transaction types."""
    COMMISSION = "commission"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    WITHDRAWAL = "withdrawal"


class ResellerTransactionBase(BaseModel):
    """Base model for reseller transactions."""
    reseller_id: int = Field(..., description="ID of the reseller")
    amount: float = Field(..., description="Transaction amount")
    transaction_type: ResellerTransactionType = Field(..., description="Type of transaction")
    description: str = Field(..., description="Transaction description")
    reference_id: Optional[str] = Field(None, description="External reference ID")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerTransactionCreate(ResellerTransactionBase):
    """Schema for creating a new reseller transaction."""
    pass


class ResellerTransactionResponse(ResellerTransactionBase):
    """Schema for reseller transaction response."""
    id: int = Field(..., description="Unique identifier for the transaction")
    created_at: datetime = Field(..., description="Creation timestamp")
    balance_after: float = Field(..., description="Reseller balance after transaction")
    
    model_config = ConfigDict(from_attributes=True)


class CommissionRuleType(str, Enum):
    """Enum for commission rule types."""
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    TIERED = "tiered"


class ResellerCommissionRuleBase(BaseModel):
    """Base model for reseller commission rules."""
    reseller_id: int = Field(..., description="ID of the reseller")
    name: str = Field(..., description="Name of the commission rule")
    description: Optional[str] = Field(None, description="Description of the rule")
    rule_type: CommissionRuleType = Field(..., description="Type of commission rule")
    value: float = Field(..., description="Value (percentage or fixed amount)")
    product_category: Optional[str] = Field(None, description="Product category this rule applies to")
    min_order_value: Optional[float] = Field(None, description="Minimum order value for rule to apply")
    max_order_value: Optional[float] = Field(None, description="Maximum order value for rule to apply")
    is_active: bool = Field(True, description="Whether this rule is active")
    priority: int = Field(1, description="Priority of this rule (lower number = higher priority)")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerCommissionRuleCreate(ResellerCommissionRuleBase):
    """Schema for creating a new reseller commission rule."""
    pass


class ResellerCommissionRuleResponse(ResellerCommissionRuleBase):
    """Schema for reseller commission rule response."""
    id: int = Field(..., description="Unique identifier for the commission rule")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerSearch(BaseModel):
    """Schema for searching resellers."""
    query: Optional[str] = Field(None, description="Search query for reseller name or details")
    status: Optional[str] = Field(None, description="Filter by reseller status")
    region: Optional[str] = Field(None, description="Filter by region")
    min_balance: Optional[float] = Field(None, description="Minimum balance filter")
    max_balance: Optional[float] = Field(None, description="Maximum balance filter")
    from_date: Optional[datetime] = Field(None, description="Filter by created date (from)")
    to_date: Optional[datetime] = Field(None, description="Filter by created date (to)")
    limit: int = Field(50, description="Maximum number of results to return")
    offset: int = Field(0, description="Offset for pagination")
    
    model_config = ConfigDict(from_attributes=True)


class ResellerProfileCreateSchema(ResellerProfileBaseSchema):
    """Schema for creating a new reseller profile."""
    user_id: Optional[int] = Field(None, description="Associated user ID if applicable")


class ResellerProfileUpdateSchema(BaseModel):
    """Schema for updating a reseller profile."""
    name: Optional[str] = Field(None, description="Name of the reseller")
    email: Optional[EmailStr] = Field(None, description="Email of the reseller")
    phone: Optional[str] = Field(None, description="Phone number of the reseller")
    address: Optional[str] = Field(None, description="Address of the reseller")
    commission_rate: Optional[Decimal] = Field(None, description="Commission rate for the reseller")
    description: Optional[str] = Field(None, description="Description of the reseller")
    is_active: Optional[bool] = Field(None, description="Whether the reseller is active")


class ResellerProfileResponseSchema(ResellerProfileBaseSchema):
    """Schema for reseller profile response data."""
    id: int = Field(..., description="Unique identifier for the reseller profile")
    user_id: Optional[int] = Field(None, description="Associated user ID if applicable")
    created_at: datetime = Field(..., description="When the reseller profile was created")
    updated_at: Optional[datetime] = Field(None, description="When the reseller profile was last updated")
    is_active: bool = Field(..., description="Whether the reseller is active")

    model_config = ConfigDict(from_attributes=True)


class ResellerTransactionBaseSchema(BaseModel):
    """Base model for reseller transaction information."""
    reseller_id: int = Field(..., description="ID of the reseller")
    transaction_type: str = Field(..., description="Type of transaction (commission, payout, etc.)")
    amount: Decimal = Field(..., description="Amount of the transaction")
    reference: Optional[str] = Field(None, description="Reference for the transaction")
    description: Optional[str] = Field(None, description="Description of the transaction")


class ResellerTransactionCreateSchema(ResellerTransactionBaseSchema):
    """Schema for creating a new reseller transaction."""
    pass


class ResellerTransactionResponseSchema(ResellerTransactionBaseSchema):
    """Schema for reseller transaction response data."""
    id: int = Field(..., description="Unique identifier for the transaction")
    created_at: datetime = Field(..., description="When the transaction was created")
    processed_at: Optional[datetime] = Field(None, description="When the transaction was processed")
    status: str = Field(..., description="Status of the transaction")

    model_config = ConfigDict(from_attributes=True)


class ResellerCustomerBaseSchema(BaseModel):
    """Base model for reseller customer information."""
    reseller_id: int = Field(..., description="ID of the reseller")
    customer_id: int = Field(..., description="ID of the customer")
    notes: Optional[str] = Field(None, description="Notes about the customer")


class ResellerCustomerCreateSchema(ResellerCustomerBaseSchema):
    """Schema for creating a new reseller customer association."""
    pass


class ResellerCustomerResponseSchema(ResellerCustomerBaseSchema):
    """Schema for reseller customer response data."""
    id: int = Field(..., description="Unique identifier for the association")
    created_at: datetime = Field(..., description="When the association was created")
    customer_name: str = Field(..., description="Name of the customer")
    customer_email: EmailStr = Field(..., description="Email of the customer")

    model_config = ConfigDict(from_attributes=True)


class ResellerReportRequestSchema(BaseModel):
    """Schema for requesting a reseller report."""
    reseller_id: int = Field(..., description="ID of the reseller")
    start_date: datetime = Field(..., description="Start date for the report period")
    end_date: datetime = Field(..., description="End date for the report period")
    report_type: str = Field(..., description="Type of report (commissions, customers, sales)")


class ResellerReportResponseSchema(BaseModel):
    """Schema for reseller report response data."""
    reseller_id: int = Field(..., description="ID of the reseller")
    reseller_name: str = Field(..., description="Name of the reseller")
    start_date: datetime = Field(..., description="Start date of the report period")
    end_date: datetime = Field(..., description="End date of the report period")
    report_type: str = Field(..., description="Type of report")
    report_data: Dict[str, Any] = Field(..., description="Report data")
    generated_at: datetime = Field(..., description="When the report was generated")

    model_config = ConfigDict(from_attributes=True)
