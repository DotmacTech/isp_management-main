# Network Performance Monitoring

This document provides comprehensive information about the Network Performance Monitoring features of the ISP Management Platform.

## Overview

The Network Performance Monitoring module enables ISP administrators to monitor and analyze network performance metrics, service availability, and customer usage statistics. It integrates with Elasticsearch for data storage and Kibana for visualization, providing real-time insights into network health and performance.

## Key Features

1. **Network Performance Metrics Collection**
   - Latency monitoring
   - Packet loss detection
   - Bandwidth utilization tracking
   - Connection count monitoring

2. **Service Availability Tracking**
   - Real-time service status monitoring
   - Response time measurement
   - Error rate tracking
   - Historical uptime reporting

3. **Customer Usage Statistics**
   - Data usage tracking by customer
   - Session count monitoring
   - Usage trends analysis
   - Quota management

4. **Alert System**
   - Threshold-based alerts for network metrics
   - Service outage notifications
   - Customer quota alerts
   - Configurable notification channels (email, Slack)

5. **Dashboards**
   - Network performance dashboard
   - Service availability dashboard
   - Customer usage dashboard
   - Custom visualization support

## Architecture

The Network Performance Monitoring module follows a modular architecture:

1. **Data Collection Layer**
   - `NetworkPerformanceCollector`: Collects metrics from various sources
   - Celery tasks for scheduled collection
   - Support for SNMP, ping, HTTP checks, and custom protocols

2. **Data Storage Layer**
   - PostgreSQL for relational data storage
   - Elasticsearch for time-series metrics and logs
   - Automatic synchronization between databases

3. **Visualization Layer**
   - Kibana dashboards for metrics visualization
   - Custom dashboards for specific monitoring needs
   - Real-time and historical data views

4. **Alert Layer**
   - Threshold-based alert rules
   - Multiple notification channels
   - Alert history and management

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NETWORK_METRICS_INTERVAL` | Interval for collecting network metrics (seconds) | 300 |
| `SYNC_LOGS_INTERVAL` | Interval for syncing logs to Elasticsearch (seconds) | 900 |
| `SYNC_METRICS_INTERVAL` | Interval for syncing metrics to Elasticsearch (seconds) | 900 |
| `HEALTH_CHECK_INTERVAL` | Interval for health checks (seconds) | 60 |
| `PING_COUNT` | Number of pings to send for latency/packet loss checks | 5 |
| `PING_TIMEOUT` | Timeout for ping operations (seconds) | 2 |
| `SNMP_COMMUNITY` | SNMP community string | public |
| `SNMP_VERSION` | SNMP version | 2c |
| `SNMP_TIMEOUT` | Timeout for SNMP operations (seconds) | 5 |

### Elasticsearch Integration

The Network Performance Monitoring module integrates with Elasticsearch for storing and querying metrics data. The following environment variables control this integration:

| Variable | Description | Default |
|----------|-------------|---------|
| `ELASTICSEARCH_ENABLED` | Enable/disable Elasticsearch integration | true |
| `ELASTICSEARCH_HOSTS` | Comma-separated list of Elasticsearch hosts | http://elasticsearch:9200 |
| `ELASTICSEARCH_USERNAME` | Elasticsearch username | elastic |
| `ELASTICSEARCH_PASSWORD` | Elasticsearch password | changeme |
| `ELASTICSEARCH_VERIFY_CERTS` | Verify SSL certificates | false |
| `ELASTICSEARCH_LOG_INDEX_PREFIX` | Prefix for log indices | isp-logs |
| `ELASTICSEARCH_METRIC_INDEX_PREFIX` | Prefix for metric indices | isp-metrics |

## API Endpoints

### Network Nodes Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/monitoring/network-nodes/` | List all network nodes |
| GET | `/monitoring/network-nodes/{node_id}` | Get a specific network node |
| POST | `/monitoring/network-nodes/` | Create a new network node |
| PUT | `/monitoring/network-nodes/{node_id}` | Update a network node |
| DELETE | `/monitoring/network-nodes/{node_id}` | Delete a network node |

## Dashboards

### Network Performance Dashboard

The Network Performance Dashboard provides visualizations for:
- Network latency by node
- Packet loss rates
- Bandwidth utilization
- Connection counts
- Traffic patterns

### Service Availability Dashboard

The Service Availability Dashboard provides visualizations for:
- Service uptime percentages
- Response time trends
- Error rates
- Health status indicators
- Recent service outages

### Customer Usage Dashboard

The Customer Usage Dashboard provides visualizations for:
- Total data usage by customer
- Session counts
- Data usage trends by traffic type
- Authentication events
- Top customers by usage

## Alert Rules

The system includes pre-configured alert rules for:

1. **High Network Latency**
   - Triggers when average latency exceeds 50ms
   - Notifies via email and Slack

2. **High Packet Loss**
   - Triggers when packet loss exceeds 2%
   - Notifies via email and Slack

3. **Bandwidth Saturation**
   - Triggers when bandwidth utilization exceeds 85%
   - Notifies via email and Slack

4. **Connection Count Spike**
   - Triggers when connection count exceeds 5000
   - Notifies via email and Slack

5. **Customer Quota Exceeded**
   - Triggers when customer usage exceeds 90% of quota
   - Notifies via email

## Usage Examples

### Adding a New Network Node

```python
import requests

# API endpoint
url = "https://api.ispmanagement.com/monitoring/network-nodes/"

# Authentication
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}

# Network node data
data = {
    "id": "router-main",
    "name": "Main Router",
    "ip_address": "192.168.1.1",
    "type": "router",
    "location": "Main Office",
    "model": "Cisco 4321",
    "manufacturer": "Cisco",
    "mac_address": "00:11:22:33:44:55",
    "is_active": True,
    "snmp_community": "public",
    "snmp_version": "2c"
}

# Create the network node
response = requests.post(url, json=data, headers=headers)
print(response.json())
```

### Querying Network Metrics

```python
import requests
from datetime import datetime, timedelta

# API endpoint
url = "https://api.ispmanagement.com/monitoring/metrics/"

# Authentication
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}

# Query parameters
params = {
    "metric_type": "NETWORK_LATENCY",
    "node_id": "router-main",
    "start_time": (datetime.utcnow() - timedelta(hours=24)).isoformat(),
    "end_time": datetime.utcnow().isoformat(),
    "interval": "5m"
}

# Get the metrics
response = requests.get(url, params=params, headers=headers)
print(response.json())
```

## Troubleshooting

### Common Issues

1. **Metrics Not Being Collected**
   - Check if the Celery worker is running
   - Verify network connectivity to the nodes
   - Check permissions for SNMP or SSH access

2. **Elasticsearch Synchronization Issues**
   - Verify Elasticsearch is running and accessible
   - Check Elasticsearch credentials
   - Review logs for synchronization errors

3. **Alert Notifications Not Working**
   - Verify email/Slack configuration
   - Check alert rule thresholds
   - Ensure notification connectors are properly configured

### Logs

Logs related to the Network Performance Monitoring module can be found in:

- Application logs: `/var/log/isp_management/application.log`
- Celery worker logs: `/var/log/isp_management/celery_worker.log`
- Elasticsearch logs: `/var/log/elasticsearch/elasticsearch.log`
- Kibana logs: `/var/log/kibana/kibana.log`

## Maintenance

### Index Lifecycle Management

The system automatically manages Elasticsearch indices using Index Lifecycle Management (ILM) policies:

- Hot phase: Recent data, optimized for querying
- Warm phase: Older data, reduced resources
- Cold phase: Historical data, minimal resources
- Delete phase: Data beyond retention period

The `optimize-indices.sh` script configures these policies.

### Dashboard Updates

Custom dashboards can be exported from Kibana and saved in the `docker/elasticsearch/kibana/dashboards/` directory. The `import-dashboards.sh` script can be used to import these dashboards into a new Kibana instance.

## Security Considerations

- Network node credentials (SNMP, SSH) are stored securely in the database
- API endpoints require appropriate permissions
- Elasticsearch integration uses secure connections and authentication
- Alert rules and notifications are restricted to authorized users
