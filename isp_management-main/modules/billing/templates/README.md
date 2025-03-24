# Billing Module Templating System

This directory contains the templates used by the billing module for generating dynamic content such as invoices, email notifications, and reports.

## Directory Structure

- **invoices/**: Templates for generating invoice documents
- **emails/**: Templates for email notifications
- **reports/**: Templates for billing reports

## Template Usage

Templates are rendered using Jinja2 and can be accessed through the `template_service.py` module. The service provides functions for rendering templates and caching the rendered output for improved performance.

### Available Templates

1. **Invoice Template** (`invoices/invoice_template.html`)
   - Used for generating HTML and PDF invoices
   - Context variables:
     - `invoice`: Invoice details (id, amount, status, etc.)
     - `customer`: Customer details (name, email, address, etc.)
     - `invoice_items`: List of items in the invoice
     - `discounts`: List of applied discounts
     - `taxes`: List of applied taxes
     - `payments`: List of payments made for the invoice
     - `balance_due`: Remaining balance to be paid

2. **Invoice Reminder Email** (`emails/invoice_reminder.html`)
   - Used for sending reminder emails for overdue invoices
   - Context variables:
     - `invoice`: Invoice details with balance_due
     - `customer`: Customer details
     - `days_overdue`: Number of days the invoice is overdue
     - `payment_link`: Link to the payment page

3. **Monthly Billing Report** (`reports/monthly_billing_report.html`)
   - Used for generating monthly billing reports
   - Context variables:
     - `month_name`: Name of the month
     - `year`: Year of the report
     - `generation_date`: Date when the report was generated
     - `total_revenue`: Total revenue for the month
     - `invoice_count`: Number of invoices generated
     - `payment_count`: Number of payments received
     - `outstanding_amount`: Total outstanding amount
     - `revenue_categories`: Revenue breakdown by category
     - `payment_methods`: Payment method distribution
     - `invoice_statuses`: Invoice status distribution
     - `top_customers`: List of top customers by revenue

## Custom Filters

The following custom filters are available in templates:

- `date`: Format a datetime object as a date string
- `format_currency`: Format a decimal value as a currency string
- `nl2br`: Convert newlines to HTML line breaks

## Caching

Rendered templates are cached in Redis to improve performance. The cache is invalidated in the following scenarios:

1. When a template file is modified
2. When explicitly requested via the API
3. On a scheduled basis (weekly)

## Extending the System

### Adding a New Template

1. Create a new HTML template in the appropriate directory
2. Add a rendering function in `template_service.py`
3. Update the API endpoints in `endpoints.py` to expose the new template
4. Update the documentation in this README

### Modifying an Existing Template

1. Edit the HTML template file
2. Invalidate the cache by calling `invalidate_template_cache()`
3. Update the documentation if necessary

## API Endpoints

The following API endpoints are available for accessing the templates:

- `GET /api/billing/invoices/{invoice_id}/html`: Get HTML representation of an invoice
- `GET /api/billing/invoices/{invoice_id}/pdf`: Get PDF representation of an invoice
- `GET /api/billing/invoices/{invoice_id}/email-reminder`: Get HTML email reminder for an invoice
- `POST /api/billing/reports/monthly`: Generate a monthly billing report
- `POST /api/billing/cache/clear`: Clear the template cache

## Scheduled Tasks

The following Celery tasks are scheduled for automatic template processing:

- `send_invoice_reminders`: Sends reminder emails for overdue invoices (daily at 9:00 AM)
- `generate_monthly_billing_report`: Generates monthly billing reports (1st of each month at 1:00 AM)
- `clear_template_cache`: Clears the template cache (weekly on Sunday at 2:00 AM)
