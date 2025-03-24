from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DateRangeRequest(BaseModel):
    """Base request model for date range reports."""
    start_date: datetime
    end_date: datetime


class RevenueSummaryResponse(BaseModel):
    """Response model for revenue summary."""
    start_date: str
    end_date: str
    invoiced_amount: float
    paid_amount: float
    outstanding_amount: float
    invoice_count: int
    payment_count: int
    collection_rate: float


class RevenuePeriodItem(BaseModel):
    """Item in revenue by period response."""
    period: str
    period_name: Optional[str] = None
    revenue: float


class RevenueByPeriodRequest(DateRangeRequest):
    """Request model for revenue by period."""
    period: str = Field("month", description="Grouping period: day, week, month, quarter, year")


class RevenueByPeriodResponse(BaseModel):
    """Response model for revenue by period."""
    data: List[RevenuePeriodItem]


class RevenueByServiceItem(BaseModel):
    """Item in revenue by service response."""
    service: str
    revenue: float


class RevenueByServiceResponse(BaseModel):
    """Response model for revenue by service."""
    data: List[RevenueByServiceItem]


class PaymentMethodItem(BaseModel):
    """Item in payment method distribution response."""
    method: str
    count: int
    amount: float
    percentage: float


class PaymentMethodDistributionResponse(BaseModel):
    """Response model for payment method distribution."""
    data: List[PaymentMethodItem]


class SubscriptionMetricsResponse(BaseModel):
    """Response model for subscription metrics."""
    date: str
    active_subscriptions: int
    subscriptions_by_status: Dict[str, int]
    subscriptions_by_cycle: Dict[str, int]
    monthly_recurring_revenue: float
    annual_recurring_revenue: float


class SubscriptionGrowthItem(BaseModel):
    """Item in subscription growth response."""
    period: str
    period_name: Optional[str] = None
    new_subscriptions: int
    cancelled_subscriptions: int
    active_subscriptions: int
    net_change: int


class SubscriptionGrowthRequest(DateRangeRequest):
    """Request model for subscription growth."""
    period: str = Field("month", description="Grouping period: day, week, month")


class SubscriptionGrowthResponse(BaseModel):
    """Response model for subscription growth."""
    data: List[SubscriptionGrowthItem]


class ChurnRateItem(BaseModel):
    """Item in churn rate response."""
    period: str
    period_name: Optional[str] = None
    starting_subscriptions: int
    cancelled_subscriptions: int
    churn_rate: float


class ChurnRateResponse(BaseModel):
    """Response model for churn rate."""
    data: List[ChurnRateItem]


class AccountsReceivableAgingBucket(BaseModel):
    """Bucket in accounts receivable aging response."""
    amount: float
    count: int


class AccountsReceivableAgingResponse(BaseModel):
    """Response model for accounts receivable aging."""
    total_outstanding: float
    buckets: Dict[str, AccountsReceivableAgingBucket]


class FinancialStatementRequest(DateRangeRequest):
    """Request model for financial statement."""
    statement_type: str = Field("income", description="Statement type: income, balance")


class IncomeStatementResponse(BaseModel):
    """Response model for income statement."""
    statement_type: str
    start_date: str
    end_date: str
    revenue: float
    refunds: float
    net_revenue: float
    cost_of_services: float
    gross_profit: float
    expenses: Dict[str, float]
    total_expenses: float
    net_income: float


class BalanceSheetResponse(BaseModel):
    """Response model for balance sheet."""
    statement_type: str
    as_of_date: str
    assets: Dict[str, float]
    liabilities: Dict[str, float]
    equity: Dict[str, float]


class CustomerLifetimeValueRequest(BaseModel):
    """Request model for customer lifetime value."""
    user_id: Optional[int] = None
    segment: Optional[str] = None


class CustomerLifetimeValueResponse(BaseModel):
    """Response model for customer lifetime value."""
    user_id: Optional[int] = None
    total_revenue: float
    months_active: Optional[float] = None
    monthly_revenue: float
    estimated_lifetime_value: float
    paying_customers: Optional[int] = None
    average_revenue_per_customer: Optional[float] = None
    average_customer_lifespan_months: Optional[int] = None


class ExportFinancialDataRequest(DateRangeRequest):
    """Request model for exporting financial data."""
    report_type: str = Field(..., description="Report type: revenue, subscriptions, payments")


class ExportFinancialDataResponse(BaseModel):
    """Response model for exporting financial data."""
    report_type: str
    start_date: str
    end_date: str
    generated_at: str
    data: List[Dict[str, Any]]
