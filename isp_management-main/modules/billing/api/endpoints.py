from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path, Body
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_user, get_current_user_role
from backend_core.models import User, Invoice, InvoiceDiscount, InvoiceTax
from backend_core.cache import get_cached_invoice_details, cache_invoice_details
from backend_core.utils.hateoas import add_resource_links, generate_collection_links, add_link
from backend_core.schemas import PaginatedResponse, HateoasResponse
from .schemas import (
    DiscountCreateSchema,
    DiscountResponseSchema,
    CreditNoteCreateSchema,
    CreditNoteResponseSchema,
    TaxRateCreateSchema,
    TaxRateResponseSchema,
    InvoiceDetailResponseSchema,
    InvoiceDetailsResponseSchema,
    DiscountDetailSchema,
    TaxDetailSchema,
    CreditNoteDetailSchema,
    InvoiceCreateSchema,
    InvoiceResponseSchema,
    PaymentCreateSchema,
    PaymentResponseSchema,
    OverdueInvoiceResponseSchema,
    MonthlyReportRequestSchema
)
from .schemas.subscription import (
    SubscriptionCreateSchema,
    SubscriptionUpdateSchema,
    SubscriptionResponseSchema,
    RecurringBillingProfileCreateSchema,
    RecurringBillingProfileResponseSchema,
    UsageRecordCreateSchema,
    UsageRecordResponseSchema,
    SubscriptionPlanChangeSchema
)
from .schemas.tax import (
    TaxRateCreateSchema,
    TaxRateUpdateSchema,
    TaxRateResponseSchema,
    TaxExemptionCreateSchema,
    TaxExemptionResponseSchema,
    TaxCalculationRequestSchema,
    TaxCalculationResponseSchema
)
from .schemas.discount import (
    DiscountCreateSchema,
    DiscountUpdateSchema,
    DiscountResponseSchema,
    DiscountUsageCreateSchema,
    DiscountValidationRequestSchema,
    DiscountValidationResponseSchema,
    DiscountCalculationRequestSchema,
    DiscountCalculationResponseSchema
)
from .schemas.reporting import (
    DateRangeRequestSchema,
    RevenueSummaryResponseSchema,
    RevenueByPeriodRequestSchema,
    RevenueByPeriodResponseSchema,
    RevenueByServiceResponseSchema,
    PaymentMethodDistributionResponseSchema,
    SubscriptionMetricsResponseSchema,
    SubscriptionGrowthRequestSchema,
    SubscriptionGrowthResponseSchema,
    ChurnRateResponseSchema,
    AccountsReceivableAgingResponseSchema,
    FinancialStatementRequestSchema,
    CustomerLifetimeValueRequestSchema,
    CustomerLifetimeValueResponseSchema,
    ExportFinancialDataRequestSchema,
    ExportFinancialDataResponseSchema
)
from modules.billing.services import (
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
    dependencies=[Depends(get_current_user_role)]
)

@router.post("/invoices", response_model=InvoiceResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreateSchema,
    db: Session = Depends(get_db)
):
    """Create a new invoice."""
    billing_service = BillingService(db)
    invoice = billing_service.create_invoice(invoice_data)
    
    # Convert to response model
    response = InvoiceResponseSchema.from_orm(invoice)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/billing/invoices",
        resource_id=invoice.id,
        related_resources=["payments", "discounts", "taxes"]
    )
    
    # Add additional links
    add_link(
        response=response,
        rel="details",
        href=f"/api/v1/billing/invoices/{invoice.id}/details",
        method="GET",
        title="Get detailed invoice information"
    )
    
    add_link(
        response=response,
        rel="pdf",
        href=f"/api/v1/billing/invoices/{invoice.id}/pdf",
        method="GET",
        title="Get invoice as PDF"
    )
    
    add_link(
        response=response,
        rel="html",
        href=f"/api/v1/billing/invoices/{invoice.id}/html",
        method="GET",
        title="Get invoice as HTML"
    )
    
    add_link(
        response=response,
        rel="customer",
        href=f"/api/v1/customers/{invoice.customer_id}",
        method="GET",
        title="View customer details"
    )
    
    return response

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponseSchema)
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
            detail=f"Invoice with ID {invoice_id} not found"
        )
    
    # Convert to response model
    response = InvoiceResponseSchema.from_orm(invoice)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/billing/invoices",
        resource_id=invoice.id,
        related_resources=["payments", "discounts", "taxes"]
    )
    
    # Add additional links specific to invoices
    add_link(
        response=response,
        rel="pdf",
        href=f"/api/v1/billing/invoices/{invoice_id}/pdf",
        method="GET",
        title="Get invoice as PDF"
    )
    
    add_link(
        response=response,
        rel="html",
        href=f"/api/v1/billing/invoices/{invoice_id}/html",
        method="GET",
        title="Get invoice as HTML"
    )
    
    add_link(
        response=response,
        rel="details",
        href=f"/api/v1/billing/invoices/{invoice_id}/details",
        method="GET",
        title="Get detailed invoice information"
    )
    
    add_link(
        response=response,
        rel="pay",
        href=f"/api/v1/billing/invoices/{invoice_id}/payments",
        method="POST",
        title="Make a payment for this invoice"
    )
    
    add_link(
        response=response,
        rel="customer",
        href=f"/api/v1/customers/{response.customer_id}",
        method="GET",
        title="View customer details"
    )
    
    add_link(
        response=response,
        rel="reminder_email",
        href=f"/api/v1/billing/invoices/{invoice_id}/reminder-email",
        method="POST",
        title="Send invoice reminder email"
    )
    
    return response

@router.get("/users/{user_id}/invoices", response_model=PaginatedResponse[InvoiceResponseSchema])
async def get_user_invoices(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all invoices for a specific user."""
    billing_service = BillingService(db)
    invoices, total = billing_service.get_user_invoices(user_id, skip, limit)
    
    # Create paginated response
    response = PaginatedResponse[InvoiceResponseSchema](
        items=[InvoiceResponseSchema.from_orm(invoice) for invoice in invoices],
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Add HATEOAS links for each invoice
    for invoice_response in response.items:
        add_resource_links(
            response=invoice_response,
            resource_path="/api/v1/billing/invoices",
            resource_id=invoice_response.id,
            related_resources=["payments", "discounts", "taxes"]
        )
        
        # Add additional links specific to invoices
        add_link(
            response=invoice_response,
            rel="details",
            href=f"/api/v1/billing/invoices/{invoice_response.id}/details",
            method="GET",
            title="Get detailed invoice information"
        )
        
        add_link(
            response=invoice_response,
            rel="pdf",
            href=f"/api/v1/billing/invoices/{invoice_response.id}/pdf",
            method="GET",
            title="Get invoice as PDF"
        )
    
    # Add collection links
    links = generate_collection_links(
        resource_path=f"/api/v1/billing/users/{user_id}/invoices",
        page=(skip // limit) + 1,
        limit=limit,
        total=total
    )
    
    response._links.update(links)
    
    # Add user link
    add_link(
        response=response,
        rel="user",
        href=f"/api/v1/users/{user_id}",
        method="GET",
        title="View user details"
    )
    
    return response

@router.get("/invoices/{invoice_id}/details", response_model=InvoiceDetailsResponseSchema)
async def get_invoice_details(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about an invoice, including discounts and taxes."""
    # Try to get from cache first
    cached_details = get_cached_invoice_details(invoice_id)
    if cached_details:
        # Convert to response model and add HATEOAS links
        response = InvoiceDetailsResponseSchema(**cached_details)
        
        # Add HATEOAS links
        add_resource_links(
            response=response,
            resource_path="/api/v1/billing/invoices",
            resource_id=invoice_id
        )
        
        add_link(
            response=response,
            rel="invoice",
            href=f"/api/v1/billing/invoices/{invoice_id}",
            method="GET",
            title="View basic invoice information"
        )
        
        add_link(
            response=response,
            rel="pdf",
            href=f"/api/v1/billing/invoices/{invoice_id}/pdf",
            method="GET",
            title="Get invoice as PDF"
        )
        
        add_link(
            response=response,
            rel="html",
            href=f"/api/v1/billing/invoices/{invoice_id}/html",
            method="GET",
            title="Get invoice as HTML"
        )
        
        # Add links to each discount
        if hasattr(response, "discounts") and response.discounts:
            for discount in response.discounts:
                add_link(
                    response=discount,
                    rel="self",
                    href=f"/api/v1/billing/discounts/{discount.id}",
                    method="GET",
                    title="View discount details"
                )
        
        # Add links to each tax
        if hasattr(response, "taxes") and response.taxes:
            for tax in response.taxes:
                add_link(
                    response=tax,
                    rel="self",
                    href=f"/api/v1/billing/taxes/{tax.id}",
                    method="GET",
                    title="View tax details"
                )
        
        # Add links to each credit note
        if hasattr(response, "credit_notes") and response.credit_notes:
            for credit_note in response.credit_notes:
                add_link(
                    response=credit_note,
                    rel="self",
                    href=f"/api/v1/billing/credit-notes/{credit_note.id}",
                    method="GET",
                    title="View credit note details"
                )
        
        return response
    
    # If not in cache, get from database
    billing_service = BillingService(db)
    invoice = billing_service.get_invoice(invoice_id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found"
        )
    
    # Check if the user has access to this invoice
    if current_user.id != invoice.user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this invoice"
        )
    
    # Get discounts
    discounts = db.query(InvoiceDiscount).filter(InvoiceDiscount.invoice_id == invoice_id).all()
    discount_details = []
    for discount in discounts:
        discount_detail = DiscountDetailSchema(
            id=discount.discount_id,
            name=discount.discount.name,
            description=discount.discount.description,
            amount=float(discount.amount),
            percentage=discount.discount.percentage
        )
        discount_details.append(discount_detail)
    
    # Get taxes
    taxes = db.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice_id).all()
    tax_details = []
    for tax in taxes:
        tax_detail = TaxDetailSchema(
            id=tax.tax_rate_id,
            name=tax.tax_rate.name,
            rate=tax.tax_rate.rate,
            amount=float(tax.amount)
        )
        tax_details.append(tax_detail)
    
    # Get credit notes applied to this invoice
    credit_notes = billing_service.get_credit_notes_for_invoice(invoice_id)
    credit_note_details = []
    for credit_note in credit_notes:
        credit_note_detail = CreditNoteDetailSchema(
            id=credit_note.id,
            amount=float(credit_note.amount),
            date_issued=credit_note.date_issued,
            reason=credit_note.reason
        )
        credit_note_details.append(credit_note_detail)
    
    # Calculate totals
    subtotal = float(invoice.amount)
    discount_total = sum(discount.amount for discount in discounts)
    tax_total = sum(tax.amount for tax in taxes)
    credit_note_total = sum(credit_note.amount for credit_note in credit_notes)
    
    total = subtotal - float(discount_total) + float(tax_total) - float(credit_note_total)
    
    # Create response
    response = InvoiceDetailsResponseSchema(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        customer_id=invoice.customer_id,
        amount=float(invoice.amount),
        status=invoice.status,
        due_date=invoice.due_date,
        issue_date=invoice.issue_date,
        discounts=discount_details,
        taxes=tax_details,
        credit_notes=credit_note_details,
        subtotal=subtotal,
        total_discounts=float(discount_total),
        total_taxes=float(tax_total),
        total_credit_notes=float(credit_note_total),
        final_amount=total
    )
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/billing/invoices",
        resource_id=invoice_id
    )
    
    add_link(
        response=response,
        rel="invoice",
        href=f"/api/v1/billing/invoices/{invoice_id}",
        method="GET",
        title="View basic invoice information"
    )
    
    add_link(
        response=response,
        rel="pdf",
        href=f"/api/v1/billing/invoices/{invoice_id}/pdf",
        method="GET",
        title="Get invoice as PDF"
    )
    
    add_link(
        response=response,
        rel="html",
        href=f"/api/v1/billing/invoices/{invoice_id}/html",
        method="GET",
        title="Get invoice as HTML"
    )
    
    add_link(
        response=response,
        rel="pay",
        href=f"/api/v1/billing/invoices/{invoice_id}/payments",
        method="POST",
        title="Make a payment for this invoice"
    )
    
    # Add links to each discount
    for discount in response.discounts:
        add_link(
            response=discount,
            rel="self",
            href=f"/api/v1/billing/discounts/{discount.id}",
            method="GET",
            title="View discount details"
        )
    
    # Add links to each tax
    for tax in response.taxes:
        add_link(
            response=tax,
            rel="self",
            href=f"/api/v1/billing/taxes/{tax.id}",
            method="GET",
            title="View tax details"
        )
    
    # Add links to each credit note
    for credit_note in response.credit_notes:
        add_link(
            response=credit_note,
            rel="self",
            href=f"/api/v1/billing/credit-notes/{credit_note.id}",
            method="GET",
            title="View credit note details"
        )
    
    # Cache the response for future requests
    cache_invoice_details(invoice_id, response)
    
    return response

# ... rest of the code remains the same ...
