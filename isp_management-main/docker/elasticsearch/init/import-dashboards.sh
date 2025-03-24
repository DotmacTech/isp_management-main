#!/bin/bash

# Script to import dashboards into Kibana
# This script should be run after Elasticsearch and Kibana are up and running

set -e

# Configuration
KIBANA_URL=${KIBANA_URL:-"http://localhost:5601"}
KIBANA_USER=${KIBANA_USER:-"elastic"}
KIBANA_PASSWORD=${KIBANA_PASSWORD:-"changeme"}
DASHBOARDS_DIR=${DASHBOARDS_DIR:-"/opt/kibana/dashboards"}
WAIT_TIMEOUT=${WAIT_TIMEOUT:-300}

# Function to check if Kibana is ready
wait_for_kibana() {
  echo "Waiting for Kibana to be available..."
  start_time=$(date +%s)
  while true; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    
    if [ $elapsed_time -gt $WAIT_TIMEOUT ]; then
      echo "Timeout waiting for Kibana to be available"
      exit 1
    fi
    
    if curl -s -k -u "${KIBANA_USER}:${KIBANA_PASSWORD}" "${KIBANA_URL}/api/status" | grep -q '"overall":{"level":"available"'; then
      echo "Kibana is available!"
      break
    fi
    
    echo "Kibana not ready yet. Waiting 10 seconds..."
    sleep 10
  done
}

# Function to import a dashboard
import_dashboard() {
  local dashboard_file=$1
  local dashboard_name=$(basename "$dashboard_file" .ndjson)
  
  echo "Importing dashboard: $dashboard_name"
  
  # Import the dashboard using Kibana API
  response=$(curl -s -k -X POST \
    "${KIBANA_URL}/api/saved_objects/_import" \
    -H "kbn-xsrf: true" \
    -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
    --form file=@"${dashboard_file}" \
    --form overwrite=true)
  
  # Check for success
  if echo "$response" | grep -q '"success":true'; then
    echo "Successfully imported dashboard: $dashboard_name"
  else
    echo "Failed to import dashboard: $dashboard_name"
    echo "Response: $response"
    return 1
  fi
}

# Main execution
echo "Starting dashboard import process..."

# Wait for Kibana to be ready
wait_for_kibana

# Create index patterns if they don't exist
echo "Creating index patterns..."
curl -s -k -X POST \
  "${KIBANA_URL}/api/saved_objects/index-pattern/isp-logs-*" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
  -d '{"attributes":{"title":"isp-logs-*","timeFieldName":"timestamp"}}' > /dev/null

curl -s -k -X POST \
  "${KIBANA_URL}/api/saved_objects/index-pattern/isp-metrics-*" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
  -d '{"attributes":{"title":"isp-metrics-*","timeFieldName":"timestamp"}}' > /dev/null

# Import all dashboards
echo "Importing dashboards from $DASHBOARDS_DIR..."
for dashboard_file in "$DASHBOARDS_DIR"/*.ndjson; do
  if [ -f "$dashboard_file" ]; then
    import_dashboard "$dashboard_file"
  fi
done

echo "Dashboard import process completed!"
