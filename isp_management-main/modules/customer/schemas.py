"""
Pydantic schemas for the Customer Management Module.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict
import uuid

from modules.customer.models import (
    CustomerType,
    CustomerStatus,
    SubscriptionState,
    DocumentType,
    VerificationStatus,
    AddressType,
    ContactType,
    CommunicationType
)
from modules.customer.utils import validate_phone, is_valid_tax_id


# Base schemas
class BaseResponse(BaseModel):
    """Base response schema with common fields."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Customer schemas
class CustomerBase(BaseModel):
    """Base schema for customer data."""
    customer_type: CustomerType = Field(default=CustomerType.INDIVIDUAL, description="Type of customer")
    first_name: Optional[str] = Field(None, description="Customer first name (for individuals)")
    last_name: Optional[str] = Field(None, description="Customer last name (for individuals)")
    company_name: Optional[str] = Field(None, description="Company name (for businesses)")
    tax_id: Optional[str] = Field(None, description="Tax ID (for businesses)")
    registration_number: Optional[str] = Field(None, description="Business registration number")
    email: Optional[EmailStr] = Field(None, description="Primary customer email")
    phone: Optional[str] = Field(None, description="Primary customer phone number")
    mobile: Optional[str] = Field(None, description="Primary customer mobile number")
    username: Optional[str] = Field(None, description="Username for customer portal")
    portal_id: Optional[str] = Field(None, description="Portal ID for login and PPPoE authentication")
    marketing_consent: bool = Field(False, description="Whether customer consents to marketing")
    referral_source: Optional[str] = Field(None, description="How the customer was referred")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")
    contact_methods: Optional[List["ContactMethod"]] = Field(None, description="Additional contact methods")

    @field_validator('phone', 'mobile')
    @classmethod
    def validate_phone_numbers(cls, v):
        if v and not validate_phone(v):
            raise ValueError(f"Invalid phone number format: {v}")
        return v

    @field_validator('tax_id')
    @classmethod
    def validate_tax_id_format(cls, v, info):
        if v and info.data.get('customer_type') in [CustomerType.BUSINESS, CustomerType.GOVERNMENT]:
            if not is_valid_tax_id(v):
                raise ValueError(f"Invalid tax ID format: {v}")
        return v

    @model_validator(mode='after')
    def validate_customer_type_fields(cls, values):
        customer_type = values.customer_type
        if customer_type == CustomerType.INDIVIDUAL:
            if not values.first_name or not values.last_name:
                raise ValueError("First name and last name are required for individual customers")
        elif customer_type in [CustomerType.BUSINESS, CustomerType.GOVERNMENT, CustomerType.EDUCATIONAL, CustomerType.NON_PROFIT]:
            if not values.company_name:
                raise ValueError("Company name is required for business customers")
        return values


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""
    status: CustomerStatus = Field(default=CustomerStatus.PENDING, description="Customer status")
    subscription_state: SubscriptionState = Field(
        default=SubscriptionState.PENDING_ACTIVATION, 
        description="Subscription state"
    )
    password: Optional[str] = Field(None, description="Password for customer portal")


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    status: Optional[CustomerStatus] = None
    marketing_consent: Optional[bool] = None
    referral_source: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None

    @field_validator('phone', 'mobile')
    @classmethod
    def validate_phone_numbers(cls, v):
        if v and not validate_phone(v):
            raise ValueError(f"Invalid phone number format: {v}")
        return v


class CustomerResponse(BaseResponse):
    """Schema for customer response."""
    uuid: uuid.UUID
    customer_number: str
    customer_type: CustomerType
    status: CustomerStatus
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    mobile: Optional[str]
    username: Optional[str]
    portal_id: Optional[str]
    is_email_verified: bool
    email_verification_date: Optional[datetime]
    subscription_state: SubscriptionState
    subscription_start_date: Optional[datetime]
    subscription_end_date: Optional[datetime]
    marketing_consent: bool
    marketing_consent_date: Optional[datetime]
    referral_source: Optional[str]


class CustomerDetailResponse(CustomerResponse):
    """Schema for detailed customer response with related entities."""
    addresses: Optional[List["AddressResponse"]] = []
    contacts: Optional[List["ContactResponse"]] = []
    communication_preferences: Optional[List["CommunicationPreferenceResponse"]] = []
    documents: Optional[List["DocumentResponse"]] = []
    customer_notes: Optional[List["NoteResponse"]] = []
    tags: Optional[List["TagResponse"]] = []
    custom_fields: Optional[List["CustomFieldResponse"]] = []
    contact_methods: Optional[List["ContactMethod"]] = []


class CustomerListResponse(BaseModel):
    """Schema for paginated customer list response."""
    items: List[CustomerResponse]
    total: int
    skip: int
    limit: int


# Address schemas
class AddressBase(BaseModel):
    """Base schema for address data."""
    address_type: AddressType = Field(default=AddressType.BILLING, description="Type of address")
    street_address1: str = Field(..., description="Street address line 1")
    street_address2: Optional[str] = Field(None, description="Street address line 2")
    city: str = Field(..., description="City")
    state_province: Optional[str] = Field(None, description="State or province")
    postal_code: str = Field(..., description="Postal code")
    country: str = Field(..., description="Country")
    is_default: bool = Field(False, description="Whether this is the default address")
    latitude: Optional[float] = Field(None, description="Latitude for geolocation")
    longitude: Optional[float] = Field(None, description="Longitude for geolocation")


class AddressCreate(AddressBase):
    """Schema for creating an address."""
    pass


class AddressUpdate(BaseModel):
    """Schema for updating an address."""
    address_type: Optional[AddressType] = None
    street_address1: Optional[str] = None
    street_address2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None
    is_verified: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AddressResponse(BaseResponse, AddressBase):
    """Schema for address response."""
    is_verified: bool
    verification_date: Optional[datetime]


# Contact schemas
class ContactBase(BaseModel):
    """Base schema for contact data."""
    contact_type: ContactType = Field(default=ContactType.PRIMARY, description="Type of contact")
    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    position: Optional[str] = Field(None, description="Contact position")
    department: Optional[str] = Field(None, description="Contact department")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    mobile: Optional[str] = Field(None, description="Contact mobile")
    is_primary: bool = Field(False, description="Whether this is the primary contact")
    is_active: bool = Field(True, description="Whether this contact is active")

    @field_validator('phone', 'mobile')
    @classmethod
    def validate_phone_numbers(cls, v):
        if v and not validate_phone(v):
            raise ValueError(f"Invalid phone number format: {v}")
        return v


class ContactCreate(ContactBase):
    """Schema for creating a contact."""
    pass


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""
    contact_type: Optional[ContactType] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator('phone', 'mobile')
    @classmethod
    def validate_phone_numbers(cls, v):
        if v and not validate_phone(v):
            raise ValueError(f"Invalid phone number format: {v}")
        return v


class ContactResponse(BaseResponse, ContactBase):
    """Schema for contact response."""
    pass


# Communication preference schemas
class CommunicationPreferenceBase(BaseModel):
    """Base schema for communication preference data."""
    communication_type: CommunicationType = Field(..., description="Type of communication")
    enabled: bool = Field(True, description="Whether this communication type is enabled")
    billing_notifications: bool = Field(True, description="Whether to send billing notifications")
    service_notifications: bool = Field(True, description="Whether to send service notifications")
    marketing_communications: bool = Field(False, description="Whether to send marketing communications")
    technical_notifications: bool = Field(True, description="Whether to send technical notifications")
    emergency_alerts: bool = Field(True, description="Whether to send emergency alerts")


class CommunicationPreferenceCreate(CommunicationPreferenceBase):
    """Schema for creating a communication preference."""
    pass


class CommunicationPreferenceUpdate(BaseModel):
    """Schema for updating a communication preference."""
    enabled: Optional[bool] = None
    billing_notifications: Optional[bool] = None
    service_notifications: Optional[bool] = None
    marketing_communications: Optional[bool] = None
    technical_notifications: Optional[bool] = None
    emergency_alerts: Optional[bool] = None


class CommunicationPreferenceResponse(BaseResponse, CommunicationPreferenceBase):
    """Schema for communication preference response."""
    pass


# Document schemas
class DocumentBase(BaseModel):
    """Base schema for document data."""
    document_type: DocumentType = Field(..., description="Type of document")
    document_number: Optional[str] = Field(None, description="Document number (e.g., passport number)")
    document_name: str = Field(..., description="Name of document")
    issue_date: Optional[datetime] = Field(None, description="Date document was issued")
    expiry_date: Optional[datetime] = Field(None, description="Date document expires")


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    pass


class DocumentVerificationUpdate(BaseModel):
    """Schema for updating document verification status."""
    verification_status: VerificationStatus = Field(..., description="Verification status")
    verified_by: str = Field(..., description="Name of person who verified the document")
    verification_notes: Optional[str] = Field(None, description="Notes about verification")


class DocumentResponse(BaseResponse, DocumentBase):
    """Schema for document response."""
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    verification_status: VerificationStatus
    verified_by: Optional[str]
    verification_date: Optional[datetime]
    verification_notes: Optional[str]


# Note schemas
class NoteBase(BaseModel):
    """Base schema for note data."""
    title: Optional[str] = Field(None, description="Note title")
    content: str = Field(..., description="Note content")
    is_important: bool = Field(False, description="Whether the note is important")
    is_private: bool = Field(False, description="Whether the note is private")


class NoteCreate(NoteBase):
    """Schema for creating a note."""
    created_by: str = Field(..., description="Name of person who created the note")


class NoteUpdate(BaseModel):
    """Schema for updating a note."""
    title: Optional[str] = None
    content: Optional[str] = None
    is_important: Optional[bool] = None
    is_private: Optional[bool] = None


class NoteResponse(BaseResponse, NoteBase):
    """Schema for note response."""
    created_by: str


# Tag schemas
class TagBase(BaseModel):
    """Base schema for tag data."""
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field(None, description="Tag color (hex code)")
    auto_assign: bool = Field(False, description="Whether to automatically assign this tag")
    auto_assign_criteria: Optional[Dict[str, Any]] = Field(None, description="Criteria for auto-assignment")


class TagCreate(TagBase):
    """Schema for creating a tag."""
    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    auto_assign: Optional[bool] = None
    auto_assign_criteria: Optional[Dict[str, Any]] = None


class TagResponse(BaseResponse, TagBase):
    """Schema for tag response."""
    pass


# Custom field schemas
class CustomFieldBase(BaseModel):
    """Base schema for custom field data."""
    field_name: str = Field(..., description="Name of the custom field")
    field_type: str = Field(..., description="Type of the custom field (string, number, boolean, date, etc.)")
    field_value: Optional[str] = Field(None, description="Value of the custom field")
    is_searchable: bool = Field(True, description="Whether this field is searchable")
    is_api_visible: bool = Field(True, description="Whether this field is visible via API")
    description: Optional[str] = Field(None, description="Description of the custom field")


class CustomFieldCreate(CustomFieldBase):
    """Schema for creating a custom field."""
    pass


class CustomFieldUpdate(BaseModel):
    """Schema for updating a custom field."""
    field_name: Optional[str] = None
    field_type: Optional[str] = None
    field_value: Optional[str] = None
    is_searchable: Optional[bool] = None
    is_api_visible: Optional[bool] = None
    description: Optional[str] = None


class CustomFieldResponse(BaseResponse, CustomFieldBase):
    """Schema for custom field response."""
    pass


# Contact method schema
class ContactMethod(BaseModel):
    """Schema for contact method data."""
    type: str = Field(..., description="Type of contact method (email, phone, etc.)")
    value: str = Field(..., description="Contact method value")
    is_primary: bool = Field(False, description="Whether this is the primary contact method of its type")
    is_verified: bool = Field(False, description="Whether this contact method has been verified")
    verification_date: Optional[datetime] = Field(None, description="Date when the contact method was verified")


# Verification schemas
class EmailVerificationCreate(BaseModel):
    """Schema for creating an email verification."""
    email: Optional[EmailStr] = Field(None, description="Email to verify (if different from customer's email)")


class EmailVerificationResponse(BaseResponse):
    """Schema for email verification response."""
    email: str
    status: VerificationStatus
    expires_at: datetime
    verified_at: Optional[datetime]


class EmailVerificationResult(BaseModel):
    """Schema for email verification result."""
    success: bool
    message: str
    customer_id: Optional[int] = None


# Subscription schemas
class SubscriptionStateUpdate(BaseModel):
    """Schema for updating subscription state."""
    subscription_state: SubscriptionState = Field(..., description="New subscription state")
    update_dates: bool = Field(True, description="Whether to update subscription dates")


# Update forward references
CustomerDetailResponse.update_forward_refs()
