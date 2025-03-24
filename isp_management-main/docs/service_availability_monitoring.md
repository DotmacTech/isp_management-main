# Service Availability Monitoring

## Overview

The Service Availability Monitoring module is a comprehensive solution for monitoring the health and availability of critical services within the ISP Management Platform. It provides real-time monitoring, outage detection, alerting, and historical data analysis for service endpoints.

## Architecture

The Service Availability Monitoring module follows a modular architecture with the following components:

### Core Components

1. **Models**
   - `ServiceEndpoint`: Defines service endpoints to be monitored
   - `ServiceStatus`: Records status checks for service endpoints
   - `ServiceOutage`: Tracks service outages and their resolution
   - `MaintenanceWindow`: Manages scheduled maintenance periods

2. **Services**
   - `AvailabilityService`: Manages service endpoints and status checks
   - `OutageManagementService`: Handles outage detection, verification, and resolution

3. **Collectors**
   - `ServiceAvailabilityCollector`: Collects service availability data and syncs with Elasticsearch

4. **Tasks**
   - Scheduled Celery tasks for regular service checks
   - Tasks for outage detection and verification
   - Tasks for data synchronization with Elasticsearch

5. **API Routes**
   - RESTful API endpoints for managing service endpoints, statuses, outages, and maintenance windows

### Data Flow

1. **Service Check Process**:
   - Celery task triggers service check at configured intervals
   - Collector checks service availability using appropriate protocol
   - Status is recorded in the database
   - Status is synced to Elasticsearch for visualization

2. **Outage Detection Process**:
   - Consecutive failures trigger outage detection
   - Outage is verified to reduce false positives
   - Outage is recorded and notifications are sent
   - Outage is synced to Elasticsearch for visualization

3. **Maintenance Window Process**:
   - Maintenance windows are scheduled in advance
   - Services in maintenance are excluded from outage detection
   - Notifications are suppressed during maintenance
   - Maintenance windows are displayed in dashboards

## Database Schema

### ServiceEndpoint

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier for the service endpoint |
| name | String | Display name for the service endpoint |
| url | String | URL or address of the service endpoint |
| protocol | Enum | Protocol type (HTTP, HTTPS, TCP, UDP, DNS, ICMP) |
| check_interval | Integer | Interval between checks in seconds |
| timeout | Integer | Timeout for service checks in seconds |
| retries | Integer | Number of retries for service checks |
| expected_status_code | Integer | Expected HTTP status code (for HTTP/HTTPS) |
| expected_response_pattern | String | Expected response pattern (regex) |
| is_active | Boolean | Whether the endpoint is active |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### ServiceStatus

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier for the status check |
| endpoint_id | String | Reference to service endpoint |
| status | Enum | Status type (UP, DOWN, DEGRADED, UNKNOWN) |
| response_time | Float | Response time in milliseconds |
| timestamp | DateTime | Timestamp of the status check |
| error_message | String | Error message if status is DOWN |
| elasticsearch_synced | Boolean | Whether the status has been synced to Elasticsearch |

### ServiceOutage

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier for the outage |
| endpoint_id | String | Reference to service endpoint |
| severity | Enum | Severity level (CRITICAL, MAJOR, MINOR, WARNING) |
| description | String | Description of the outage |
| start_time | DateTime | Start time of the outage |
| resolved | Boolean | Whether the outage has been resolved |
| resolved_at | DateTime | Time when the outage was resolved |
| resolution_notes | String | Notes about the resolution |
| notification_channels | JSON | Channels used for notifications |
| elasticsearch_synced | Boolean | Whether the outage has been synced to Elasticsearch |

### MaintenanceWindow

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier for the maintenance window |
| description | String | Description of the maintenance window |
| start_time | DateTime | Start time of the maintenance window |
| end_time | DateTime | End time of the maintenance window |
| created_by | String | User who created the maintenance window |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |
| endpoints | Relationship | Service endpoints affected by the maintenance |

## API Endpoints

### Service Endpoints

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

### Outages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/outages/` | List all service outages |
| GET | `/outages/active` | Get active service outages |
| GET | `/outages/{outage_id}` | Get a specific service outage |
| POST | `/outages/{outage_id}/resolve` | Resolve a service outage |
| GET | `/outages/summary` | Get summary of service outages |

### Maintenance Windows

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/maintenance/` | List all maintenance windows |
| GET | `/maintenance/active` | Get active maintenance windows |
| POST | `/maintenance/` | Create a new maintenance window |
| GET | `/maintenance/{window_id}` | Get a specific maintenance window |
| PUT | `/maintenance/{window_id}` | Update a maintenance window |
| DELETE | `/maintenance/{window_id}` | Delete a maintenance window |

## Elasticsearch Integration

The Service Availability Monitoring module integrates with Elasticsearch for data storage, visualization, and alerting.

### Indices

| Index | Description |
|-------|-------------|
| isp-service-status-{date} | Stores service status data |
| isp-service-outage-{date} | Stores service outage data |

### Kibana Dashboards

The module provides the following Kibana dashboards and visualizations:

1. **Service Status Overview**: Pie chart showing the distribution of service statuses
2. **Active Outages**: Metric showing the number of active outages
3. **Service Response Time**: Line chart showing response time trends by service
4. **Service Status History**: Area chart showing status history over time
5. **Recent Outages**: Table showing recent outages with details
6. **Outages by Service**: Pie chart showing outage distribution by service
7. **Outages by Severity**: Histogram showing outages by severity over time
8. **Maintenance Windows**: Table showing upcoming and past maintenance windows

### Alert Rules

The module provides the following Elasticsearch alert rules:

1. **Service Down Alert**: Alerts when a service is down
2. **Service Response Time Alert**: Alerts when a service has high response time
3. **Multiple Services Down Alert**: Alerts when multiple services are down
4. **Active Outages Alert**: Alerts when there are active outages
5. **Long Duration Outage Alert**: Alerts when an outage has been active for a long time

## Configuration

The Service Availability Monitoring module can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| SERVICE_CHECK_INTERVAL | Interval for checking service availability in seconds | 60 |
| SERVICE_CHECK_TIMEOUT | Timeout for service checks in seconds | 5 |
| SERVICE_CHECK_RETRIES | Number of retries for service checks | 3 |
| OUTAGE_DETECTION_THRESHOLD | Number of consecutive failures to declare an outage | 3 |
| OUTAGE_VERIFICATION_ENABLED | Whether to verify outages before alerting | true |
| ALERT_NOTIFICATION_CHANNELS | Comma-separated list of notification channels | "email" |
| ELASTICSEARCH_SYNC_INTERVAL | Interval for syncing data to Elasticsearch in seconds | 300 |
| CLEANUP_RETENTION_DAYS | Number of days to retain service status data | 30 |

## Usage Examples

### Adding a Service Endpoint

```python
from modules.monitoring.models.service_availability import ProtocolType
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
```

### Manually Checking a Service

```python
from modules.monitoring.collectors.service_availability_collector import collect_specific_service_availability

# Check the service
result = collect_specific_service_availability(db, "api-gateway")
print(f"Service status: {result['status']}")
```

### Creating a Maintenance Window

```python
from modules.monitoring.services.availability_service_outage import OutageManagementService
from datetime import datetime, timedelta

def create_maintenance_window(db: Session):
    outage_service = OutageManagementService(db)
    window = outage_service.create_maintenance_window({
        "endpoint_ids": ["api-gateway", "auth-service"],
        "start_time": datetime.utcnow() + timedelta(days=1),
        "end_time": datetime.utcnow() + timedelta(days=1, hours=2),
        "description": "Scheduled maintenance for API gateway and Auth service",
        "created_by": "admin"
    })
    return window
```

### Resolving an Outage

```python
from modules.monitoring.services.availability_service_outage import OutageManagementService

def resolve_outage(db: Session, outage_id: str):
    outage_service = OutageManagementService(db)
    resolved_outage = outage_service.resolve_outage(
        outage_id,
        resolution_notes="Fixed network connectivity issue"
    )
    return resolved_outage
```

## Testing

The Service Availability Monitoring module includes comprehensive unit tests and integration tests.

### Running Unit Tests

```bash
pytest tests/modules/monitoring/test_service_availability.py -v
```

### Running Integration Tests

```bash
python modules/monitoring/scripts/test_service_availability.py
```

## Troubleshooting

### Common Issues

1. **Service checks failing**: Verify network connectivity and service endpoint configuration.
2. **Elasticsearch sync not working**: Check Elasticsearch connection and index templates.
3. **Alerts not triggering**: Verify alert rule configuration and notification channels.
4. **High response times**: Check network latency and service performance.

### Logs

Service availability monitoring logs can be found in the following locations:

- Application logs: `/var/log/isp_management/monitoring.log`
- Celery task logs: `/var/log/isp_management/celery.log`
- Elasticsearch logs: `/var/log/elasticsearch/elasticsearch.log`

## Best Practices

1. **Service Endpoint Configuration**
   - Use meaningful IDs and names for service endpoints
   - Set appropriate check intervals based on service criticality
   - Configure reasonable timeouts and retries to avoid false positives

2. **Outage Management**
   - Set appropriate thresholds for outage detection
   - Use verification to reduce false positives
   - Document outage resolutions for future reference

3. **Maintenance Windows**
   - Schedule maintenance windows in advance
   - Provide detailed descriptions of maintenance activities
   - Notify stakeholders before and after maintenance

4. **Alerting**
   - Configure appropriate notification channels
   - Set up escalation policies for critical services
   - Avoid alert fatigue by tuning thresholds

## Future Enhancements

1. **Advanced Protocol Support**
   - SNMP monitoring
   - Database connection checks
   - Custom protocol handlers

2. **Dependency Mapping**
   - Service dependency visualization
   - Impact analysis for outages
   - Cascading failure detection

3. **Advanced Alerting**
   - Machine learning-based anomaly detection
   - Predictive outage prevention
   - Automated remediation actions

4. **Integration with External Systems**
   - Incident management systems
   - Ticketing systems
   - On-call rotation systems
