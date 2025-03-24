"""
Pydantic schemas for the Integration Management Module.

This module defines the Pydantic schemas for validating API requests and responses
related to integrations, their configurations, versions, and activity logs.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator, SecretStr, ConfigDict
import json

from ..models.integration import IntegrationStatus, IntegrationEnvironment, IntegrationType, ActivityType, ActivityStatus


# Base schemas
class IntegrationBase(BaseModel):
    """Base schema for integration data."""
    name: str = Field(..., min_length=1, max_length=255)
    type: IntegrationType
    description: Optional[str] = None
    environment: IntegrationEnvironment


class WebhookEndpointBase(BaseModel):
    """Base schema for webhook endpoint."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    path: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True

    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        # Add path validation logic here
        if not v.startswith('/'):
            v = '/' + v
        return v

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "name": "Sample Webhook",
                "description": "A sample webhook endpoint",
                "path": "/sample-webhook",
                "is_active": True
            }
        }
    )


# Request schemas
class IntegrationCreate(IntegrationBase):
    """Schema for creating a new integration."""
    configuration: Dict[str, Any] = Field(default_factory=dict)
    credentials: Dict[str, Any] = Field(...)
    
    @field_validator('credentials')
    @classmethod
    def validate_credentials(cls, v):
        """Ensure credentials are provided based on integration type."""
        if not v:
            raise ValueError("Credentials must be provided")
        return v


class IntegrationUpdate(BaseModel):
    """Schema for updating an existing integration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    status: Optional[IntegrationStatus] = None
    environment: Optional[IntegrationEnvironment] = None
    
    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "name": "Updated Integration",
                "description": "An updated integration",
                "status": "active"
            }
        }
    )


class WebhookEndpointCreate(BaseModel):
    """Schema for creating a webhook endpoint."""
    integration_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    path: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    secret_key: Optional[SecretStr] = None
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        # Add path validation logic here
        if not v.startswith('/'):
            v = '/' + v
        return v
    
    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "integration_id": 1,
                "name": "Sample Webhook",
                "description": "A sample webhook endpoint",
                "path": "/sample-webhook",
                "is_active": True
            }
        }
    )


class WebhookEndpointUpdate(BaseModel):
    """Schema for updating a webhook endpoint."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    path: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    secret_key: Optional[SecretStr] = None
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        if v is None:
            return v
        if not v.startswith('/'):
            v = '/' + v
        return v
    
    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "name": "Updated Webhook",
                "description": "An updated webhook endpoint",
                "path": "/updated-webhook",
                "is_active": False
            }
        }
    )


class WebhookEventCreate(BaseModel):
    """Schema for creating a new webhook event."""
    event_type: str
    payload: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None
    signature: Optional[str] = None
    ip_address: Optional[str] = None


# Response schemas
class IntegrationResponse(IntegrationBase):
    """Schema for integration response."""
    id: int
    status: IntegrationStatus
    configuration: Dict[str, Any]
    last_health_check: Optional[datetime] = None
    health_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class IntegrationDetailResponse(IntegrationResponse):
    """Schema for detailed integration response."""
    webhook_count: int
    activity_count: int
    version_count: int
    latest_version: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class IntegrationVersionResponse(BaseModel):
    """Schema for integration version response."""
    id: int
    integration_id: int
    version: str
    configuration: Dict[str, Any]
    active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class IntegrationActivityResponse(BaseModel):
    """Schema for integration activity response."""
    id: int
    integration_id: int
    activity_type: ActivityType
    status: ActivityStatus
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_id: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class WebhookEndpointResponse(BaseModel):
    """Schema for webhook endpoint response."""
    id: int
    integration_id: int
    name: str
    description: Optional[str] = None
    path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class WebhookEventResponse(BaseModel):
    """Schema for webhook event response."""
    id: int
    endpoint_id: int
    event_type: str
    payload: Dict[str, Any]
    status: ActivityStatus
    processing_attempts: int
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# List response schemas
class IntegrationListResponse(BaseModel):
    """Schema for list of integrations response."""
    items: List[IntegrationResponse]
    total: int
    skip: int
    limit: int


class IntegrationVersionListResponse(BaseModel):
    """Schema for list of integration versions response."""
    items: List[IntegrationVersionResponse]
    total: int
    skip: int
    limit: int


class IntegrationActivityListResponse(BaseModel):
    """Schema for list of integration activities response."""
    items: List[IntegrationActivityResponse]
    total: int
    skip: int
    limit: int


class WebhookEndpointListResponse(BaseModel):
    """Schema for list of webhook endpoints response."""
    items: List[WebhookEndpointResponse]
    total: int
    skip: int
    limit: int


class WebhookEventListResponse(BaseModel):
    """Schema for list of webhook events response."""
    items: List[WebhookEventResponse]
    total: int
    skip: int
    limit: int


# Status and credential schemas
class IntegrationStatusResponse(BaseModel):
    """Schema for integration status response."""
    status: IntegrationStatus
    last_health_check: Optional[datetime] = None
    health_status: Optional[str] = None
    connectivity: str = Field(..., description="healthy/degraded/failing")
    error_details: Optional[str] = None


class CredentialRotationResponse(BaseModel):
    """Schema for credential rotation response."""
    message: str
    new_credentials: Dict[str, Any]


class CredentialResponse(BaseModel):
    """Schema for credential response."""
    credentials: Dict[str, Any]


# Webhook processing schemas
class WebhookProcessingResponse(BaseModel):
    """Schema for webhook processing response."""
    status: str = "received"
    processing_id: str
