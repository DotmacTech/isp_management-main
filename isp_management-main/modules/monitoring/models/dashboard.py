"""
Dashboard models for the monitoring module.

This module defines models for dashboard configurations and widgets
for the monitoring module's reporting dashboards.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend_core.database import Base


class WidgetType(str, Enum):
    """Enum for dashboard widget types."""
    CHART = "chart"
    GAUGE = "gauge"
    TABLE = "table"
    METRIC = "metric"
    TEXT = "text"
    MAP = "map"
    CUSTOM = "custom"


class ChartType(str, Enum):
    """Enum for chart types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"


class DashboardConfiguration(Base):
    """
    Model for dashboard configurations.
    
    This model stores dashboard configurations for the monitoring module,
    including layout and widget settings.
    """
    __tablename__ = "dashboard_configurations"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    layout = Column(JSON, nullable=True)  # Layout configuration
    is_default = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    owner_id = Column(String, nullable=True)  # User ID of the owner
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the dashboard configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the dashboard configuration.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "layout": self.layout,
            "is_default": self.is_default,
            "is_public": self.is_public,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "widgets": [widget.to_dict() for widget in self.widgets] if self.widgets else []
        }
    
    def to_kibana_dashboard(self) -> Dict[str, Any]:
        """
        Convert the dashboard configuration to a Kibana dashboard format.
        
        Returns:
            Dict[str, Any]: Kibana dashboard representation.
        """
        # This is a simplified version, actual Kibana dashboard JSON is more complex
        widgets = []
        for widget in self.widgets:
            widgets.append(widget.to_kibana_widget())
        
        return {
            "id": self.id,
            "title": self.name,
            "description": self.description,
            "panels": widgets,
            "version": 1,
            "timeRange": {
                "from": "now-24h",
                "to": "now"
            }
        }


class DashboardWidget(Base):
    """
    Model for dashboard widgets.
    
    This model stores widget configurations for dashboard visualizations.
    """
    __tablename__ = "dashboard_widgets"
    
    id = Column(String, primary_key=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configurations.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    widget_type = Column(String, nullable=False)
    chart_type = Column(String, nullable=True)
    data_source = Column(String, nullable=False)  # Index or data source name
    query = Column(JSON, nullable=True)  # Query configuration
    visualization = Column(JSON, nullable=True)  # Visualization settings
    position = Column(JSON, nullable=True)  # Position in the dashboard
    size = Column(JSON, nullable=True)  # Size of the widget
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    dashboard = relationship("DashboardConfiguration", back_populates="widgets")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the dashboard widget to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the dashboard widget.
        """
        return {
            "id": self.id,
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "description": self.description,
            "widget_type": self.widget_type,
            "chart_type": self.chart_type,
            "data_source": self.data_source,
            "query": self.query,
            "visualization": self.visualization,
            "position": self.position,
            "size": self.size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_kibana_widget(self) -> Dict[str, Any]:
        """
        Convert the dashboard widget to a Kibana visualization format.
        
        Returns:
            Dict[str, Any]: Kibana visualization representation.
        """
        # This is a simplified version, actual Kibana visualization JSON is more complex
        return {
            "id": self.id,
            "type": self.widget_type,
            "name": self.name,
            "panelIndex": self.id,
            "gridData": {
                "x": self.position.get("x", 0) if self.position else 0,
                "y": self.position.get("y", 0) if self.position else 0,
                "w": self.size.get("width", 6) if self.size else 6,
                "h": self.size.get("height", 3) if self.size else 3,
                "i": self.id
            },
            "version": "7.10.0",
            "embeddableConfig": {
                "title": self.name,
                "description": self.description,
                "enhancements": {}
            }
        }


class SavedVisualization(Base):
    """
    Model for saved visualizations.
    
    This model stores saved visualizations that can be reused across dashboards.
    """
    __tablename__ = "saved_visualizations"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    widget_type = Column(String, nullable=False)
    chart_type = Column(String, nullable=True)
    data_source = Column(String, nullable=False)
    query = Column(JSON, nullable=True)
    visualization = Column(JSON, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    owner_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the saved visualization to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the saved visualization.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "widget_type": self.widget_type,
            "chart_type": self.chart_type,
            "data_source": self.data_source,
            "query": self.query,
            "visualization": self.visualization,
            "is_public": self.is_public,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_kibana_visualization(self) -> Dict[str, Any]:
        """
        Convert the saved visualization to a Kibana visualization format.
        
        Returns:
            Dict[str, Any]: Kibana visualization representation.
        """
        # This is a simplified version, actual Kibana visualization JSON is more complex
        return {
            "id": self.id,
            "type": self.widget_type,
            "attributes": {
                "title": self.name,
                "description": self.description,
                "version": 1,
                "kibanaSavedObjectMeta": {
                    "searchSourceJSON": json.dumps({
                        "index": self.data_source,
                        "query": self.query,
                        "filter": []
                    })
                },
                "visState": json.dumps({
                    "title": self.name,
                    "type": self.widget_type,
                    "params": self.visualization,
                    "aggs": []
                })
            }
        }
