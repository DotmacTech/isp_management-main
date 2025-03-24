"""
Unit tests for the monitoring module's dashboard integration.

This module tests the functionality related to integrating monitoring data
with dashboards for visualization in the ISP Management Platform.
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

from modules.monitoring.models import (
    DashboardConfiguration, DashboardWidget, SystemMetric
)
from modules.monitoring.services.dashboard_service import DashboardService


@pytest.fixture
def mock_elasticsearch_client():
    """Provide a mock Elasticsearch client for testing."""
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "hits": {
            "total": {"value": 10},
            "hits": [{"_source": {"value": i, "timestamp": datetime.utcnow().isoformat()}} for i in range(10)]
        },
        "aggregations": {
            "avg_value": {"value": 45.5},
            "max_value": {"value": 95.0},
            "min_value": {"value": 10.0}
        }
    }
    return mock_client


@pytest.fixture
def sample_dashboard_configurations(db_session):
    """Create sample dashboard configurations for testing."""
    # Network performance dashboard
    network_dashboard = DashboardConfiguration(
        id=1,
        name="Network Performance",
        description="Dashboard for monitoring network performance metrics",
        layout=json.dumps({
            "rows": 2,
            "columns": 2,
            "widgets": [
                {"id": 1, "position": {"row": 0, "col": 0, "width": 1, "height": 1}},
                {"id": 2, "position": {"row": 0, "col": 1, "width": 1, "height": 1}},
                {"id": 3, "position": {"row": 1, "col": 0, "width": 2, "height": 1}}
            ]
        }),
        is_public=True,
        created_by=1
    )
    
    # System health dashboard
    system_dashboard = DashboardConfiguration(
        id=2,
        name="System Health",
        description="Dashboard for monitoring system health metrics",
        layout=json.dumps({
            "rows": 2,
            "columns": 2,
            "widgets": [
                {"id": 4, "position": {"row": 0, "col": 0, "width": 2, "height": 1}},
                {"id": 5, "position": {"row": 1, "col": 0, "width": 1, "height": 1}},
                {"id": 6, "position": {"row": 1, "col": 1, "width": 1, "height": 1}}
            ]
        }),
        is_public=True,
        created_by=1
    )
    
    # Customer usage dashboard
    customer_dashboard = DashboardConfiguration(
        id=3,
        name="Customer Usage",
        description="Dashboard for monitoring customer usage metrics",
        layout=json.dumps({
            "rows": 2,
            "columns": 2,
            "widgets": [
                {"id": 7, "position": {"row": 0, "col": 0, "width": 2, "height": 1}},
                {"id": 8, "position": {"row": 1, "col": 0, "width": 1, "height": 1}},
                {"id": 9, "position": {"row": 1, "col": 1, "width": 1, "height": 1}}
            ]
        }),
        is_public=False,
        created_by=2
    )
    
    db_session.add_all([network_dashboard, system_dashboard, customer_dashboard])
    db_session.commit()
    
    return {
        "network": network_dashboard,
        "system": system_dashboard,
        "customer": customer_dashboard
    }


@pytest.fixture
def sample_dashboard_widgets(db_session, sample_dashboard_configurations):
    """Create sample dashboard widgets for testing."""
    # Network dashboard widgets
    latency_chart = DashboardWidget(
        id=1,
        dashboard_id=sample_dashboard_configurations["network"].id,
        widget_type="line_chart",
        title="Network Latency",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "NETWORK_LATENCY",
            "time_range": "24h",
            "group_by": ["node_id"]
        }),
        refresh_interval_seconds=60,
        position_x=0,
        position_y=0,
        width=1,
        height=1
    )
    
    packet_loss_chart = DashboardWidget(
        id=2,
        dashboard_id=sample_dashboard_configurations["network"].id,
        widget_type="line_chart",
        title="Packet Loss",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "NETWORK_PACKET_LOSS",
            "time_range": "24h",
            "group_by": ["node_id"]
        }),
        refresh_interval_seconds=60,
        position_x=1,
        position_y=0,
        width=1,
        height=1
    )
    
    bandwidth_chart = DashboardWidget(
        id=3,
        dashboard_id=sample_dashboard_configurations["network"].id,
        widget_type="area_chart",
        title="Bandwidth Utilization",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "NETWORK_BANDWIDTH_UTILIZATION",
            "time_range": "24h",
            "group_by": ["node_id", "interface"]
        }),
        refresh_interval_seconds=60,
        position_x=0,
        position_y=1,
        width=2,
        height=1
    )
    
    # System dashboard widgets
    cpu_gauge = DashboardWidget(
        id=4,
        dashboard_id=sample_dashboard_configurations["system"].id,
        widget_type="gauge",
        title="CPU Usage",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "CPU_USAGE",
            "time_range": "5m",
            "aggregation": "avg"
        }),
        refresh_interval_seconds=30,
        position_x=0,
        position_y=0,
        width=2,
        height=1
    )
    
    memory_gauge = DashboardWidget(
        id=5,
        dashboard_id=sample_dashboard_configurations["system"].id,
        widget_type="gauge",
        title="Memory Usage",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "MEMORY_USAGE",
            "time_range": "5m",
            "aggregation": "avg"
        }),
        refresh_interval_seconds=30,
        position_x=0,
        position_y=1,
        width=1,
        height=1
    )
    
    disk_gauge = DashboardWidget(
        id=6,
        dashboard_id=sample_dashboard_configurations["system"].id,
        widget_type="gauge",
        title="Disk Usage",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "DISK_USAGE",
            "time_range": "5m",
            "aggregation": "avg"
        }),
        refresh_interval_seconds=30,
        position_x=1,
        position_y=1,
        width=1,
        height=1
    )
    
    # Customer dashboard widgets
    data_usage_chart = DashboardWidget(
        id=7,
        dashboard_id=sample_dashboard_configurations["customer"].id,
        widget_type="bar_chart",
        title="Customer Data Usage",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "CUSTOMER_DATA_USAGE",
            "time_range": "7d",
            "group_by": ["customer_id"],
            "limit": 10,
            "order_by": "value",
            "order": "desc"
        }),
        refresh_interval_seconds=300,
        position_x=0,
        position_y=0,
        width=2,
        height=1
    )
    
    session_count_chart = DashboardWidget(
        id=8,
        dashboard_id=sample_dashboard_configurations["customer"].id,
        widget_type="line_chart",
        title="Customer Sessions",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "CUSTOMER_SESSION_COUNT",
            "time_range": "24h",
            "group_by": ["customer_id"],
            "limit": 10
        }),
        refresh_interval_seconds=300,
        position_x=0,
        position_y=1,
        width=1,
        height=1
    )
    
    traffic_type_pie = DashboardWidget(
        id=9,
        dashboard_id=sample_dashboard_configurations["customer"].id,
        widget_type="pie_chart",
        title="Traffic by Type",
        data_source="metrics",
        query=json.dumps({
            "metric_type": "CUSTOMER_DATA_USAGE",
            "time_range": "24h",
            "group_by": ["metadata.traffic_type"],
            "aggregation": "sum"
        }),
        refresh_interval_seconds=300,
        position_x=1,
        position_y=1,
        width=1,
        height=1
    )
    
    db_session.add_all([
        latency_chart, packet_loss_chart, bandwidth_chart,
        cpu_gauge, memory_gauge, disk_gauge,
        data_usage_chart, session_count_chart, traffic_type_pie
    ])
    db_session.commit()
    
    return {
        "latency_chart": latency_chart,
        "packet_loss_chart": packet_loss_chart,
        "bandwidth_chart": bandwidth_chart,
        "cpu_gauge": cpu_gauge,
        "memory_gauge": memory_gauge,
        "disk_gauge": disk_gauge,
        "data_usage_chart": data_usage_chart,
        "session_count_chart": session_count_chart,
        "traffic_type_pie": traffic_type_pie
    }


class TestDashboardService:
    """Tests for the DashboardService class."""
    
    def test_init(self, db_session, mock_elasticsearch_client):
        """Test initializing the dashboard service."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        assert service.db_session == db_session
        assert service.es_client == mock_elasticsearch_client
    
    def test_get_dashboard(self, db_session, sample_dashboard_configurations, mock_elasticsearch_client):
        """Test getting a dashboard configuration."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get network dashboard
        dashboard_id = sample_dashboard_configurations["network"].id
        dashboard = service.get_dashboard(dashboard_id)
        
        assert dashboard is not None
        assert dashboard.id == dashboard_id
        assert dashboard.name == "Network Performance"
        
        # Try to get non-existent dashboard
        non_existent = service.get_dashboard(999)
        assert non_existent is None
    
    def test_get_dashboard_with_widgets(self, db_session, sample_dashboard_configurations, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test getting a dashboard with its widgets."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get network dashboard with widgets
        dashboard_id = sample_dashboard_configurations["network"].id
        dashboard, widgets = service.get_dashboard_with_widgets(dashboard_id)
        
        assert dashboard is not None
        assert dashboard.id == dashboard_id
        assert len(widgets) == 3
        
        # Check widget types
        widget_types = [w.widget_type for w in widgets]
        assert "line_chart" in widget_types
        assert "area_chart" in widget_types
    
    def test_get_public_dashboards(self, db_session, sample_dashboard_configurations, mock_elasticsearch_client):
        """Test getting public dashboards."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get public dashboards
        public_dashboards = service.get_public_dashboards()
        
        assert len(public_dashboards) == 2
        dashboard_names = [d.name for d in public_dashboards]
        assert "Network Performance" in dashboard_names
        assert "System Health" in dashboard_names
        assert "Customer Usage" not in dashboard_names
    
    def test_get_user_dashboards(self, db_session, sample_dashboard_configurations, mock_elasticsearch_client):
        """Test getting user dashboards."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get dashboards for user 1
        user_id = 1
        user_dashboards = service.get_user_dashboards(user_id)
        
        assert len(user_dashboards) == 2
        dashboard_names = [d.name for d in user_dashboards]
        assert "Network Performance" in dashboard_names
        assert "System Health" in dashboard_names
        
        # Get dashboards for user 2
        user_id = 2
        user_dashboards = service.get_user_dashboards(user_id)
        
        assert len(user_dashboards) == 1
        assert user_dashboards[0].name == "Customer Usage"
    
    def test_create_dashboard(self, db_session, mock_elasticsearch_client):
        """Test creating a dashboard."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Create a new dashboard
        dashboard_data = {
            "name": "Test Dashboard",
            "description": "Test dashboard for unit tests",
            "layout": {
                "rows": 1,
                "columns": 2,
                "widgets": []
            },
            "is_public": True,
            "created_by": 1
        }
        
        dashboard = service.create_dashboard(dashboard_data)
        
        assert dashboard is not None
        assert dashboard.name == "Test Dashboard"
        assert dashboard.description == "Test dashboard for unit tests"
        assert dashboard.is_public is True
        assert dashboard.created_by == 1
        assert isinstance(dashboard.layout, str)
        layout = json.loads(dashboard.layout)
        assert layout["rows"] == 1
        assert layout["columns"] == 2
    
    def test_update_dashboard(self, db_session, sample_dashboard_configurations, mock_elasticsearch_client):
        """Test updating a dashboard."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get network dashboard
        dashboard_id = sample_dashboard_configurations["network"].id
        
        # Update dashboard
        update_data = {
            "name": "Updated Network Dashboard",
            "description": "Updated description",
            "is_public": False
        }
        
        updated = service.update_dashboard(dashboard_id, update_data)
        
        assert updated is True
        
        # Get updated dashboard
        dashboard = service.get_dashboard(dashboard_id)
        
        assert dashboard.name == "Updated Network Dashboard"
        assert dashboard.description == "Updated description"
        assert dashboard.is_public is False
    
    def test_delete_dashboard(self, db_session, sample_dashboard_configurations, mock_elasticsearch_client):
        """Test deleting a dashboard."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get customer dashboard
        dashboard_id = sample_dashboard_configurations["customer"].id
        
        # Delete dashboard
        deleted = service.delete_dashboard(dashboard_id)
        
        assert deleted is True
        
        # Try to get deleted dashboard
        dashboard = service.get_dashboard(dashboard_id)
        
        assert dashboard is None
    
    def test_add_widget(self, db_session, sample_dashboard_configurations, mock_elasticsearch_client):
        """Test adding a widget to a dashboard."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get network dashboard
        dashboard_id = sample_dashboard_configurations["network"].id
        
        # Add widget
        widget_data = {
            "widget_type": "table",
            "title": "Connection Count",
            "data_source": "metrics",
            "query": {
                "metric_type": "NETWORK_CONNECTION_COUNT",
                "time_range": "1h",
                "group_by": ["node_id"],
                "limit": 10
            },
            "refresh_interval_seconds": 60,
            "position_x": 0,
            "position_y": 2,
            "width": 2,
            "height": 1
        }
        
        widget = service.add_widget(dashboard_id, widget_data)
        
        assert widget is not None
        assert widget.dashboard_id == dashboard_id
        assert widget.widget_type == "table"
        assert widget.title == "Connection Count"
        assert widget.data_source == "metrics"
        assert isinstance(widget.query, str)
        query = json.loads(widget.query)
        assert query["metric_type"] == "NETWORK_CONNECTION_COUNT"
    
    def test_update_widget(self, db_session, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test updating a widget."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get latency chart widget
        widget_id = sample_dashboard_widgets["latency_chart"].id
        
        # Update widget
        update_data = {
            "title": "Updated Network Latency",
            "refresh_interval_seconds": 120,
            "query": {
                "metric_type": "NETWORK_LATENCY",
                "time_range": "12h",
                "group_by": ["node_id"]
            }
        }
        
        updated = service.update_widget(widget_id, update_data)
        
        assert updated is True
        
        # Get updated widget
        widget = db_session.query(DashboardWidget).get(widget_id)
        
        assert widget.title == "Updated Network Latency"
        assert widget.refresh_interval_seconds == 120
        assert isinstance(widget.query, str)
        query = json.loads(widget.query)
        assert query["time_range"] == "12h"
    
    def test_delete_widget(self, db_session, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test deleting a widget."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get disk gauge widget
        widget_id = sample_dashboard_widgets["disk_gauge"].id
        
        # Delete widget
        deleted = service.delete_widget(widget_id)
        
        assert deleted is True
        
        # Try to get deleted widget
        widget = db_session.query(DashboardWidget).get(widget_id)
        
        assert widget is None
    
    def test_get_widget_data(self, db_session, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test getting data for a widget."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get CPU gauge widget
        widget = sample_dashboard_widgets["cpu_gauge"]
        
        # Get widget data
        data = service.get_widget_data(widget)
        
        assert data is not None
        assert "value" in data
        assert "timestamp" in data
        
        # Check that Elasticsearch was queried
        mock_elasticsearch_client.search.assert_called_once()


class TestDashboardIntegration:
    """Tests for dashboard integration with monitoring data."""
    
    def test_network_performance_dashboard(self, db_session, sample_dashboard_configurations, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test integration of network performance metrics with dashboard."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get network dashboard with widgets
        dashboard_id = sample_dashboard_configurations["network"].id
        dashboard, widgets = service.get_dashboard_with_widgets(dashboard_id)
        
        # Get data for each widget
        for widget in widgets:
            data = service.get_widget_data(widget)
            assert data is not None
            
            # Check that data matches widget type
            if widget.widget_type == "line_chart":
                assert "series" in data
            elif widget.widget_type == "area_chart":
                assert "series" in data
    
    def test_system_health_dashboard(self, db_session, sample_dashboard_configurations, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test integration of system health metrics with dashboard."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get system dashboard with widgets
        dashboard_id = sample_dashboard_configurations["system"].id
        dashboard, widgets = service.get_dashboard_with_widgets(dashboard_id)
        
        # Get data for each widget
        for widget in widgets:
            data = service.get_widget_data(widget)
            assert data is not None
            
            # Check that data matches widget type
            if widget.widget_type == "gauge":
                assert "value" in data
                assert "min" in data
                assert "max" in data
    
    def test_customer_usage_dashboard(self, db_session, sample_dashboard_configurations, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test integration of customer usage metrics with dashboard."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get customer dashboard with widgets
        dashboard_id = sample_dashboard_configurations["customer"].id
        dashboard, widgets = service.get_dashboard_with_widgets(dashboard_id)
        
        # Get data for each widget
        for widget in widgets:
            data = service.get_widget_data(widget)
            assert data is not None
            
            # Check that data matches widget type
            if widget.widget_type == "bar_chart":
                assert "categories" in data
                assert "series" in data
            elif widget.widget_type == "line_chart":
                assert "series" in data
            elif widget.widget_type == "pie_chart":
                assert "slices" in data
    
    def test_dashboard_refresh(self, db_session, sample_dashboard_widgets, mock_elasticsearch_client):
        """Test refreshing dashboard data."""
        service = DashboardService(db_session, es_client=mock_elasticsearch_client)
        
        # Get CPU gauge widget
        widget = sample_dashboard_widgets["cpu_gauge"]
        
        # Get widget data
        data1 = service.get_widget_data(widget)
        
        # Update mock to return different data
        mock_elasticsearch_client.search.return_value = {
            "hits": {
                "total": {"value": 10},
                "hits": [{"_source": {"value": i * 2, "timestamp": datetime.utcnow().isoformat()}} for i in range(10)]
            },
            "aggregations": {
                "avg_value": {"value": 65.5},
                "max_value": {"value": 98.0},
                "min_value": {"value": 20.0}
            }
        }
        
        # Get widget data again
        data2 = service.get_widget_data(widget)
        
        # Data should be different
        assert data1 != data2
