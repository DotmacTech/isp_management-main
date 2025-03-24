"""
Customer schemas for the CRM & Ticketing module.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator

from .common import ContactTypeEnum, ContactMethodEnum


class CustomerBase(BaseModel):
    """Base schema for customer data."""
    core_customer_id: int = Field(..., description="ID of the core customer record")
    satisfaction_score: Optional[int] = Field(None, ge=1, le=10, description="Customer satisfaction score (1-10)")
    lifetime_value: Optional[int] = Field(None, ge=0, description="Customer lifetime value in cents")
    acquisition_channel: Optional[str] = Field(None, description="Channel through which customer was acquired")
    acquisition_date: Optional[datetime] = Field(None, description="Date when customer was acquired")
    preferred_contact_method: Optional[ContactMethodEnum] = Field(None, description="Customer's preferred contact method")
    notes: Optional[str] = Field(None, description="General notes about the customer")
    tags: Optional[List[str]] = Field(None, description="Tags associated with the customer")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields for the customer")


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating an existing customer."""
    satisfaction_score: Optional[int] = Field(None, ge=1, le=10, description="Customer satisfaction score (1-10)")
    lifetime_value: Optional[int] = Field(None, ge=0, description="Customer lifetime value in cents")
    acquisition_channel: Optional[str] = Field(None, description="Channel through which customer was acquired")
    acquisition_date: Optional[datetime] = Field(None, description="Date when customer was acquired")
    preferred_contact_method: Optional[ContactMethodEnum] = Field(None, description="Customer's preferred contact method")
    notes: Optional[str] = Field(None, description="General notes about the customer")
    tags: Optional[List[str]] = Field(None, description="Tags associated with the customer")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields for the customer")


class CustomerResponse(CustomerBase):
    """Schema for customer response."""
    id: int
    created_at: datetime
    updated_at: datetime
    last_contact_date: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class CustomerContactBase(BaseModel):
    """Base schema for customer contact information."""
    contact_type: ContactTypeEnum
    contact_method: ContactMethodEnum
    name: str = Field(..., min_length=1, max_length=100, description="Name or label for the contact")
    value: str = Field(..., min_length=1, max_length=255, description="Contact value (email, phone, etc.)")
    is_primary: bool = Field(False, description="Whether this is the primary contact of its type")
    is_verified: bool = Field(False, description="Whether this contact has been verified")


class CustomerContactCreate(CustomerContactBase):
    """Schema for creating a new customer contact."""
    customer_id: int


class CustomerContactUpdate(BaseModel):
    """Schema for updating an existing customer contact."""
    contact_type: Optional[ContactTypeEnum] = None
    contact_method: Optional[ContactMethodEnum] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = Field(None, min_length=1, max_length=255)
    is_primary: Optional[bool] = None
    is_verified: Optional[bool] = None


class CustomerContactResponse(CustomerContactBase):
    """Schema for customer contact response."""
    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class CustomerNoteBase(BaseModel):
    """Base schema for customer notes."""
    title: str = Field(..., min_length=1, max_length=100, description="Note title")
    content: str = Field(..., description="Note content")
    is_private: bool = Field(False, description="Whether this note is private to staff")


class CustomerNoteCreate(CustomerNoteBase):
    """Schema for creating a new customer note."""
    customer_id: int


class CustomerNoteUpdate(BaseModel):
    """Schema for updating an existing customer note."""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = None
    is_private: Optional[bool] = None


class CustomerNoteResponse(CustomerNoteBase):
    """Schema for customer note response."""
    id: int
    customer_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
