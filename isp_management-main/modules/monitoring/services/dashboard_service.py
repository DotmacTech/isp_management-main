"""
Service for managing dashboards in the monitoring module.

This service provides functionality for creating, retrieving, updating, and
deleting dashboards and dashboard widgets, as well as fetching data for widgets.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from modules.monitoring.models.dashboard import (
    DashboardConfiguration, DashboardWidget, WidgetType, ChartType
)
from modules.monitoring.models import SystemMetric
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)


class DashboardService:
    """Service for managing dashboards in the monitoring module."""

    def __init__(self, db_session: Session, es_client: Optional[ElasticsearchClient] = None):
        """
        Initialize the dashboard service.
        
        Args:
            db_session: SQLAlchemy database session
            es_client: Elasticsearch client for fetching widget data
        """
        self.db_session = db_session
        self.es_client = es_client or ElasticsearchClient()

    def get_dashboard(self, dashboard_id: int) -> Optional[DashboardConfiguration]:
        """
        Get a dashboard by ID.
        
        Args:
            dashboard_id: ID of the dashboard to retrieve
            
        Returns:
            Dashboard configuration or None if not found
        """
        return self.db_session.query(DashboardConfiguration).filter(
            DashboardConfiguration.id == dashboard_id
        ).first()

    def get_dashboard_with_widgets(self, dashboard_id: int) -> Tuple[Optional[DashboardConfiguration], List[DashboardWidget]]:
        """
        Get a dashboard with its widgets.
        
        Args:
            dashboard_id: ID of the dashboard to retrieve
            
        Returns:
            Tuple of (dashboard, widgets) or (None, []) if not found
        """
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return None, []
            
        widgets = self.db_session.query(DashboardWidget).filter(
            DashboardWidget.dashboard_id == dashboard_id
        ).all()
        
        return dashboard, widgets

    def get_public_dashboards(self) -> List[DashboardConfiguration]:
        """
        Get all public dashboards.
        
        Returns:
            List of public dashboard configurations
        """
        return self.db_session.query(DashboardConfiguration).filter(
            DashboardConfiguration.is_public == True
        ).all()

    def get_user_dashboards(self, user_id: int) -> List[DashboardConfiguration]:
        """
        Get dashboards owned by a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of dashboard configurations owned by the user
        """
        return self.db_session.query(DashboardConfiguration).filter(
            DashboardConfiguration.created_by == user_id
        ).all()

    def create_dashboard(self, dashboard_data: Dict[str, Any]) -> DashboardConfiguration:
        """
        Create a new dashboard.
        
        Args:
            dashboard_data: Dictionary containing dashboard configuration data
            
        Returns:
            Created dashboard configuration
        """
        # Convert layout to JSON string if it's a dict
        if isinstance(dashboard_data.get('layout'), dict):
            dashboard_data['layout'] = json.dumps(dashboard_data['layout'])
            
        dashboard = DashboardConfiguration(
            name=dashboard_data.get('name'),
            description=dashboard_data.get('description'),
            layout=dashboard_data.get('layout'),
            is_public=dashboard_data.get('is_public', False),
            created_by=dashboard_data.get('created_by')
        )
        
        self.db_session.add(dashboard)
        self.db_session.commit()
        self.db_session.refresh(dashboard)
        
        return dashboard

    def update_dashboard(self, dashboard_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Update an existing dashboard.
        
        Args:
            dashboard_id: ID of the dashboard to update
            update_data: Dictionary containing updated dashboard data
            
        Returns:
            True if dashboard was updated, False if not found
        """
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return False
            
        # Update fields
        if 'name' in update_data:
            dashboard.name = update_data['name']
        if 'description' in update_data:
            dashboard.description = update_data['description']
        if 'layout' in update_data:
            if isinstance(update_data['layout'], dict):
                dashboard.layout = json.dumps(update_data['layout'])
            else:
                dashboard.layout = update_data['layout']
        if 'is_public' in update_data:
            dashboard.is_public = update_data['is_public']
            
        dashboard.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        return True

    def delete_dashboard(self, dashboard_id: int) -> bool:
        """
        Delete a dashboard.
        
        Args:
            dashboard_id: ID of the dashboard to delete
            
        Returns:
            True if dashboard was deleted, False if not found
        """
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return False
            
        self.db_session.delete(dashboard)
        self.db_session.commit()
        return True

    def add_widget(self, dashboard_id: int, widget_data: Dict[str, Any]) -> Optional[DashboardWidget]:
        """
        Add a widget to a dashboard.
        
        Args:
            dashboard_id: ID of the dashboard to add the widget to
            widget_data: Dictionary containing widget configuration data
            
        Returns:
            Created widget or None if dashboard not found
        """
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return None
            
        # Convert query to JSON string if it's a dict
        if isinstance(widget_data.get('query'), dict):
            widget_data['query'] = json.dumps(widget_data['query'])
            
        widget = DashboardWidget(
            dashboard_id=dashboard_id,
            widget_type=widget_data.get('widget_type'),
            title=widget_data.get('title'),
            data_source=widget_data.get('data_source'),
            query=widget_data.get('query'),
            refresh_interval_seconds=widget_data.get('refresh_interval_seconds'),
            position_x=widget_data.get('position_x'),
            position_y=widget_data.get('position_y'),
            width=widget_data.get('width'),
            height=widget_data.get('height')
        )
        
        self.db_session.add(widget)
        self.db_session.commit()
        self.db_session.refresh(widget)
        
        return widget

    def update_widget(self, widget_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Update an existing widget.
        
        Args:
            widget_id: ID of the widget to update
            update_data: Dictionary containing updated widget data
            
        Returns:
            True if widget was updated, False if not found
        """
        widget = self.db_session.query(DashboardWidget).filter(
            DashboardWidget.id == widget_id
        ).first()
        
        if not widget:
            return False
            
        # Update fields
        if 'title' in update_data:
            widget.title = update_data['title']
        if 'refresh_interval_seconds' in update_data:
            widget.refresh_interval_seconds = update_data['refresh_interval_seconds']
        if 'query' in update_data:
            if isinstance(update_data['query'], dict):
                widget.query = json.dumps(update_data['query'])
            else:
                widget.query = update_data['query']
        if 'widget_type' in update_data:
            widget.widget_type = update_data['widget_type']
        if 'data_source' in update_data:
            widget.data_source = update_data['data_source']
        if 'position_x' in update_data:
            widget.position_x = update_data['position_x']
        if 'position_y' in update_data:
            widget.position_y = update_data['position_y']
        if 'width' in update_data:
            widget.width = update_data['width']
        if 'height' in update_data:
            widget.height = update_data['height']
            
        self.db_session.commit()
        return True

    def delete_widget(self, widget_id: int) -> bool:
        """
        Delete a widget.
        
        Args:
            widget_id: ID of the widget to delete
            
        Returns:
            True if widget was deleted, False if not found
        """
        widget = self.db_session.query(DashboardWidget).filter(
            DashboardWidget.id == widget_id
        ).first()
        
        if not widget:
            return False
            
        self.db_session.delete(widget)
        self.db_session.commit()
        return True

    def get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """
        Get data for a dashboard widget.
        
        Args:
            widget: Dashboard widget to get data for
            
        Returns:
            Dictionary containing widget data
        """
        if not widget.query:
            return {"error": "No query defined for widget"}
            
        try:
            query = json.loads(widget.query) if isinstance(widget.query, str) else widget.query
        except json.JSONDecodeError:
            logger.error(f"Failed to parse widget query: {widget.query}")
            return {"error": "Invalid widget query"}
            
        # Handle different data sources
        if widget.data_source == "metrics":
            return self._get_metrics_data(widget, query)
        elif widget.data_source == "logs":
            return self._get_logs_data(widget, query)
        elif widget.data_source == "alerts":
            return self._get_alerts_data(widget, query)
        else:
            return {"error": f"Unsupported data source: {widget.data_source}"}

    def _get_metrics_data(self, widget: DashboardWidget, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get metrics data for a widget.
        
        Args:
            widget: Dashboard widget
            query: Widget query
            
        Returns:
            Dictionary containing metrics data
        """
        # Use Elasticsearch for metrics data if available
        if self.es_client and self.es_client.is_connected():
            return self._get_metrics_from_elasticsearch(widget, query)
            
        # Fall back to database if Elasticsearch is not available
        return self._get_metrics_from_database(widget, query)

    def _get_metrics_from_elasticsearch(self, widget: DashboardWidget, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get metrics data from Elasticsearch.
        
        Args:
            widget: Dashboard widget
            query: Widget query
            
        Returns:
            Dictionary containing metrics data from Elasticsearch
        """
        # Build Elasticsearch query
        es_query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"metric_type": query.get("metric_type")}}
                    ],
                    "filter": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{query.get('time_range', '24h')}",
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "avg_value": {"avg": {"field": "value"}},
                "max_value": {"max": {"field": "value"}},
                "min_value": {"min": {"field": "value"}}
            }
        }
        
        # Add group by if specified
        if "group_by" in query and query["group_by"]:
            es_query["aggs"]["by_group"] = {
                "terms": {"field": query["group_by"][0], "size": query.get("limit", 10)},
                "aggs": {
                    "avg_value": {"avg": {"field": "value"}},
                    "max_value": {"max": {"field": "value"}},
                    "min_value": {"min": {"field": "value"}},
                    "by_time": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "interval": "1h"
                        },
                        "aggs": {
                            "avg_value": {"avg": {"field": "value"}}
                        }
                    }
                }
            }
        
        # Execute Elasticsearch query
        result = self.es_client.search(
            index="metrics",
            body=es_query
        )
        
        # Process results based on widget type
        if widget.widget_type == "line_chart" or widget.widget_type == "area_chart":
            return self._process_chart_data(result, query)
        elif widget.widget_type == "gauge":
            return self._process_gauge_data(result)
        elif widget.widget_type == "bar_chart":
            return self._process_bar_chart_data(result, query)
        elif widget.widget_type == "pie_chart":
            return self._process_pie_chart_data(result, query)
        elif widget.widget_type == "table":
            return self._process_table_data(result, query)
        else:
            # Default processing
            return {
                "value": result["aggregations"]["avg_value"]["value"] if "aggregations" in result else None,
                "timestamp": datetime.utcnow().isoformat()
            }

    def _get_metrics_from_database(self, widget: DashboardWidget, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get metrics data from the database.
        
        Args:
            widget: Dashboard widget
            query: Widget query
            
        Returns:
            Dictionary containing metrics data from the database
        """
        # Calculate time range
        time_range = query.get("time_range", "24h")
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            start_time = datetime.utcnow() - timedelta(hours=hours)
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            start_time = datetime.utcnow() - timedelta(days=days)
        elif time_range.endswith("m"):
            minutes = int(time_range[:-1])
            start_time = datetime.utcnow() - timedelta(minutes=minutes)
        else:
            # Default to 24 hours
            start_time = datetime.utcnow() - timedelta(hours=24)
        
        # Query database for metrics
        db_query = self.db_session.query(SystemMetric).filter(
            SystemMetric.metric_type == query.get("metric_type"),
            SystemMetric.timestamp >= start_time
        )
        
        # Apply group by if specified
        if "group_by" in query and query["group_by"]:
            # This is a simplified implementation
            # In a real system, you would use SQLAlchemy's group_by and aggregate functions
            metrics = db_query.all()
            
            # Process results based on widget type
            if widget.widget_type == "line_chart" or widget.widget_type == "area_chart":
                return self._process_db_chart_data(metrics, query)
            elif widget.widget_type == "gauge":
                return self._process_db_gauge_data(metrics)
            elif widget.widget_type == "bar_chart":
                return self._process_db_bar_chart_data(metrics, query)
            elif widget.widget_type == "pie_chart":
                return self._process_db_pie_chart_data(metrics, query)
            elif widget.widget_type == "table":
                return self._process_db_table_data(metrics, query)
        else:
            # No grouping, just get aggregates
            metrics = db_query.all()
            
            # Calculate aggregates
            if not metrics:
                return {"value": None, "timestamp": datetime.utcnow().isoformat()}
                
            values = [m.value for m in metrics if m.value is not None]
            if not values:
                return {"value": None, "timestamp": datetime.utcnow().isoformat()}
                
            avg_value = sum(values) / len(values) if values else None
            max_value = max(values) if values else None
            min_value = min(values) if values else None
            
            # Process based on widget type
            if widget.widget_type == "gauge":
                return {
                    "value": avg_value,
                    "min": min_value,
                    "max": max_value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "value": avg_value,
                    "timestamp": datetime.utcnow().isoformat()
                }

    def _get_logs_data(self, widget: DashboardWidget, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get logs data for a widget.
        
        Args:
            widget: Dashboard widget
            query: Widget query
            
        Returns:
            Dictionary containing logs data
        """
        # Implement logs data retrieval
        # This is a placeholder implementation
        return {"message": "Logs data retrieval not implemented"}

    def _get_alerts_data(self, widget: DashboardWidget, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get alerts data for a widget.
        
        Args:
            widget: Dashboard widget
            query: Widget query
            
        Returns:
            Dictionary containing alerts data
        """
        # Implement alerts data retrieval
        # This is a placeholder implementation
        return {"message": "Alerts data retrieval not implemented"}

    def _process_chart_data(self, es_result: Dict[str, Any], query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Elasticsearch results for chart widgets.
        
        Args:
            es_result: Elasticsearch query result
            query: Widget query
            
        Returns:
            Processed chart data
        """
        # Check if we have group by results
        if "aggregations" in es_result and "by_group" in es_result["aggregations"]:
            # Process grouped data
            series = []
            for bucket in es_result["aggregations"]["by_group"]["buckets"]:
                group_name = bucket["key"]
                data_points = []
                
                # Process time series data
                for time_bucket in bucket["by_time"]["buckets"]:
                    timestamp = time_bucket["key_as_string"]
                    value = time_bucket["avg_value"]["value"]
                    data_points.append({"timestamp": timestamp, "value": value})
                
                series.append({
                    "name": group_name,
                    "data": data_points
                })
            
            return {"series": series}
        else:
            # Process non-grouped data (single series)
            # In a real implementation, you would query time series data
            # This is a simplified placeholder
            return {
                "series": [
                    {
                        "name": "Value",
                        "data": [
                            {"timestamp": datetime.utcnow().isoformat(), "value": es_result["aggregations"]["avg_value"]["value"]}
                        ]
                    }
                ]
            }

    def _process_gauge_data(self, es_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Elasticsearch results for gauge widgets.
        
        Args:
            es_result: Elasticsearch query result
            
        Returns:
            Processed gauge data
        """
        if "aggregations" not in es_result:
            return {"value": None, "min": None, "max": None, "timestamp": datetime.utcnow().isoformat()}
            
        return {
            "value": es_result["aggregations"]["avg_value"]["value"],
            "min": es_result["aggregations"]["min_value"]["value"],
            "max": es_result["aggregations"]["max_value"]["value"],
            "timestamp": datetime.utcnow().isoformat()
        }

    def _process_bar_chart_data(self, es_result: Dict[str, Any], query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Elasticsearch results for bar chart widgets.
        
        Args:
            es_result: Elasticsearch query result
            query: Widget query
            
        Returns:
            Processed bar chart data
        """
        if "aggregations" not in es_result or "by_group" not in es_result["aggregations"]:
            return {"categories": [], "series": []}
            
        categories = []
        values = []
        
        for bucket in es_result["aggregations"]["by_group"]["buckets"]:
            categories.append(bucket["key"])
            values.append(bucket["avg_value"]["value"])
        
        return {
            "categories": categories,
            "series": [{"name": "Value", "data": values}]
        }

    def _process_pie_chart_data(self, es_result: Dict[str, Any], query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Elasticsearch results for pie chart widgets.
        
        Args:
            es_result: Elasticsearch query result
            query: Widget query
            
        Returns:
            Processed pie chart data
        """
        if "aggregations" not in es_result or "by_group" not in es_result["aggregations"]:
            return {"slices": []}
            
        slices = []
        
        for bucket in es_result["aggregations"]["by_group"]["buckets"]:
            slices.append({
                "name": bucket["key"],
                "value": bucket["avg_value"]["value"]
            })
        
        return {"slices": slices}

    def _process_table_data(self, es_result: Dict[str, Any], query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Elasticsearch results for table widgets.
        
        Args:
            es_result: Elasticsearch query result
            query: Widget query
            
        Returns:
            Processed table data
        """
        if "aggregations" not in es_result or "by_group" not in es_result["aggregations"]:
            return {"headers": [], "rows": []}
            
        headers = ["Name", "Average", "Maximum", "Minimum"]
        rows = []
        
        for bucket in es_result["aggregations"]["by_group"]["buckets"]:
            rows.append([
                bucket["key"],
                bucket["avg_value"]["value"],
                bucket["max_value"]["value"],
                bucket["min_value"]["value"]
            ])
        
        return {"headers": headers, "rows": rows}

    # Database processing methods (simplified implementations)
    def _process_db_chart_data(self, metrics: List[SystemMetric], query: Dict[str, Any]) -> Dict[str, Any]:
        """Process database results for chart widgets."""
        return {"series": [{"name": "Value", "data": [{"timestamp": m.timestamp.isoformat(), "value": m.value} for m in metrics]}]}

    def _process_db_gauge_data(self, metrics: List[SystemMetric]) -> Dict[str, Any]:
        """Process database results for gauge widgets."""
        values = [m.value for m in metrics if m.value is not None]
        if not values:
            return {"value": None, "min": None, "max": None, "timestamp": datetime.utcnow().isoformat()}
        return {
            "value": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _process_db_bar_chart_data(self, metrics: List[SystemMetric], query: Dict[str, Any]) -> Dict[str, Any]:
        """Process database results for bar chart widgets."""
        # Simplified implementation
        return {"categories": [], "series": [{"name": "Value", "data": []}]}

    def _process_db_pie_chart_data(self, metrics: List[SystemMetric], query: Dict[str, Any]) -> Dict[str, Any]:
        """Process database results for pie chart widgets."""
        # Simplified implementation
        return {"slices": []}

    def _process_db_table_data(self, metrics: List[SystemMetric], query: Dict[str, Any]) -> Dict[str, Any]:
        """Process database results for table widgets."""
        # Simplified implementation
        return {"headers": [], "rows": []}
