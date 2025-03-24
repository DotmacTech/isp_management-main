#!/usr/bin/env python
"""
Script to update Elasticsearch index templates for service monitoring.

This script loads the Elasticsearch index templates from the docker/elasticsearch/templates
directory and updates them in the Elasticsearch cluster.

Usage:
    python update_es_templates.py [--es-host ELASTICSEARCH_HOST]

Options:
    --es-host ELASTICSEARCH_HOST    Elasticsearch host URL (default: http://localhost:9200)
"""

import os
import sys
import json
import argparse
import logging
import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("update_es_templates")

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
templates_dir = os.path.join(project_root, "docker", "elasticsearch", "templates")


def get_elasticsearch_auth():
    """Get Elasticsearch authentication credentials from environment variables."""
    username = os.environ.get("ELASTICSEARCH_USERNAME")
    password = os.environ.get("ELASTICSEARCH_PASSWORD")
    
    if username and password:
        return HTTPBasicAuth(username, password)
    return None


def update_template(es_host, template_file, auth=None):
    """Update an Elasticsearch index template."""
    try:
        # Load template from file
        with open(template_file, "r") as f:
            template_data = json.load(f)
        
        # Extract template name from filename
        template_name = os.path.splitext(os.path.basename(template_file))[0]
        
        # Update template in Elasticsearch
        url = f"{es_host}/_template/{template_name}"
        headers = {"Content-Type": "application/json"}
        
        response = requests.put(url, json=template_data, headers=headers, auth=auth)
        
        if response.status_code in (200, 201):
            logger.info(f"Successfully updated template: {template_name}")
            return True
        else:
            logger.error(f"Failed to update template {template_name}: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error updating template {os.path.basename(template_file)}: {e}")
        return False


def update_all_templates(es_host, auth=None):
    """Update all Elasticsearch index templates."""
    if not os.path.exists(templates_dir):
        logger.error(f"Templates directory not found: {templates_dir}")
        return False
    
    # Find all JSON template files
    template_files = [
        os.path.join(templates_dir, f) 
        for f in os.listdir(templates_dir) 
        if f.endswith(".json")
    ]
    
    if not template_files:
        logger.warning(f"No template files found in {templates_dir}")
        return True
    
    # Update each template
    success = True
    for template_file in template_files:
        if not update_template(es_host, template_file, auth):
            success = False
    
    return success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Update Elasticsearch index templates")
    parser.add_argument(
        "--es-host", 
        default=os.environ.get("ELASTICSEARCH_HOSTS", "http://localhost:9200"),
        help="Elasticsearch host URL"
    )
    args = parser.parse_args()
    
    # Get authentication credentials
    auth = get_elasticsearch_auth()
    
    # Update templates
    logger.info(f"Updating Elasticsearch templates at {args.es_host}")
    success = update_all_templates(args.es_host, auth)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
