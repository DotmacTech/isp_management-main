# Integration Management Module

The Integration Management Module provides a centralized system for managing integrations with third-party services and external systems in the ISP Management Platform. It supports various integration types, including payment gateways, SMS providers, email providers, and more.

## Features

- **Integration Management**: Create, update, delete, and list integrations with third-party services
- **Secure Credential Storage**: Encrypt sensitive credentials for secure storage
- **Version Control**: Track changes to integration configurations
- **Webhook Handling**: Receive and process webhook events from external services
- **Activity Logging**: Track all integration activities for auditing
- **Background Processing**: Process webhook events and test integrations asynchronously
- **Metrics Collection**: Monitor integration performance and reliability
- **API Documentation**: Comprehensive API documentation with examples

## Architecture

The Integration Management Module follows a layered architecture:

1. **API Layer**: RESTful API endpoints for managing integrations and webhooks
2. **Service Layer**: Business logic for integration management
3. **Data Layer**: Database models and repositories
4. **Adapter Layer**: Integration-specific adapters for different service types
5. **Background Tasks**: Asynchronous processing of webhook events and integration tests
6. **Monitoring**: Metrics collection and reporting

### Key Components

- **Models**: Database models for integrations, webhook endpoints, webhook events, and activities
- **Schemas**: Pydantic schemas for request/response validation
- **Services**: Business logic for integration management
- **Adapters**: Integration-specific adapters for different service types
- **API Endpoints**: RESTful API endpoints for managing integrations and webhooks
- **Background Tasks**: Celery tasks for asynchronous processing
- **Security**: Utilities for encrypting credentials and validating webhook signatures
- **Metrics**: Collection and reporting of integration metrics

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (for Celery)
- Elasticsearch (for metrics and logging)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run database migrations:
   ```bash
   alembic upgrade head
   ```
4. Start the Celery worker:
   ```bash
   celery -A core.celery.app worker -l info -Q integration_management
   ```
5. Start the Celery beat scheduler:
   ```bash
   celery -A core.celery.app beat -l info
   ```
6. Start the API server:
   ```bash
   uvicorn main:app --reload
   ```

## Usage

### Managing Integrations

#### Creating an Integration

```python
from modules.integration_management.services.integration_service import IntegrationService
from modules.integration_management.schemas.integration import IntegrationCreate

# Create an integration service
integration_service = IntegrationService(db)

# Create an integration
integration_data = IntegrationCreate(
    name="Stripe Payment Gateway",
    description="Integration with Stripe for payment processing",
    type="PAYMENT_GATEWAY",
    environment="production",
    configuration={
        "base_url": "https://api.stripe.com",
        "webhook_url": "https://api.example.com/webhooks/stripe"
    },
    credentials={
        "api_key": "sk_live_51AbCdEfGhIjKlMnOpQrStUvWxYz"
    }
)

integration = integration_service.create_integration(integration_data)
```

#### Testing an Integration Connection

```python
# Test the connection
result = integration_service.test_connection(integration.id)

if result["success"]:
    print("Connection successful!")
else:
    print(f"Connection failed: {result['message']}")
```

### Managing Webhook Endpoints

#### Creating a Webhook Endpoint

```python
from modules.integration_management.schemas.webhook import WebhookEndpointCreate

# Create a webhook endpoint
webhook_data = WebhookEndpointCreate(
    integration_id=integration.id,
    name="Stripe Payment Events",
    description="Webhook for Stripe payment events",
    path="stripe-payments",
    active=True,
    verify_signature=True,
    signature_header="Stripe-Signature"
)

webhook = integration_service.create_webhook_endpoint(webhook_data)
```

### Processing Webhook Events

#### Receiving a Webhook Event

```python
# In an API endpoint
@router.post("/webhooks/receive/{webhook_path}")
async def receive_webhook(
    webhook_path: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Get request headers and body
    headers = dict(request.headers)
    body = await request.body()
    
    # Process the webhook event
    integration_service = IntegrationService(db)
    webhook = integration_service.get_webhook_endpoint_by_path(webhook_path)
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    # Process the webhook event
    event = integration_service.process_webhook_event(webhook.id, headers, body)
    
    return {"status": "success", "event_id": event.id}
```

### Background Tasks

#### Processing Webhook Events

The module includes several Celery tasks for asynchronous processing:

- `process_webhook_event`: Process a webhook event
- `test_integration_connection`: Test an integration connection
- `test_all_active_integrations`: Test all active integrations
- `process_pending_webhook_events`: Process pending webhook events
- `collect_integration_metrics`: Collect metrics for all integrations

These tasks can be scheduled using Celery Beat:

```python
# In celery_config.py
beat_schedule = {
    'test-all-active-integrations': {
        'task': 'integration_management.test_all_active_integrations',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
    'process-pending-webhook-events': {
        'task': 'integration_management.process_pending_webhook_events',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'collect-integration-metrics': {
        'task': 'integration_management.collect_integration_metrics',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}
```

## Monitoring

The module collects metrics for monitoring integration performance and reliability. These metrics are available through the monitoring dashboard and can be exported to external monitoring systems like Prometheus, StatsD, or Elasticsearch.

### Available Metrics

- `integrations_by_status`: Number of integrations by status
- `integrations_by_type`: Number of integrations by type
- `total_webhooks`: Total number of webhook endpoints
- `active_webhooks`: Number of active webhook endpoints
- `total_webhook_events`: Total number of webhook events
- `processed_webhook_events`: Number of processed webhook events
- `pending_webhook_events`: Number of pending webhook events
- `webhook_events_last_24h`: Number of webhook events in the last 24 hours
- `webhook_processing_time`: Time taken to process webhook events
- `integration_connection_tests`: Number of integration connection tests

## API Documentation

Comprehensive API documentation is available in the [API Documentation](./docs/api_documentation.md) file.

## Testing

The module includes a comprehensive test suite for all components. To run the tests:

```bash
pytest tests/integration_management/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
