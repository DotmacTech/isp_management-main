# ISP Management Platform - Billing Module Documentation

## Overview

The Billing Module is a core component of the ISP Management Platform that handles all financial transactions between the ISP and its customers. This module has been enhanced to include advanced features such as discount management, credit notes, and tax calculations.

## Features

### 1. Invoice Management

- **Creation**: Automatically generate invoices for customers based on their subscription plans
- **Tracking**: Monitor the status of invoices (unpaid, paid, overdue, cancelled)
- **Payment Processing**: Record payments against invoices
- **Detailed View**: Get comprehensive invoice details including taxes, discounts, and credit notes

### 2. Discount Management

- **Types**: Support for percentage-based and fixed amount discounts
- **Time Validity**: Set valid from/to dates for discounts
- **Targeted Application**: Apply discounts to specific tariff plans
- **Invoice Application**: Apply discounts to individual invoices

### 3. Credit Notes

- **Issuance**: Create credit notes for customers (e.g., for service outages, overpayments)
- **Application**: Apply credit notes to invoices to reduce the amount due
- **Tracking**: Monitor remaining amounts on credit notes
- **Reference**: Link credit notes to original invoices when applicable

### 4. Tax Calculation

- **Tax Rates**: Define different tax rates based on country and region
- **Automatic Calculation**: Automatically apply appropriate taxes to invoices
- **Detailed Breakdown**: View detailed tax calculations on invoices

### 5. Performance Optimization

- **Caching**: Redis-based caching for frequently accessed data:
  - Tax rates by country/region
  - Active discounts
  - Invoice details
  - User credit notes
- **Database Indexing**: Strategic indexes on key fields to improve query performance
- **Efficient Queries**: Optimized database queries to reduce load on the database

## Database Schema

The billing module uses the following main tables:

- `invoices`: Stores invoice information
- `payments`: Records payments made against invoices
- `discounts`: Defines available discounts
- `invoice_discounts`: Links discounts to specific invoices
- `credit_notes`: Stores credit note information
- `credit_note_applications`: Records how credit notes are applied to invoices
- `tax_rates`: Defines tax rates for different regions
- `invoice_taxes`: Links tax calculations to specific invoices

## API Endpoints

### Invoice Endpoints

- `POST /api/billing/invoices`: Create a new invoice
- `GET /api/billing/invoices/{invoice_id}`: Get basic invoice information
- `GET /api/billing/invoices/{invoice_id}/details`: Get detailed invoice information including taxes, discounts, and credit notes
- `GET /api/billing/invoices/overdue`: Get list of overdue invoices
- `POST /api/billing/invoices/{invoice_id}/payments`: Record a payment for an invoice

### Discount Endpoints

- `POST /api/billing/discounts`: Create a new discount
- `GET /api/billing/discounts/{discount_id}`: Get discount information
- `GET /api/billing/discounts/active`: Get all currently active discounts
- `POST /api/billing/invoices/{invoice_id}/discounts`: Apply a discount to an invoice

### Credit Note Endpoints

- `POST /api/billing/credit-notes`: Create a new credit note
- `GET /api/billing/credit-notes/{credit_note_id}`: Get credit note information
- `GET /api/billing/users/{user_id}/credit-notes`: Get all credit notes for a user
- `POST /api/billing/invoices/{invoice_id}/credit-notes`: Apply a credit note to an invoice

### Tax Endpoints

- `POST /api/billing/tax-rates`: Create a new tax rate
- `GET /api/billing/tax-rates/{tax_rate_id}`: Get tax rate information
- `POST /api/billing/invoices/{invoice_id}/calculate-taxes`: Calculate taxes for an invoice

## Implementation Details

### Authorization

All billing endpoints require proper authorization:
- Regular users can only access their own billing information
- Staff and admin users can access billing information for any user

### Caching Strategy

The billing module implements a Redis-based caching system to improve performance for frequently accessed data:

1. **Tax Rates**: 
   - Cached by country/region with a 24-hour expiration
   - Automatically invalidated when new tax rates are created or updated

2. **Active Discounts**:
   - All active discounts cached with a 1-hour expiration
   - Refreshed when discounts are applied to invoices

3. **Invoice Details**:
   - Detailed invoice information cached with a 5-minute expiration
   - Invalidated whenever an invoice is modified (payments, discounts, taxes, etc.)

4. **User Credit Notes**:
   - User's credit notes cached with a 10-minute expiration
   - Invalidated when new credit notes are created or applied

### Database Indexing

To improve query performance, the following indexes have been added:

- `invoices`: Indexes on `user_id`, `status`, and `due_date`
- `credit_notes`: Indexes on `user_id` and `status`
- `tax_rates`: Indexes on `country` and `region`
- `discounts`: Indexes on `is_active`, `valid_from`, and `valid_to`

### Error Handling

The caching system is designed to be fault-tolerant:

- If Redis is unavailable, the system falls back to database queries
- Cache misses are logged for monitoring purposes
- All cache operations include error handling to prevent application failures

## Testing

The billing module includes comprehensive tests covering:
- Discount management
- Credit note creation and application
- Tax calculation
- Invoice detail retrieval with proper authorization

## Front-end Integration

The front-end application should implement the following views:
- Invoice list and detail view
- Payment form
- Discount management interface
- Credit note creation and application
- Tax rate configuration (admin only)

## Future Enhancements

Planned future enhancements for the billing module include:
- Recurring billing automation
- Payment gateway integration
- Invoice templating
- Multi-currency support
- Tax reporting
