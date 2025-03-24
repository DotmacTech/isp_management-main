#!/bin/bash
# Import Elasticsearch index templates and ILM policies

set -e

# Wait for Elasticsearch to be available
echo "Waiting for Elasticsearch to be available..."
until curl -s "http://elasticsearch:9200" > /dev/null; do
    sleep 1
done
echo "Elasticsearch is available."

# Create ILM policy for metrics
echo "Creating ILM policy for metrics..."
curl -X PUT "http://elasticsearch:9200/_ilm/policy/isp-metrics-policy" -H 'Content-Type: application/json' -d '
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "1d",
            "max_size": "5gb"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "set_priority": {
            "priority": 0
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'

# Import network metrics template
echo "Importing network metrics template..."
curl -X PUT "http://elasticsearch:9200/_index_template/network-metrics-template" -H 'Content-Type: application/json' -d @/templates/network-metrics-template.json

# Create initial indices and aliases
echo "Creating initial indices and aliases..."

# Network metrics index
curl -X PUT "http://elasticsearch:9200/isp-network-metrics-000001" -H 'Content-Type: application/json' -d '
{
  "aliases": {
    "isp-network-metrics": {
      "is_write_index": true
    }
  }
}'

# Service metrics index
curl -X PUT "http://elasticsearch:9200/isp-service-metrics-000001" -H 'Content-Type: application/json' -d '
{
  "aliases": {
    "isp-service-metrics": {
      "is_write_index": true
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "index.lifecycle.name": "isp-metrics-policy",
    "index.lifecycle.rollover_alias": "isp-service-metrics"
  },
  "mappings": {
    "properties": {
      "@timestamp": {
        "type": "date"
      },
      "service_id": {
        "type": "keyword"
      },
      "service_name": {
        "type": "keyword"
      },
      "service_type": {
        "type": "keyword"
      },
      "host": {
        "type": "keyword"
      },
      "port": {
        "type": "integer"
      },
      "url": {
        "type": "keyword"
      },
      "metric_type": {
        "type": "keyword"
      },
      "metric_name": {
        "type": "keyword"
      },
      "value": {
        "type": "float"
      },
      "unit": {
        "type": "keyword"
      },
      "availability": {
        "type": "boolean"
      },
      "response_time": {
        "type": "float"
      },
      "error_rate": {
        "type": "float"
      },
      "request_count": {
        "type": "integer"
      },
      "tags": {
        "type": "keyword"
      },
      "alert_level": {
        "type": "keyword"
      }
    }
  }
}'

# Customer usage index
curl -X PUT "http://elasticsearch:9200/isp-customer-usage-000001" -H 'Content-Type: application/json' -d '
{
  "aliases": {
    "isp-customer-usage": {
      "is_write_index": true
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "index.lifecycle.name": "isp-metrics-policy",
    "index.lifecycle.rollover_alias": "isp-customer-usage"
  },
  "mappings": {
    "properties": {
      "@timestamp": {
        "type": "date"
      },
      "customer_id": {
        "type": "keyword"
      },
      "customer_name": {
        "type": "keyword"
      },
      "account_id": {
        "type": "keyword"
      },
      "plan_id": {
        "type": "keyword"
      },
      "plan_name": {
        "type": "keyword"
      },
      "metric_type": {
        "type": "keyword"
      },
      "metric_name": {
        "type": "keyword"
      },
      "value": {
        "type": "float"
      },
      "unit": {
        "type": "keyword"
      },
      "data_usage": {
        "type": "float"
      },
      "session_count": {
        "type": "integer"
      },
      "session_duration": {
        "type": "float"
      },
      "authentication_events": {
        "type": "integer"
      },
      "quota_percentage": {
        "type": "float"
      },
      "tags": {
        "type": "keyword"
      },
      "alert_level": {
        "type": "keyword"
      }
    }
  }
}'

echo "Index templates and ILM policies imported successfully."
