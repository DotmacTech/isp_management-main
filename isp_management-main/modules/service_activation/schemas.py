"""
Pydantic schemas for the Service Activation Module.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum

from modules.service_activation.models import ActivationStatus, StepStatus


class ServiceActivationBase(BaseModel):
    """Base schema for service activation."""
    customer_id: int
    service_id: int
    tariff_id: int
    metadata: Optional[Dict[str, Any]] = None


class ServiceActivationCreate(ServiceActivationBase):
    """Schema for creating a new service activation."""
    pass


class ServiceActivationUpdate(BaseModel):
    """Schema for updating a service activation."""
    status: Optional[ActivationStatus] = None
    payment_verified: Optional[bool] = None
    prerequisites_checked: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ActivationStepBase(BaseModel):
    """Base schema for activation steps."""
    step_name: str
    step_order: int
    description: Optional[str] = None
    max_retries: int = 3
    is_rollback_step: bool = False
    depends_on_step_id: Optional[int] = None


class ActivationStepCreate(ActivationStepBase):
    """Schema for creating a new activation step."""
    activation_id: int


class ActivationStepUpdate(BaseModel):
    """Schema for updating an activation step."""
    status: Optional[StepStatus] = None
    description: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    max_retries: Optional[int] = None


class ActivationLogBase(BaseModel):
    """Base schema for activation logs."""
    level: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ActivationLogCreate(ActivationLogBase):
    """Schema for creating a new activation log."""
    activation_id: int
    step_id: Optional[int] = None


class ActivationStepResponse(ActivationStepBase):
    """Schema for activation step response."""
    id: int
    activation_id: int
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ActivationLogResponse(ActivationLogBase):
    """Schema for activation log response."""
    id: int
    activation_id: int
    step_id: Optional[int] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ServiceActivationResponse(ServiceActivationBase):
    """Schema for service activation response."""
    id: int
    status: ActivationStatus
    payment_verified: bool
    prerequisites_checked: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    steps: List[ActivationStepResponse] = []
    logs: List[ActivationLogResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkflowDefinition(BaseModel):
    """Schema for defining a workflow."""
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]
    rollback_steps: Optional[List[Dict[str, Any]]] = None


class PrerequisiteCheckResult(BaseModel):
    """Schema for prerequisite check results."""
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
