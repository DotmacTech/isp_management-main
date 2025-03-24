"""
Pydantic schemas for system metrics.

This module defines Pydantic schemas for system metrics, which are used for
API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class MetricTypeEnum(str, Enum):
    """Enum for metric types."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Enum for metric types used in record_metric."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_THROUGHPUT = "network_throughput"
    NETWORK_LATENCY = "network_latency"
    PACKET_LOSS = "packet_loss"
    CONNECTION_COUNT = "connection_count"
    REQUEST_COUNT = "request_count"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    QUEUE_SIZE = "queue_size"
    CUSTOM = "custom"


class MetricUnit(str, Enum):
    """Enum for metric units."""
    PERCENTAGE = "percentage"
    BYTES = "bytes"
    MEGABYTES = "megabytes"
    GIGABYTES = "gigabytes"
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    COUNT = "count"
    REQUESTS_PER_SECOND = "requests_per_second"
    BYTES_PER_SECOND = "bytes_per_second"
    MEGABITS_PER_SECOND = "megabits_per_second"
    CUSTOM = "custom"


class SystemMetricBase(BaseModel):
    """Base schema for system metrics."""
    node_id: str = Field(..., description="ID of the network node")
    metric_type: MetricTypeEnum = Field(..., description="Type of the metric")
    value: float = Field(..., description="Value of the metric")
    unit: MetricUnit = Field(..., description="Unit of the metric")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class SystemMetricCreate(SystemMetricBase):
    """Schema for creating system metrics."""
    pass


class SystemMetricUpdate(BaseModel):
    """Schema for updating system metrics."""
    value: Optional[float] = Field(None, description="Value of the metric")
    unit: Optional[MetricUnit] = Field(None, description="Unit of the metric")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    elasticsearch_synced: Optional[bool] = Field(None, description="Whether the metric has been synced to Elasticsearch")


class SystemMetricInDB(SystemMetricBase):
    """Schema for system metrics in the database."""
    id: str = Field(..., description="ID of the system metric")
    created_at: datetime = Field(..., description="Time when the metric was created")
    elasticsearch_synced: bool = Field(..., description="Whether the metric has been synced to Elasticsearch")

    model_config = ConfigDict(from_attributes=True)


class SystemMetricResponse(SystemMetricInDB):
    """Schema for system metric responses."""
    pass


class SystemMetricList(BaseModel):
    """Schema for a list of system metrics."""
    items: List[SystemMetricResponse] = Field(..., description="List of system metrics")
    total: int = Field(..., description="Total number of system metrics")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class SystemMetricSummary(BaseModel):
    """Summary of system metrics for a specific node and type."""
    node_id: str = Field(..., description="ID of the network node")
    metric_type: MetricTypeEnum = Field(..., description="Type of the metric")
    average_value: float = Field(..., description="Average value of the metric")
    min_value: float = Field(..., description="Minimum value of the metric")
    max_value: float = Field(..., description="Maximum value of the metric")
    latest_value: float = Field(..., description="Latest value of the metric")
    unit: MetricUnit = Field(..., description="Unit of the metric")
    count: int = Field(..., description="Number of metrics in the summary")
    start_time: datetime = Field(..., description="Start time of the summary period")
    end_time: datetime = Field(..., description="End time of the summary period")


class SystemMetricAggregation(BaseModel):
    """Aggregation of system metrics by time interval."""
    node_id: str = Field(..., description="ID of the network node")
    metric_type: MetricTypeEnum = Field(..., description="Type of the metric")
    interval: str = Field(..., description="Aggregation interval (e.g., '1h', '1d')")
    timestamps: List[datetime] = Field(..., description="List of timestamps for each data point")
    values: List[float] = Field(..., description="List of aggregated values for each timestamp")
    unit: MetricUnit = Field(..., description="Unit of the metric")
    aggregation_function: str = Field(..., description="Function used for aggregation (e.g., 'avg', 'max')")


class SystemMetricFilter(BaseModel):
    """Schema for filtering system metrics."""
    node_id: Optional[str] = Field(None, description="Filter by node ID")
    metric_type: Optional[MetricTypeEnum] = Field(None, description="Filter by metric type")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    min_value: Optional[float] = Field(None, description="Filter by minimum value")
    max_value: Optional[float] = Field(None, description="Filter by maximum value")
    elasticsearch_synced: Optional[bool] = Field(None, description="Filter by Elasticsearch sync status")


# Network Performance Metric Schemas
class NetworkPerformanceMetricBase(BaseModel):
    """Base schema for network performance metrics."""
    source_node_id: str = Field(..., description="ID of the source network node")
    target_node_id: str = Field(..., description="ID of the target network node")
    latency: float = Field(..., description="Latency in milliseconds")
    packet_loss: float = Field(..., description="Packet loss percentage")
    jitter: Optional[float] = Field(None, description="Jitter in milliseconds")
    bandwidth: Optional[float] = Field(None, description="Bandwidth in Mbps")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class NetworkPerformanceMetricCreate(NetworkPerformanceMetricBase):
    """Schema for creating network performance metrics."""
    pass


class NetworkPerformanceMetricUpdate(BaseModel):
    """Schema for updating network performance metrics."""
    latency: Optional[float] = Field(None, description="Latency in milliseconds")
    packet_loss: Optional[float] = Field(None, description="Packet loss percentage")
    jitter: Optional[float] = Field(None, description="Jitter in milliseconds")
    bandwidth: Optional[float] = Field(None, description="Bandwidth in Mbps")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    elasticsearch_synced: Optional[bool] = Field(None, description="Whether the metric has been synced to Elasticsearch")


class NetworkPerformanceMetricInDB(NetworkPerformanceMetricBase):
    """Schema for network performance metrics in the database."""
    id: str = Field(..., description="ID of the network performance metric")
    created_at: datetime = Field(..., description="Time when the metric was created")
    elasticsearch_synced: bool = Field(..., description="Whether the metric has been synced to Elasticsearch")

    model_config = ConfigDict(from_attributes=True)


class NetworkPerformanceMetricResponse(NetworkPerformanceMetricInDB):
    """Schema for network performance metric responses."""
    pass


# Customer Usage Metric Schemas
class CustomerUsageMetricBase(BaseModel):
    """Base schema for customer usage metrics."""
    customer_id: str = Field(..., description="ID of the customer")
    download_bytes: int = Field(..., description="Download bytes")
    upload_bytes: int = Field(..., description="Upload bytes")
    session_duration: Optional[int] = Field(None, description="Session duration in seconds")
    ip_address: Optional[str] = Field(None, description="IP address")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class CustomerUsageMetricCreate(CustomerUsageMetricBase):
    """Schema for creating customer usage metrics."""
    pass


class CustomerUsageMetricUpdate(BaseModel):
    """Schema for updating customer usage metrics."""
    download_bytes: Optional[int] = Field(None, description="Download bytes")
    upload_bytes: Optional[int] = Field(None, description="Upload bytes")
    session_duration: Optional[int] = Field(None, description="Session duration in seconds")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    elasticsearch_synced: Optional[bool] = Field(None, description="Whether the metric has been synced to Elasticsearch")


class CustomerUsageMetricInDB(CustomerUsageMetricBase):
    """Schema for customer usage metrics in the database."""
    id: str = Field(..., description="ID of the customer usage metric")
    created_at: datetime = Field(..., description="Time when the metric was created")
    elasticsearch_synced: bool = Field(..., description="Whether the metric has been synced to Elasticsearch")

    model_config = ConfigDict(from_attributes=True)


class CustomerUsageMetricResponse(CustomerUsageMetricInDB):
    """Schema for customer usage metric responses."""
    pass
