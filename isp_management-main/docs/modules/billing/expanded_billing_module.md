# Expanded Billing Module Documentation

## Overview

The expanded billing module enhances the ISP Management Platform with comprehensive financial management capabilities. This document provides detailed information on the new features, including subscription management, tax management, discount management, and financial reporting.

## Table of Contents

1. [Architecture](#architecture)
2. [Subscription Management](#subscription-management)
3. [Tax Management](#tax-management)
4. [Discount Management](#discount-management)
5. [Financial Reporting](#financial-reporting)
6. [API Reference](#api-reference)
7. [Integration Examples](#integration-examples)
8. [Testing](#testing)

## Architecture

The expanded billing module follows the modular architecture of the ISP Management Platform. Each feature is implemented as a separate service with its own models, schemas, and endpoints, but they all integrate seamlessly with the core billing functionality.

```
modules/billing/
├── models.py                  # Database models
├── schemas/                   # Pydantic schemas
│   ├── __init__.py            # Schema exports
│   ├── subscription.py        # Subscription schemas
│   ├── tax.py                 # Tax schemas
│   ├── discount.py            # Discount schemas
│   └── reporting.py           # Reporting schemas
├── services/                  # Business logic
│   ├── subscription_service.py # Subscription management
│   ├── tax_service.py         # Tax management
│   ├── discount_service.py    # Discount management
│   └── reporting_service.py   # Financial reporting
└── endpoints.py               # API endpoints
```

## Subscription Management

The subscription management service handles the entire lifecycle of customer subscriptions, from creation to cancellation, with support for various billing models.

### Key Features

- **Subscription Creation and Management**: Create, update, and manage customer subscriptions
- **Billing Cycles**: Support for monthly, quarterly, and annual billing cycles
- **Plan Changes**: Upgrade or downgrade between subscription plans with prorated billing
- **Subscription Status**: Track active, paused, cancelled, and expired subscriptions
- **Usage-Based Billing**: Record and bill for metered services based on actual usage
- **Recurring Billing Profiles**: Manage recurring payment settings for subscriptions

### Usage Examples

#### Creating a Subscription

```python
from modules.billing.services.subscription_service import SubscriptionService
from modules.billing.schemas.subscription import SubscriptionCreate

subscription_service = SubscriptionService(db_session)

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

#### Pausing a Subscription

```python
subscription = subscription_service.pause_subscription(
    subscription_id=1,
    pause_days=30,
    reason="Customer request"
)
```

#### Recording Usage for Metered Billing

```python
from modules.billing.schemas.subscription import UsageRecordCreate

usage_data = UsageRecordCreate(
    subscription_id=1,
    metric="bandwidth",
    quantity=150.5,  # e.g., 150.5 GB
    timestamp=datetime.now()
)

usage_record = subscription_service.record_usage(usage_data)
```

## Tax Management

The tax management service provides comprehensive tax handling capabilities, including tax rate configuration, exemption management, and tax calculation.

### Key Features

- **Tax Rate Management**: Configure tax rates for different countries and regions
- **Tax Exemptions**: Manage tax exemptions for eligible customers
- **Tax Calculation**: Calculate applicable taxes based on customer location and exemption status
- **Tax Reporting**: Generate tax reports for compliance purposes

### Usage Examples

#### Creating a Tax Rate

```python
from modules.billing.services.tax_service import TaxService
from modules.billing.schemas.tax import TaxRateCreate

tax_service = TaxService(db_session)

tax_rate_data = TaxRateCreate(
    name="VAT",
    description="Value Added Tax",
    rate=Decimal("0.20"),
    country="GB",
    is_default=True
)

tax_rate = tax_service.create_tax_rate(tax_rate_data)
```

#### Creating a Tax Exemption

```python
from modules.billing.schemas.tax import TaxExemptionCreate

exemption_data = TaxExemptionCreate(
    user_id=1,
    tax_rate_id=2,
    exemption_certificate="EXEMPT-12345",
    valid_from=datetime.now(),
    valid_to=datetime.now() + timedelta(days=365)
)

exemption = tax_service.create_tax_exemption(exemption_data)
```

#### Calculating Tax

```python
tax_calculation = tax_service.calculate_tax(
    amount=Decimal("100.00"),
    country="US",
    region="CA",  # California
    user_id=1     # Optional, to check for exemptions
)

print(f"Total tax: {tax_calculation['total_tax']}")
```

## Discount Management

The discount service manages various types of discounts, including promotional codes, referral discounts, and loyalty discounts.

### Key Features

- **Discount Types**: Support for different discount types (promotional, referral, loyalty)
- **Discount Application**: Apply discounts to invoices or subscription plans
- **Validation Rules**: Set validity periods, usage limits, and minimum order amounts
- **Discount Tracking**: Track discount usage and effectiveness

### Usage Examples

#### Creating a Discount

```python
from modules.billing.services.discount_service import DiscountService
from modules.billing.schemas.discount import DiscountCreate
from modules.billing.models import DiscountType, DiscountStatus

discount_service = DiscountService(db_session)

discount_data = DiscountCreate(
    name="Summer Promotion",
    description="Summer 2025 promotional discount",
    discount_type=DiscountType.PROMOTIONAL,
    amount=Decimal("15.00"),
    is_percentage=True,
    code="SUMMER25",
    valid_from=datetime.now(),
    valid_to=datetime.now() + timedelta(days=90),
    max_uses=500,
    max_uses_per_user=1,
    min_order_amount=Decimal("50.00"),
    status=DiscountStatus.ACTIVE
)

discount = discount_service.create_discount(discount_data)
```

#### Validating a Discount Code

```python
validation = discount_service.validate_discount_code(
    code="SUMMER25",
    user_id=1,
    amount=Decimal("75.00"),
    plan_id=None
)

if validation["valid"]:
    print(f"Discount amount: {validation['discount_amount']}")
else:
    print(f"Invalid discount: {validation['reason']}")
```

#### Calculating Discount Amount

```python
calculation = discount_service.calculate_discount_amount(
    discount_id=1,
    base_amount=Decimal("100.00")
)

print(f"Final amount after discount: {calculation['final_amount']}")
```

## Financial Reporting

The reporting service generates comprehensive financial reports, including revenue summaries, subscription metrics, and financial statements.

### Key Features

- **Revenue Reports**: Generate revenue summaries and breakdowns by period and service
- **Subscription Metrics**: Track subscription growth, churn rates, and recurring revenue
- **Accounts Receivable**: Analyze accounts receivable aging
- **Financial Statements**: Generate income statements and balance sheets
- **Customer Metrics**: Calculate customer lifetime value and average revenue per customer
- **Data Export**: Export financial data for external analysis

### Usage Examples

#### Generating a Revenue Summary

```python
from modules.billing.services.reporting_service import ReportingService

reporting_service = ReportingService(db_session)

start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now()

revenue_summary = reporting_service.get_revenue_summary(start_date, end_date)

print(f"Total revenue: {revenue_summary['paid_amount']}")
print(f"Collection rate: {revenue_summary['collection_rate']}%")
```

#### Analyzing Subscription Growth

```python
subscription_growth = reporting_service.get_subscription_growth(
    start_date=datetime.now() - timedelta(days=90),
    end_date=datetime.now(),
    period="month"
)

for period in subscription_growth:
    print(f"{period['period']}: Net change: {period['net_change']}")
```

#### Calculating Customer Lifetime Value

```python
clv = reporting_service.get_customer_lifetime_value(user_id=1)

print(f"Customer lifetime value: ${clv['estimated_lifetime_value']}")
```

## API Reference

The expanded billing module provides a comprehensive set of RESTful API endpoints for interacting with the various services.

### Subscription Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/billing/subscriptions` | POST | Create a new subscription |
| `/api/billing/subscriptions/{subscription_id}` | GET | Get subscription by ID |
| `/api/billing/users/{user_id}/subscriptions` | GET | Get all subscriptions for a user |
| `/api/billing/subscriptions/{subscription_id}` | PUT | Update a subscription |
| `/api/billing/subscriptions/{subscription_id}/cancel` | POST | Cancel a subscription |
| `/api/billing/subscriptions/{subscription_id}/pause` | POST | Pause a subscription |
| `/api/billing/subscriptions/{subscription_id}/resume` | POST | Resume a paused subscription |
| `/api/billing/subscriptions/{subscription_id}/change-plan` | POST | Change subscription plan |
| `/api/billing/billing-profiles` | POST | Create a recurring billing profile |
| `/api/billing/users/{user_id}/billing-profiles` | GET | Get all billing profiles for a user |
| `/api/billing/subscriptions/{subscription_id}/usage` | POST | Record usage for metered billing |
| `/api/billing/subscriptions/{subscription_id}/usage` | GET | Get usage records for a subscription |

### Tax Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/billing/tax-rates` | POST | Create a new tax rate |
| `/api/billing/tax-rates/{tax_rate_id}` | GET | Get tax rate by ID |
| `/api/billing/tax-rates` | GET | Get all tax rates, optionally filtered by country/region |
| `/api/billing/tax-rates/{tax_rate_id}` | PUT | Update a tax rate |
| `/api/billing/tax-rates/{tax_rate_id}` | DELETE | Delete a tax rate |
| `/api/billing/tax-exemptions` | POST | Create a tax exemption for a user |
| `/api/billing/users/{user_id}/tax-exemptions` | GET | Get all tax exemptions for a user |
| `/api/billing/tax/calculate` | POST | Calculate tax for a given amount and location |

### Discount Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/billing/discounts` | POST | Create a new discount |
| `/api/billing/discounts/{discount_id}` | GET | Get discount by ID |
| `/api/billing/discounts` | GET | Get all active discounts |
| `/api/billing/discounts/{discount_id}` | PUT | Update a discount |
| `/api/billing/discounts/validate` | POST | Validate a discount code |
| `/api/billing/discounts/calculate` | POST | Calculate discount amount |
| `/api/billing/invoices/{invoice_id}/discounts/{discount_id}` | POST | Apply discount to invoice |
| `/api/billing/discounts/referral/{user_id}` | POST | Create a referral discount for a user |

### Reporting Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/billing/reports/revenue-summary` | POST | Get a summary of revenue for a date range |
| `/api/billing/reports/revenue-by-period` | POST | Get revenue broken down by period |
| `/api/billing/reports/revenue-by-service` | POST | Get revenue broken down by service type |
| `/api/billing/reports/payment-methods` | POST | Get distribution of payments by payment method |
| `/api/billing/reports/subscription-metrics` | GET | Get metrics about subscriptions |
| `/api/billing/reports/subscription-growth` | POST | Get subscription growth over time |
| `/api/billing/reports/churn-rate` | POST | Get churn rate over time |
| `/api/billing/reports/accounts-receivable-aging` | GET | Get accounts receivable aging report |
| `/api/billing/reports/financial-statement` | POST | Generate a financial statement |
| `/api/billing/reports/customer-lifetime-value` | POST | Calculate customer lifetime value |
| `/api/billing/reports/export` | POST | Export financial data for external use |

## Integration Examples

### Integration with Payment Gateways

The expanded billing module is designed to integrate with various payment gateways. Here's an example of how to integrate with a payment gateway when processing a payment:

```python
from modules.billing.services import BillingService
from modules.billing.schemas import PaymentCreate

billing_service = BillingService(db_session)

payment_data = PaymentCreate(
    invoice_id=1,
    user_id=1,
    amount=Decimal("100.00"),
    payment_method="credit_card",
    payment_details={
        "card_token": "tok_visa",
        "gateway": "stripe"
    }
)

payment = billing_service.process_payment(payment_data)
```

### Integration with CRM Module

The billing module can be integrated with the CRM module to provide a complete view of customer financial information:

```python
from modules.billing.services.subscription_service import SubscriptionService
from modules.crm.services.customer_service import CustomerService

subscription_service = SubscriptionService(db_session)
customer_service = CustomerService(db_session)

# Get customer information
customer = customer_service.get_customer(customer_id=1)

# Get customer's subscriptions
subscriptions = subscription_service.get_user_subscriptions(customer.user_id)

# Display customer with subscription information
customer_data = {
    "customer": customer,
    "subscriptions": subscriptions
}
```

### Integration with Monitoring Module

The billing module can be integrated with the monitoring module to automatically record usage for metered billing:

```python
from modules.billing.services.subscription_service import SubscriptionService
from modules.billing.schemas.subscription import UsageRecordCreate
from modules.monitoring.services.bandwidth_service import BandwidthService

subscription_service = SubscriptionService(db_session)
bandwidth_service = BandwidthService(db_session)

# Get bandwidth usage for a user
user_id = 1
bandwidth_usage = bandwidth_service.get_user_bandwidth_usage(user_id)

# Get the user's subscription
subscriptions = subscription_service.get_user_subscriptions(user_id)
if subscriptions:
    # Record usage for the first active subscription
    usage_data = UsageRecordCreate(
        subscription_id=subscriptions[0].id,
        metric="bandwidth",
        quantity=bandwidth_usage.total_gb,
        timestamp=datetime.now()
    )
    
    usage_record = subscription_service.record_usage(usage_data)
```

## Testing

The expanded billing module includes comprehensive tests to ensure all functionality works as expected. The tests are located in the `tests/modules/billing/` directory.

### Running the Tests

To run the tests for the expanded billing module:

```bash
pytest tests/modules/billing/test_expanded_billing.py
```

### Test Coverage

The tests cover all major functionality of the expanded billing module:

- Subscription management (creation, cancellation, pausing, resuming, plan changes)
- Tax management (tax rates, exemptions, calculations)
- Discount management (creation, validation, calculations)
- Financial reporting (revenue summaries, subscription metrics)
- API endpoints (request validation, response formatting)

### Writing New Tests

When adding new functionality to the billing module, make sure to add corresponding tests. Here's an example of how to structure a new test:

```python
def test_new_feature(db_session, test_user):
    """Test the new feature."""
    # Setup
    service = RelevantService(db_session)
    
    # Create test data
    test_data = {...}
    
    # Execute the feature
    result = service.new_feature(test_data)
    
    # Assert the results
    assert result is not None
    assert result.some_property == expected_value
    
    # Clean up
    db_session.delete(result)
    db_session.commit()
```
