#!/bin/bash
# Script to optimize Elasticsearch indices for better performance

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s http://elasticsearch:9200 >/dev/null; do
    sleep 5
    echo "Still waiting..."
done
echo "Elasticsearch is ready!"

# Create ILM policy for logs
echo "Creating ILM policy for logs..."
curl -X PUT "http://elasticsearch:9200/_ilm/policy/isp-logs-policy" \
  -H 'Content-Type: application/json' \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "min_age": "0ms",
          "actions": {
            "rollover": {
              "max_age": "7d",
              "max_size": "10gb"
            },
            "set_priority": {
              "priority": 100
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
            },
            "set_priority": {
              "priority": 50
            }
          }
        },
        "cold": {
          "min_age": "60d",
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

# Create ILM policy for metrics
echo "Creating ILM policy for metrics..."
curl -X PUT "http://elasticsearch:9200/_ilm/policy/isp-metrics-policy" \
  -H 'Content-Type: application/json' \
  -d '{
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
          "min_age": "60d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }'

# Apply ILM policy to logs index template
echo "Applying ILM policy to logs index template..."
curl -X PUT "http://elasticsearch:9200/_template/isp-logs-template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["isp-logs-*"],
    "settings": {
      "index.lifecycle.name": "isp-logs-policy",
      "index.lifecycle.rollover_alias": "isp-logs"
    }
  }'

# Apply ILM policy to metrics index template
echo "Applying ILM policy to metrics index template..."
curl -X PUT "http://elasticsearch:9200/_template/isp-metrics-template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["isp-metrics-*"],
    "settings": {
      "index.lifecycle.name": "isp-metrics-policy",
      "index.lifecycle.rollover_alias": "isp-metrics"
    }
  }'

# Create index aliases
echo "Creating index aliases..."
curl -X PUT "http://elasticsearch:9200/isp-logs-000001" \
  -H 'Content-Type: application/json' \
  -d '{
    "aliases": {
      "isp-logs": {
        "is_write_index": true
      }
    },
    "settings": {
      "index.lifecycle.name": "isp-logs-policy"
    }
  }'

curl -X PUT "http://elasticsearch:9200/isp-metrics-000001" \
  -H 'Content-Type: application/json' \
  -d '{
    "aliases": {
      "isp-metrics": {
        "is_write_index": true
      }
    },
    "settings": {
      "index.lifecycle.name": "isp-metrics-policy"
    }
  }'

# Optimize shard allocation
echo "Optimizing shard allocation..."
curl -X PUT "http://elasticsearch:9200/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "persistent": {
      "cluster.routing.allocation.disk.threshold_enabled": true,
      "cluster.routing.allocation.disk.watermark.low": "85%",
      "cluster.routing.allocation.disk.watermark.high": "90%",
      "cluster.routing.allocation.disk.watermark.flood_stage": "95%"
    }
  }'

# Configure index defaults
echo "Configuring index defaults..."
curl -X PUT "http://elasticsearch:9200/_template/default_template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["*"],
    "order": -1,
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "refresh_interval": "5s",
      "index.translog.durability": "async",
      "index.translog.sync_interval": "5s"
    }
  }'

echo "Elasticsearch optimization complete!"
