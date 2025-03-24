#!/bin/bash
# Script to initialize Elasticsearch with index templates and default dashboards

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s http://elasticsearch:9200 >/dev/null; do
    sleep 5
    echo "Still waiting..."
done
echo "Elasticsearch is ready!"

# Create index templates for logs
echo "Creating index template for logs..."
curl -X PUT "http://elasticsearch:9200/_template/isp-logs-template" -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["isp-logs-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.refresh_interval": "5s"
  },
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "timestamp": { "type": "date" },
      "service_name": { "type": "keyword" },
      "log_level": { "type": "keyword" },
      "message": { 
        "type": "text",
        "fields": {
          "keyword": { "type": "keyword", "ignore_above": 256 }
        }
      },
      "host_name": { "type": "keyword" },
      "trace_id": { "type": "keyword" },
      "correlation_id": { "type": "keyword" },
      "user_id": { "type": "long" },
      "source_ip": { "type": "ip" },
      "request_path": { "type": "keyword" },
      "request_method": { "type": "keyword" },
      "response_status": { "type": "integer" },
      "execution_time_ms": { "type": "float" },
      "metadata": { "type": "object", "dynamic": true }
    }
  }
}'

# Create index templates for metrics
echo "Creating index template for metrics..."
curl -X PUT "http://elasticsearch:9200/_template/isp-metrics-template" -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["isp-metrics-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.refresh_interval": "5s"
  },
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "timestamp": { "type": "date" },
      "service_name": { "type": "keyword" },
      "host_name": { "type": "keyword" },
      "metric_type": { "type": "keyword" },
      "value": { "type": "float" },
      "unit": { "type": "keyword" },
      "tags": { "type": "object", "dynamic": true },
      "sampling_rate": { "type": "float" }
    }
  }
}'

# Create index templates for health checks
echo "Creating index template for health checks..."
curl -X PUT "http://elasticsearch:9200/_template/isp-health-template" -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["isp-health-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.refresh_interval": "5s"
  },
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "timestamp": { "type": "date" },
      "component_name": { "type": "keyword" },
      "status": { "type": "keyword" },
      "message": { "type": "text" },
      "details": { "type": "object", "dynamic": true },
      "response_time_ms": { "type": "float" }
    }
  }
}'

echo "Elasticsearch initialization completed!"
