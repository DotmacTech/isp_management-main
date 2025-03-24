"""
Pydantic schemas for dashboards.

This module defines Pydantic schemas for dashboard configurations and widgets,
which are used for API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, ForwardRef, Union, TypeVar, Generic
from enum import Enum

from pydantic import BaseModel, Field, create_model, ConfigDict


class WidgetTypeEnum(str, Enum):
    """Enum for dashboard widget types."""
    CHART = "chart"
    GAUGE = "gauge"
    TABLE = "table"
    METRIC = "metric"
    TEXT = "text"
    MAP = "map"
    CUSTOM = "custom"


class ChartTypeEnum(str, Enum):
    """Enum for chart types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"


# Dashboard Metric Schemas
class DashboardMetricBase(BaseModel):
    """Base schema for dashboard metrics."""
    name: str = Field(..., description="Name of the metric")
    description: Optional[str] = Field(None, description="Description of the metric")
    metric_type: str = Field(..., description="Type of the metric")
    data_source: str = Field(..., description="Data source for the metric")
    query: Dict[str, Any] = Field(..., description="Query configuration")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    thresholds: Optional[Dict[str, Any]] = Field(None, description="Threshold configuration")
    refresh_interval: int = Field(60, description="Refresh interval in seconds")


class DashboardMetric(DashboardMetricBase):
    """Schema for dashboard metrics."""
    id: str = Field(..., description="ID of the metric")
    created_at: datetime = Field(..., description="Time when the metric was created")
    updated_at: datetime = Field(..., description="Time when the metric was last updated")
    
    model_config = ConfigDict(from_attributes=True)


class DashboardMetricCreate(DashboardMetricBase):
    """Schema for creating dashboard metrics."""
    pass


class DashboardMetricUpdate(BaseModel):
    """Schema for updating dashboard metrics."""
    name: Optional[str] = Field(None, description="Name of the metric")
    description: Optional[str] = Field(None, description="Description of the metric")
    metric_type: Optional[str] = Field(None, description="Type of the metric")
    data_source: Optional[str] = Field(None, description="Data source for the metric")
    query: Optional[Dict[str, Any]] = Field(None, description="Query configuration")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    thresholds: Optional[Dict[str, Any]] = Field(None, description="Threshold configuration")
    refresh_interval: Optional[int] = Field(None, description="Refresh interval in seconds")


class DashboardMetricResponse(DashboardMetric):
    """Schema for dashboard metric responses."""
    pass


class DashboardMetricList(BaseModel):
    """Schema for a list of dashboard metrics."""
    items: List[DashboardMetricResponse] = Field(..., description="List of dashboard metrics")
    total: int = Field(..., description="Total number of dashboard metrics")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


# Dashboard Configuration Schemas
class DashboardConfigurationBase(BaseModel):
    """Base schema for dashboard configurations."""
    name: str = Field(..., description="Name of the dashboard configuration")
    description: Optional[str] = Field(None, description="Description of the dashboard configuration")
    layout: Optional[Dict[str, Any]] = Field(None, description="Layout configuration")
    is_default: bool = Field(False, description="Whether this is the default dashboard")
    is_public: bool = Field(False, description="Whether this dashboard is public")
    owner_id: Optional[str] = Field(None, description="ID of the owner")


class DashboardConfigurationCreate(DashboardConfigurationBase):
    """Schema for creating dashboard configurations."""
    pass


class DashboardConfigurationUpdate(BaseModel):
    """Schema for updating dashboard configurations."""
    name: Optional[str] = Field(None, description="Name of the dashboard configuration")
    description: Optional[str] = Field(None, description="Description of the dashboard configuration")
    layout: Optional[Dict[str, Any]] = Field(None, description="Layout configuration")
    is_default: Optional[bool] = Field(None, description="Whether this is the default dashboard")
    is_public: Optional[bool] = Field(None, description="Whether this dashboard is public")


class DashboardConfigurationInDB(DashboardConfigurationBase):
    """Schema for dashboard configurations in the database."""
    id: str = Field(..., description="ID of the dashboard configuration")
    created_at: datetime = Field(..., description="Time when the dashboard configuration was created")
    updated_at: datetime = Field(..., description="Time when the dashboard configuration was last updated")
    widgets: List[Dict[str, Any]] = Field(default_factory=list, description="List of widgets")
    
    model_config = ConfigDict(from_attributes=True)


class DashboardConfigurationResponse(DashboardConfigurationInDB):
    """Schema for dashboard configuration responses."""
    pass


class DashboardConfigurationList(BaseModel):
    """Schema for a list of dashboard configurations."""
    items: List[DashboardConfigurationResponse] = Field(..., description="List of dashboard configurations")
    total: int = Field(..., description="Total number of dashboard configurations")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class DashboardConfigurationFilter(BaseModel):
    """Schema for filtering dashboard configurations."""
    owner_id: Optional[str] = Field(None, description="Filter by owner ID")
    is_default: Optional[bool] = Field(None, description="Filter by default status")
    is_public: Optional[bool] = Field(None, description="Filter by public status")


# Dashboard Widget Schemas
class DashboardWidgetBase(BaseModel):
    """Base schema for dashboard widgets."""
    dashboard_id: str = Field(..., description="ID of the dashboard configuration")
    name: str = Field(..., description="Name of the widget")
    description: Optional[str] = Field(None, description="Description of the widget")
    widget_type: WidgetTypeEnum = Field(..., description="Type of the widget")
    chart_type: Optional[ChartTypeEnum] = Field(None, description="Type of the chart")
    data_source: str = Field(..., description="Data source for the widget")
    query: Optional[Dict[str, Any]] = Field(None, description="Query configuration")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Visualization settings")
    position: Optional[Dict[str, Any]] = Field(None, description="Position in the dashboard")
    size: Optional[Dict[str, Any]] = Field(None, description="Size of the widget")


class DashboardWidgetCreate(DashboardWidgetBase):
    """Schema for creating dashboard widgets."""
    pass


class DashboardWidgetUpdate(BaseModel):
    """Schema for updating dashboard widgets."""
    name: Optional[str] = Field(None, description="Name of the widget")
    description: Optional[str] = Field(None, description="Description of the widget")
    widget_type: Optional[WidgetTypeEnum] = Field(None, description="Type of the widget")
    chart_type: Optional[ChartTypeEnum] = Field(None, description="Type of the chart")
    data_source: Optional[str] = Field(None, description="Data source for the widget")
    query: Optional[Dict[str, Any]] = Field(None, description="Query configuration")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Visualization settings")
    position: Optional[Dict[str, Any]] = Field(None, description="Position in the dashboard")
    size: Optional[Dict[str, Any]] = Field(None, description="Size of the widget")


class DashboardWidgetInDB(DashboardWidgetBase):
    """Schema for dashboard widgets in the database."""
    id: str = Field(..., description="ID of the dashboard widget")
    created_at: datetime = Field(..., description="Time when the widget was created")
    updated_at: datetime = Field(..., description="Time when the widget was last updated")
    
    model_config = ConfigDict(from_attributes=True)


class DashboardWidgetResponse(DashboardWidgetInDB):
    """Schema for dashboard widget responses."""
    pass


class DashboardWidgetList(BaseModel):
    """Schema for a list of dashboard widgets."""
    items: List[DashboardWidgetResponse] = Field(..., description="List of dashboard widgets")
    total: int = Field(..., description="Total number of dashboard widgets")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


# Saved Visualization Schemas
class SavedVisualizationBase(BaseModel):
    """Base schema for saved visualizations."""
    name: str = Field(..., description="Name of the saved visualization")
    description: Optional[str] = Field(None, description="Description of the saved visualization")
    widget_type: WidgetTypeEnum = Field(..., description="Type of the widget")
    chart_type: Optional[ChartTypeEnum] = Field(None, description="Type of the chart")
    data_source: str = Field(..., description="Data source for the visualization")
    query: Optional[Dict[str, Any]] = Field(None, description="Query configuration")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Visualization settings")
    is_public: bool = Field(False, description="Whether this visualization is public")
    owner_id: Optional[str] = Field(None, description="ID of the owner")


class SavedVisualizationCreate(SavedVisualizationBase):
    """Schema for creating saved visualizations."""
    pass


class SavedVisualizationUpdate(BaseModel):
    """Schema for updating saved visualizations."""
    name: Optional[str] = Field(None, description="Name of the saved visualization")
    description: Optional[str] = Field(None, description="Description of the saved visualization")
    widget_type: Optional[WidgetTypeEnum] = Field(None, description="Type of the widget")
    chart_type: Optional[ChartTypeEnum] = Field(None, description="Type of the chart")
    data_source: Optional[str] = Field(None, description="Data source for the visualization")
    query: Optional[Dict[str, Any]] = Field(None, description="Query configuration")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Visualization settings")
    is_public: Optional[bool] = Field(None, description="Whether this visualization is public")


class SavedVisualizationInDB(SavedVisualizationBase):
    """Schema for saved visualizations in the database."""
    id: str = Field(..., description="ID of the saved visualization")
    created_at: datetime = Field(..., description="Time when the visualization was created")
    updated_at: datetime = Field(..., description="Time when the visualization was last updated")
    
    model_config = ConfigDict(from_attributes=True)


class SavedVisualizationResponse(SavedVisualizationInDB):
    """Schema for saved visualization responses."""
    pass


class SavedVisualizationList(BaseModel):
    """Schema for a list of saved visualizations."""
    items: List[SavedVisualizationResponse] = Field(..., description="List of saved visualizations")
    total: int = Field(..., description="Total number of saved visualizations")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class SavedVisualizationFilter(BaseModel):
    """Schema for filtering saved visualizations."""
    owner_id: Optional[str] = Field(None, description="Filter by owner ID")
    widget_type: Optional[WidgetTypeEnum] = Field(None, description="Filter by widget type")
    chart_type: Optional[ChartTypeEnum] = Field(None, description="Filter by chart type")
    is_public: Optional[bool] = Field(None, description="Filter by public status")


# Generic paginated response
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated responses."""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
