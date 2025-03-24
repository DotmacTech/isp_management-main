"""
Unit tests for the customer usage statistics monitoring.

This module tests the functionality related to tracking and analyzing
customer usage statistics in the ISP Management Platform.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, ANY

from modules.monitoring.collectors.network_performance_collector import NetworkPerformanceCollector
from modules.monitoring.models import SystemMetric


@pytest.fixture
def mock_elasticsearch_client():
    """Provide a mock Elasticsearch client for testing."""
    mock_client = MagicMock()
    mock_client.bulk_index_metrics.return_value = {"errors": False, "items": []}
    return mock_client


@pytest.fixture
def sample_customer_data(db_session):
    """Create sample customer usage data for testing."""
    # Create sample metrics for customer data usage
    metrics = []
    
    # Customer 1 - Multiple data points over time
    customer_id = "customer-test-1"
    for i in range(24):  # 24 hours of data
        timestamp = datetime.utcnow() - timedelta(hours=i)
        # Create data usage metric (varying between 100MB and 500MB per hour)
        data_usage = SystemMetric(
            service_name="radius",
            host_name="radius-server",
            metric_type="CUSTOMER_DATA_USAGE",
            value=float((i % 5 + 1) * 100 * 1024 * 1024),  # 100-500 MB in bytes
            unit="bytes",
            timestamp=timestamp,
            customer_id=customer_id,
            metadata=json.dumps({
                "collection_method": "radius_logs",
                "traffic_type": "web" if i % 4 == 0 else "streaming" if i % 4 == 1 else "download" if i % 4 == 2 else "other",
                "quota": 10 * 1024 * 1024 * 1024,  # 10 GB
                "plan_type": "premium"
            })
        )
        metrics.append(data_usage)
        
        # Create session count metric (varying between 1 and 3 sessions)
        session_count = SystemMetric(
            service_name="radius",
            host_name="radius-server",
            metric_type="CUSTOMER_SESSION_COUNT",
            value=float((i % 3) + 1),  # 1-3 sessions
            unit="sessions",
            timestamp=timestamp,
            customer_id=customer_id,
            metadata=json.dumps({
                "collection_method": "radius_logs",
                "plan_type": "premium"
            })
        )
        metrics.append(session_count)
    
    # Customer 2 - Different plan type
    customer_id = "customer-test-2"
    for i in range(24):  # 24 hours of data
        timestamp = datetime.utcnow() - timedelta(hours=i)
        # Create data usage metric (varying between 50MB and 200MB per hour)
        data_usage = SystemMetric(
            service_name="radius",
            host_name="radius-server",
            metric_type="CUSTOMER_DATA_USAGE",
            value=float((i % 4 + 1) * 50 * 1024 * 1024),  # 50-200 MB in bytes
            unit="bytes",
            timestamp=timestamp,
            customer_id=customer_id,
            metadata=json.dumps({
                "collection_method": "radius_logs",
                "traffic_type": "web" if i % 4 == 0 else "streaming" if i % 4 == 1 else "download" if i % 4 == 2 else "other",
                "quota": 5 * 1024 * 1024 * 1024,  # 5 GB
                "plan_type": "basic"
            })
        )
        metrics.append(data_usage)
        
        # Create session count metric (varying between 1 and 2 sessions)
        session_count = SystemMetric(
            service_name="radius",
            host_name="radius-server",
            metric_type="CUSTOMER_SESSION_COUNT",
            value=float((i % 2) + 1),  # 1-2 sessions
            unit="sessions",
            timestamp=timestamp,
            customer_id=customer_id,
            metadata=json.dumps({
                "collection_method": "radius_logs",
                "plan_type": "basic"
            })
        )
        metrics.append(session_count)
    
    # Add all metrics to the database
    db_session.add_all(metrics)
    db_session.commit()
    
    return {
        "customer_ids": ["customer-test-1", "customer-test-2"],
        "metrics_count": len(metrics)
    }


class TestCustomerUsageStatistics:
    """Tests for customer usage statistics monitoring."""
    
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
        assert "plan_type" in metric["metadata"]
    
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
        assert "plan_type" in metric["metadata"]
    
    def test_customer_data_usage_storage(self, db_session, sample_customer_data):
        """Test that customer data usage metrics are properly stored in the database."""
        # Query for customer 1's data usage metrics
        customer_id = "customer-test-1"
        metrics = db_session.query(SystemMetric).filter_by(
            customer_id=customer_id,
            metric_type="CUSTOMER_DATA_USAGE"
        ).order_by(SystemMetric.timestamp.desc()).all()
        
        assert len(metrics) == 24  # 24 hours of data
        
        # Check the most recent metric
        latest_metric = metrics[0]
        assert latest_metric.customer_id == customer_id
        assert latest_metric.unit == "bytes"
        assert latest_metric.value > 0
        
        # Check metadata
        metadata = json.loads(latest_metric.metadata)
        assert "collection_method" in metadata
        assert "traffic_type" in metadata
        assert "quota" in metadata
        assert "plan_type" in metadata
        assert metadata["plan_type"] == "premium"
    
    def test_customer_session_count_storage(self, db_session, sample_customer_data):
        """Test that customer session count metrics are properly stored in the database."""
        # Query for customer 2's session count metrics
        customer_id = "customer-test-2"
        metrics = db_session.query(SystemMetric).filter_by(
            customer_id=customer_id,
            metric_type="CUSTOMER_SESSION_COUNT"
        ).order_by(SystemMetric.timestamp.desc()).all()
        
        assert len(metrics) == 24  # 24 hours of data
        
        # Check the most recent metric
        latest_metric = metrics[0]
        assert latest_metric.customer_id == customer_id
        assert latest_metric.unit == "sessions"
        assert 1 <= latest_metric.value <= 2  # Between 1 and 2 sessions
        
        # Check metadata
        metadata = json.loads(latest_metric.metadata)
        assert "collection_method" in metadata
        assert "plan_type" in metadata
        assert metadata["plan_type"] == "basic"
    
    def test_customer_data_usage_aggregation(self, db_session, sample_customer_data):
        """Test aggregating customer data usage over time periods."""
        # Query for customer 1's total data usage in the last 24 hours
        customer_id = "customer-test-1"
        start_time = datetime.utcnow() - timedelta(hours=24)
        
        # Calculate total data usage
        total_usage = db_session.query(SystemMetric).filter(
            SystemMetric.customer_id == customer_id,
            SystemMetric.metric_type == "CUSTOMER_DATA_USAGE",
            SystemMetric.timestamp >= start_time
        ).all()
        
        # Sum up the values
        total_bytes = sum(metric.value for metric in total_usage)
        
        # Convert to GB for easier verification
        total_gb = total_bytes / (1024 * 1024 * 1024)
        
        # We should have some reasonable amount of data usage
        assert total_gb > 0
        assert len(total_usage) == 24  # 24 hours of data
    
    def test_customer_usage_by_traffic_type(self, db_session, sample_customer_data):
        """Test analyzing customer usage by traffic type."""
        # Query for customer 1's usage by traffic type
        customer_id = "customer-test-1"
        
        # Get all metrics
        metrics = db_session.query(SystemMetric).filter(
            SystemMetric.customer_id == customer_id,
            SystemMetric.metric_type == "CUSTOMER_DATA_USAGE"
        ).all()
        
        # Group by traffic type
        usage_by_type = {}
        for metric in metrics:
            metadata = json.loads(metric.metadata)
            traffic_type = metadata.get("traffic_type", "unknown")
            
            if traffic_type not in usage_by_type:
                usage_by_type[traffic_type] = 0
            
            usage_by_type[traffic_type] += metric.value
        
        # Check that we have data for different traffic types
        assert len(usage_by_type) > 0
        assert "web" in usage_by_type
        assert "streaming" in usage_by_type
        assert "download" in usage_by_type
    
    def test_customer_usage_threshold_detection(self, db_session, sample_customer_data):
        """Test detecting when a customer exceeds usage thresholds."""
        # Query for customer 1's total data usage
        customer_id = "customer-test-1"
        
        # Calculate total data usage
        total_usage = db_session.query(SystemMetric).filter(
            SystemMetric.customer_id == customer_id,
            SystemMetric.metric_type == "CUSTOMER_DATA_USAGE"
        ).all()
        
        # Sum up the values
        total_bytes = sum(metric.value for metric in total_usage)
        
        # Get the quota from the metadata of the first metric
        first_metric = total_usage[0]
        metadata = json.loads(first_metric.metadata)
        quota_bytes = metadata.get("quota", 0)
        
        # Calculate percentage of quota used
        quota_percentage = (total_bytes / quota_bytes) * 100 if quota_bytes > 0 else 0
        
        # Check if threshold is exceeded (for example, 80% of quota)
        threshold_exceeded = quota_percentage > 80
        
        # We're just testing the logic here, not asserting a specific result
        assert isinstance(threshold_exceeded, bool)
        assert quota_percentage >= 0
    
    def test_customer_concurrent_sessions(self, db_session, sample_customer_data):
        """Test tracking concurrent customer sessions."""
        # Query for customer 1's maximum concurrent sessions
        customer_id = "customer-test-1"
        
        # Get all session count metrics
        metrics = db_session.query(SystemMetric).filter(
            SystemMetric.customer_id == customer_id,
            SystemMetric.metric_type == "CUSTOMER_SESSION_COUNT"
        ).all()
        
        # Find the maximum session count
        max_sessions = max(metric.value for metric in metrics) if metrics else 0
        
        # Check that we have a reasonable maximum
        assert 1 <= max_sessions <= 3  # Between 1 and 3 sessions


class TestCustomerUsageElasticsearchIntegration:
    """Tests for customer usage statistics Elasticsearch integration."""
    
    def test_send_customer_metrics_to_elasticsearch(self, db_session, mock_elasticsearch_client):
        """Test sending customer usage metrics to Elasticsearch."""
        collector = NetworkPerformanceCollector(db_session)
        collector.es_client = mock_elasticsearch_client
        
        # Create some test metrics
        collector.metrics = [
            {
                "metric_type": "CUSTOMER_DATA_USAGE",
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": "test-customer-1",
                "value": 1024 * 1024 * 100,  # 100 MB
                "unit": "bytes",
                "metadata": {
                    "collection_method": "radius_logs",
                    "traffic_type": "web",
                    "quota": 1024 * 1024 * 1024,  # 1 GB
                    "quota_percentage": 10.0,
                    "plan_type": "premium"
                }
            },
            {
                "metric_type": "CUSTOMER_SESSION_COUNT",
                "timestamp": datetime.utcnow().isoformat(),
                "customer_id": "test-customer-1",
                "value": 2,
                "unit": "sessions",
                "metadata": {
                    "collection_method": "radius_logs",
                    "plan_type": "premium"
                }
            }
        ]
        
        # Send metrics to Elasticsearch
        collector.send_to_elasticsearch()
        
        # Check that bulk_index_metrics was called with the correct arguments
        mock_elasticsearch_client.bulk_index_metrics.assert_called_once_with(collector.metrics)
