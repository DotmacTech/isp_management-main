#!/bin/bash

# Script to import Kibana dashboards, visualizations, and other saved objects
# This script should be run after Elasticsearch and Kibana are up and running

# Configuration
KIBANA_URL=${KIBANA_URL:-"http://localhost:5601"}
KIBANA_API_URL="${KIBANA_URL}/api/saved_objects"
KIBANA_SPACE=${KIBANA_SPACE:-"default"}
KIBANA_USER=${KIBANA_USER:-"elastic"}
KIBANA_PASSWORD=${KIBANA_PASSWORD:-"changeme"}
VISUALIZATIONS_DIR="/usr/share/kibana/visualizations"
DASHBOARDS_DIR="/usr/share/kibana/dashboards"
INDEX_PATTERNS_DIR="/usr/share/kibana/index-patterns"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to check if Kibana is ready
check_kibana_ready() {
  echo -e "${YELLOW}Checking if Kibana is ready...${NC}"
  
  local max_attempts=30
  local attempt=0
  
  while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt+1))
    
    # Check if Kibana is ready
    status_code=$(curl -s -o /dev/null -w "%{http_code}" -u "${KIBANA_USER}:${KIBANA_PASSWORD}" "${KIBANA_URL}/api/status")
    
    if [ "$status_code" -eq 200 ]; then
      echo -e "${GREEN}Kibana is ready!${NC}"
      return 0
    else
      echo -e "${YELLOW}Kibana is not ready yet. Attempt $attempt/$max_attempts. Waiting 10 seconds...${NC}"
      sleep 10
    fi
  done
  
  echo -e "${RED}Kibana did not become ready within the expected time. Exiting.${NC}"
  return 1
}

# Function to import index patterns
import_index_patterns() {
  echo -e "${YELLOW}Importing index patterns...${NC}"
  
  for file in "$INDEX_PATTERNS_DIR"/*.json; do
    if [ -f "$file" ]; then
      filename=$(basename "$file")
      pattern_name="${filename%.json}"
      
      echo -e "${YELLOW}Importing index pattern: $pattern_name${NC}"
      
      response=$(curl -s -X POST \
        -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        -d @"$file" \
        "${KIBANA_API_URL}/index-pattern")
      
      if echo "$response" | grep -q "error"; then
        echo -e "${RED}Failed to import index pattern $pattern_name: $response${NC}"
      else
        echo -e "${GREEN}Successfully imported index pattern: $pattern_name${NC}"
      fi
    fi
  done
}

# Function to import visualizations
import_visualizations() {
  echo -e "${YELLOW}Importing visualizations...${NC}"
  
  for file in "$VISUALIZATIONS_DIR"/*.json; do
    if [ -f "$file" ]; then
      filename=$(basename "$file")
      vis_name="${filename%.json}"
      
      echo -e "${YELLOW}Importing visualization: $vis_name${NC}"
      
      response=$(curl -s -X POST \
        -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        -d @"$file" \
        "${KIBANA_API_URL}/visualization")
      
      if echo "$response" | grep -q "error"; then
        echo -e "${RED}Failed to import visualization $vis_name: $response${NC}"
      else
        echo -e "${GREEN}Successfully imported visualization: $vis_name${NC}"
      fi
    fi
  done
}

# Function to import dashboards
import_dashboards() {
  echo -e "${YELLOW}Importing dashboards...${NC}"
  
  for file in "$DASHBOARDS_DIR"/*.json; do
    if [ -f "$file" ]; then
      filename=$(basename "$file")
      dashboard_name="${filename%.json}"
      
      echo -e "${YELLOW}Importing dashboard: $dashboard_name${NC}"
      
      response=$(curl -s -X POST \
        -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        -d @"$file" \
        "${KIBANA_API_URL}/dashboard")
      
      if echo "$response" | grep -q "error"; then
        echo -e "${RED}Failed to import dashboard $dashboard_name: $response${NC}"
      else
        echo -e "${GREEN}Successfully imported dashboard: $dashboard_name${NC}"
      fi
    fi
  done
}

# Function to create alert connectors
create_alert_connectors() {
  echo -e "${YELLOW}Creating alert connectors...${NC}"
  
  # Create email connector
  email_connector='{
    "name": "email-connector",
    "connector_type_id": ".email",
    "config": {
      "from": "alerts@isp-management.com",
      "host": "smtp.example.com",
      "port": 587,
      "secure": true
    },
    "secrets": {
      "user": "alerts@isp-management.com",
      "password": "changeme"
    }
  }'
  
  response=$(curl -s -X POST \
    -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d "$email_connector" \
    "${KIBANA_URL}/api/actions/connector")
  
  if echo "$response" | grep -q "error"; then
    echo -e "${RED}Failed to create email connector: $response${NC}"
  else
    echo -e "${GREEN}Successfully created email connector${NC}"
  fi
  
  # Create Slack connector
  slack_connector='{
    "name": "slack-connector",
    "connector_type_id": ".slack",
    "config": {
      "webhookUrl": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    }
  }'
  
  response=$(curl -s -X POST \
    -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d "$slack_connector" \
    "${KIBANA_URL}/api/actions/connector")
  
  if echo "$response" | grep -q "error"; then
    echo -e "${RED}Failed to create Slack connector: $response${NC}"
  else
    echo -e "${GREEN}Successfully created Slack connector${NC}"
  fi
}

# Function to import alert rules
import_alert_rules() {
  echo -e "${YELLOW}Importing alert rules...${NC}"
  
  # Import alert rules from file
  for file in "/usr/share/kibana/alert-rules"/*.json; do
    if [ -f "$file" ]; then
      echo -e "${YELLOW}Importing alert rules from: $(basename "$file")${NC}"
      
      # Read the file content
      rules_content=$(cat "$file")
      
      # Import each rule in the array
      echo "$rules_content" | jq -c '.[]' | while read -r rule; do
        rule_name=$(echo "$rule" | jq -r '.attributes.name')
        echo -e "${YELLOW}Importing rule: $rule_name${NC}"
        
        response=$(curl -s -X POST \
          -u "${KIBANA_USER}:${KIBANA_PASSWORD}" \
          -H "kbn-xsrf: true" \
          -H "Content-Type: application/json" \
          -d "$rule" \
          "${KIBANA_URL}/api/alerting/rule")
        
        if echo "$response" | grep -q "error"; then
          echo -e "${RED}Failed to import rule $rule_name: $response${NC}"
        else
          echo -e "${GREEN}Successfully imported rule: $rule_name${NC}"
        fi
      done
    fi
  done
}

# Main execution
echo -e "${YELLOW}Starting Kibana objects import...${NC}"

# Check if Kibana is ready
check_kibana_ready || exit 1

# Create alert connectors
create_alert_connectors

# Import index patterns
import_index_patterns

# Import visualizations
import_visualizations

# Import dashboards
import_dashboards

# Import alert rules
import_alert_rules

echo -e "${GREEN}Kibana objects import completed!${NC}"
