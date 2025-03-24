"""
Pydantic schemas for metric searching.

This module defines Pydantic schemas for metric search parameters and results,
which are used for API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from pydantic import BaseModel, Field


class AggregationTypeEnum(str, Enum):
    """Enum for aggregation types."""
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    PERCENTILE = "percentile"
    CARDINALITY = "cardinality"
    STATS = "stats"


class TimeIntervalEnum(str, Enum):
    """Enum for time intervals."""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class SortDirectionEnum(str, Enum):
    """Enum for sort direction."""
    ASC = "asc"
    DESC = "desc"


class MetricSearchParams(BaseModel):
    """Schema for metric search parameters."""
    metric_type: Optional[str] = Field(None, description="Type of metric to search for")
    start_time: Optional[datetime] = Field(None, description="Start time for the search")
    end_time: Optional[datetime] = Field(None, description="End time for the search")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply")
    aggregation: Optional[AggregationTypeEnum] = Field(None, description="Aggregation to apply")
    interval: Optional[TimeIntervalEnum] = Field(None, description="Time interval for aggregation")
    group_by: Optional[List[str]] = Field(None, description="Fields to group by")
    fields: Optional[List[str]] = Field(None, description="Fields to include in the response")
    page: int = Field(1, description="Page number")
    size: int = Field(50, description="Number of items per page")
    sort_by: Optional[str] = Field("timestamp", description="Field to sort by")
    sort_direction: SortDirectionEnum = Field(SortDirectionEnum.DESC, description="Sort direction")
    percentile: Optional[float] = Field(None, description="Percentile for percentile aggregation")
    include_raw: bool = Field(False, description="Whether to include raw data points")


class MetricDataPoint(BaseModel):
    """Schema for a single metric data point."""
    timestamp: datetime = Field(..., description="Timestamp of the data point")
    value: float = Field(..., description="Value of the data point")
    tags: Optional[Dict[str, str]] = Field(None, description="Tags associated with the data point")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MetricSearchResult(BaseModel):
    """Schema for metric search result."""
    metric_name: str = Field(..., description="Name of the metric")
    metric_type: str = Field(..., description="Type of the metric")
    start_time: datetime = Field(..., description="Start time of the data")
    end_time: datetime = Field(..., description="End time of the data")
    interval: Optional[TimeIntervalEnum] = Field(None, description="Time interval for aggregation")
    aggregation: Optional[AggregationTypeEnum] = Field(None, description="Aggregation applied")
    data_points: List[MetricDataPoint] = Field(..., description="Data points")
    tags: Optional[Dict[str, str]] = Field(None, description="Tags associated with the metric")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MetricSearchResponse(BaseModel):
    """Schema for metric search response."""
    items: List[MetricSearchResult] = Field(..., description="List of metric search results")
    total: int = Field(..., description="Total number of metrics matching the search criteria")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")


class MetricAggregationParams(BaseModel):
    """Schema for metric aggregation parameters."""
    metric_type: str = Field(..., description="Type of metric to aggregate")
    aggregation: AggregationTypeEnum = Field(..., description="Aggregation to apply")
    field: str = Field(..., description="Field to aggregate on")
    start_time: Optional[datetime] = Field(None, description="Start time for the aggregation")
    end_time: Optional[datetime] = Field(None, description="End time for the aggregation")
    interval: Optional[TimeIntervalEnum] = Field(None, description="Time interval for aggregation")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply before aggregation")
    group_by: Optional[List[str]] = Field(None, description="Fields to group by")
    percentile: Optional[float] = Field(None, description="Percentile for percentile aggregation")


class MetricAggregationResult(BaseModel):
    """Schema for metric aggregation result."""
    metric_type: str = Field(..., description="Type of metric that was aggregated")
    aggregation: AggregationTypeEnum = Field(..., description="Aggregation that was applied")
    field: str = Field(..., description="Field that was aggregated on")
    start_time: datetime = Field(..., description="Start time of the aggregation")
    end_time: datetime = Field(..., description="End time of the aggregation")
    interval: Optional[TimeIntervalEnum] = Field(None, description="Time interval for aggregation")
    buckets: List[Dict[str, Any]] = Field(..., description="Aggregation buckets")
    total: int = Field(..., description="Total number of documents in the aggregation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MetricExportParams(BaseModel):
    """Schema for metric export parameters."""
    metric_type: Optional[str] = Field(None, description="Type of metric to export")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply")
    start_time: Optional[datetime] = Field(None, description="Start time for the export")
    end_time: Optional[datetime] = Field(None, description="End time for the export")
    fields: Optional[List[str]] = Field(None, description="Fields to include in the export")
    format: str = Field("csv", description="Export format (csv, json, etc.)")
    aggregation: Optional[AggregationTypeEnum] = Field(None, description="Aggregation to apply")
    interval: Optional[TimeIntervalEnum] = Field(None, description="Time interval for aggregation")
    max_results: Optional[int] = Field(10000, description="Maximum number of results to export")
    include_metadata: bool = Field(False, description="Whether to include metadata in the export")


class MetricExportResponse(BaseModel):
    """Schema for metric export response."""
    export_id: str = Field(..., description="ID of the export job")
    status: str = Field(..., description="Status of the export job")
    created_at: datetime = Field(..., description="Time when the export job was created")
    file_name: Optional[str] = Field(None, description="Name of the export file")
    file_size: Optional[int] = Field(None, description="Size of the export file in bytes")
    download_url: Optional[str] = Field(None, description="URL to download the export file")
    expires_at: Optional[datetime] = Field(None, description="Time when the download URL expires")
    record_count: Optional[int] = Field(None, description="Number of records in the export")
    parameters: MetricExportParams = Field(..., description="Parameters used for the export")
