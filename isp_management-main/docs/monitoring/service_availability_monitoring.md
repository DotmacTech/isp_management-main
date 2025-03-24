# Service Availability Monitoring

## Overview

The Service Availability Monitoring component provides real-time tracking of critical ISP services and infrastructure. It continuously monitors the availability and health of various services, detects outages, and triggers alerts when services become unavailable or degraded.

## Features

### Service Health Monitoring

- **Continuous Service Checks**: Periodic checks of service availability using HTTP, TCP, ICMP, and custom protocols
- **Health Status Tracking**: Recording of service status (UP, DOWN, DEGRADED) with timestamps
- **Response Time Monitoring**: Tracking of service response times to detect performance degradation
- **Service Dependencies**: Mapping of dependencies between services for root cause analysis

### Outage Detection and Management

- **Automatic Outage Detection**: Identification of service outages based on configurable thresholds
- **Outage Verification**: Multi-location verification to reduce false positives
- **Outage Tracking**: Recording of outage duration, affected services, and impact severity
- **Service Recovery Detection**: Automatic detection of service recovery

### Alerting and Notification

- **Configurable Alert Thresholds**: Customizable thresholds for different services and metrics
- **Multi-channel Notifications**: Email, SMS, Slack, and webhook notifications
- **Alert Escalation**: Tiered escalation based on outage duration and severity
- **Maintenance Windows**: Scheduled maintenance periods to suppress alerts

## Architecture

The Service Availability Monitoring component follows a modular architecture:

1. **Service Checker Module**: Performs health checks on services using various protocols
2. **Status Recorder**: Records service health status in the database and Elasticsearch
3. **Outage Detector**: Analyzes service status to detect and verify outages
4. **Alert Manager**: Manages alert rules, thresholds, and notification channels

## Database Models

### ServiceEndpoint

```python
class ServiceEndpoint(Base):
    """Model for service endpoints to be monitored."""
    __tablename__ = "service_endpoints"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    url = Column(String(255), nullable=False)
    protocol = Column(Enum(ProtocolType), nullable=False)
    port = Column(Integer, nullable=True)
    check_interval = Column(Integer, nullable=False, default=60)  # seconds
    timeout = Column(Integer, nullable=False, default=5)  # seconds
    retries = Column(Integer, nullable=False, default=3)
    expected_status_code = Column(Integer, nullable=True)  # For HTTP
    expected_response_pattern = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    status_history = relationship("ServiceStatus", back_populates="endpoint")
    outages = relationship("ServiceOutage", back_populates="endpoint")
```

### ServiceStatus

```python
class ServiceStatus(Base):
    """Model for service status history."""
    __tablename__ = "service_status"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    endpoint_id = Column(String(50), ForeignKey("service_endpoints.id"), nullable=False)
    status = Column(Enum(StatusType), nullable=False)
    response_time = Column(Float, nullable=True)  # milliseconds
    status_message = Column(String(255), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    elasticsearch_synced = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    endpoint = relationship("ServiceEndpoint", back_populates="status_history")
```

### ServiceOutage

```python
class ServiceOutage(Base):
    """Model for service outages."""
    __tablename__ = "service_outages"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    endpoint_id = Column(String(50), ForeignKey("service_endpoints.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    severity = Column(Enum(SeverityLevel), nullable=False)
    affected_customers = Column(Integer, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    endpoint = relationship("ServiceEndpoint", back_populates="outages")
    alerts = relationship("ServiceAlert", back_populates="outage")
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/monitoring/services/` | List all monitored services |
| GET | `/monitoring/services/{service_id}` | Get details of a specific service |
| POST | `/monitoring/services/` | Add a new service to monitor |
| PUT | `/monitoring/services/{service_id}` | Update a monitored service |
| DELETE | `/monitoring/services/{service_id}` | Remove a service from monitoring |
| GET | `/monitoring/services/{service_id}/status` | Get current status of a service |
| GET | `/monitoring/services/{service_id}/history` | Get status history of a service |
| GET | `/monitoring/outages/` | List all service outages |
| GET | `/monitoring/outages/active` | List currently active outages |
| GET | `/monitoring/outages/{outage_id}` | Get details of a specific outage |
| POST | `/monitoring/outages/{outage_id}/resolve` | Mark an outage as resolved |

## Celery Tasks

The following Celery tasks are used for service availability monitoring:

- `check_service_availability`: Checks the availability of a single service
- `check_all_services`: Checks all active services
- `verify_outage`: Verifies a potential outage by performing additional checks
- `sync_service_status_to_elasticsearch`: Syncs service status data to Elasticsearch
- `cleanup_old_service_status`: Removes old service status records based on retention policy

## Configuration

Service availability monitoring can be configured using environment variables:

- `SERVICE_CHECK_INTERVAL`: Default interval for service checks in seconds (default: 60)
- `SERVICE_CHECK_TIMEOUT`: Default timeout for service checks in seconds (default: 5)
- `SERVICE_CHECK_RETRIES`: Default number of retries for service checks (default: 3)
- `OUTAGE_DETECTION_THRESHOLD`: Number of consecutive failures to declare an outage (default: 3)
- `OUTAGE_VERIFICATION_ENABLED`: Whether to verify outages before alerting (default: true)
- `ALERT_NOTIFICATION_CHANNELS`: Comma-separated list of notification channels (default: "email")

## Elasticsearch Integration

Service status data is stored in Elasticsearch for long-term storage, visualization, and analysis. The following indices are used:

- `isp-service-status-{date}`: Stores service status data
- `isp-service-outages-{date}`: Stores service outage data

## Kibana Dashboards

The following Kibana dashboards are available for service availability monitoring:

- **Service Availability Overview**: Shows the current status of all services
- **Service Response Time**: Shows response time trends for all services
- **Outage History**: Shows historical outage data and trends
- **Service Health Heatmap**: Shows service health across different time periods

## Usage Example

```python
# Add a new service to monitor
from modules.monitoring.models import ServiceEndpoint, ProtocolType
from sqlalchemy.orm import Session

def add_service_endpoint(db: Session):
    endpoint = ServiceEndpoint(
        id="radius-auth",
        name="RADIUS Authentication Service",
        description="Primary RADIUS authentication service",
        url="radius.example.com",
        protocol=ProtocolType.RADIUS,
        port=1812,
        check_interval=30,
        timeout=3,
        retries=2,
        is_active=True
    )
    db.add(endpoint)
    db.commit()
    return endpoint

# Manually check service status
from modules.monitoring.services.availability_service import AvailabilityService

availability_service = AvailabilityService(db)
status = availability_service.check_service("radius-auth")
print(f"Service status: {status.status}, Response time: {status.response_time}ms")
```

## Integration with Other Modules

The Service Availability Monitoring component integrates with:

- **Network Performance Monitoring**: Correlates service outages with network performance issues
- **Customer Support Module**: Provides service status information for customer support
- **Billing Module**: Allows for service credits based on outage duration
- **Notification Module**: Sends notifications about service status changes

## Future Enhancements

- **Synthetic Monitoring**: Simulate user interactions to test complex service flows
- **Distributed Monitoring**: Check services from multiple geographic locations
- **Machine Learning**: Predict service outages based on historical patterns
- **Automatic Remediation**: Automatically attempt to restore failed services
