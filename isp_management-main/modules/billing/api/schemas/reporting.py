"""
Reporting schemas for the billing module.

This module provides Pydantic models for financial and subscription reporting operations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class DateRangeRequest(BaseModel):
    """Base schema for date range-based report requests."""
    start_date: datetime = Field(..., description="Start date for the report period")
    end_date: datetime = Field(..., description="End date for the report period")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    
    model_config = ConfigDict(from_attributes=True)


class RevenueSummaryResponse(BaseModel):
    """Schema for revenue summary report response."""
    total_revenue: Decimal = Field(..., description="Total revenue in the period")
    gross_revenue: Decimal = Field(..., description="Gross revenue before taxes")
    tax_amount: Decimal = Field(..., description="Total tax amount")
    total_invoices: int = Field(..., description="Number of invoices in the period")
    paid_invoices: int = Field(..., description="Number of paid invoices")
    unpaid_invoices: int = Field(..., description="Number of unpaid invoices")
    average_invoice_amount: Decimal = Field(..., description="Average invoice amount")
    
    model_config = ConfigDict(from_attributes=True)


class RevenueByPeriodRequest(DateRangeRequest):
    """Schema for revenue by period report request."""
    interval: str = Field("month", description="Time interval for grouping (day, week, month, quarter, year)")


class RevenueDataPoint(BaseModel):
    """Schema for a single data point in time series reports."""
    period: str = Field(..., description="Time period label")
    value: Decimal = Field(..., description="Value for the period")
    
    model_config = ConfigDict(from_attributes=True)


class RevenueByPeriodResponse(BaseModel):
    """Schema for revenue by period report response."""
    data_points: List[RevenueDataPoint] = Field(..., description="Revenue data points by period")
    total: Decimal = Field(..., description="Total revenue for entire period")
    
    model_config = ConfigDict(from_attributes=True)


class RevenueByServiceResponse(BaseModel):
    """Schema for revenue breakdown by service type response."""
    service_revenue: Dict[str, Decimal] = Field(..., description="Revenue by service type")
    total_revenue: Decimal = Field(..., description="Total revenue")
    
    model_config = ConfigDict(from_attributes=True)


class PaymentMethodDistributionResponse(BaseModel):
    """Schema for payment method distribution report response."""
    distribution: Dict[str, Dict[str, Any]] = Field(..., description="Payment method distribution with counts and percentages")
    total_payments: int = Field(..., description="Total number of payments")
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionMetricsResponse(BaseModel):
    """Schema for subscription metrics report response."""
    total_subscriptions: int = Field(..., description="Total active subscriptions")
    new_subscriptions: int = Field(..., description="New subscriptions in period")
    cancelled_subscriptions: int = Field(..., description="Cancelled subscriptions in period")
    churn_rate: float = Field(..., description="Churn rate as percentage")
    average_subscription_value: Decimal = Field(..., description="Average revenue per subscription")
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionGrowthRequest(DateRangeRequest):
    """Schema for subscription growth report request."""
    interval: str = Field("month", description="Time interval for grouping (day, week, month, quarter, year)")


class SubscriptionGrowthResponse(BaseModel):
    """Schema for subscription growth report response."""
    data_points: List[Dict[str, Any]] = Field(..., description="Subscription growth data points by period")
    net_growth: int = Field(..., description="Net subscription growth over period")
    
    model_config = ConfigDict(from_attributes=True)


class ChurnRateResponse(BaseModel):
    """Schema for churn rate report response."""
    churn_rate: float = Field(..., description="Overall churn rate as percentage")
    data_points: List[Dict[str, Any]] = Field(..., description="Churn rate data points by period")
    churn_by_plan: Dict[str, float] = Field(..., description="Churn rate by subscription plan")
    
    model_config = ConfigDict(from_attributes=True)


class AgingBucket(BaseModel):
    """Schema for an accounts receivable aging bucket."""
    range_label: str = Field(..., description="Aging range label (e.g., '0-30 days')")
    amount: Decimal = Field(..., description="Total amount in aging bucket")
    count: int = Field(..., description="Number of invoices in aging bucket")
    
    model_config = ConfigDict(from_attributes=True)


class AccountsReceivableAgingResponse(BaseModel):
    """Schema for accounts receivable aging report response."""
    aging_buckets: List[AgingBucket] = Field(..., description="Aging buckets with amounts")
    total_outstanding: Decimal = Field(..., description="Total outstanding amount")
    
    model_config = ConfigDict(from_attributes=True)


class FinancialStatementRequest(DateRangeRequest):
    """Schema for financial statement report request."""
    statement_type: str = Field(..., description="Type of statement (income, balance, cash_flow)")


class CustomerLifetimeValueRequest(DateRangeRequest):
    """Schema for customer lifetime value report request."""
    segment: Optional[str] = Field(None, description="Customer segment to analyze")


class CustomerLifetimeValueResponse(BaseModel):
    """Schema for customer lifetime value report response."""
    average_ltv: Decimal = Field(..., description="Average lifetime value")
    ltv_by_segment: Dict[str, Decimal] = Field(..., description="Lifetime value by customer segment")
    data_points: List[Dict[str, Any]] = Field(..., description="LTV data points by period")
    
    model_config = ConfigDict(from_attributes=True)


class ExportFormat(str, Enum):
    """Export format options."""
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    JSON = "json"


class ExportFinancialDataRequest(DateRangeRequest):
    """Schema for exporting financial data request."""
    report_type: str = Field(..., description="Type of report to export")
    format: ExportFormat = Field(ExportFormat.CSV, description="Export format")


class ExportFinancialDataResponse(BaseModel):
    """Schema for exporting financial data response."""
    file_url: str = Field(..., description="URL to download the exported file")
    expiry_time: datetime = Field(..., description="Expiry time for the download URL")
    
    model_config = ConfigDict(from_attributes=True)


# Backward compatibility aliases with Schema suffix
DateRangeRequestSchema = DateRangeRequest
RevenueSummaryResponseSchema = RevenueSummaryResponse
RevenueByPeriodRequestSchema = RevenueByPeriodRequest
RevenueByPeriodResponseSchema = RevenueByPeriodResponse
RevenueByServiceResponseSchema = RevenueByServiceResponse
PaymentMethodDistributionResponseSchema = PaymentMethodDistributionResponse
SubscriptionMetricsResponseSchema = SubscriptionMetricsResponse
SubscriptionGrowthRequestSchema = SubscriptionGrowthRequest
SubscriptionGrowthResponseSchema = SubscriptionGrowthResponse
ChurnRateResponseSchema = ChurnRateResponse
AccountsReceivableAgingResponseSchema = AccountsReceivableAgingResponse
FinancialStatementRequestSchema = FinancialStatementRequest
CustomerLifetimeValueRequestSchema = CustomerLifetimeValueRequest
CustomerLifetimeValueResponseSchema = CustomerLifetimeValueResponse
ExportFinancialDataRequestSchema = ExportFinancialDataRequest
ExportFinancialDataResponseSchema = ExportFinancialDataResponse


# Additional schema for monthly reporting
class MonthlyReportRequest(DateRangeRequest):
    """Schema for monthly report request."""
    report_type: str = Field(..., description="Type of monthly report")
    format: ExportFormat = Field(ExportFormat.CSV, description="Report format")
    
    model_config = ConfigDict(from_attributes=True)


# Backward compatibility alias
MonthlyReportRequestSchema = MonthlyReportRequest
