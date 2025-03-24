"""
Pydantic schemas for alert searching.

This module defines Pydantic schemas for alert search parameters and results,
which are used for API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from pydantic import BaseModel, Field

from modules.monitoring.schemas.alert import AlertSeverityEnum, AlertStatusEnum, AlertTypeEnum


class SortOrderEnum(str, Enum):
    """Enum for sort order."""
    ASC = "asc"
    DESC = "desc"


class AlertSearchParams(BaseModel):
    """Schema for alert search parameters."""
    query: Optional[str] = Field(None, description="Search query string")
    alert_type: Optional[AlertTypeEnum] = Field(None, description="Filter by alert type")
    severity: Optional[AlertSeverityEnum] = Field(None, description="Filter by alert severity")
    status: Optional[AlertStatusEnum] = Field(None, description="Filter by alert status")
    start_time: Optional[datetime] = Field(None, description="Start time for the search")
    end_time: Optional[datetime] = Field(None, description="End time for the search")
    source: Optional[str] = Field(None, description="Filter by alert source")
    entity_id: Optional[str] = Field(None, description="Filter by entity ID")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    acknowledged: Optional[bool] = Field(None, description="Filter by acknowledged status")
    resolved: Optional[bool] = Field(None, description="Filter by resolved status")
    assigned_to: Optional[str] = Field(None, description="Filter by assignee")
    fields: Optional[List[str]] = Field(None, description="Fields to include in the response")
    exclude_fields: Optional[List[str]] = Field(None, description="Fields to exclude from the response")
    page: int = Field(1, description="Page number")
    size: int = Field(50, description="Number of items per page")
    sort_by: Optional[str] = Field("created_at", description="Field to sort by")
    sort_order: SortOrderEnum = Field(SortOrderEnum.DESC, description="Sort order")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class AlertSearchResult(BaseModel):
    """Schema for a single alert search result."""
    id: str = Field(..., description="ID of the alert")
    name: str = Field(..., description="Name of the alert")
    description: Optional[str] = Field(None, description="Description of the alert")
    alert_type: AlertTypeEnum = Field(..., description="Type of the alert")
    severity: AlertSeverityEnum = Field(..., description="Severity of the alert")
    status: AlertStatusEnum = Field(..., description="Status of the alert")
    created_at: datetime = Field(..., description="Time when the alert was created")
    updated_at: datetime = Field(..., description="Time when the alert was last updated")
    source: str = Field(..., description="Source of the alert")
    entity_id: Optional[str] = Field(None, description="ID of the entity associated with the alert")
    entity_type: Optional[str] = Field(None, description="Type of the entity associated with the alert")
    acknowledged: bool = Field(False, description="Whether the alert has been acknowledged")
    resolved: bool = Field(False, description="Whether the alert has been resolved")
    resolved_at: Optional[datetime] = Field(None, description="Time when the alert was resolved")
    assigned_to: Optional[str] = Field(None, description="ID of the user the alert is assigned to")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AlertSearchResponse(BaseModel):
    """Schema for alert search response."""
    items: List[AlertSearchResult] = Field(..., description="List of alert search results")
    total: int = Field(..., description="Total number of alerts matching the search criteria")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    query: Optional[str] = Field(None, description="Search query string")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregation results")


class AlertAggregationParams(BaseModel):
    """Schema for alert aggregation parameters."""
    field: str = Field(..., description="Field to aggregate on")
    aggregation_type: str = Field(..., description="Type of aggregation")
    interval: Optional[str] = Field(None, description="Interval for time-based aggregations")
    size: Optional[int] = Field(10, description="Number of buckets to return")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply before aggregation")
    query: Optional[str] = Field(None, description="Search query string")
    start_time: Optional[datetime] = Field(None, description="Start time for the aggregation")
    end_time: Optional[datetime] = Field(None, description="End time for the aggregation")


class AlertAggregationResult(BaseModel):
    """Schema for alert aggregation result."""
    field: str = Field(..., description="Field that was aggregated on")
    aggregation_type: str = Field(..., description="Type of aggregation that was performed")
    buckets: List[Dict[str, Any]] = Field(..., description="Aggregation buckets")
    total: int = Field(..., description="Total number of documents in the aggregation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AlertExportParams(BaseModel):
    """Schema for alert export parameters."""
    query: Optional[str] = Field(None, description="Search query string")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply")
    start_time: Optional[datetime] = Field(None, description="Start time for the export")
    end_time: Optional[datetime] = Field(None, description="End time for the export")
    fields: Optional[List[str]] = Field(None, description="Fields to include in the export")
    format: str = Field("csv", description="Export format (csv, json, etc.)")
    max_results: Optional[int] = Field(10000, description="Maximum number of results to export")
    include_metadata: bool = Field(False, description="Whether to include metadata in the export")


class AlertExportResponse(BaseModel):
    """Schema for alert export response."""
    export_id: str = Field(..., description="ID of the export job")
    status: str = Field(..., description="Status of the export job")
    created_at: datetime = Field(..., description="Time when the export job was created")
    file_name: Optional[str] = Field(None, description="Name of the export file")
    file_size: Optional[int] = Field(None, description="Size of the export file in bytes")
    download_url: Optional[str] = Field(None, description="URL to download the export file")
    expires_at: Optional[datetime] = Field(None, description="Time when the download URL expires")
    record_count: Optional[int] = Field(None, description="Number of records in the export")
    parameters: AlertExportParams = Field(..., description="Parameters used for the export")
