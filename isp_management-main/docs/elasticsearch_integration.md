# Elasticsearch Integration for ISP Management Platform

This document provides comprehensive instructions for setting up and using the Elasticsearch integration with the ISP Management Platform's Monitoring Module.

## Overview

The Elasticsearch integration enables centralized logging, metrics collection, and system health monitoring for the ISP Management Platform. It provides the following capabilities:

- **Centralized Logging**: Collect and store logs from all services in Elasticsearch
- **Metrics Collection**: Store system metrics in Elasticsearch for historical analysis
- **Health Monitoring**: Track system health and component status
- **Visualization**: Use Kibana dashboards to visualize logs, metrics, and health data
- **Alerting**: Configure alerts based on log patterns and metric thresholds

## Architecture

The Elasticsearch integration consists of the following components:

- **Elasticsearch**: Stores logs, metrics, and health data
- **Kibana**: Provides visualization and dashboards
- **Logstash**: Processes and transforms logs before sending to Elasticsearch
- **Filebeat**: Collects logs from files and containers

The integration follows this data flow:

1. Application logs and metrics are stored in the database
2. Scheduled tasks sync logs and metrics to Elasticsearch
3. Elasticsearch indexes the data
4. Kibana provides visualization through pre-configured dashboards

## Prerequisites

- Docker and Docker Compose
- Access to the ISP Management Platform codebase
- Basic understanding of Elasticsearch and Kibana

## Setup Instructions

### 1. Start the Elasticsearch Stack

The ISP Management Platform includes a Docker Compose configuration for running the Elasticsearch stack. To start it:

```bash
cd /Users/michaelayoade/CascadeProjects/isp_management/docker/elasticsearch
chmod +x start-elasticsearch-stack.sh
./start-elasticsearch-stack.sh
```

This script will:
- Start Elasticsearch, Kibana, Logstash, and Filebeat
- Initialize Elasticsearch with index templates
- Import pre-configured Kibana dashboards

### 2. Configure the ISP Management Platform

Set the following environment variables to enable Elasticsearch integration:

```bash
# Enable Elasticsearch integration
ELASTICSEARCH_ENABLED=true

# Elasticsearch connection settings
ELASTICSEARCH_HOSTS=http://localhost:9200
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_VERIFY_CERTS=true

# Index settings
ELASTICSEARCH_LOG_INDEX_PREFIX=isp-logs
ELASTICSEARCH_METRIC_INDEX_PREFIX=isp-metrics
ELASTICSEARCH_INDEX_DATE_FORMAT=YYYY.MM.dd

# Performance settings
ELASTICSEARCH_NUMBER_OF_SHARDS=1
ELASTICSEARCH_NUMBER_OF_REPLICAS=0
ELASTICSEARCH_SYNC_BATCH_SIZE=100
```

### 3. Run Database Migrations

Run the database migrations to add the `elasticsearch_synced` field to the logs and metrics tables:

```bash
cd /Users/michaelayoade/CascadeProjects/isp_management
alembic upgrade head
```

### 4. Restart the ISP Management Platform

Restart the ISP Management Platform to apply the changes:

```bash
# If running with uvicorn
uvicorn isp_management.main:app --reload

# If running with docker-compose
docker-compose restart
```

## Using the Elasticsearch Integration

### Viewing Logs and Metrics

1. Access Kibana at http://localhost:5601
2. Navigate to the "Dashboards" section
3. Open one of the pre-configured dashboards:
   - ISP Management - System Health Dashboard
   - ISP Management - System Metrics Dashboard
   - ISP Management - Application Logs Dashboard

### Searching Logs

1. In Kibana, go to "Discover"
2. Select the "isp-logs-*" index pattern
3. Use the search bar to search for specific logs
4. Use filters to narrow down the results

Example searches:
- `log_level:ERROR`: Find all error logs
- `service_name:billing AND message:*failed*`: Find billing service logs with "failed" in the message
- `metadata.user_id:123`: Find logs related to a specific user

### Analyzing Metrics

1. In Kibana, go to "Discover"
2. Select the "isp-metrics-*" index pattern
3. Use the search bar to search for specific metrics
4. Use visualizations to analyze metrics over time

Example searches:
- `metric_type:cpu_usage AND value>80`: Find high CPU usage metrics
- `service_name:radius`: Find metrics for the RADIUS service
- `host_name:server1`: Find metrics for a specific host

### Creating Custom Visualizations

1. In Kibana, go to "Visualize"
2. Click "Create visualization"
3. Select a visualization type (e.g., Line, Bar, Pie)
4. Configure the visualization with the desired metrics and dimensions
5. Save the visualization
6. Add the visualization to a dashboard

### Creating Custom Dashboards

1. In Kibana, go to "Dashboard"
2. Click "Create dashboard"
3. Add visualizations to the dashboard
4. Arrange and resize visualizations as needed
5. Save the dashboard

## Monitoring Features

### Network Performance Monitoring

The Elasticsearch integration includes network performance monitoring capabilities:

- **Bandwidth Usage**: Track bandwidth usage by service and customer
- **Latency**: Monitor network latency between components
- **Packet Loss**: Track packet loss rates
- **Connection Counts**: Monitor active connections

To view network performance metrics:
1. Open the "System Metrics Dashboard" in Kibana
2. Look for the "Network Traffic" visualization

### Service Availability Tracking

The integration tracks service availability and performance:

- **Uptime**: Monitor service uptime percentage
- **Response Time**: Track service response times
- **Error Rates**: Monitor service error rates
- **Health Status**: Track overall service health status

To view service availability metrics:
1. Open the "System Health Dashboard" in Kibana
2. Look for the "Service Availability" visualization

### Customer Usage Statistics

The integration collects customer usage statistics:

- **Data Usage**: Track customer data usage over time
- **Session Counts**: Monitor customer session counts
- **Authentication Events**: Track customer authentication events
- **Billing Events**: Monitor customer billing events

To view customer usage statistics:
1. Open the "Customer Usage Dashboard" in Kibana (if available)
2. Look for customer-specific visualizations

## Troubleshooting

### Common Issues

#### Elasticsearch Not Starting

If Elasticsearch fails to start, check:
- Docker logs: `docker logs isp-elasticsearch`
- Memory settings: Ensure the host has enough memory
- File permissions: Ensure the data directory is writable

#### Logs Not Appearing in Elasticsearch

If logs are not appearing in Elasticsearch, check:
- Elasticsearch connection: Ensure the connection settings are correct
- Sync tasks: Check if the sync tasks are running
- Database records: Check if logs exist in the database

#### Kibana Dashboards Not Loading

If Kibana dashboards are not loading, check:
- Kibana logs: `docker logs isp-kibana`
- Index patterns: Ensure index patterns are created
- Elasticsearch indices: Check if indices exist in Elasticsearch

### Viewing Logs

To view logs for the Elasticsearch stack:

```bash
# Elasticsearch logs
docker logs isp-elasticsearch

# Kibana logs
docker logs isp-kibana

# Logstash logs
docker logs isp-logstash

# Filebeat logs
docker logs isp-filebeat
```

## Advanced Configuration

### Scaling Elasticsearch

For production environments, consider scaling Elasticsearch:

1. Increase the number of shards and replicas:
   ```
   ELASTICSEARCH_NUMBER_OF_SHARDS=3
   ELASTICSEARCH_NUMBER_OF_REPLICAS=1
   ```

2. Configure a multi-node Elasticsearch cluster:
   - Edit the Docker Compose file to add more Elasticsearch nodes
   - Configure node roles (master, data, ingest)
   - Set up proper discovery settings

### Securing Elasticsearch

For production environments, secure Elasticsearch:

1. Enable X-Pack security:
   ```yaml
   xpack.security.enabled: true
   ```

2. Set up SSL/TLS:
   ```yaml
   xpack.security.transport.ssl.enabled: true
   xpack.security.http.ssl.enabled: true
   ```

3. Configure authentication:
   - Set up users and roles
   - Use strong passwords
   - Consider integrating with LDAP or Active Directory

### Index Lifecycle Management

Configure index lifecycle management to automatically manage indices:

1. Create an index lifecycle policy:
   ```json
   {
     "policy": {
       "phases": {
         "hot": {
           "min_age": "0ms",
           "actions": {
             "rollover": {
               "max_age": "7d",
               "max_size": "10gb"
             }
           }
         },
         "warm": {
           "min_age": "30d",
           "actions": {
             "shrink": {
               "number_of_shards": 1
             },
             "forcemerge": {
               "max_num_segments": 1
             }
           }
         },
         "cold": {
           "min_age": "60d",
           "actions": {}
         },
         "delete": {
           "min_age": "90d",
           "actions": {
             "delete": {}
           }
         }
       }
     }
   }
   ```

2. Apply the policy to indices:
   ```
   PUT _template/isp-logs-template
   {
     "index_patterns": ["isp-logs-*"],
     "settings": {
       "index.lifecycle.name": "isp-logs-policy",
       "index.lifecycle.rollover_alias": "isp-logs"
     }
   }
   ```

## References

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Documentation](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Logstash Documentation](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Filebeat Documentation](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)
