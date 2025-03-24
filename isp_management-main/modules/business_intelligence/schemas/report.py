"""
Pydantic schemas for the Business Intelligence and Reporting module.

This module provides the schemas for validating and serializing data related to
report templates, scheduled reports, and report executions.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, validator, root_validator

from ..models.report import (
    ReportType, ReportFormat, ReportFrequency, DeliveryMethod, ReportStatus
)


class DataSourceBase(BaseModel):
    """Base schema for data source operations."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    source_type: str = Field(..., min_length=1, max_length=50)
    connection_details: Dict[str, Any] = Field(...)
    is_active: bool = True


class DataSourceCreate(DataSourceBase):
    """Schema for creating a new data source."""
    pass


class DataSourceUpdate(BaseModel):
    """Schema for updating an existing data source."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    connection_details: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DataSourceResponse(DataSourceBase):
    """Schema for data source responses."""
    id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ReportTemplateBase(BaseModel):
    """Base schema for report template operations."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    report_type: ReportType
    template_data: Dict[str, Any] = Field(...)
    query_definition: Dict[str, Any] = Field(...)
    parameters_schema: Optional[Dict[str, Any]] = None
    is_system: bool = False


class ReportTemplateCreate(ReportTemplateBase):
    """Schema for creating a new report template."""
    data_source_ids: List[int] = Field(default_factory=list)


class ReportTemplateUpdate(BaseModel):
    """Schema for updating an existing report template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    query_definition: Optional[Dict[str, Any]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    data_source_ids: Optional[List[int]] = None


class ReportTemplateResponse(ReportTemplateBase):
    """Schema for report template responses."""
    id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    data_sources: List[DataSourceResponse] = Field(default_factory=list)

    class Config:
        orm_mode = True


class ScheduledReportBase(BaseModel):
    """Base schema for scheduled report operations."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    template_id: int
    frequency: ReportFrequency
    cron_expression: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    delivery_method: DeliveryMethod
    delivery_config: Dict[str, Any] = Field(...)
    is_active: bool = True

    @validator('cron_expression')
    def validate_cron_expression(cls, v, values):
        """Validate that cron_expression is provided for custom frequency."""
        if values.get('frequency') == ReportFrequency.CUSTOM and not v:
            raise ValueError('Cron expression is required for custom frequency')
        return v


class ScheduledReportCreate(ScheduledReportBase):
    """Schema for creating a new scheduled report."""
    pass


class ScheduledReportUpdate(BaseModel):
    """Schema for updating an existing scheduled report."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    frequency: Optional[ReportFrequency] = None
    cron_expression: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    delivery_method: Optional[DeliveryMethod] = None
    delivery_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @validator('cron_expression')
    def validate_cron_expression(cls, v, values):
        """Validate that cron_expression is provided for custom frequency."""
        if values.get('frequency') == ReportFrequency.CUSTOM and v is None:
            raise ValueError('Cron expression is required for custom frequency')
        return v


class ScheduledReportResponse(ScheduledReportBase):
    """Schema for scheduled report responses."""
    id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    last_execution_time: Optional[datetime] = None
    next_execution_time: Optional[datetime] = None
    template: ReportTemplateResponse

    class Config:
        orm_mode = True


class ReportExecutionBase(BaseModel):
    """Base schema for report execution operations."""
    template_id: int
    scheduled_report_id: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    formats: List[ReportFormat] = Field(...)


class ReportExecutionCreate(ReportExecutionBase):
    """Schema for creating a new report execution."""
    pass


class ReportOutputResponse(BaseModel):
    """Schema for report output responses."""
    id: int
    format: ReportFormat
    file_path: str
    file_size: int
    created_at: datetime

    class Config:
        orm_mode = True


class ReportExecutionResponse(ReportExecutionBase):
    """Schema for report execution responses."""
    id: int
    status: ReportStatus
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    requested_by_id: int
    outputs: List[ReportOutputResponse] = Field(default_factory=list)
    template: ReportTemplateResponse

    class Config:
        orm_mode = True


class ReportAccessLogCreate(BaseModel):
    """Schema for creating a new report access log."""
    execution_id: int
    action: str = Field(..., min_length=1, max_length=50)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ReportAccessLogResponse(ReportAccessLogCreate):
    """Schema for report access log responses."""
    id: int
    user_id: int
    access_time: datetime

    class Config:
        orm_mode = True


class ReportParameter(BaseModel):
    """Schema for report parameters."""
    name: str
    value: Any


class GenerateReportRequest(BaseModel):
    """Schema for generating a report."""
    template_id: int
    parameters: Optional[List[ReportParameter]] = None
    formats: List[ReportFormat] = Field(default_factory=lambda: [ReportFormat.PDF])


class ReportSearchParams(BaseModel):
    """Schema for searching reports."""
    name: Optional[str] = None
    report_type: Optional[ReportType] = None
    created_by_id: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class ScheduledReportSearchParams(BaseModel):
    """Schema for searching scheduled reports."""
    name: Optional[str] = None
    template_id: Optional[int] = None
    frequency: Optional[ReportFrequency] = None
    is_active: Optional[bool] = None
    created_by_id: Optional[int] = None


class ReportExecutionSearchParams(BaseModel):
    """Schema for searching report executions."""
    template_id: Optional[int] = None
    scheduled_report_id: Optional[int] = None
    status: Optional[ReportStatus] = None
    requested_by_id: Optional[int] = None
    started_after: Optional[datetime] = None
    started_before: Optional[datetime] = None


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Schema for paginated responses."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
