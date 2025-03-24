#!/usr/bin/env python
"""
Script to set up Elasticsearch indices for the Configuration Management Module.

This script creates the necessary Elasticsearch indices and mappings for the
Configuration Management Module if they don't already exist.
"""

import argparse
import logging
import os
import sys
from elasticsearch import Elasticsearch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.config_management.services.elasticsearch_service import ConfigurationElasticsearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Set up Elasticsearch indices for the Configuration Management Module'
    )
    parser.add_argument(
        '--es-host',
        default=os.environ.get('ELASTICSEARCH_HOST', 'localhost'),
        help='Elasticsearch host (default: localhost)'
    )
    parser.add_argument(
        '--es-port',
        default=os.environ.get('ELASTICSEARCH_PORT', '9200'),
        help='Elasticsearch port (default: 9200)'
    )
    parser.add_argument(
        '--es-username',
        default=os.environ.get('ELASTICSEARCH_USERNAME', ''),
        help='Elasticsearch username'
    )
    parser.add_argument(
        '--es-password',
        default=os.environ.get('ELASTICSEARCH_PASSWORD', ''),
        help='Elasticsearch password'
    )
    parser.add_argument(
        '--index-prefix',
        default=os.environ.get('ELASTICSEARCH_INDEX_PREFIX', 'isp'),
        help='Prefix for Elasticsearch indices (default: isp)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recreation of indices even if they already exist'
    )
    return parser.parse_args()


def setup_indices(args):
    """Set up Elasticsearch indices for the Configuration Management Module."""
    # Create Elasticsearch client
    es_hosts = [f"http://{args.es_host}:{args.es_port}"]
    es_auth = None
    if args.es_username and args.es_password:
        es_auth = (args.es_username, args.es_password)

    es_client = Elasticsearch(
        hosts=es_hosts,
        basic_auth=es_auth,
        verify_certs=False
    )

    # Check if Elasticsearch is available
    if not es_client.ping():
        logger.error(f"Could not connect to Elasticsearch at {es_hosts}")
        return False

    # Create ConfigurationElasticsearchService
    es_service = ConfigurationElasticsearchService(
        es_client=es_client,
        index_prefix=args.index_prefix
    )

    # Delete indices if force flag is set
    if args.force:
        logger.info("Force flag set, deleting existing indices...")
        indices = [
            f"{args.index_prefix}-configurations",
            f"{args.index_prefix}-configuration-history",
            f"{args.index_prefix}-configuration-groups"
        ]
        for index in indices:
            if es_client.indices.exists(index=index):
                logger.info(f"Deleting index: {index}")
                es_client.indices.delete(index=index)

    # Create indices
    logger.info("Creating indices...")
    es_service.create_indices_if_not_exist()

    logger.info("Indices setup complete!")
    return True


def main():
    """Main entry point."""
    args = parse_args()
    
    logger.info(f"Setting up Elasticsearch indices with prefix: {args.index_prefix}")
    
    if setup_indices(args):
        logger.info("Elasticsearch indices setup successfully!")
    else:
        logger.error("Failed to set up Elasticsearch indices")
        sys.exit(1)


if __name__ == "__main__":
    main()
