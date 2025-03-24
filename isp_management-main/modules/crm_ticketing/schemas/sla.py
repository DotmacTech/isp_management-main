"""
SLA (Service Level Agreement) schemas for the CRM & Ticketing module.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .common import TicketPriorityEnum, TicketTypeEnum


class SLABase(BaseModel):
    """Base schema for SLA data."""
    name: str = Field(..., min_length=1, max_length=100, description="SLA name")
    description: Optional[str] = Field(None, description="SLA description")
    is_default: Optional[bool] = Field(False, description="Whether this is the default SLA")
    is_active: Optional[bool] = Field(True, description="Whether this SLA is active")
    
    # SLA targets in minutes
    first_response_minutes: Dict[str, int] = Field(
        ..., 
        description="First response time targets in minutes by priority"
    )
    next_update_minutes: Dict[str, int] = Field(
        ..., 
        description="Update frequency targets in minutes by priority"
    )
    resolution_minutes: Dict[str, int] = Field(
        ..., 
        description="Resolution time targets in minutes by priority"
    )
    
    # Business hours
    business_hours_only: Optional[bool] = Field(True, description="Whether SLA applies only during business hours")
    business_hours_start: Optional[int] = Field(9, ge=0, le=23, description="Business hours start (24-hour format)")
    business_hours_end: Optional[int] = Field(17, ge=0, le=23, description="Business hours end (24-hour format)")
    business_days: Optional[List[int]] = Field([1, 2, 3, 4, 5], description="Business days (0=Sunday, 6=Saturday)")
    
    # Applicable ticket types
    applicable_ticket_types: Optional[List[TicketTypeEnum]] = Field(
        None, 
        description="Ticket types this SLA applies to"
    )
    
    @validator('first_response_minutes', 'next_update_minutes', 'resolution_minutes')
    def validate_sla_minutes(cls, v):
        """Validate that SLA minutes are provided for all priorities."""
        for priority in TicketPriorityEnum:
            if priority.value not in v:
                raise ValueError(f"Missing SLA target for priority: {priority.value}")
        return v
    
    @validator('business_days')
    def validate_business_days(cls, v):
        """Validate that business days are valid."""
        if v:
            for day in v:
                if day < 0 or day > 6:
                    raise ValueError(f"Invalid business day: {day}. Must be between 0 and 6.")
        return v


class SLACreate(SLABase):
    """Schema for creating a new SLA."""
    pass


class SLAUpdate(BaseModel):
    """Schema for updating an existing SLA."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    first_response_minutes: Optional[Dict[str, int]] = None
    next_update_minutes: Optional[Dict[str, int]] = None
    resolution_minutes: Optional[Dict[str, int]] = None
    business_hours_only: Optional[bool] = None
    business_hours_start: Optional[int] = Field(None, ge=0, le=23)
    business_hours_end: Optional[int] = Field(None, ge=0, le=23)
    business_days: Optional[List[int]] = None
    applicable_ticket_types: Optional[List[TicketTypeEnum]] = None


class SLAResponse(SLABase):
    """Schema for SLA response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class SLAMetricBase(BaseModel):
    """Base schema for SLA metrics."""
    period_start: datetime
    period_end: datetime
    total_tickets: int
    first_response_breaches: int
    update_breaches: int
    resolution_breaches: int
    first_response_compliance: float
    update_compliance: float
    resolution_compliance: float
    overall_compliance: float
    avg_first_response_time: Optional[float] = None
    avg_resolution_time: Optional[float] = None
    metrics_by_priority: Dict[str, Dict[str, Any]]


class SLAMetricResponse(SLAMetricBase):
    """Schema for SLA metric response."""
    id: int
    sla_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
