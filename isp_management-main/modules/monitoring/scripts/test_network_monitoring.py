#!/usr/bin/env python3
"""
Test script for network performance monitoring functionality.

This script tests the network performance monitoring features by:
1. Creating test network nodes
2. Collecting network performance metrics
3. Querying metrics from Elasticsearch
4. Testing alert thresholds
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta
import json
import random
from typing import Dict, List, Any

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from sqlalchemy.orm import Session
from modules.core.database import get_db, engine
from modules.monitoring.models import NetworkNode, NodeType, Base
from modules.monitoring.schemas.network_node import NetworkNodeCreate
from modules.monitoring.services.network_service import NetworkService
from modules.monitoring.collectors.network_performance_collector import NetworkPerformanceCollector
from modules.monitoring.elasticsearch import ElasticsearchClient
from modules.monitoring.tasks import collect_network_performance_metrics_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_test_database():
    """Create test database tables if they don't exist."""
    logger.info("Setting up test database...")
    Base.metadata.create_all(bind=engine)


def create_test_nodes(db: Session) -> List[NetworkNode]:
    """Create test network nodes for monitoring."""
    logger.info("Creating test network nodes...")
    
    # Define test nodes
    test_nodes = [
        {
            "id": "router-main-test",
            "name": "Main Router (Test)",
            "ip_address": "192.168.1.1",
            "type": NodeType.ROUTER,
            "location": "Main Office",
            "model": "Cisco 4321",
            "manufacturer": "Cisco",
            "is_active": True,
            "snmp_community": "public",
            "snmp_version": "2c"
        },
        {
            "id": "switch-core-test",
            "name": "Core Switch (Test)",
            "ip_address": "192.168.1.2",
            "type": NodeType.SWITCH,
            "location": "Main Office",
            "model": "Cisco Catalyst 3750",
            "manufacturer": "Cisco",
            "is_active": True,
            "snmp_community": "public",
            "snmp_version": "2c"
        },
        {
            "id": "ap-office-test",
            "name": "Office AP (Test)",
            "ip_address": "192.168.1.3",
            "type": NodeType.ACCESS_POINT,
            "location": "Main Office",
            "model": "Ubiquiti UniFi AP Pro",
            "manufacturer": "Ubiquiti",
            "is_active": True,
            "snmp_community": "public",
            "snmp_version": "2c"
        },
        {
            "id": "server-radius-test",
            "name": "RADIUS Server (Test)",
            "ip_address": "192.168.1.4",
            "type": NodeType.SERVER,
            "location": "Data Center",
            "model": "Dell PowerEdge R740",
            "manufacturer": "Dell",
            "is_active": True,
            "snmp_community": "public",
            "snmp_version": "2c"
        },
        {
            "id": "router-branch-test",
            "name": "Branch Router (Test)",
            "ip_address": "192.168.2.1",
            "type": NodeType.ROUTER,
            "location": "Branch Office",
            "model": "Cisco 2901",
            "manufacturer": "Cisco",
            "is_active": True,
            "snmp_community": "public",
            "snmp_version": "2c"
        }
    ]
    
    # Create network service
    network_service = NetworkService(db)
    
    # Create nodes
    created_nodes = []
    for node_data in test_nodes:
        try:
            # Check if node already exists
            existing_node = network_service.get_node_by_id(node_data["id"])
            if existing_node:
                logger.info(f"Node {node_data['id']} already exists, skipping creation")
                created_nodes.append(existing_node)
                continue
            
            # Create node
            node_schema = NetworkNodeCreate(**node_data)
            node = network_service.create_node(node_schema)
            created_nodes.append(node)
            logger.info(f"Created test node: {node.name} ({node.id})")
        except Exception as e:
            logger.error(f"Error creating test node {node_data['id']}: {str(e)}")
    
    return created_nodes


def test_network_service(db: Session):
    """Test the NetworkService functionality."""
    logger.info("Testing NetworkService...")
    
    # Create network service
    network_service = NetworkService(db)
    
    # Test get all nodes
    nodes = network_service.get_all_nodes()
    logger.info(f"Retrieved {len(nodes)} network nodes")
    
    # Test filtering
    router_nodes = network_service.get_all_nodes(node_type=NodeType.ROUTER.value)
    logger.info(f"Retrieved {len(router_nodes)} router nodes")
    
    active_nodes = network_service.get_all_nodes(is_active=True)
    logger.info(f"Retrieved {len(active_nodes)} active nodes")
    
    # Test get node by ID
    if nodes:
        node_id = nodes[0].id
        node = network_service.get_node_by_id(node_id)
        logger.info(f"Retrieved node by ID: {node.name} ({node.id})")
    
    # Test get node status summary
    status_summary = network_service.get_node_status_summary()
    logger.info(f"Node status summary: {status_summary}")


def test_metrics_collection(db: Session):
    """Test network metrics collection."""
    logger.info("Testing network metrics collection...")
    
    # Create network service
    network_service = NetworkService(db)
    
    # Collect metrics
    collection_result = network_service.collect_network_metrics()
    logger.info(f"Metrics collection result: {collection_result}")
    
    # Wait for metrics to be indexed in Elasticsearch
    logger.info("Waiting for metrics to be indexed in Elasticsearch...")
    time.sleep(5)
    
    # Query metrics from Elasticsearch
    start_time = datetime.utcnow() - timedelta(minutes=10)
    metrics = network_service.get_network_metrics(
        start_time=start_time,
        limit=10
    )
    logger.info(f"Retrieved {len(metrics)} metrics from Elasticsearch")
    
    # Print sample metrics
    if metrics:
        logger.info(f"Sample metric: {json.dumps(metrics[0], indent=2)}")


def test_celery_task():
    """Test the Celery task for network metrics collection."""
    logger.info("Testing Celery task for network metrics collection...")
    
    # Run the task
    result = collect_network_performance_metrics_task.delay()
    
    # Wait for task to complete
    logger.info("Waiting for task to complete...")
    task_result = result.get(timeout=30)
    
    logger.info(f"Task result: {task_result}")


def test_elasticsearch_client():
    """Test the ElasticsearchClient functionality."""
    logger.info("Testing ElasticsearchClient...")
    
    # Create Elasticsearch client
    es_client = ElasticsearchClient()
    
    # Test connection
    if es_client.es.ping():
        logger.info("Successfully connected to Elasticsearch")
    else:
        logger.error("Failed to connect to Elasticsearch")
        return
    
    # Test index template
    template_name = "isp-network-metrics"
    template_exists = es_client.es.indices.exists_template(name=template_name)
    logger.info(f"Template '{template_name}' exists: {template_exists}")
    
    # Test indices
    indices = es_client.es.indices.get(index="isp-network-metrics-*")
    logger.info(f"Found {len(indices)} network metrics indices")
    
    # Test search
    search_result = es_client.search(
        index="isp-network-metrics-*",
        body={
            "query": {
                "match_all": {}
            },
            "size": 10
        }
    )
    
    hits = search_result.get("hits", {}).get("hits", [])
    logger.info(f"Search returned {len(hits)} hits")


def cleanup_test_nodes(db: Session):
    """Clean up test nodes after testing."""
    logger.info("Cleaning up test nodes...")
    
    # Create network service
    network_service = NetworkService(db)
    
    # Get all test nodes
    test_nodes = db.query(NetworkNode).filter(
        NetworkNode.id.like("%test%")
    ).all()
    
    # Delete test nodes
    for node in test_nodes:
        try:
            network_service.delete_node(node.id)
            logger.info(f"Deleted test node: {node.name} ({node.id})")
        except Exception as e:
            logger.error(f"Error deleting test node {node.id}: {str(e)}")


def main():
    """Main test function."""
    logger.info("Starting network performance monitoring tests...")
    
    # Setup test database
    setup_test_database()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create test nodes
        create_test_nodes(db)
        
        # Test network service
        test_network_service(db)
        
        # Test metrics collection
        test_metrics_collection(db)
        
        # Test Elasticsearch client
        test_elasticsearch_client()
        
        # Test Celery task
        test_celery_task()
        
        logger.info("All tests completed successfully!")
        
        # Ask if test nodes should be cleaned up
        cleanup = input("Do you want to clean up test nodes? (y/n): ")
        if cleanup.lower() == 'y':
            cleanup_test_nodes(db)
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
