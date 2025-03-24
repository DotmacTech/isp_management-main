#!/bin/bash
# Script to import Kibana dashboards

# Wait for Kibana to be ready
echo "Waiting for Kibana to be ready..."
until curl -s http://kibana:5601/api/status >/dev/null; do
    sleep 5
    echo "Still waiting..."
done
echo "Kibana is ready!"

# Create Kibana index patterns
echo "Creating Kibana index patterns..."

# Create logs index pattern
curl -X POST "http://kibana:5601/api/saved_objects/index-pattern/isp-logs-*" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{"attributes": {"title": "isp-logs-*", "timeFieldName": "timestamp"}}'

# Create metrics index pattern
curl -X POST "http://kibana:5601/api/saved_objects/index-pattern/isp-metrics-*" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{"attributes": {"title": "isp-metrics-*", "timeFieldName": "timestamp"}}'

# Create health index pattern
curl -X POST "http://kibana:5601/api/saved_objects/index-pattern/isp-health-*" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{"attributes": {"title": "isp-health-*", "timeFieldName": "timestamp"}}'

# Import dashboards
echo "Importing Kibana dashboards..."

# Import system health dashboard
curl -X POST "http://kibana:5601/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  --form file=@/dashboards/system-health-dashboard.ndjson

# Import system metrics dashboard
curl -X POST "http://kibana:5601/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  --form file=@/dashboards/system-metrics-dashboard.ndjson

# Import application logs dashboard
curl -X POST "http://kibana:5601/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  --form file=@/dashboards/application-logs-dashboard.ndjson

echo "Kibana dashboards imported successfully!"
