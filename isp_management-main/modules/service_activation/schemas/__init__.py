"""
Schemas for the service_activation module.

This package contains schemas for the service_activation module.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from modules.service_activation.models import ActivationStatus


class ServiceActivationBase(BaseModel):
    """Base schema for service activation."""
    customer_id: int = Field(..., description="ID of the customer")
    service_type: str = Field(..., description="Type of service to activate")
    plan_id: int = Field(..., description="ID of the plan")
    requested_activation_date: Optional[datetime] = Field(None, description="Requested activation date")
    notes: Optional[str] = Field(None, description="Additional notes")


class ServiceActivationCreate(ServiceActivationBase):
    """Schema for creating a new service activation request."""
    pass


class ServiceActivationResponse(ServiceActivationBase):
    """Schema for service activation response."""
    id: int = Field(..., description="Unique identifier")
    status: ActivationStatus = Field(..., description="Current status of activation")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    scheduled_date: Optional[datetime] = Field(None, description="Actual scheduled date")
    completed_date: Optional[datetime] = Field(None, description="Date when activation was completed")
    failure_reason: Optional[str] = Field(None, description="Reason for failure if applicable")
    assigned_to: Optional[int] = Field(None, description="ID of staff assigned to this activation")
    
    model_config = ConfigDict(from_attributes=True)


class ServiceActivationUpdate(BaseModel):
    """Schema for updating a service activation request."""
    status: Optional[ActivationStatus] = Field(None, description="New status")
    scheduled_date: Optional[datetime] = Field(None, description="Scheduled date")
    notes: Optional[str] = Field(None, description="Additional notes")
    assigned_to: Optional[int] = Field(None, description="ID of staff assigned to this activation")
    
    model_config = ConfigDict(from_attributes=True)


class ActivationTaskBase(BaseModel):
    """Base schema for activation tasks."""
    activation_id: int = Field(..., description="ID of the activation request")
    task_name: str = Field(..., description="Name of the task")
    description: Optional[str] = Field(None, description="Task description")
    is_mandatory: bool = Field(True, description="Whether the task is mandatory")
    dependency_task_ids: Optional[List[int]] = Field(None, description="IDs of tasks this depends on")


class ActivationTaskCreate(ActivationTaskBase):
    """Schema for creating a new activation task."""
    pass


class ActivationTaskResponse(ActivationTaskBase):
    """Schema for activation task response."""
    id: int = Field(..., description="Unique identifier")
    status: str = Field(..., description="Current status of the task")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    assigned_to: Optional[int] = Field(None, description="ID of staff assigned to this task")
    
    model_config = ConfigDict(from_attributes=True)


class ActivationStepBase(BaseModel):
    """Base schema for activation workflow steps."""
    activation_id: int = Field(..., description="ID of the activation request")
    step_name: str = Field(..., description="Name of the step")
    description: str = Field(..., description="Step description")
    order: int = Field(..., description="Order in the workflow sequence")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in minutes")
    is_automated: bool = Field(False, description="Whether the step is automated")


class ActivationStepCreate(ActivationStepBase):
    """Schema for creating a new activation workflow step."""
    pass


class ActivationStepResponse(ActivationStepBase):
    """Schema for activation step response."""
    id: int = Field(..., description="Unique identifier")
    status: str = Field(..., description="Current status of the step")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    assigned_to: Optional[int] = Field(None, description="ID of staff assigned to this step")
    actual_duration: Optional[int] = Field(None, description="Actual duration in minutes")
    
    model_config = ConfigDict(from_attributes=True)


class ActivationLogBase(BaseModel):
    """Base schema for activation logs."""
    activation_id: int = Field(..., description="ID of the activation request")
    log_type: str = Field(..., description="Type of log entry")
    message: str = Field(..., description="Log message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    user_id: Optional[int] = Field(None, description="ID of user who created the log")


class ActivationLogCreate(ActivationLogBase):
    """Schema for creating a new activation log entry."""
    pass


class ActivationLogResponse(ActivationLogBase):
    """Schema for activation log response."""
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    user_name: Optional[str] = Field(None, description="Name of the user who created the log")
    
    model_config = ConfigDict(from_attributes=True)


class PrerequisiteCheckResultStatus(str, Enum):
    """Enum for prerequisite check result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class PrerequisiteCheckResult(BaseModel):
    """Schema for prerequisite check results."""
    check_name: str = Field(..., description="Name of the prerequisite check")
    status: PrerequisiteCheckResultStatus = Field(..., description="Status of the check")
    message: str = Field(..., description="Result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    
    model_config = ConfigDict(from_attributes=True)
