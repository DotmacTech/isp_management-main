"""
Billing module schemas package.

This package contains all the Pydantic schemas for the billing module,
including schemas for invoices, payments, subscriptions, taxes, discounts,
and financial reporting.
"""

# Import schemas from the API schemas package
from modules.billing.api.schemas import (
    CreditNoteDetailSchema,
    InvoiceItemSchema,
    InvoiceCreateSchema,
    InvoiceResponseSchema,
    InvoiceDetailResponseSchema,
    InvoiceDetailsResponseSchema,
    OverdueInvoiceResponseSchema,
    PaymentMethod,
    PaymentStatus,
    PaymentCreateSchema,
    PaymentResponseSchema,
)

# Import module-specific schemas
from modules.billing.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceDetailsResponse,
    InvoiceFilterParams,
    ProformaInvoiceCreate,
    InvoiceItemCreate,
    CreditNoteCreate
)

# Import payment schemas
from modules.billing.schemas.payment import (
    PaymentBase,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentMethodStats,
    PaymentMethodsStatsResponse,
    PaymentTransactionBase,
    PaymentTransactionCreate,
    PaymentTransactionUpdate,
    PaymentTransactionResponse,
    RefundBase,
    RefundCreate,
    RefundUpdate,
    RefundResponse,
    PaymentGatewayConfigBase,
    PaymentGatewayConfigCreate,
    PaymentGatewayConfigUpdate,
    PaymentGatewayConfigResponse
)

# Import reporting schemas
from modules.billing.api.schemas.reporting import (
    ExportFormat,
    DateRangeRequest,
    DateRangeRequestSchema,
    RevenueSummaryResponse,
    RevenueSummaryResponseSchema,
    RevenueByPeriodRequest,
    RevenueByPeriodRequestSchema,
    RevenueByPeriodResponse,
    RevenueByPeriodResponseSchema,
    RevenueByServiceResponse,
    RevenueByServiceResponseSchema,
    PaymentMethodDistributionResponse,
    PaymentMethodDistributionResponseSchema,
    SubscriptionMetricsResponse,
    SubscriptionMetricsResponseSchema,
    SubscriptionGrowthRequest,
    SubscriptionGrowthRequestSchema,
    SubscriptionGrowthResponse,
    SubscriptionGrowthResponseSchema,
    ChurnRateResponse,
    ChurnRateResponseSchema,
    AccountsReceivableAgingResponse,
    AccountsReceivableAgingResponseSchema,
    FinancialStatementRequest,
    FinancialStatementRequestSchema,
    CustomerLifetimeValueRequest,
    CustomerLifetimeValueRequestSchema,
    CustomerLifetimeValueResponse,
    CustomerLifetimeValueResponseSchema,
    ExportFinancialDataRequest,
    ExportFinancialDataRequestSchema,
    ExportFinancialDataResponse,
    ExportFinancialDataResponseSchema,
    MonthlyReportRequest,
    MonthlyReportRequestSchema
)

# Import discount schemas
from modules.billing.api.schemas.discount import (
    DiscountType,
    DiscountStatus,
    DiscountBase,
    DiscountCreate,
    DiscountCreateSchema,
    DiscountUpdate,
    DiscountUpdateSchema,
    DiscountResponse,
    DiscountResponseSchema,
    DiscountUsageBase,
    DiscountUsageCreate,
    DiscountUsageCreateSchema,
    DiscountUsageResponse,
    DiscountUsageResponseSchema,
    DiscountValidationRequest,
    DiscountValidationRequestSchema,
    DiscountValidationResponse,
    DiscountValidationResponseSchema,
    DiscountCalculationRequest,
    DiscountCalculationRequestSchema,
    DiscountCalculationResponse,
    DiscountCalculationResponseSchema,
    DiscountDetail,
    DiscountDetailSchema
)

# Import subscription schemas
from modules.billing.api.schemas.subscription import (
    # Basic subscription schemas
    SubscriptionPeriod,
    SubscriptionStatus,
    SubscriptionBase,
    SubscriptionCreate,
    SubscriptionCreateSchema,
    SubscriptionUpdate,
    SubscriptionUpdateSchema,
    SubscriptionResponse,
    SubscriptionResponseSchema,
    SubscriptionHistoryEntry,
    SubscriptionWithHistory,
    
    # Recurring billing schemas
    RecurringBillingProfileBase,
    RecurringBillingProfileCreate,
    RecurringBillingProfileCreateSchema,
    RecurringBillingProfileResponse,
    RecurringBillingProfileResponseSchema,
    
    # Usage record schemas
    UsageRecordBase,
    UsageRecordCreate,
    UsageRecordCreateSchema,
    UsageRecordResponse,
    UsageRecordResponseSchema,
    
    # Plan change schemas
    SubscriptionPlanChange,
    SubscriptionPlanChangeSchema
)

# Import tax schemas
from modules.billing.api.schemas.tax import (
    TaxType,
    TaxStatus,
    TaxRateBase,
    TaxRateCreate,
    TaxRateUpdate,
    TaxRateResponse,
    TaxExemptionBase,
    TaxExemptionCreate,
    TaxExemptionResponse,
    TaxCalculationRequest,
    TaxCalculationResponse,
    TaxDetail,
    # Schema suffix versions
    TaxRateCreateSchema,
    TaxRateUpdateSchema,
    TaxRateResponseSchema,
    TaxExemptionCreateSchema,
    TaxExemptionResponseSchema,
    TaxCalculationRequestSchema,
    TaxCalculationResponseSchema
)

# For backward compatibility
CreditNoteCreate = CreditNoteCreate  # Using the imported class from invoice schemas
CreditNoteResponse = CreditNoteDetailSchema
TaxDetail = TaxDetail  # Using the actual class from tax schemas
CreditNoteDetail = CreditNoteDetailSchema
InvoiceDetailResponse = InvoiceDetailResponseSchema
InvoiceDetailsResponse = InvoiceDetailsResponse  # Using the imported class from invoice schemas
InvoiceCreate = InvoiceCreate  # Using the imported class from invoice schemas
InvoiceResponse = InvoiceResponse  # Using the imported class from invoice schemas
PaymentCreate = PaymentCreateSchema
PaymentResponse = PaymentResponseSchema
OverdueInvoiceResponse = OverdueInvoiceResponseSchema
