# Central Logging and Monitoring Service

This document provides comprehensive information about the central logging and monitoring service implemented in the ISP Management Platform.

## Overview

The central logging and monitoring service provides a unified interface for logging, monitoring, and tracking system events, errors, and performance metrics across all modules of the platform. It integrates with Elasticsearch for log storage and Prometheus for metrics collection, offering a complete observability solution.

## Features

- **Centralized Logging**: All logs from different modules are collected and stored in a central location
- **Structured Logging**: Logs include context, timestamps, and correlation IDs
- **Log Levels**: Support for different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Performance Monitoring**: Track system and application metrics
- **Alerting**: Configurable thresholds for alerts on critical metrics
- **Dashboard**: Web-based dashboard for visualizing logs and metrics
- **API Integration**: Easy-to-use API for logging and monitoring
- **Database Monitoring**: Track database operations and performance
- **Request Tracing**: Correlation IDs for tracing requests across services

## Configuration

The logging and monitoring service is configured through environment variables in the `Settings` class in `config.py`:

```python
# Elasticsearch configuration
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")

# Prometheus configuration
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

# Monitoring interval (seconds)
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "60"))

# Alert configuration
ENABLE_EMAIL_ALERTS = os.getenv("ENABLE_EMAIL_ALERTS", "false").lower() == "true"
ENABLE_SLACK_ALERTS = os.getenv("ENABLE_SLACK_ALERTS", "false").lower() == "true"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
```

## Usage

### Basic Logging

The logging service provides a simple API for logging messages at different levels:

```python
from isp_management.backend_core.log_utils import log_debug, log_info, log_warning, log_error, log_critical

# Log a simple message
log_info("User logged in successfully")

# Log with additional context
log_info(
    "Payment processed",
    context={
        "user_id": 123,
        "amount": 50.0,
        "currency": "USD"
    }
)

# Log an error with exception
try:
    # Some code that might fail
    result = 1 / 0
except Exception as e:
    log_error(
        "Error processing payment",
        exception=e,
        context={
            "user_id": 123,
            "amount": 50.0
        }
    )
```

### Function Logging

You can use the `log_function` decorator to automatically log function entry and exit:

```python
from isp_management.backend_core.log_utils import log_function

@log_function(log_args=True, log_result=True)
def process_payment(user_id, amount, currency="USD"):
    # Process payment logic
    return {"status": "success", "transaction_id": "tx_123"}
```

This will log:
- When the function is called, including arguments
- When the function returns, including the result and execution time
- Any exceptions that occur during execution

### API Request Logging

FastAPI routes can be logged using the `LoggingRoute` class:

```python
from fastapi import APIRouter
from isp_management.backend_core.log_utils import LoggingRoute

router = APIRouter(route_class=LoggingRoute)

@router.get("/users/{user_id}")
def get_user(user_id: int):
    # Get user logic
    return {"user_id": user_id, "name": "John Doe"}
```

### Database Query Logging

Database queries can be logged using the `LoggingDBMiddleware`:

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from isp_management.backend_core.database import get_db
from isp_management.backend_core.log_utils import LoggingDBMiddleware

# Create middleware
db_middleware = LoggingDBMiddleware(get_db)

# Use in endpoint
@router.get("/users")
def get_users(db: Session = Depends(db_middleware)):
    # Use db session as normal
    users = db.query(User).all()
    return users
```

## Monitoring

### System Metrics

The monitoring service automatically collects the following system metrics:

- CPU usage
- Memory usage
- Disk usage
- Network I/O
- Database connections
- Database size

### Application Metrics

You can track custom application metrics:

```python
from isp_management.backend_core.monitoring_service import get_monitoring_service

monitoring = get_monitoring_service()

# Update business metrics
monitoring.update_business_metrics(
    active_users=1000,
    active_sessions=500,
    billing_revenue=10000.0,
    customer_count=2000
)

# Track cache access
monitoring.track_cache(hit=True)  # Cache hit
monitoring.track_cache(hit=False)  # Cache miss

# Track task execution
monitoring.track_task("email_sending", duration=1.5, error=False)
```

### Monitoring Decorator

You can use the `monitor_function` decorator to automatically monitor function execution:

```python
from isp_management.backend_core.monitoring_service import monitor_function

@monitor_function
async def process_billing():
    # Billing processing logic
    pass
```

## Alerting

The monitoring service can trigger alerts when metrics exceed configured thresholds:

```python
from isp_management.backend_core.monitoring_service import get_monitoring_service

monitoring = get_monitoring_service()

# Set alert threshold
monitoring.set_alert_threshold("cpu_usage", 90.0)  # Alert when CPU usage exceeds 90%

# Register custom alert callback
def my_alert_callback(alert):
    # Custom alert handling logic
    print(f"Alert: {alert['message']}")

monitoring.register_alert_callback(my_alert_callback)
```

## Dashboard

The monitoring dashboard is available at `/api/dashboard/` and provides a real-time view of system metrics, logs, and alerts. The dashboard includes:

- System metrics charts
- Database metrics
- Recent alerts
- Recent logs
- Alert threshold configuration

## Best Practices

1. **Use Appropriate Log Levels**:
   - DEBUG: Detailed information for debugging
   - INFO: General information about system operation
   - WARNING: Indication of potential issues
   - ERROR: Error conditions that should be investigated
   - CRITICAL: Critical conditions that require immediate attention

2. **Include Context**:
   - Add relevant context to logs (user ID, transaction ID, etc.)
   - Use correlation IDs for request tracing

3. **Avoid Sensitive Information**:
   - Never log passwords, tokens, or other sensitive information
   - Sanitize user input before logging

4. **Use Structured Logging**:
   - Use the context parameter to add structured data to logs
   - This makes logs easier to search and analyze

5. **Set Appropriate Alert Thresholds**:
   - Configure alert thresholds based on normal system behavior
   - Avoid alert fatigue by setting reasonable thresholds

## Troubleshooting

### Common Issues

1. **Elasticsearch Connection Issues**:
   - Check that Elasticsearch is running and accessible
   - Verify the ELASTICSEARCH_URL environment variable

2. **Prometheus Metrics Not Showing**:
   - Check that the Prometheus server is running
   - Verify the PROMETHEUS_PORT environment variable

3. **Alerts Not Being Sent**:
   - Check that email or Slack alerts are enabled
   - Verify the ADMIN_EMAIL or SLACK_WEBHOOK_URL environment variables

### Viewing Logs

Logs can be viewed in several ways:

1. **Dashboard**: Use the web dashboard at `/api/dashboard/`
2. **API**: Use the `/api/dashboard/logs` endpoint
3. **Elasticsearch**: Query Elasticsearch directly
4. **Standard Output**: Logs are also sent to standard output

## Integration with Other Services

### Webhooks

The logging service can be integrated with the webhook system to trigger webhooks on specific log events:

```python
from isp_management.modules.communications.webhooks import WebhookService
from isp_management.backend_core.logging_service import get_logger

logger = get_logger()
webhook_service = WebhookService()

# Register a custom alert callback that triggers webhooks
def webhook_alert_callback(alert):
    webhook_service.trigger_event(
        "system.alert",
        {
            "alert_type": alert["type"],
            "message": alert["message"],
            "value": alert["value"],
            "threshold": alert["threshold"],
            "timestamp": alert["timestamp"]
        }
    )

# Register the callback
monitoring = get_monitoring_service()
monitoring.register_alert_callback(webhook_alert_callback)
```

### External Services

The logging service can be integrated with external services for advanced monitoring and alerting:

```python
from isp_management.modules.communications.external_services import ExternalServiceClient
from isp_management.backend_core.monitoring_service import get_monitoring_service

monitoring = get_monitoring_service()
service_client = ExternalServiceClient()

# Register a custom alert callback that sends alerts to external services
def external_service_alert_callback(alert):
    service_client.send_notification(
        service_type="monitoring",
        payload={
            "alert_type": alert["type"],
            "message": alert["message"],
            "value": alert["value"],
            "threshold": alert["threshold"],
            "timestamp": alert["timestamp"]
        }
    )

# Register the callback
monitoring.register_alert_callback(external_service_alert_callback)
```

## Extending the Logging Service

The logging service can be extended with custom functionality:

### Custom Log Handlers

```python
import logging
from isp_management.backend_core.logging_service import get_logger

# Create a custom log handler
class CustomLogHandler(logging.Handler):
    def emit(self, record):
        # Custom log handling logic
        pass

# Add the handler to the logger
logger = get_logger()
custom_handler = CustomLogHandler()
logging.getLogger().addHandler(custom_handler)
```

### Custom Metrics

```python
from prometheus_client import Counter
from isp_management.backend_core.monitoring_service import get_monitoring_service, REGISTRY

# Create a custom metric
custom_counter = Counter(
    'custom_counter',
    'A custom counter metric',
    ['label1', 'label2'],
    registry=REGISTRY
)

# Increment the counter
custom_counter.labels(label1='value1', label2='value2').inc()
```

## Conclusion

The central logging and monitoring service provides a comprehensive solution for tracking system events, errors, and performance metrics across all modules of the ISP Management Platform. By following the guidelines in this document, you can effectively use the service to improve system observability and troubleshooting capabilities.
