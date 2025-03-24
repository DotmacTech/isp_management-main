from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path, Body
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_user, get_current_admin_user
from backend_core.models import User, Invoice, InvoiceDiscount, InvoiceTax
from backend_core.cache import get_cached_invoice_details, cache_invoice_details
from .schemas import (
    DiscountCreate,
    DiscountResponse,
    CreditNoteCreate,
    CreditNoteResponse,
    TaxRateCreate,
    TaxRateResponse,
    InvoiceDetailResponse,
    InvoiceDetailsResponse,
    DiscountDetail,
    TaxDetail,
    CreditNoteDetail,
    InvoiceCreate,
    InvoiceResponse,
    PaymentCreate,
    PaymentResponse,
    OverdueInvoiceResponse,
    MonthlyReportRequest
)
from .schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    RecurringBillingProfileCreate,
    RecurringBillingProfileResponse,
    UsageRecordCreate,
    UsageRecordResponse,
    SubscriptionPlanChange
)
from .schemas.tax import (
    TaxRateCreate,
    TaxRateUpdate,
    TaxRateResponse,
    TaxExemptionCreate,
    TaxExemptionResponse,
    TaxCalculationRequest,
    TaxCalculationResponse
)
from .schemas.discount import (
    DiscountCreate,
    DiscountUpdate,
    DiscountResponse,
    DiscountUsageCreate,
    DiscountValidationRequest,
    DiscountValidationResponse,
    DiscountCalculationRequest,
    DiscountCalculationResponse
)
from .schemas.reporting import (
    DateRangeRequest,
    RevenueSummaryResponse,
    RevenueByPeriodRequest,
    RevenueByPeriodResponse,
    RevenueByServiceResponse,
    PaymentMethodDistributionResponse,
    SubscriptionMetricsResponse,
    SubscriptionGrowthRequest,
    SubscriptionGrowthResponse,
    ChurnRateResponse,
    AccountsReceivableAgingResponse,
    FinancialStatementRequest,
    CustomerLifetimeValueRequest,
    CustomerLifetimeValueResponse,
    ExportFinancialDataRequest,
    ExportFinancialDataResponse
)
from .services import (
    BillingService, 
    InvoiceService, 
    PaymentService, 
    SubscriptionService, 
    TaxService, 
    DiscountService, 
    ReportingService
)

router = APIRouter(
    prefix="/api/billing",
    tags=["billing"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    db: Session = Depends(get_db)
):
    """Create a new invoice."""
    billing_service = BillingService(db)
    return billing_service.create_invoice(invoice_data)

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Get invoice by ID."""
    billing_service = BillingService(db)
    invoice = billing_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice

@router.get("/users/{user_id}/invoices", response_model=List[InvoiceResponse])
async def get_user_invoices(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all invoices for a specific user."""
    billing_service = BillingService(db)
    return billing_service.get_user_invoices(user_id)

@router.post("/payments", response_model=PaymentResponse)
async def process_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db)
):
    """Process a payment for an invoice."""
    billing_service = BillingService(db)
    return billing_service.process_payment(payment_data)

@router.get("/invoices/overdue", response_model=List[OverdueInvoiceResponse])
async def check_overdue_invoices(
    db: Session = Depends(get_db)
):
    """Get all overdue invoices."""
    billing_service = BillingService(db)
    return billing_service.check_overdue_invoices()

# Discount Management Endpoints
@router.post("/discounts", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED)
async def create_discount(
    discount_data: DiscountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new discount."""
    discount_service = DiscountService(db)
    return discount_service.create_discount(discount_data)

@router.get("/discounts/{discount_id}", response_model=DiscountResponse)
async def get_discount(
    discount_id: int,
    db: Session = Depends(get_db)
):
    """Get discount by ID."""
    discount_service = DiscountService(db)
    discount = discount_service.get_discount(discount_id)
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discount not found"
        )
    return discount

@router.get("/discounts", response_model=List[DiscountResponse])
async def get_active_discounts(
    db: Session = Depends(get_db)
):
    """Get all active discounts."""
    discount_service = DiscountService(db)
    return discount_service.get_active_discounts()

@router.put("/discounts/{discount_id}", response_model=DiscountResponse)
async def update_discount(
    discount_id: int,
    discount_data: DiscountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a discount."""
    discount_service = DiscountService(db)
    return discount_service.update_discount(discount_id, discount_data)

@router.post("/discounts/validate", response_model=DiscountValidationResponse)
async def validate_discount_code(
    validation_data: DiscountValidationRequest,
    db: Session = Depends(get_db)
):
    """Validate a discount code."""
    discount_service = DiscountService(db)
    return discount_service.validate_discount_code(
        validation_data.code,
        validation_data.user_id,
        validation_data.amount,
        validation_data.plan_id
    )

@router.post("/discounts/calculate", response_model=DiscountCalculationResponse)
async def calculate_discount_amount(
    calculation_data: DiscountCalculationRequest,
    db: Session = Depends(get_db)
):
    """Calculate discount amount for a given base amount."""
    discount_service = DiscountService(db)
    return discount_service.calculate_discount_amount(
        calculation_data.discount_id,
        calculation_data.base_amount
    )

@router.post("/invoices/{invoice_id}/discounts/{discount_id}")
async def apply_discount_to_invoice(
    invoice_id: int,
    discount_id: int,
    db: Session = Depends(get_db)
):
    """Apply a discount to an invoice."""
    billing_service = BillingService(db)
    return billing_service.apply_discount_to_invoice(invoice_id, discount_id)

@router.post("/discounts/referral/{user_id}", response_model=DiscountResponse)
async def create_referral_discount(
    user_id: int,
    discount_percentage: float = Body(10.0),
    valid_days: int = Body(30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a referral discount for a user."""
    discount_service = DiscountService(db)
    return discount_service.create_referral_discount(
        user_id,
        Decimal(str(discount_percentage)),
        valid_days
    )

# Credit Note Endpoints
@router.post("/credit-notes", response_model=CreditNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_note(
    credit_note_data: CreditNoteCreate,
    db: Session = Depends(get_db)
):
    """Create a new credit note."""
    billing_service = BillingService(db)
    return billing_service.create_credit_note(credit_note_data)

@router.get("/credit-notes/{credit_note_id}", response_model=CreditNoteResponse)
async def get_credit_note(
    credit_note_id: int,
    db: Session = Depends(get_db)
):
    """Get credit note by ID."""
    billing_service = BillingService(db)
    credit_note = billing_service.get_credit_note(credit_note_id)
    if not credit_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit note not found"
        )
    return credit_note

@router.get("/users/{user_id}/credit-notes", response_model=List[CreditNoteResponse])
async def get_user_credit_notes(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all credit notes for a specific user."""
    billing_service = BillingService(db)
    return billing_service.get_user_credit_notes(user_id)

@router.post("/credit-notes/{credit_note_id}/apply/{invoice_id}")
async def apply_credit_note_to_invoice(
    credit_note_id: int,
    invoice_id: int,
    amount: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Apply a credit note to an invoice."""
    billing_service = BillingService(db)
    decimal_amount = Decimal(str(amount)) if amount else None
    return billing_service.apply_credit_note_to_invoice(credit_note_id, invoice_id, decimal_amount)

# Tax Management Endpoints
@router.post("/tax-rates", response_model=TaxRateResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_rate(
    tax_rate_data: TaxRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new tax rate."""
    tax_service = TaxService(db)
    return tax_service.create_tax_rate(tax_rate_data)

@router.get("/tax-rates/{tax_rate_id}", response_model=TaxRateResponse)
async def get_tax_rate(
    tax_rate_id: int,
    db: Session = Depends(get_db)
):
    """Get tax rate by ID."""
    tax_service = TaxService(db)
    tax_rate = tax_service.get_tax_rate(tax_rate_id)
    if not tax_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax rate not found"
        )
    return tax_rate

@router.get("/tax-rates", response_model=List[TaxRateResponse])
async def get_tax_rates(
    country: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all tax rates, optionally filtered by country and region."""
    tax_service = TaxService(db)
    return tax_service.get_tax_rates(country, region)

@router.put("/tax-rates/{tax_rate_id}", response_model=TaxRateResponse)
async def update_tax_rate(
    tax_rate_id: int,
    tax_rate_data: TaxRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a tax rate."""
    tax_service = TaxService(db)
    return tax_service.update_tax_rate(tax_rate_id, tax_rate_data)

@router.delete("/tax-rates/{tax_rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_rate(
    tax_rate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a tax rate."""
    tax_service = TaxService(db)
    tax_service.delete_tax_rate(tax_rate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/tax-exemptions", response_model=TaxExemptionResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_exemption(
    exemption_data: TaxExemptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a tax exemption for a user."""
    tax_service = TaxService(db)
    return tax_service.create_tax_exemption(exemption_data)

@router.get("/users/{user_id}/tax-exemptions", response_model=List[TaxExemptionResponse])
async def get_user_tax_exemptions(
    user_id: int,
    include_expired: bool = False,
    db: Session = Depends(get_db)
):
    """Get all tax exemptions for a specific user."""
    tax_service = TaxService(db)
    return tax_service.get_user_tax_exemptions(user_id, include_expired)

@router.post("/tax/calculate", response_model=TaxCalculationResponse)
async def calculate_tax(
    calculation_data: TaxCalculationRequest,
    db: Session = Depends(get_db)
):
    """Calculate tax for a given amount, country, and region."""
    tax_service = TaxService(db)
    return tax_service.calculate_tax(
        calculation_data.amount,
        calculation_data.country,
        calculation_data.region,
        calculation_data.user_id
    )

# Subscription Management Endpoints
@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    """Create a new subscription for a user."""
    subscription_service = SubscriptionService(db)
    return subscription_service.create_subscription(subscription_data)

@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """Get subscription by ID."""
    subscription_service = SubscriptionService(db)
    subscription = subscription_service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return subscription

@router.get("/users/{user_id}/subscriptions", response_model=List[SubscriptionResponse])
async def get_user_subscriptions(
    user_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """Get all subscriptions for a specific user."""
    subscription_service = SubscriptionService(db)
    return subscription_service.get_user_subscriptions(user_id, include_inactive)

@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    db: Session = Depends(get_db)
):
    """Update a subscription."""
    subscription_service = SubscriptionService(db)
    return subscription_service.update_subscription(subscription_id, subscription_data)

@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Cancel a subscription."""
    subscription_service = SubscriptionService(db)
    return subscription_service.cancel_subscription(subscription_id, reason)

@router.post("/subscriptions/{subscription_id}/pause", response_model=SubscriptionResponse)
async def pause_subscription(
    subscription_id: int,
    pause_days: int = Body(...),
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Pause a subscription for a specified number of days."""
    subscription_service = SubscriptionService(db)
    return subscription_service.pause_subscription(subscription_id, pause_days, reason)

@router.post("/subscriptions/{subscription_id}/resume", response_model=SubscriptionResponse)
async def resume_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """Resume a paused subscription."""
    subscription_service = SubscriptionService(db)
    return subscription_service.resume_subscription(subscription_id)

@router.post("/subscriptions/{subscription_id}/change-plan", response_model=SubscriptionResponse)
async def change_subscription_plan(
    subscription_id: int,
    plan_change: SubscriptionPlanChange,
    db: Session = Depends(get_db)
):
    """Change a subscription to a different plan."""
    subscription_service = SubscriptionService(db)
    return subscription_service.change_plan(
        subscription_id,
        plan_change.new_plan_id,
        plan_change.prorate
    )

@router.post("/billing-profiles", response_model=RecurringBillingProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_profile(
    profile_data: RecurringBillingProfileCreate,
    db: Session = Depends(get_db)
):
    """Create a new recurring billing profile."""
    subscription_service = SubscriptionService(db)
    return subscription_service.create_billing_profile(profile_data)

@router.get("/users/{user_id}/billing-profiles", response_model=List[RecurringBillingProfileResponse])
async def get_user_billing_profiles(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all billing profiles for a specific user."""
    subscription_service = SubscriptionService(db)
    return subscription_service.get_user_billing_profiles(user_id)

@router.post("/subscriptions/{subscription_id}/usage", response_model=UsageRecordResponse, status_code=status.HTTP_201_CREATED)
async def record_usage(
    subscription_id: int,
    usage_data: UsageRecordCreate,
    db: Session = Depends(get_db)
):
    """Record usage for usage-based billing."""
    subscription_service = SubscriptionService(db)
    # Ensure subscription_id in path matches the one in the request body
    usage_data.subscription_id = subscription_id
    return subscription_service.record_usage(usage_data)

@router.get("/subscriptions/{subscription_id}/usage", response_model=List[UsageRecordResponse])
async def get_subscription_usage(
    subscription_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get usage records for a subscription."""
    subscription_service = SubscriptionService(db)
    return subscription_service.get_subscription_usage(subscription_id, start_date, end_date)

# Reporting Endpoints
@router.post("/reports/revenue-summary", response_model=RevenueSummaryResponse)
async def get_revenue_summary(
    date_range: DateRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get a summary of revenue for a date range."""
    reporting_service = ReportingService(db)
    return reporting_service.get_revenue_summary(date_range.start_date, date_range.end_date)

@router.post("/reports/revenue-by-period", response_model=RevenueByPeriodResponse)
async def get_revenue_by_period(
    request: RevenueByPeriodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get revenue broken down by period."""
    reporting_service = ReportingService(db)
    data = reporting_service.get_revenue_by_period(
        request.start_date,
        request.end_date,
        request.period
    )
    return {"data": data}

@router.post("/reports/revenue-by-service", response_model=RevenueByServiceResponse)
async def get_revenue_by_service(
    date_range: DateRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get revenue broken down by service type."""
    reporting_service = ReportingService(db)
    data = reporting_service.get_revenue_by_service(date_range.start_date, date_range.end_date)
    return {"data": data}

@router.post("/reports/payment-methods", response_model=PaymentMethodDistributionResponse)
async def get_payment_method_distribution(
    date_range: DateRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get distribution of payments by payment method."""
    reporting_service = ReportingService(db)
    data = reporting_service.get_payment_method_distribution(date_range.start_date, date_range.end_date)
    return {"data": data}

@router.get("/reports/subscription-metrics", response_model=SubscriptionMetricsResponse)
async def get_subscription_metrics(
    date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get metrics about subscriptions at a specific date."""
    reporting_service = ReportingService(db)
    return reporting_service.get_subscription_metrics(date)

@router.post("/reports/subscription-growth", response_model=SubscriptionGrowthResponse)
async def get_subscription_growth(
    request: SubscriptionGrowthRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get subscription growth over time."""
    reporting_service = ReportingService(db)
    data = reporting_service.get_subscription_growth(
        request.start_date,
        request.end_date,
        request.period
    )
    return {"data": data}

@router.post("/reports/churn-rate", response_model=ChurnRateResponse)
async def get_churn_rate(
    date_range: DateRangeRequest,
    period: str = "month",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get churn rate over time."""
    reporting_service = ReportingService(db)
    data = reporting_service.get_churn_rate(date_range.start_date, date_range.end_date, period)
    return {"data": data}

@router.get("/reports/accounts-receivable-aging", response_model=AccountsReceivableAgingResponse)
async def get_accounts_receivable_aging(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get accounts receivable aging report."""
    reporting_service = ReportingService(db)
    return reporting_service.get_accounts_receivable_aging()

@router.post("/reports/financial-statement", response_model=Dict)
async def get_financial_statement(
    request: FinancialStatementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Generate a financial statement."""
    reporting_service = ReportingService(db)
    return reporting_service.get_financial_statement(
        request.start_date,
        request.end_date,
        request.statement_type
    )

@router.post("/reports/customer-lifetime-value", response_model=CustomerLifetimeValueResponse)
async def get_customer_lifetime_value(
    request: CustomerLifetimeValueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Calculate customer lifetime value."""
    reporting_service = ReportingService(db)
    return reporting_service.get_customer_lifetime_value(request.user_id, request.segment)

@router.post("/reports/export", response_model=ExportFinancialDataResponse)
async def export_financial_data(
    request: ExportFinancialDataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Export financial data for external use."""
    reporting_service = ReportingService(db)
    return reporting_service.export_financial_data(
        request.start_date,
        request.end_date,
        request.report_type
    )

@router.get("/invoices/{invoice_id}/details", response_model=InvoiceDetailsResponse)
async def get_invoice_details(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about an invoice, including discounts and taxes."""
    # Try to get from cache first
    cached_details = get_cached_invoice_details(invoice_id)
    if cached_details is not None:
        # Check authorization even for cached results
        if cached_details["user_id"] != current_user.id and current_user.role not in ["admin", "staff"]:
            raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
        return cached_details
    
    # If not in cache, get from database
    billing_service = BillingService(db)
    invoice = billing_service.get_invoice(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # Check authorization
    if invoice.user_id != current_user.id and current_user.role not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
    
    # Calculate subtotal (before discounts and taxes)
    subtotal = invoice.amount
    
    # Get applied discounts
    discounts = []
    total_discount = Decimal("0.00")
    for discount in invoice.discounts:
        discount_amount = discount.amount
        total_discount += discount_amount
        discounts.append({
            "id": discount.discount_id,
            "name": discount.discount.name,
            "amount": discount_amount
        })
    
    # Get applied taxes
    taxes = []
    total_tax = Decimal("0.00")
    for tax in invoice.taxes:
        tax_amount = tax.tax_amount
        total_tax += tax_amount
        taxes.append({
            "id": tax.tax_rate_id,
            "name": tax.tax_rate.name,
            "rate": tax.tax_rate.rate,
            "amount": tax_amount
        })
    
    # Calculate total
    total = subtotal - total_discount + total_tax
    
    # Get credit note applications
    credit_notes = []
    total_credit = Decimal("0.00")
    for application in invoice.credit_note_applications:
        credit_amount = application.amount
        total_credit += credit_amount
        credit_notes.append({
            "id": application.credit_note_id,
            "amount": credit_amount,
            "applied_at": application.applied_at
        })
    
    invoice_details = {
        "id": invoice.id,
        "user_id": invoice.user_id,
        "status": invoice.status,
        "subtotal": subtotal,
        "discounts": discounts,
        "total_discount": total_discount,
        "taxes": taxes,
        "total_tax": total_tax,
        "credit_notes": credit_notes,
        "total_credit": total_credit,
        "total": total,
        "due_date": invoice.due_date,
        "created_at": invoice.created_at,
        "paid_at": invoice.paid_at
    }
    
    # Cache the invoice details
    cache_invoice_details(invoice_id, invoice_details)
    
    return invoice_details

# Invoice Template Endpoints
@router.get("/invoices/{invoice_id}/html", response_class=Response)
async def get_invoice_html(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get HTML representation of an invoice."""
    billing_service = BillingService(db)
    
    # Check if user has access to this invoice
    invoice = billing_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if the user is authorized to view this invoice
    if not current_user.is_admin and invoice.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this invoice"
        )
    
    html = billing_service.generate_invoice_html(invoice_id)
    return Response(content=html, media_type="text/html")

@router.get("/invoices/{invoice_id}/pdf", response_class=Response)
async def get_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get PDF representation of an invoice."""
    billing_service = BillingService(db)
    
    # Check if user has access to this invoice
    invoice = billing_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if the user is authorized to view this invoice
    if not current_user.is_admin and invoice.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this invoice"
        )
    
    pdf = billing_service.generate_invoice_pdf(invoice_id)
    
    # Set filename for download
    filename = f"invoice_{invoice_id}.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    
    return Response(
        content=pdf, 
        media_type="application/pdf",
        headers=headers
    )

@router.get("/invoices/{invoice_id}/email-reminder", response_class=Response)
async def get_invoice_reminder_email(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get HTML email reminder for an invoice."""
    # Only admins can generate email reminders
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can generate email reminders"
        )
    
    billing_service = BillingService(db)
    
    # Check if invoice exists
    invoice = billing_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    html = billing_service.generate_invoice_reminder_email(invoice_id)
    return Response(content=html, media_type="text/html")

@router.post("/reports/monthly", response_class=Response)
async def generate_monthly_billing_report(
    report_request: MonthlyReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a monthly billing report."""
    # Only admins can generate reports
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can generate reports"
        )
    
    billing_service = BillingService(db)
    
    # Validate month and year
    if report_request.month < 1 or report_request.month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12"
        )
    
    if report_request.year < 2000 or report_request.year > datetime.now().year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year"
        )
    
    html = billing_service.generate_monthly_billing_report(
        report_request.year, 
        report_request.month
    )
    
    return Response(content=html, media_type="text/html")

# Cache management endpoints
@router.post("/cache/clear")
async def clear_billing_cache(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear billing cache."""
    # Only admins can clear cache
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can clear cache"
        )
    
    from backend_core.cache import (
        cache_clear_pattern,
        invalidate_billing_statistics_cache
    )
    
    # Clear all billing-related caches
    cache_clear_pattern("tax_rate:*")
    cache_clear_pattern("active_discounts")
    cache_clear_pattern("invoice:*")
    cache_clear_pattern("user_credit_notes:*")
    cache_clear_pattern("user_invoices:*")
    cache_clear_pattern("payment_history:*")
    invalidate_billing_statistics_cache()
    
    # Clear template cache
    from modules.billing.template_service import invalidate_template_cache
    invalidate_template_cache()
    
    return {"message": "Billing cache cleared successfully"}
