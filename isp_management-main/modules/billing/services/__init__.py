"""
Billing services package.

This package contains all service classes for the billing module.
Services handle business logic and are used by API routes.
"""

from .invoice_service import InvoiceService
from .payment_service import PaymentService
from .subscription_service import SubscriptionService
from .discount_service import DiscountService
from .tax_service import TaxService
from .credit_service import CreditService
from .reporting_service import ReportingService


class BillingService:
    """
    Main billing service that combines all individual services.
    
    This service provides a unified interface to all billing operations.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize all sub-services."""
        self.invoice_service = InvoiceService(*args, **kwargs)
        self.payment_service = PaymentService(*args, **kwargs)
        self.subscription_service = SubscriptionService(*args, **kwargs)
        self.discount_service = DiscountService(*args, **kwargs)
        self.tax_service = TaxService(*args, **kwargs)
        self.credit_service = CreditService(*args, **kwargs)
        self.report_service = ReportingService(*args, **kwargs)


__all__ = [
    "InvoiceService",
    "PaymentService",
    "SubscriptionService",
    "DiscountService",
    "TaxService",
    "CreditService",
    "BillingService",
    "ReportingService",
]
