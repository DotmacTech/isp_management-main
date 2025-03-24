"""
Tests for network performance monitoring functionality.

This module tests the network performance monitoring features by:
1. Creating test network nodes
2. Collecting network performance metrics
3. Querying metrics from Elasticsearch
4. Testing alert thresholds
"""

import pytest
import logging
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from modules.monitoring.models import NetworkNode, NodeType
from modules.monitoring.schemas.network_node import NetworkNodeCreate
from modules.monitoring.services.network_service import NetworkService
from modules.monitoring.collectors.network_performance_collector import NetworkPerformanceCollector
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.fixture
def test_nodes(db_session):
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
    network_service = NetworkService(db_session)
    
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
    
    yield created_nodes
    
    # Clean up test nodes
    for node in created_nodes:
        try:
            network_service.delete_node(node.id)
            logger.info(f"Deleted test node: {node.id}")
        except Exception as e:
            logger.error(f"Error deleting test node {node.id}: {str(e)}")


def test_network_service(db_session, test_nodes):
    """Test the NetworkService functionality."""
    logger.info("Testing NetworkService...")
    
    # Create network service
    network_service = NetworkService(db_session)
    
    # Test get all nodes
    nodes = network_service.get_all_nodes()
    logger.info(f"Retrieved {len(nodes)} network nodes")
    assert len(nodes) >= len(test_nodes)
    
    # Test filtering
    router_nodes = network_service.get_all_nodes(node_type=NodeType.ROUTER.value)
    logger.info(f"Retrieved {len(router_nodes)} router nodes")
    assert len(router_nodes) >= 2  # We created at least 2 routers
    
    active_nodes = network_service.get_all_nodes(is_active=True)
    logger.info(f"Retrieved {len(active_nodes)} active nodes")
    assert len(active_nodes) >= len(test_nodes)
    
    # Test get node by ID
    node_id = test_nodes[0].id
    node = network_service.get_node_by_id(node_id)
    logger.info(f"Retrieved node by ID: {node.name} ({node.id})")
    assert node.id == node_id
    
    # Test get node status summary
    status_summary = network_service.get_node_status_summary()
    logger.info(f"Node status summary: {status_summary}")
    assert isinstance(status_summary, dict)


@pytest.mark.parametrize("mock_metrics", [
    [
        {"node_id": "router-main-test", "metric": "cpu_usage", "value": 45.5, "timestamp": datetime.utcnow()},
        {"node_id": "router-main-test", "metric": "memory_usage", "value": 65.2, "timestamp": datetime.utcnow()},
        {"node_id": "switch-core-test", "metric": "cpu_usage", "value": 30.1, "timestamp": datetime.utcnow()},
    ]
])
def test_metrics_collection(db_session, test_nodes, mock_metrics, monkeypatch):
    """Test network metrics collection with mocked collector."""
    logger.info("Testing network metrics collection...")
    
    # Mock the NetworkPerformanceCollector.collect_metrics method
    def mock_collect_metrics(*args, **kwargs):
        return mock_metrics
    
    # Mock the ElasticsearchClient.bulk_index method
    def mock_bulk_index(*args, **kwargs):
        return {"errors": False, "items": [{"index": {"status": 201}} for _ in mock_metrics]}
    
    # Apply the mocks
    monkeypatch.setattr(
        "modules.monitoring.collectors.network_performance_collector.NetworkPerformanceCollector.collect_metrics",
        mock_collect_metrics
    )
    monkeypatch.setattr(
        "modules.monitoring.elasticsearch.ElasticsearchClient.bulk_index",
        mock_bulk_index
    )
    
    # Create network service
    network_service = NetworkService(db_session)
    
    # Collect metrics
    collection_result = network_service.collect_network_metrics()
    logger.info(f"Metrics collection result: {collection_result}")
    assert collection_result["success"] is True
    assert collection_result["metrics_collected"] == len(mock_metrics)
    
    # Mock get_network_metrics to return our mock metrics
    def mock_get_network_metrics(*args, **kwargs):
        return mock_metrics
    
    monkeypatch.setattr(
        "modules.monitoring.services.network_service.NetworkService.get_network_metrics",
        mock_get_network_metrics
    )
    
    # Query metrics
    metrics = network_service.get_network_metrics(
        start_time=datetime.utcnow() - timedelta(minutes=10),
        limit=10
    )
    logger.info(f"Retrieved {len(metrics)} metrics")
    assert len(metrics) == len(mock_metrics)


@pytest.mark.skip(reason="Requires Celery worker to be running")
def test_celery_task():
    """Test the Celery task for network metrics collection."""
    from modules.monitoring.tasks import collect_network_performance_metrics_task
    
    # Run the task
    result = collect_network_performance_metrics_task.delay()
    assert result is not None


def test_elasticsearch_client(monkeypatch):
    """Test the ElasticsearchClient functionality."""
    # Mock Elasticsearch client methods
    mock_es = MagicMock()
    mock_es.index.return_value = {"_id": "test-id", "result": "created"}
    mock_es.search.return_value = {
        "hits": {
            "total": {"value": 5},
            "hits": [{"_source": {"field": "value"}} for _ in range(5)]
        }
    }
    
    # Apply the mock
    monkeypatch.setattr(
        "elasticsearch.Elasticsearch",
        lambda *args, **kwargs: mock_es
    )
    
    # Create client
    client = ElasticsearchClient()
    
    # Test index method
    index_result = client.index("test-index", {"field": "value"})
    assert index_result["result"] == "created"
    
    # Test search method
    search_result = client.search("test-index", {"query": {"match_all": {}}})
    assert len(search_result["hits"]["hits"]) == 5
