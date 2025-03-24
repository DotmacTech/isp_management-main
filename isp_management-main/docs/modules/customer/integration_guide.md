# Customer Management Module Integration Guide

This guide explains how to integrate the Customer Management Module with other modules in the ISP Management Platform.

## Table of Contents

1. [Overview](#overview)
2. [Integration with Billing Module](#integration-with-billing-module)
3. [Integration with Tariff Module](#integration-with-tariff-module)
4. [Integration with RADIUS & AAA Module](#integration-with-radius--aaa-module)
5. [Integration with Monitoring Module](#integration-with-monitoring-module)
6. [Integration with Reseller Module](#integration-with-reseller-module)
7. [Event-Based Communication](#event-based-communication)
8. [API Integration](#api-integration)
9. [Troubleshooting](#troubleshooting)

## Overview

The Customer Management Module serves as a central repository for customer data within the ISP Management Platform. It provides APIs and events that other modules can use to access and update customer information.

### Key Integration Points

- **Customer Identity**: Unique customer identifiers used across all modules
- **Customer Status**: Active/Inactive status affecting service availability
- **Subscription State**: Current subscription state affecting billing and service access
- **Customer Documents**: Verification documents that may be required for service activation
- **Communication Preferences**: How and when to contact customers

## Integration with Billing Module

### Customer to Billing Relationship

The Billing Module relies on customer data for:
- Generating invoices
- Processing payments
- Managing billing addresses
- Handling billing notifications

### Integration Steps

1. **Customer Creation Event**:
   - When a new customer is created, the Customer Module emits a `customer.created` event
   - The Billing Module listens for this event and creates a corresponding billing account

2. **Address Updates**:
   - When a billing address is updated, the Customer Module emits a `customer.address.updated` event
   - The Billing Module updates the billing address for future invoices

3. **Subscription State Changes**:
   - When a customer's subscription state changes, the Billing Module is notified
   - Billing adjusts invoicing based on the new subscription state

### API Endpoints

- `GET /api/billing/customers/{customer_id}/invoices`: Get all invoices for a customer
- `POST /api/billing/customers/{customer_id}/payments`: Process a payment for a customer

### Code Example

```python
# In Billing Module
from isp_management.modules.customer.models import Customer
from isp_management.modules.customer.services import CustomerService

async def create_billing_account(customer_id: int):
    """Create a billing account for a customer."""
    customer_service = CustomerService()
    customer = await customer_service.get_customer(session, customer_id)
    
    # Create billing account using customer data
    billing_account = BillingAccount(
        customer_id=customer.id,
        email=customer.email,
        status=map_customer_status_to_billing_status(customer.status)
    )
    
    session.add(billing_account)
    await session.commit()
    return billing_account
```

## Integration with Tariff Module

### Customer to Tariff Relationship

The Tariff Module uses customer data for:
- Assigning tariff plans to customers
- Enforcing Fair Usage Policies (FUP)
- Managing service upgrades/downgrades
- Tracking usage against tariff limits

### Integration Steps

1. **Tariff Plan Assignment**:
   - The Tariff Module assigns plans to customers via the Customer API
   - Updates to tariff plans trigger subscription state updates

2. **Usage Tracking**:
   - The Tariff Module records usage data linked to customer IDs
   - FUP enforcement uses customer subscription state information

### API Endpoints

- `GET /api/tariff/customers/{customer_id}/plans`: Get all tariff plans for a customer
- `POST /api/tariff/customers/{customer_id}/plans`: Assign a tariff plan to a customer

### Code Example

```python
# In Tariff Module
from isp_management.modules.customer.services import CustomerService

async def assign_tariff_plan(customer_id: int, tariff_plan_id: int):
    """Assign a tariff plan to a customer."""
    customer_service = CustomerService()
    
    # First check if customer exists and is active
    customer = await customer_service.get_customer(session, customer_id)
    if customer.status != CustomerStatus.ACTIVE:
        raise ValidationException("Cannot assign tariff plan to inactive customer")
    
    # Assign tariff plan
    user_tariff_plan = UserTariffPlan(
        customer_id=customer_id,
        tariff_plan_id=tariff_plan_id,
        start_date=datetime.utcnow()
    )
    
    session.add(user_tariff_plan)
    await session.commit()
    
    # Update customer subscription state
    await customer_service.update_subscription_state(
        session=session,
        customer_id=customer_id,
        subscription_state=SubscriptionState.ACTIVE,
        update_dates=True
    )
    
    return user_tariff_plan
```

## Integration with RADIUS & AAA Module

### Customer to RADIUS Relationship

The RADIUS Module uses customer data for:
- Authentication of customers
- Authorization of service access
- Accounting for service usage
- Enforcing service restrictions

### Integration Steps

1. **Customer Authentication**:
   - RADIUS uses customer credentials for authentication
   - Customer status determines if authentication is allowed

2. **Service Authorization**:
   - Customer subscription state determines service access
   - Document verification status may affect service levels

### API Endpoints

- `GET /api/radius/customers/{customer_id}/sessions`: Get active RADIUS sessions for a customer
- `POST /api/radius/customers/{customer_id}/authorize`: Check if a customer is authorized for service

### Code Example

```python
# In RADIUS Module
from isp_management.modules.customer.services import CustomerService

async def authenticate_customer(username: str, password: str):
    """Authenticate a customer for RADIUS access."""
    customer_service = CustomerService()
    
    # Find customer by username
    customer = await customer_service.get_customer_by_username(session, username)
    if not customer:
        return False
    
    # Check if customer is active and subscription is valid
    if (customer.status != CustomerStatus.ACTIVE or 
            customer.subscription_state != SubscriptionState.ACTIVE):
        return False
    
    # Verify password
    if not verify_password(password, customer.password_hash):
        return False
    
    return True
```

## Integration with Monitoring Module

### Customer to Monitoring Relationship

The Monitoring Module uses customer data for:
- Tracking customer-specific metrics
- Alerting based on customer preferences
- Service quality monitoring
- Usage pattern analysis

### Integration Steps

1. **Customer-Specific Monitoring**:
   - Monitoring uses customer IDs to associate metrics with customers
   - Customer service addresses determine network segments to monitor

2. **Alert Notifications**:
   - Communication preferences determine how alerts are sent
   - Customer status affects alert priority

### API Endpoints

- `GET /api/monitoring/customers/{customer_id}/metrics`: Get monitoring metrics for a customer
- `POST /api/monitoring/customers/{customer_id}/alerts`: Create an alert for a customer

### Code Example

```python
# In Monitoring Module
from isp_management.modules.customer.services import CustomerService
from isp_management.modules.customer.communication_service import CommunicationService

async def send_customer_alert(customer_id: int, alert_type: str, alert_message: str):
    """Send an alert to a customer based on their communication preferences."""
    customer_service = CustomerService()
    communication_service = CommunicationService()
    
    # Get customer and their communication preferences
    customer = await customer_service.get_customer(session, customer_id)
    preferences = await communication_service.get_customer_preferences(session, customer_id)
    
    # Determine which channels to use for the alert
    channels = []
    for preference in preferences:
        if preference.enabled and preference.emergency_alerts:
            channels.append(preference.communication_type)
    
    # Send the alert through each enabled channel
    for channel in channels:
        if channel == CommunicationType.EMAIL and customer.email:
            await send_email_alert(customer.email, alert_type, alert_message)
        elif channel == CommunicationType.SMS and customer.phone:
            await send_sms_alert(customer.phone, alert_type, alert_message)
```

## Integration with Reseller Module

### Customer to Reseller Relationship

The Reseller Module uses customer data for:
- Managing reseller customers
- Commission calculations
- Service provisioning through resellers
- Reseller-specific customer views

### Integration Steps

1. **Reseller Customer Management**:
   - Resellers create and manage customers through the Customer API
   - Reseller ID is associated with customers they manage

2. **Hierarchical Customer Views**:
   - Resellers only see their own customers
   - Platform admins see all customers

### API Endpoints

- `GET /api/reseller/{reseller_id}/customers`: Get all customers for a reseller
- `POST /api/reseller/{reseller_id}/customers`: Create a customer under a reseller

### Code Example

```python
# In Reseller Module
from isp_management.modules.customer.services import CustomerService

async def get_reseller_customers(reseller_id: int):
    """Get all customers associated with a reseller."""
    customer_service = CustomerService()
    
    # Query customers with the reseller_id
    customers = await customer_service.get_customers_by_filter(
        session,
        filter_params={"reseller_id": reseller_id}
    )
    
    return customers
```

## Event-Based Communication

The Customer Management Module emits events that other modules can subscribe to:

### Key Events

- `customer.created`: Emitted when a new customer is created
- `customer.updated`: Emitted when customer details are updated
- `customer.deleted`: Emitted when a customer is deleted
- `customer.subscription_state.changed`: Emitted when subscription state changes
- `customer.address.created`: Emitted when a new address is added
- `customer.address.updated`: Emitted when an address is updated
- `customer.document.verified`: Emitted when a document is verified
- `customer.email.verified`: Emitted when an email is verified

### Event Structure

```json
{
  "event_type": "customer.created",
  "timestamp": "2025-03-14T19:30:00Z",
  "data": {
    "customer_id": 123,
    "customer_type": "INDIVIDUAL",
    "email": "john.doe@example.com",
    "status": "ACTIVE"
  }
}
```

### Subscribing to Events

```python
# In any module
from isp_management.backend_core.event_bus import EventBus

async def setup_event_handlers():
    event_bus = EventBus()
    
    # Subscribe to customer created events
    await event_bus.subscribe(
        "customer.created",
        handle_customer_created
    )

async def handle_customer_created(event_data):
    customer_id = event_data["data"]["customer_id"]
    # Process the new customer
    # ...
```

## API Integration

### Direct API Calls

Modules can directly call Customer Management API endpoints:

```python
# In any module
import httpx

async def get_customer_details(customer_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://api-gateway/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {api_token}"}
        )
        return response.json()
```

### Service-to-Service Communication

For internal module communication, use service classes directly:

```python
# In any module
from isp_management.modules.customer.services import CustomerService

async def process_customer_data(customer_id: int):
    customer_service = CustomerService()
    customer = await customer_service.get_customer(session, customer_id)
    # Process customer data
    # ...
```

## Troubleshooting

### Common Integration Issues

1. **Customer Not Found**
   - Ensure the customer ID is correct
   - Check if the customer has been deleted or deactivated

2. **Permission Denied**
   - Verify that the calling module has the required permissions
   - Check if the user has access to the customer data

3. **Event Processing Failures**
   - Implement retry logic for event handlers
   - Use dead-letter queues for failed events

4. **Data Synchronization Issues**
   - Implement idempotent operations
   - Use transaction IDs to prevent duplicate processing

### Logging and Monitoring

Always include customer IDs in logs for easier troubleshooting:

```python
logger.info(f"Processing subscription change for customer {customer_id}")
```

Set up monitoring for integration points:
- API call success rates
- Event processing times
- Error rates by module and operation

### Support Contacts

For integration issues, contact:
- Email: integration-support@isp-management.com
- Slack: #customer-module-integration
