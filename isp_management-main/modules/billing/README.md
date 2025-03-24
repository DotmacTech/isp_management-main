# ISP Management Platform - Billing Module

## Overview

The Billing Module is a core component of the ISP Management Platform, responsible for handling all financial transactions between the ISP and its customers. This module provides comprehensive billing capabilities including invoice generation, payment processing, subscription management, tax management, discount management, credit notes, and financial reporting.

## Features

### Invoice Management
- Create, retrieve, update, and delete invoices
- Track invoice status (unpaid, paid, overdue, cancelled)
- Generate detailed invoice reports
- Export invoices as HTML and PDF

### Payment Processing
- Record and track customer payments
- Support multiple payment methods
- Automatic invoice status updates upon payment
- Payment gateway integration

### Subscription Management
- Create and manage customer subscriptions
- Support for different billing cycles (monthly, quarterly, annual)
- Subscription plan changes (upgrades/downgrades)
- Pause and resume subscriptions
- Usage-based billing with metered services
- Recurring billing profiles

### Tax Management
- Configure tax rates based on country and region
- Manage tax exemptions for specific customers
- Automatically calculate and apply taxes to invoices
- Generate tax reports for compliance

### Discount Management
- Create and manage various types of discounts (fixed amount, percentage)
- Support for promotional codes, referral discounts, and loyalty discounts
- Set validity periods and usage limits for discounts
- Apply discounts to specific invoices or subscription plans
- Track discount usage

### Credit Notes
- Issue credit notes to customers for refunds or adjustments
- Apply credit notes to future invoices
- Track remaining credit note balance
- View credit note history by user

### Financial Reporting
- Generate revenue summaries and breakdowns
- Track subscription metrics and growth
- Calculate churn rates
- Accounts receivable aging reports
- Financial statements (income, balance)
- Customer lifetime value analysis
- Export financial data for external use

## API Endpoints

### Invoice Endpoints
- `POST /invoices` - Create a new invoice
- `GET /invoices/{invoice_id}` - Get invoice by ID
- `GET /users/{user_id}/invoices` - Get all invoices for a user
- `GET /invoices/overdue` - Get all overdue invoices
- `GET /invoices/{invoice_id}/details` - Get detailed invoice information
- `GET /invoices/{invoice_id}/html` - Get HTML representation of an invoice
- `GET /invoices/{invoice_id}/pdf` - Get PDF representation of an invoice

### Payment Endpoints
- `POST /payments` - Record a new payment
- `GET /payments/{payment_id}` - Get payment by ID
- `GET /users/{user_id}/payments` - Get all payments for a user

### Subscription Endpoints
- `POST /subscriptions` - Create a new subscription
- `GET /subscriptions/{subscription_id}` - Get subscription by ID
- `GET /users/{user_id}/subscriptions` - Get all subscriptions for a user
- `PUT /subscriptions/{subscription_id}` - Update a subscription
- `POST /subscriptions/{subscription_id}/cancel` - Cancel a subscription
- `POST /subscriptions/{subscription_id}/pause` - Pause a subscription
- `POST /subscriptions/{subscription_id}/resume` - Resume a paused subscription
- `POST /subscriptions/{subscription_id}/change-plan` - Change subscription plan
- `POST /billing-profiles` - Create a recurring billing profile
- `GET /users/{user_id}/billing-profiles` - Get all billing profiles for a user
- `POST /subscriptions/{subscription_id}/usage` - Record usage for metered billing
- `GET /subscriptions/{subscription_id}/usage` - Get usage records for a subscription

### Discount Endpoints
- `POST /discounts` - Create a new discount
- `GET /discounts/{discount_id}` - Get discount by ID
- `GET /discounts` - Get all active discounts
- `PUT /discounts/{discount_id}` - Update a discount
- `POST /discounts/validate` - Validate a discount code
- `POST /discounts/calculate` - Calculate discount amount
- `POST /invoices/{invoice_id}/discounts/{discount_id}` - Apply discount to invoice
- `POST /discounts/referral/{user_id}` - Create a referral discount for a user

### Credit Note Endpoints
- `POST /credit-notes` - Create a new credit note
- `GET /credit-notes/{credit_note_id}` - Get credit note by ID
- `GET /users/{user_id}/credit-notes` - Get all credit notes for a user
- `POST /credit-notes/{credit_note_id}/apply/{invoice_id}` - Apply credit note to invoice

### Tax Endpoints
- `POST /tax-rates` - Create a new tax rate
- `GET /tax-rates/{tax_rate_id}` - Get tax rate by ID
- `GET /tax-rates` - Get all tax rates, optionally filtered by country/region
- `PUT /tax-rates/{tax_rate_id}` - Update a tax rate
- `DELETE /tax-rates/{tax_rate_id}` - Delete a tax rate
- `POST /tax-exemptions` - Create a tax exemption for a user
- `GET /users/{user_id}/tax-exemptions` - Get all tax exemptions for a user
- `POST /tax/calculate` - Calculate tax for a given amount and location

### Reporting Endpoints
- `POST /reports/revenue-summary` - Get a summary of revenue for a date range
- `POST /reports/revenue-by-period` - Get revenue broken down by period
- `POST /reports/revenue-by-service` - Get revenue broken down by service type
- `POST /reports/payment-methods` - Get distribution of payments by payment method
- `GET /reports/subscription-metrics` - Get metrics about subscriptions
- `POST /reports/subscription-growth` - Get subscription growth over time
- `POST /reports/churn-rate` - Get churn rate over time
- `GET /reports/accounts-receivable-aging` - Get accounts receivable aging report
- `POST /reports/financial-statement` - Generate a financial statement
- `POST /reports/customer-lifetime-value` - Calculate customer lifetime value
- `POST /reports/export` - Export financial data for external use

## Database Models

The billing module uses the following database models:

- `Invoice` - Stores invoice information
- `Payment` - Records payment details
- `Discount` - Defines discount types and values
- `InvoiceDiscount` - Links discounts to invoices
- `CreditNote` - Stores credit note information
- `CreditNoteApplication` - Records credit note applications to invoices
- `TaxRate` - Defines tax rates by country/region
- `TaxExemption` - Stores tax exemptions for users
- `InvoiceTax` - Links taxes to invoices
- `Subscription` - Stores subscription information
- `SubscriptionPlan` - Defines available subscription plans
- `RecurringBillingProfile` - Stores recurring billing settings
- `UsageRecord` - Records usage for metered billing

## Implementation Details

### Subscription Management

The subscription management service handles the entire lifecycle of a subscription, including:
- Creating new subscriptions
- Updating subscription details
- Processing subscription cancellations, pauses, and resumes
- Handling plan changes (upgrades/downgrades)
- Managing recurring billing profiles
- Recording and calculating usage-based charges

### Tax Management

The tax management service provides comprehensive tax handling capabilities:
- Managing tax rates for different countries and regions
- Processing tax exemptions for eligible customers
- Calculating applicable taxes based on customer location and exemption status
- Generating tax reports for compliance purposes

### Discount Management

The discount service manages various types of discounts:
- Promotional codes with validity periods and usage limits
- Referral discounts for customer acquisition
- Loyalty discounts for customer retention
- Validation of discount eligibility
- Tracking discount usage and effectiveness

### Financial Reporting

The reporting service generates comprehensive financial reports:
- Revenue summaries and breakdowns by period and service
- Subscription metrics including growth and churn
- Accounts receivable aging analysis
- Financial statements for accounting purposes
- Customer lifetime value calculations
- Data export capabilities for external analysis

## Usage Examples

### Creating a Subscription

```python
from modules.billing.services.subscription_service import SubscriptionService
from modules.billing.schemas.subscription import SubscriptionCreate
from datetime import datetime, timedelta

# Initialize the subscription service
subscription_service = SubscriptionService(db_session)

# Create a new subscription
subscription_data = SubscriptionCreate(
    user_id=1,
    plan_id=2,
    start_date=datetime.now(),
    billing_cycle="monthly",
    auto_renew=True,
    payment_method_id=1
)
subscription = subscription_service.create_subscription(subscription_data)
```

### Applying a Discount to an Invoice

```python
from modules.billing.services import BillingService

# Initialize the billing service
billing_service = BillingService(db_session)

# Apply a discount to an invoice
billing_service.apply_discount_to_invoice(invoice_id=1, discount_id=2)
```

### Creating and Applying a Credit Note

```python
from modules.billing.services import BillingService
from modules.billing.schemas import CreditNoteCreate
from decimal import Decimal

# Initialize the billing service
billing_service = BillingService(db_session)

# Create a credit note
credit_note_data = CreditNoteCreate(
    user_id=1,
    amount=Decimal("50.00"),
    reason="Service outage compensation"
)
credit_note = billing_service.create_credit_note(credit_note_data)

# Apply the credit note to an invoice
billing_service.apply_credit_note_to_invoice(
    credit_note_id=credit_note.id,
    invoice_id=1,
    amount=Decimal("25.00")  # Apply partial amount
)
```

### Calculating Taxes

```python
from modules.billing.services.tax_service import TaxService
from decimal import Decimal

# Initialize the tax service
tax_service = TaxService(db_session)

# Calculate tax for an amount
tax_calculation = tax_service.calculate_tax(
    amount=Decimal("100.00"),
    country="US",
    region="CA",  # California
    user_id=1  # Optional, to check for exemptions
)
```

### Generating a Revenue Report

```python
from modules.billing.services.reporting_service import ReportingService
from datetime import datetime, timedelta

# Initialize the reporting service
reporting_service = ReportingService(db_session)

# Get revenue summary for the last month
start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now()
revenue_summary = reporting_service.get_revenue_summary(start_date, end_date)
```

## Testing

The billing module includes comprehensive unit tests to ensure all functionality works as expected. Run the tests using pytest:

```bash
pytest tests/modules/billing/
```

## Future Enhancements

- Enhanced payment gateway integrations
- Multi-currency support
- Advanced dunning management
- Installment payment plans
- Dynamic pricing models
- AI-powered revenue optimization
- Enhanced fraud detection
