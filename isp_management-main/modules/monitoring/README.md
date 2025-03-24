# ISP Management Platform - Monitoring Module

## Overview

The Monitoring Module is a comprehensive solution for monitoring various aspects of an ISP's infrastructure and services. It provides real-time monitoring, alerting, and historical data analysis for network performance, service availability, and customer usage statistics.

## Features

### 1. Network Performance Monitoring

- **Traffic Analysis**: Monitor network traffic patterns and bandwidth utilization
- **Latency Tracking**: Track network latency and packet loss
- **Interface Monitoring**: Monitor interface status and utilization
- **Threshold Alerts**: Configure alerts for performance threshold violations

### 2. Service Availability Monitoring

- **Service Endpoint Management**: Monitor HTTP, HTTPS, TCP, UDP, DNS, and ICMP services
- **Outage Detection**: Automatically detect and track service outages
- **Maintenance Windows**: Schedule and manage maintenance periods
- **Service Health Dashboard**: Visualize service health and availability metrics

### 3. Customer Usage Statistics

- **Bandwidth Usage**: Track customer bandwidth usage
- **Session Monitoring**: Monitor customer session duration and activity
- **Usage Trends**: Analyze usage patterns and trends
- **Quota Management**: Monitor and enforce usage quotas

### 4. Alert System

- **Threshold-based Alerts**: Configure alerts based on customizable thresholds
- **Notification Channels**: Send alerts via email, SMS, Slack, and other channels
- **Alert Escalation**: Configure escalation policies for critical alerts
- **Alert History**: Track and analyze historical alerts

### 5. Reporting Dashboard

- **Real-time Dashboards**: View real-time monitoring data
- **Historical Reports**: Generate reports for historical data analysis
- **Custom Visualizations**: Create custom visualizations for specific metrics
- **Export Capabilities**: Export reports in various formats (PDF, CSV, etc.)

## Architecture

The Monitoring Module follows a modular architecture with the following components:

### Core Components

1. **Models**: Define the database schema for monitoring data
2. **Schemas**: Define Pydantic schemas for API input/output validation
3. **Services**: Implement business logic for monitoring features
4. **Collectors**: Gather monitoring data from various sources
5. **Tasks**: Schedule and execute background tasks using Celery
6. **Routes**: Define API endpoints for monitoring features

### Data Flow

1. **Data Collection**: Collectors gather data from various sources
2. **Data Processing**: Services process and analyze the collected data
3. **Data Storage**: Processed data is stored in PostgreSQL and Elasticsearch
4. **Data Visualization**: Kibana dashboards visualize the monitoring data
5. **Alerting**: Alert system triggers notifications based on configured thresholds

## Elasticsearch Integration

The Monitoring Module integrates with Elasticsearch for efficient storage, retrieval, and visualization of monitoring data.

### Indices

| Index | Description |
|-------|-------------|
| isp-network-metrics-{date} | Network performance metrics |
| isp-service-status-{date} | Service availability status |
| isp-customer-usage-{date} | Customer usage statistics |
| isp-system-logs-{date} | System logs and events |
| isp-service-outage-{date} | Service outage records |

These indices include mappings that define the structure of the documents and use ILM policies for efficient data lifecycle management.

## Service Availability Monitoring

The Service Availability Monitoring component provides comprehensive monitoring of service endpoints and their availability status. It enables tracking of service health, managing outages, and integrating alerting mechanisms.

### Service Endpoint Management

- **Database Models**: `ServiceEndpoint`, `ServiceStatus`, `ServiceOutage`, `ServiceAlert`, and `MaintenanceWindow` models
- **API Endpoints**: RESTful API for managing service endpoints, statuses, outages, and maintenance windows
- **Collector Script**: Automated collection of service availability data
- **Elasticsearch Integration**: Storage and visualization of service statuses and outages

### Key Features

1. **Service Endpoint Monitoring**
   - HTTP, HTTPS, TCP, UDP, DNS, and ICMP protocol support
   - Response time tracking
   - Status history recording
   - Customizable check intervals and timeouts

2. **Outage Management**
   - Automatic outage detection based on consecutive failures
   - Outage verification to reduce false positives
   - Severity classification (Critical, Major, Minor, Warning)
   - Resolution tracking and notes

3. **Maintenance Windows**
   - Scheduled maintenance planning
   - Service exclusion during maintenance
   - Notification suppression during maintenance
   - Historical maintenance records

4. **Alerting System**
   - Threshold-based alerts for service outages
   - Multiple notification channels (Email, SMS, Slack, etc.)
   - Alert escalation based on outage duration
   - Alert history and management

5. **Dashboards**
   - Service availability dashboard
   - Outage history and trends
   - Response time tracking
   - Maintenance window calendar

### Configuration

Service availability monitoring can be configured using environment variables:

- `SERVICE_CHECK_INTERVAL`: Interval for checking service availability in seconds (default: 60)
- `SERVICE_CHECK_TIMEOUT`: Timeout for service checks in seconds (default: 5)
- `SERVICE_CHECK_RETRIES`: Number of retries for service checks (default: 3)
- `OUTAGE_DETECTION_THRESHOLD`: Number of consecutive failures to declare an outage (default: 3)
- `OUTAGE_VERIFICATION_ENABLED`: Whether to verify outages before alerting (default: true)
- `ALERT_NOTIFICATION_CHANNELS`: Comma-separated list of notification channels (default: "email")
- `ELASTICSEARCH_SYNC_INTERVAL`: Interval for syncing data to Elasticsearch in seconds (default: 300)
- `CLEANUP_RETENTION_DAYS`: Number of days to retain service status data (default: 30)

### Usage Example

```python
# Add a new service endpoint
from modules.monitoring.models.service_availability import ServiceEndpoint, ProtocolType
from modules.monitoring.services.availability_service import AvailabilityService
from sqlalchemy.orm import Session

def add_service_endpoint(db: Session):
    service = AvailabilityService(db)
    endpoint = service.create_endpoint({
        "id": "api-gateway",
        "name": "API Gateway",
        "url": "https://api.example.com/health",
        "protocol": ProtocolType.HTTPS,
        "check_interval": 60,
        "timeout": 5,
        "retries": 3,
        "expected_status_code": 200,
        "expected_response_pattern": "\"status\":\"UP\"",
        "is_active": True
    })
    return endpoint

# Manually check a service endpoint
from modules.monitoring.collectors.service_availability_collector import collect_specific_service_availability

# Check the service
result = collect_specific_service_availability(db, "api-gateway")
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/services/` | List all service endpoints |
| GET | `/services/{endpoint_id}` | Get a specific service endpoint |
| POST | `/services/` | Create a new service endpoint |
| PUT | `/services/{endpoint_id}` | Update a service endpoint |
| DELETE | `/services/{endpoint_id}` | Delete a service endpoint |
| POST | `/services/{endpoint_id}/check` | Manually check a service endpoint |
| GET | `/services/{endpoint_id}/status` | Get current status of a service endpoint |
| GET | `/services/{endpoint_id}/history` | Get status history of a service endpoint |
| GET | `/services/status/summary` | Get summary of service statuses |
| GET | `/outages/` | List all service outages |
| GET | `/outages/active` | Get active service outages |
| GET | `/outages/{outage_id}` | Get a specific service outage |
| POST | `/outages/{outage_id}/resolve` | Resolve a service outage |
| GET | `/outages/summary` | Get summary of service outages |
| GET | `/maintenance/` | List all maintenance windows |
| GET | `/maintenance/active` | Get active maintenance windows |
| POST | `/maintenance/` | Create a new maintenance window |
| GET | `/maintenance/{window_id}` | Get a specific maintenance window |
| PUT | `/maintenance/{window_id}` | Update a maintenance window |
| DELETE | `/maintenance/{window_id}` | Delete a maintenance window |

### Elasticsearch Integration

Service availability data is stored in Elasticsearch using the following indices:

- **Service Status**: `isp-service-status-{date}`
- **Service Outages**: `isp-service-outage-{date}`

Kibana dashboards and visualizations are provided for monitoring service availability:

- **Service Status Overview**: Pie chart showing the distribution of service statuses
- **Active Outages**: Metric showing the number of active outages
- **Service Response Time**: Line chart showing response time trends by service
- **Service Status History**: Area chart showing status history over time
- **Recent Outages**: Table showing recent outages with details
- **Outages by Service**: Pie chart showing outage distribution by service
- **Outages by Severity**: Histogram showing outages by severity over time
- **Maintenance Windows**: Table showing upcoming and past maintenance windows

## Usage Examples

### Logging Example

```python
from modules.monitoring.services.logging_service import LoggingService

# Create a logging service instance
logging_service = LoggingService()

# Log an informational message
logging_service.info("User login successful", {
    "user_id": "user123",
    "ip_address": "192.168.1.1",
    "login_time": "2023-01-01T12:00:00Z"
})

# Log an error message
logging_service.error("Database connection failed", {
    "database": "postgres",
    "error": "Connection refused",
    "retry_count": 3
})
```

### Metrics Collection Example

```python
from modules.monitoring.services.metrics_service import MetricsService

# Create a metrics service instance
metrics_service = MetricsService()

# Record a network performance metric
metrics_service.record_network_metric({
    "interface": "eth0",
    "bandwidth_usage": 75.5,
    "packet_loss": 0.2,
    "latency": 15.3
})

# Record a system metric
metrics_service.record_system_metric({
    "cpu_usage": 45.2,
    "memory_usage": 60.8,
    "disk_usage": 78.3,
    "load_average": 2.5
})
```

### Service Availability Example

```python
from modules.monitoring.services.availability_service import AvailabilityService
from modules.monitoring.models.service_availability import ProtocolType

# Create an availability service instance
availability_service = AvailabilityService(db_session)

# Add a new service endpoint to monitor
endpoint = availability_service.create_endpoint({
    "id": "radius-server",
    "name": "RADIUS Server",
    "url": "radius.example.com:1812",
    "protocol": ProtocolType.UDP,
    "check_interval": 60,
    "timeout": 5,
    "retries": 3,
    "is_active": True
})

# Check the service status
status = availability_service.check_service(endpoint.id)
print(f"Service status: {status.status.value}, Response time: {status.response_time}ms")
```

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/example/isp-management.git
   cd isp-management
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

4. Run database migrations:
   ```bash
   python scripts/run_migrations.py
   ```

5. Start the application:
   ```bash
   uvicorn main:app --reload
   ```

## Testing

Run the tests using pytest:

```bash
pytest tests/modules/monitoring/
```

## Documentation

For detailed documentation, see the following files:

- [Service Availability Monitoring](../docs/service_availability_monitoring.md)
- [Network Performance Monitoring](../docs/network_performance_monitoring.md)
- [Customer Usage Statistics](../docs/customer_usage_statistics.md)
- [Elasticsearch Integration](../docs/elasticsearch_integration.md)

## Contributing

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them:
   ```bash
   git commit -m "Add your feature description"
   ```

3. Push to the branch:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
