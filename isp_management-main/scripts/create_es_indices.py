#!/usr/bin/env python
"""
Create Elasticsearch indices for service monitoring.

This script creates the necessary Elasticsearch indices for the service
monitoring feature, including mappings and settings.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("create_es_indices")

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Import mock dependencies to avoid connection issues
try:
    from tests.mock_dependencies import setup_mock_dependencies
    mock_deps = setup_mock_dependencies()
    logger.info("Successfully set up mock dependencies for imports")
except ImportError as e:
    logger.warning(f"Could not import mock dependencies: {e}")

# Import required modules
try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import RequestError
    
    # Import from project
    from backend_core.elasticsearch_client import ElasticsearchClient
    logger.info("Successfully imported required modules")
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    sys.exit(1)

# Service status index mapping
SERVICE_STATUS_MAPPING = {
    "mappings": {
        "properties": {
            "endpoint_id": {"type": "keyword"},
            "endpoint_name": {"type": "keyword"},
            "url": {"type": "keyword"},
            "protocol": {"type": "keyword"},
            "status": {"type": "keyword"},
            "response_time": {"type": "float"},
            "error_message": {"type": "text", "analyzer": "standard"},
            "timestamp": {"type": "date"},
            "created_at": {"type": "date"}
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index.mapping.total_fields.limit": 2000,
        "index.refresh_interval": "5s"
    }
}

# Service outage index mapping
SERVICE_OUTAGE_MAPPING = {
    "mappings": {
        "properties": {
            "endpoint_id": {"type": "keyword"},
            "endpoint_name": {"type": "keyword"},
            "url": {"type": "keyword"},
            "protocol": {"type": "keyword"},
            "start_time": {"type": "date"},
            "end_time": {"type": "date"},
            "duration": {"type": "long"},
            "severity": {"type": "keyword"},
            "description": {"type": "text", "analyzer": "standard"},
            "resolved": {"type": "boolean"},
            "resolution_notes": {"type": "text", "analyzer": "standard"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"}
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index.mapping.total_fields.limit": 2000,
        "index.refresh_interval": "5s"
    }
}

def create_indices():
    """Create Elasticsearch indices for service monitoring."""
    # Get Elasticsearch hosts from environment
    es_hosts = os.environ.get("ELASTICSEARCH_HOSTS", "http://localhost:9200")
    
    try:
        # Create Elasticsearch client
        es = Elasticsearch(hosts=es_hosts.split(","))
        
        # Check if Elasticsearch is available
        if not es.ping():
            logger.error("Could not connect to Elasticsearch")
            return False
        
        # Create service status index
        status_index = "service-monitoring-status"
        if not es.indices.exists(index=status_index):
            logger.info(f"Creating index: {status_index}")
            es.indices.create(index=status_index, body=SERVICE_STATUS_MAPPING)
            logger.info(f"Successfully created index: {status_index}")
        else:
            logger.info(f"Index already exists: {status_index}")
        
        # Create service outage index
        outage_index = "service-monitoring-outages"
        if not es.indices.exists(index=outage_index):
            logger.info(f"Creating index: {outage_index}")
            es.indices.create(index=outage_index, body=SERVICE_OUTAGE_MAPPING)
            logger.info(f"Successfully created index: {outage_index}")
        else:
            logger.info(f"Index already exists: {outage_index}")
        
        # Create index template for time-based indices
        template_name = "service-monitoring-template"
        template_body = {
            "index_patterns": ["service-monitoring-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "index.mapping.total_fields.limit": 2000,
                    "index.refresh_interval": "5s"
                },
                "mappings": {
                    "properties": {
                        "endpoint_id": {"type": "keyword"},
                        "endpoint_name": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "protocol": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "response_time": {"type": "float"},
                        "error_message": {"type": "text", "analyzer": "standard"},
                        "timestamp": {"type": "date"},
                        "created_at": {"type": "date"}
                    }
                }
            }
        }
        
        try:
            es.indices.put_template(name=template_name, body=template_body)
            logger.info(f"Successfully created index template: {template_name}")
        except RequestError as e:
            # For Elasticsearch 7.x, use put_index_template
            es.indices.put_index_template(name=template_name, body=template_body)
            logger.info(f"Successfully created index template: {template_name}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error creating Elasticsearch indices: {e}")
        return False


if __name__ == "__main__":
    logger.info("Creating Elasticsearch indices for service monitoring...")
    success = create_indices()
    if success:
        logger.info("Successfully created Elasticsearch indices")
        sys.exit(0)
    else:
        logger.error("Failed to create Elasticsearch indices")
        sys.exit(1)
