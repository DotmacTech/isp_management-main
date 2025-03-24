#!/bin/bash
# Script to import alert rules into Kibana

# Wait for Kibana to be ready
echo "Waiting for Kibana to be ready..."
until curl -s http://kibana:5601/api/status >/dev/null; do
    sleep 5
    echo "Still waiting..."
done
echo "Kibana is ready!"

# Create email connector for alerts
echo "Creating email connector for alerts..."
curl -X POST "http://kibana:5601/api/actions/connector" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Email Alerts",
    "connector_type_id": ".email",
    "config": {
      "from": "alerts@ispmanagement.com",
      "host": "smtp.example.com",
      "port": 587,
      "secure": true
    },
    "secrets": {
      "user": "alerts@ispmanagement.com",
      "password": "placeholder_password"
    }
  }'

# Create Slack connector for alerts
echo "Creating Slack connector for alerts..."
curl -X POST "http://kibana:5601/api/actions/connector" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Slack Alerts",
    "connector_type_id": ".slack",
    "config": {
      "webhookUrl": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    }
  }'

# Import system alert rules
echo "Importing system alert rules..."
curl -X POST "http://kibana:5601/api/saved_objects/_import" \
  -H 'kbn-xsrf: true' \
  --form file=@/opt/kibana/alerting/alert-rules.json

# Import network performance alert rules
echo "Importing network performance alert rules..."
curl -X POST "http://kibana:5601/api/saved_objects/_import" \
  -H 'kbn-xsrf: true' \
  --form file=@/opt/kibana/alerting/network-performance-alerts.json

echo "Alert rules imported successfully!"
