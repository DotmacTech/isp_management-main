"""
Base schemas for API responses with HATEOAS support.

This module provides standardized response schemas for all API endpoints,
implementing HATEOAS (Hypermedia as the Engine of Application State) to make
the API more discoverable and self-documenting.
"""

from typing import Dict, List, Optional, Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# Type variable for generic response models
T = TypeVar('T')


class Link(BaseModel):
    """Schema for HATEOAS link."""
    href: str = Field(..., description="URL of the linked resource")
    rel: str = Field(..., description="Relationship of the linked resource to the current resource")
    method: str = Field("GET", description="HTTP method to use with this link")
    title: Optional[str] = Field(None, description="Human-readable title for the link")


class BaseResponse(BaseModel):
    """Base response schema with common fields."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class HateoasResponse(BaseModel):
    """Base response schema with HATEOAS links."""
    links: Dict[str, Link] = Field(default_factory=dict, description="HATEOAS links", alias="_links")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema with HATEOAS links."""
    items: List[T]
    total: int
    skip: int
    limit: int
    links: Dict[str, Link] = Field(default_factory=dict, description="HATEOAS links", alias="_links")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DetailedErrorResponse(BaseModel):
    """Detailed error response schema with additional information."""
    status_code: int = Field(..., description="HTTP status code")
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time when the error occurred")
    path: Optional[str] = Field(None, description="Request path that caused the error")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status_code": 400,
                "error_type": "ValidationError",
                "message": "Invalid request data",
                "details": {
                    "name": "Field required",
                    "email": "Invalid email format"
                },
                "timestamp": "2023-01-01T00:00:00",
                "path": "/api/v1/customers"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    status_code: int = Field(..., description="HTTP status code")
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[List[DetailedErrorResponse]] = Field(None, description="Detailed validation errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time when the error occurred")
    path: Optional[str] = Field(None, description="Request path that caused the error")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status_code": 400,
                "error_type": "ValidationError",
                "message": "Invalid input data",
                "details": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "invalid_email"
                    }
                ],
                "timestamp": "2023-01-01T12:00:00Z",
                "path": "/api/v1/customers"
            }
        }
    )
