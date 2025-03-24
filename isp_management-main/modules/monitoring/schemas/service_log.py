"""
Pydantic schemas for service logs.

This module defines Pydantic schemas for service logs, which are used for
API request and response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Import shared models from monitoring_models
from modules.monitoring.models.monitoring_models import (
    ServiceLogBase, ServiceLogCreate, ServiceLogUpdate, 
    ServiceLogInDB, ServiceLogResponse, LogSearchParams, LogSearchResult
)


class ServiceLogList(BaseModel):
    """Schema for a list of service logs."""
    items: List[ServiceLogResponse]
    total: int
    page: int
    size: int
    pages: int
    model_config = {"from_attributes": True}


class ServiceLogFilter(BaseModel):
    """Schema for filtering service logs."""
    endpoint_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    status_code: Optional[str] = None
    elasticsearch_synced: Optional[bool] = None
    model_config = {"from_attributes": True}
