"""
Pydantic schemas for log searching.

This module defines Pydantic schemas for log search parameters and results,
which are used for API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from pydantic import BaseModel, Field


class LogLevelEnum(str, Enum):
    """Enum for log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SortOrderEnum(str, Enum):
    """Enum for sort order."""
    ASC = "asc"
    DESC = "desc"


class LogSearchParams(BaseModel):
    """Schema for log search parameters."""
    query: Optional[str] = Field(None, description="Search query string")
    service: Optional[str] = Field(None, description="Filter by service name")
    level: Optional[LogLevelEnum] = Field(None, description="Filter by log level")
    start_time: Optional[datetime] = Field(None, description="Start time for the search")
    end_time: Optional[datetime] = Field(None, description="End time for the search")
    fields: Optional[List[str]] = Field(None, description="Fields to include in the response")
    exclude_fields: Optional[List[str]] = Field(None, description="Fields to exclude from the response")
    page: int = Field(1, description="Page number")
    size: int = Field(50, description="Number of items per page")
    sort_by: Optional[str] = Field("timestamp", description="Field to sort by")
    sort_order: SortOrderEnum = Field(SortOrderEnum.DESC, description="Sort order")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class LogSearchResult(BaseModel):
    """Schema for a single log search result."""
    id: str = Field(..., description="ID of the log entry")
    timestamp: datetime = Field(..., description="Timestamp of the log entry")
    service: str = Field(..., description="Service that generated the log")
    level: LogLevelEnum = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    source: Optional[str] = Field(None, description="Source of the log entry")
    host: Optional[str] = Field(None, description="Host that generated the log")
    trace_id: Optional[str] = Field(None, description="Trace ID for distributed tracing")
    span_id: Optional[str] = Field(None, description="Span ID for distributed tracing")
    user_id: Optional[str] = Field(None, description="ID of the user associated with the log")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class LogSearchResponse(BaseModel):
    """Schema for log search response."""
    items: List[LogSearchResult] = Field(..., description="List of log search results")
    total: int = Field(..., description="Total number of log entries matching the search criteria")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    query: Optional[str] = Field(None, description="Search query string")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregation results")


class LogAggregationParams(BaseModel):
    """Schema for log aggregation parameters."""
    field: str = Field(..., description="Field to aggregate on")
    aggregation_type: str = Field(..., description="Type of aggregation")
    interval: Optional[str] = Field(None, description="Interval for time-based aggregations")
    size: Optional[int] = Field(10, description="Number of buckets to return")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply before aggregation")
    query: Optional[str] = Field(None, description="Search query string")
    start_time: Optional[datetime] = Field(None, description="Start time for the aggregation")
    end_time: Optional[datetime] = Field(None, description="End time for the aggregation")


class LogAggregationResult(BaseModel):
    """Schema for log aggregation result."""
    field: str = Field(..., description="Field that was aggregated on")
    aggregation_type: str = Field(..., description="Type of aggregation that was performed")
    buckets: List[Dict[str, Any]] = Field(..., description="Aggregation buckets")
    total: int = Field(..., description="Total number of documents in the aggregation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class LogExportParams(BaseModel):
    """Schema for log export parameters."""
    query: Optional[str] = Field(None, description="Search query string")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply")
    start_time: Optional[datetime] = Field(None, description="Start time for the export")
    end_time: Optional[datetime] = Field(None, description="End time for the export")
    fields: Optional[List[str]] = Field(None, description="Fields to include in the export")
    format: str = Field("csv", description="Export format (csv, json, etc.)")
    max_results: Optional[int] = Field(10000, description="Maximum number of results to export")
    include_metadata: bool = Field(False, description="Whether to include metadata in the export")


class LogExportResponse(BaseModel):
    """Schema for log export response."""
    export_id: str = Field(..., description="ID of the export job")
    status: str = Field(..., description="Status of the export job")
    created_at: datetime = Field(..., description="Time when the export job was created")
    file_name: Optional[str] = Field(None, description="Name of the export file")
    file_size: Optional[int] = Field(None, description="Size of the export file in bytes")
    download_url: Optional[str] = Field(None, description="URL to download the export file")
    expires_at: Optional[datetime] = Field(None, description="Time when the download URL expires")
    record_count: Optional[int] = Field(None, description="Number of records in the export")
    parameters: LogExportParams = Field(..., description="Parameters used for the export")
