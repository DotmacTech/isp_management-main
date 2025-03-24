"""
Billing module models package.

This package contains all database models for the billing module.
"""

# Import enum classes
from modules.billing.models.enums import (
    BillingCycle,
    PaymentMethod,
    PaymentStatus,
    InvoiceStatus,
    SubscriptionStatus,
    DiscountType,
    DiscountStatus
)

# Import model classes from individual modules
from modules.billing.models.invoice import Invoice, InvoiceItem, CreditNote
from modules.billing.models.payment import Payment, PaymentRefund, PaymentTransaction, Refund
from modules.billing.models.subscription import (
    Subscription, 
    SubscriptionHistory, 
    RecurringBillingProfile, 
    UsageRecord
)
from modules.billing.models.tax import TaxRate, TaxExemption, TaxTransaction
from modules.billing.models.discount import Discount, DiscountUsage
from modules.billing.models.invoice_template import InvoiceTemplate
from modules.billing.models.payment_reminder import PaymentReminder
from modules.billing.models.payment_gateway import PaymentGatewayConfig
from modules.billing.models.tariff import TariffPlan, TariffFeature, TariffOverage, TieredPricing
from modules.billing.models.financial_transaction import FinancialTransaction, AccountingIntegration

# Expose all model classes at the package level
__all__ = [
    # Enum classes
    "BillingCycle",
    "PaymentMethod",
    "PaymentStatus", 
    "InvoiceStatus",
    "SubscriptionStatus",
    "DiscountType",
    "DiscountStatus",
    
    # Invoice models
    "Invoice",
    "InvoiceItem",
    "CreditNote",
    "InvoiceTemplate",
    
    # Payment models
    "Payment",
    "PaymentRefund",
    "PaymentTransaction",
    "Refund",
    "PaymentReminder",
    "PaymentGatewayConfig",
    
    # Subscription models
    "Subscription",
    "SubscriptionHistory",
    "RecurringBillingProfile",
    "UsageRecord",
    
    # Tax models
    "TaxRate",
    "TaxExemption",
    "TaxTransaction",
    
    # Discount models
    "Discount",
    "DiscountUsage",
    
    # Tariff models
    "TariffPlan",
    "TariffFeature", 
    "TariffOverage",
    "TieredPricing",
    
    # Financial & Accounting models
    "FinancialTransaction",
    "AccountingIntegration",
]
