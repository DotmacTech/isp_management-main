"""
Unit tests for the network performance monitoring collector.

This module tests the NetworkPerformanceCollector class which is responsible for
collecting network performance metrics such as latency, packet loss, bandwidth
utilization, and service availability.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY

from modules.monitoring.collectors.network_performance_collector import NetworkPerformanceCollector
from modules.monitoring.models.network_node import NetworkNode, NodeType
from modules.monitoring.models import SystemMetric, MetricType


@pytest.fixture
def mock_elasticsearch_client():
    """Provide a mock Elasticsearch client for testing."""
    mock_client = MagicMock()
    mock_client.bulk_index_metrics.return_value = {"errors": False, "items": []}
    return mock_client


@pytest.fixture
def sample_network_nodes(db_session):
    """Create sample network nodes for testing."""
    # Router
    router = NetworkNode(
        id="test-router-1",
        name="Test Router",
        ip_address="192.168.1.1",
        type=NodeType.ROUTER,
        location="Main Office",
        model="RT-AC68U",
        manufacturer="ASUS",
        is_active=True
    )
    
    # Switch
    switch = NetworkNode(
        id="test-switch-1",
        name="Test Switch",
        ip_address="192.168.1.2",
        type=NodeType.SWITCH,
        location="Main Office",
        model="GS108",
        manufacturer="Netgear",
        is_active=True
    )
    
    # Access Point
    ap = NetworkNode(
        id="test-ap-1",
        name="Test Access Point",
        ip_address="192.168.1.3",
        type=NodeType.ACCESS_POINT,
        location="Main Office",
        model="UAP-AC-PRO",
        manufacturer="Ubiquiti",
        is_active=True
    )
    
    # Inactive node
    inactive = NetworkNode(
        id="test-inactive-1",
        name="Inactive Node",
        ip_address="192.168.1.4",
        type=NodeType.ROUTER,
        location="Branch Office",
        model="RT-AC68U",
        manufacturer="ASUS",
        is_active=False
    )
    
    db_session.add_all([router, switch, ap, inactive])
    db_session.commit()
    
    return {
        "router": router,
        "switch": switch,
        "ap": ap,
        "inactive": inactive
    }


class TestNetworkPerformanceCollector:
    """Tests for the NetworkPerformanceCollector class."""
    
    def test_init(self, db_session):
        """Test initializing the collector."""
        collector = NetworkPerformanceCollector(db_session)
        
        assert collector.db_session == db_session
        assert collector.metrics == []
        assert isinstance(collector.config, dict)
        assert "ping_count" in collector.config
        assert "ping_timeout" in collector.config
        assert "collection_interval" in collector.config
    
    def test_collect_latency(self, db_session):
        """Test collecting latency metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Test with a valid IP
        metric = collector.collect_latency("192.168.1.1", "test-router-1")
        
        assert metric["metric_type"] == "NETWORK_LATENCY"
        assert "timestamp" in metric
        assert metric["node_id"] == "test-router-1"
        assert metric["target_ip"] == "192.168.1.1"
        assert isinstance(metric["value"], float)
        assert metric["unit"] == "ms"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "ping"
    
    def test_collect_packet_loss(self, db_session):
        """Test collecting packet loss metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Test with a valid IP
        metric = collector.collect_packet_loss("192.168.1.1", "test-router-1")
        
        assert metric["metric_type"] == "NETWORK_PACKET_LOSS"
        assert "timestamp" in metric
        assert metric["node_id"] == "test-router-1"
        assert metric["target_ip"] == "192.168.1.1"
        assert isinstance(metric["value"], float)
        assert metric["unit"] == "%"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "ping"
    
    def test_collect_bandwidth_utilization(self, db_session):
        """Test collecting bandwidth utilization metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Test with a valid node ID
        metric = collector.collect_bandwidth_utilization("test-router-1", "eth0")
        
        assert metric["metric_type"] == "NETWORK_BANDWIDTH_UTILIZATION"
        assert "timestamp" in metric
        assert metric["node_id"] == "test-router-1"
        assert metric["interface"] == "eth0"
        assert isinstance(metric["value"], float)
        assert metric["unit"] == "%"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "snmp"
    
    def test_collect_connection_count(self, db_session):
        """Test collecting connection count metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Test with a valid node ID
        metric = collector.collect_connection_count("test-router-1")
        
        assert metric["metric_type"] == "NETWORK_CONNECTION_COUNT"
        assert "timestamp" in metric
        assert metric["node_id"] == "test-router-1"
        assert isinstance(metric["value"], int)
        assert metric["unit"] == "connections"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "netstat"
    
    def test_collect_service_availability(self, db_session):
        """Test collecting service availability metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Test with HTTP endpoint
        metric = collector.collect_service_availability("test-service", "http://example.com")
        
        assert metric["metric_type"] == "SERVICE_UPTIME"
        assert "timestamp" in metric
        assert metric["service_name"] == "test-service"
        assert metric["endpoint"] == "http://example.com"
        assert isinstance(metric["value"], float)
        assert metric["status"] in ["UP", "DOWN"]
        assert isinstance(metric["response_time"], float) or metric["response_time"] == -1
        assert metric["unit"] == "%"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "http_check"
        
        # Test with socket endpoint
        metric = collector.collect_service_availability("test-service", "192.168.1.1:22")
        
        assert metric["metric_type"] == "SERVICE_UPTIME"
        assert metric["endpoint"] == "192.168.1.1:22"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "socket_check"
    
    def test_collect_customer_data_usage(self, db_session):
        """Test collecting customer data usage metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Test with a valid customer ID
        metric = collector.collect_customer_data_usage("test-customer-1")
        
        assert metric["metric_type"] == "CUSTOMER_DATA_USAGE"
        assert "timestamp" in metric
        assert metric["customer_id"] == "test-customer-1"
        assert isinstance(metric["value"], float)
        assert metric["unit"] == "bytes"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "radius_logs"
        assert "quota" in metric["metadata"]
        assert "quota_percentage" in metric["metadata"]
    
    def test_collect_customer_session_count(self, db_session):
        """Test collecting customer session count metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Test with a valid customer ID
        metric = collector.collect_customer_session_count("test-customer-1")
        
        assert metric["metric_type"] == "CUSTOMER_SESSION_COUNT"
        assert "timestamp" in metric
        assert metric["customer_id"] == "test-customer-1"
        assert isinstance(metric["value"], int)
        assert metric["unit"] == "sessions"
        assert "metadata" in metric
        assert metric["metadata"]["collection_method"] == "radius_logs"
    
    def test_collect_all_metrics(self, db_session, sample_network_nodes):
        """Test collecting all metrics."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Clear metrics list
        collector.metrics = []
        
        # Collect all metrics
        collector.collect_all_metrics()
        
        # Check that metrics were collected
        assert len(collector.metrics) > 0
        
        # Check that metrics were collected for each node
        node_ids = [node.id for node in sample_network_nodes.values()]
        metric_node_ids = [m.get("node_id") for m in collector.metrics if "node_id" in m]
        
        # Check that at least some metrics were collected for active nodes
        assert sample_network_nodes["router"].id in metric_node_ids
        assert sample_network_nodes["switch"].id in metric_node_ids
        assert sample_network_nodes["ap"].id in metric_node_ids
        
        # Check that metrics include different types
        metric_types = [m["metric_type"] for m in collector.metrics]
        assert "NETWORK_LATENCY" in metric_types
        assert "NETWORK_PACKET_LOSS" in metric_types
        assert "NETWORK_BANDWIDTH_UTILIZATION" in metric_types
        assert "NETWORK_CONNECTION_COUNT" in metric_types
        assert "SERVICE_UPTIME" in metric_types
        assert "CUSTOMER_DATA_USAGE" in metric_types
        assert "CUSTOMER_SESSION_COUNT" in metric_types
    
    def test_save_to_database(self, db_session):
        """Test saving metrics to the database."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Create some test metrics
        collector.metrics = [
            {
                "metric_type": "NETWORK_LATENCY",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": "test-router-1",
                "target_ip": "192.168.1.1",
                "value": 10.5,
                "unit": "ms",
                "metadata": {"collection_method": "ping"}
            },
            {
                "metric_type": "SERVICE_UPTIME",
                "timestamp": datetime.utcnow().isoformat(),
                "service_name": "test-service",
                "endpoint": "http://example.com",
                "value": 100.0,
                "status": "UP",
                "response_time": 50.0,
                "unit": "%",
                "metadata": {"collection_method": "http_check"}
            }
        ]
        
        # Save metrics to database
        collector.save_to_database()
        
        # Check that metrics were saved
        metrics = db_session.query(SystemMetric).all()
        assert len(metrics) == 2
        
        # Check first metric
        latency_metric = db_session.query(SystemMetric).filter_by(metric_type="NETWORK_LATENCY").first()
        assert latency_metric is not None
        assert latency_metric.value == 10.5
        assert latency_metric.unit == "ms"
        
        # Check second metric
        uptime_metric = db_session.query(SystemMetric).filter_by(metric_type="SERVICE_UPTIME").first()
        assert uptime_metric is not None
        assert uptime_metric.value == 100.0
        assert uptime_metric.unit == "%"
        assert uptime_metric.service_name == "test-service"
        assert uptime_metric.endpoint == "http://example.com"
        assert uptime_metric.status == "UP"
    
    def test_send_to_elasticsearch(self, db_session, mock_elasticsearch_client):
        """Test sending metrics to Elasticsearch."""
        collector = NetworkPerformanceCollector(db_session)
        collector.es_client = mock_elasticsearch_client
        
        # Create some test metrics
        collector.metrics = [
            {
                "metric_type": "NETWORK_LATENCY",
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": "test-router-1",
                "target_ip": "192.168.1.1",
                "value": 10.5,
                "unit": "ms",
                "metadata": {"collection_method": "ping"}
            },
            {
                "metric_type": "SERVICE_UPTIME",
                "timestamp": datetime.utcnow().isoformat(),
                "service_name": "test-service",
                "endpoint": "http://example.com",
                "value": 100.0,
                "status": "UP",
                "response_time": 50.0,
                "unit": "%",
                "metadata": {"collection_method": "http_check"}
            }
        ]
        
        # Send metrics to Elasticsearch
        collector.send_to_elasticsearch()
        
        # Check that bulk_index_metrics was called with the correct arguments
        mock_elasticsearch_client.bulk_index_metrics.assert_called_once_with(collector.metrics)
    
    @patch('time.sleep', return_value=None)  # Mock sleep to avoid waiting
    @patch('modules.monitoring.collectors.network_performance_collector.NetworkPerformanceCollector.collect_all_metrics')
    @patch('modules.monitoring.collectors.network_performance_collector.NetworkPerformanceCollector.save_to_database')
    @patch('modules.monitoring.collectors.network_performance_collector.NetworkPerformanceCollector.send_to_elasticsearch')
    def test_run(self, mock_send, mock_save, mock_collect, mock_sleep, db_session):
        """Test running the collector."""
        collector = NetworkPerformanceCollector(db_session)
        
        # Set up mock to raise KeyboardInterrupt after first iteration
        mock_sleep.side_effect = [None, KeyboardInterrupt]
        
        # Run the collector
        collector.run()
        
        # Check that methods were called
        assert mock_collect.call_count >= 1
        assert mock_save.call_count >= 1
        assert mock_send.call_count >= 1


@patch('modules.monitoring.collectors.network_performance_collector.get_db')
def test_main(mock_get_db, db_session):
    """Test the main function."""
    # Mock get_db to return our test session
    mock_get_db.return_value = iter([db_session])
    
    # Mock NetworkPerformanceCollector.run to avoid running the collector
    with patch('modules.monitoring.collectors.network_performance_collector.NetworkPerformanceCollector.run'):
        from modules.monitoring.collectors.network_performance_collector import main
        
        # Call main function
        main()
        
        # Check that get_db was called
        mock_get_db.assert_called_once()
