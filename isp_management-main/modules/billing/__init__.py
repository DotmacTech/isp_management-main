"""
Billing module for ISP Management Platform.

This module handles all billing and financial aspects of the ISP operations,
including invoice generation, payment processing, and financial reporting.
"""

# Import the API router
from modules.billing.api.routes import router

# Import services for convenient access
from modules.billing.services import (
    InvoiceService,
    PaymentService,
    SubscriptionService,
    DiscountService,
    TaxService,
    ReportingService,
    BillingService
)

# Re-export for convenient access
__all__ = [
    'router',
    'InvoiceService',
    'PaymentService',
    'SubscriptionService',
    'DiscountService',
    'TaxService',
    'ReportingService',
    'BillingService'
]
