#!/bin/bash
# Script to deploy the service availability monitoring feature
# This script runs all the necessary steps to deploy the feature in a production environment

set -e  # Exit on any error

# Display banner
echo "====================================================="
echo "  ISP Management Platform - Service Monitoring Deployment"
echo "====================================================="
echo

# Function to display step information
function step() {
    echo
    echo "→ $1"
    echo "---------------------------------------------------"
}

# Check if running with sudo/root privileges
if [[ $EUID -ne 0 ]]; then
    echo "⚠️  This script should be run with sudo privileges"
    echo "Please run: sudo $0"
    exit 1
fi

# Set environment variables if not already set
export ELASTICSEARCH_HOSTS=${ELASTICSEARCH_HOSTS:-"http://localhost:9200"}
export DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:postgres@localhost:5432/isp_management"}
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
export SERVICE_CHECK_INTERVAL=${SERVICE_CHECK_INTERVAL:-"60"}
export OUTAGE_DETECTION_THRESHOLD=${OUTAGE_DETECTION_THRESHOLD:-"3"}
export SERVICE_CHECK_TIMEOUT=${SERVICE_CHECK_TIMEOUT:-"5"}

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root directory
cd "$PROJECT_ROOT"

# Step 1: Run database migrations
step "Running database migrations"
python scripts/run_migrations.py
echo "✓ Database migrations completed"

# Step 2: Update Elasticsearch templates
step "Updating Elasticsearch templates"
python scripts/update_es_templates.py
echo "✓ Elasticsearch templates updated"

# Step 3: Run comprehensive test suite
step "Running comprehensive test suite"
python -m pytest tests/modules/monitoring -v --cov=modules.monitoring --cov-report=term --cov-report=html:coverage/monitoring
if [ $? -eq 0 ]; then
    echo "✓ All tests passed"
else
    echo "⚠️  Some tests failed"
    echo "   Please check the test output for details"
    echo "   Continuing deployment, but manual verification is recommended"
fi

# Step 4: Restart Celery workers
step "Restarting Celery workers"
if systemctl is-active --quiet isp-celery; then
    systemctl restart isp-celery
    echo "✓ Celery workers restarted"
else
    echo "⚠️  Celery service not found, skipping restart"
    echo "   You may need to manually restart Celery workers"
fi

# Step 5: Restart API server
step "Restarting API server"
if systemctl is-active --quiet isp-api; then
    systemctl restart isp-api
    echo "✓ API server restarted"
else
    echo "⚠️  API service not found, skipping restart"
    echo "   You may need to manually restart the API server"
fi

# Step 6: Run service monitoring tests
step "Running service monitoring tests"
python scripts/test_service_monitoring_integration.py -v
if [ $? -eq 0 ]; then
    echo "✓ Service monitoring tests passed"
else
    echo "⚠️  Service monitoring tests failed"
    echo "   Please check the test output for details"
fi

# Step 7: Verify Elasticsearch connectivity and indices
step "Verifying Elasticsearch connectivity and indices"
curl -s "$ELASTICSEARCH_HOSTS" > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Elasticsearch connectivity verified"
    
    # Check if service monitoring indices exist
    curl -s "$ELASTICSEARCH_HOSTS/_cat/indices/service-monitoring-*" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✓ Service monitoring indices verified"
    else
        echo "⚠️  Service monitoring indices not found"
        echo "   Creating indices..."
        python scripts/create_es_indices.py
    fi
else
    echo "⚠️  Could not connect to Elasticsearch"
    echo "   Please check your Elasticsearch configuration"
fi

# Step 8: Create initial service endpoints
step "Creating initial service endpoints"
python -c "
from modules.monitoring.services.availability_service import AvailabilityService
from modules.monitoring.models.service_availability import ProtocolType
from backend_core.database import SessionLocal

# Create database session
db = SessionLocal()

try:
    # Create availability service
    service = AvailabilityService(db)
    
    # Create default service endpoints
    endpoints = [
        {
            'id': 'api-gateway',
            'name': 'API Gateway',
            'url': 'http://localhost:8000/health',
            'protocol': 'HTTP',
            'check_interval': 60,
            'timeout': 5,
            'retries': 3,
            'expected_status_code': 200,
            'is_active': True
        },
        {
            'id': 'radius-server',
            'name': 'RADIUS Server',
            'url': 'localhost:1812',
            'protocol': 'UDP',
            'check_interval': 60,
            'timeout': 5,
            'retries': 3,
            'is_active': True
        },
        {
            'id': 'billing-service',
            'name': 'Billing Service',
            'url': 'http://localhost:8001/health',
            'protocol': 'HTTP',
            'check_interval': 60,
            'timeout': 5,
            'retries': 3,
            'expected_status_code': 200,
            'is_active': True
        },
        {
            'id': 'elasticsearch-service',
            'name': 'Elasticsearch Service',
            'url': 'localhost:9200',
            'protocol': 'TCP',
            'check_interval': 60,
            'timeout': 5,
            'retries': 3,
            'is_active': True
        },
        {
            'id': 'redis-service',
            'name': 'Redis Service',
            'url': 'localhost:6379',
            'protocol': 'TCP',
            'check_interval': 60,
            'timeout': 5,
            'retries': 3,
            'is_active': True
        }
    ]
    
    # Add endpoints if they don't exist
    for endpoint_data in endpoints:
        existing = service.get_endpoint(endpoint_data['id'])
        if not existing:
            service.create_endpoint(endpoint_data)
            print(f'Created endpoint: {endpoint_data[\"name\"]}')
        else:
            print(f'Endpoint already exists: {endpoint_data[\"name\"]}')
    
    print('Initial service endpoints created successfully')
finally:
    db.close()
"
echo "✓ Initial service endpoints created"

# Step 9: Set up Kibana dashboards
step "Setting up Kibana dashboards"
if [ -f "kibana/dashboards/service-monitoring-dashboard.json" ]; then
    echo "Importing Kibana dashboards..."
    curl -X POST "$ELASTICSEARCH_HOSTS/../kibana/api/saved_objects/_import" -H "kbn-xsrf: true" --form file=@kibana/dashboards/service-monitoring-dashboard.json
    if [ $? -eq 0 ]; then
        echo "✓ Kibana dashboards imported"
    else
        echo "⚠️  Failed to import Kibana dashboards"
        echo "   Please import them manually through the Kibana UI"
    fi
else
    echo "⚠️  Kibana dashboard file not found"
    echo "   Please import dashboards manually through the Kibana UI"
fi

# Deployment complete
echo
echo "====================================================="
echo "  Service Monitoring Deployment Complete"
echo "====================================================="
echo
echo "The service availability monitoring feature has been successfully deployed."
echo
echo "You can now access the following resources:"
echo "- API Endpoints: http://your-server/api/v1/monitoring/services/"
echo "- Kibana Dashboards: http://your-server:5601/app/kibana#/dashboard/service-availability-dashboard"
echo
echo "For more information, see the documentation at:"
echo "- docs/service_monitoring_implementation.md"
echo "- docs/service_monitoring_test_report.md"
echo
echo "If you encounter any issues, please check the logs at:"
echo "- /var/log/isp-management/api.log"
echo "- /var/log/isp-management/celery.log"
echo
