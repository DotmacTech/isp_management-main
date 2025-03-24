"""
Pydantic schemas for pagination.

This module defines Pydantic schemas for pagination, which are used for API
request and response validation.
"""

from typing import Generic, List, Optional, TypeVar, Dict, Any
from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    page: int = Field(1, description="Page number")
    size: int = Field(50, description="Number of items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_desc: bool = Field(False, description="Sort in descending order")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated responses."""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PaginationMetadata(BaseModel):
    """Schema for pagination metadata."""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")
