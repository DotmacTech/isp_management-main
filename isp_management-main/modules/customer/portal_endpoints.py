"""
API endpoints for customer portal access.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend_core.database import get_session
from backend_core.exceptions import NotFoundException, ValidationException
from backend_core.utils.hateoas import add_resource_links, add_collection_links
from modules.customer.auth_utils import get_current_active_customer
from modules.customer.models import (
    Customer, 
    CustomerAddress, 
    CustomerContactMethod, 
    CustomerCustomField,
    ContactMethodType
)
from modules.customer.schemas import (
    CustomerResponse,
    AddressResponse,
    ContactMethod,
    CustomFieldResponse
)

# Initialize router
router = APIRouter(
    prefix="/portal/me",
    tags=["customer-portal"],
)


# Exception handler
def handle_exceptions(func):
    """Decorator to handle common exceptions."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotFoundException as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return wrapper


@router.get("/", response_model=CustomerResponse)
@handle_exceptions
async def get_my_profile(
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """Get the current customer's profile."""
    # Get customer from database
    customer_result = await session.execute(
        select(Customer).where(Customer.id == current_customer["id"])
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException("Customer not found")
    
    # Convert to response model
    response = CustomerResponse.from_orm(customer).dict()
    
    # Add HATEOAS links
    response = add_resource_links(
        response,
        resource_id=customer.id,
        resource_type="customer",
        self_route=f"/customers/portal/me",
        parent_route="/customers"
    )
    
    return response


@router.get("/addresses", response_model=List[AddressResponse])
@handle_exceptions
async def get_my_addresses(
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """Get the current customer's addresses."""
    # Get addresses from database
    addresses_result = await session.execute(
        select(CustomerAddress).where(CustomerAddress.customer_id == current_customer["id"])
    )
    addresses = addresses_result.scalars().all()
    
    # Convert to response models
    response_items = []
    for address in addresses:
        item = AddressResponse.from_orm(address).dict()
        item = add_resource_links(
            item,
            resource_id=address.id,
            resource_type="address",
            self_route=f"/customers/portal/me/addresses/{address.id}",
            parent_route="/customers/portal/me"
        )
        response_items.append(item)
    
    # Add collection links
    response_items = add_collection_links(
        response_items,
        collection_route=f"/customers/portal/me/addresses",
        parent_route="/customers/portal/me"
    )
    
    return response_items


@router.get("/addresses/{address_id}", response_model=AddressResponse)
@handle_exceptions
async def get_my_address(
    address_id: int = Path(..., description="Address ID"),
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """Get a specific address for the current customer."""
    # Get address from database
    address_result = await session.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == current_customer["id"]
        )
    )
    address = address_result.scalars().first()
    
    if not address:
        raise NotFoundException(f"Address with ID {address_id} not found")
    
    # Convert to response model
    response = AddressResponse.from_orm(address).dict()
    
    # Add HATEOAS links
    response = add_resource_links(
        response,
        resource_id=address.id,
        resource_type="address",
        self_route=f"/customers/portal/me/addresses/{address.id}",
        parent_route="/customers/portal/me"
    )
    
    return response


@router.get("/contact-methods", response_model=List[ContactMethod])
@handle_exceptions
async def get_my_contact_methods(
    method_type: Optional[ContactMethodType] = Query(None, description="Filter by contact method type"),
    verified_only: bool = Query(False, description="Only return verified contact methods"),
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """Get all contact methods for the current customer."""
    # Build query
    query = select(CustomerContactMethod).where(CustomerContactMethod.customer_id == current_customer["id"])
    
    # Apply filters
    if method_type:
        query = query.where(CustomerContactMethod.method_type == method_type)
    
    if verified_only:
        query = query.where(CustomerContactMethod.is_verified == True)
    
    # Execute query
    result = await session.execute(query)
    contact_methods = result.scalars().all()
    
    # Convert to response models
    response_items = []
    for method in contact_methods:
        item = ContactMethod(
            type=method.method_type.value,
            value=method.value,
            is_primary=method.is_primary,
            is_verified=method.is_verified,
            verification_date=method.verification_date
        ).dict()
        
        item = add_resource_links(
            item,
            resource_id=method.id,
            resource_type="contact_method",
            self_route=f"/customers/portal/me/contact-methods/{method.id}",
            parent_route="/customers/portal/me"
        )
        response_items.append(item)
    
    # Add collection links
    response_items = add_collection_links(
        response_items,
        collection_route=f"/customers/portal/me/contact-methods",
        parent_route="/customers/portal/me"
    )
    
    return response_items


@router.get("/contact-methods/{method_id}", response_model=ContactMethod)
@handle_exceptions
async def get_my_contact_method(
    method_id: int = Path(..., description="Contact method ID"),
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """Get a specific contact method for the current customer."""
    # Get contact method from database
    method_result = await session.execute(
        select(CustomerContactMethod).where(
            CustomerContactMethod.id == method_id,
            CustomerContactMethod.customer_id == current_customer["id"]
        )
    )
    method = method_result.scalars().first()
    
    if not method:
        raise NotFoundException(f"Contact method with ID {method_id} not found")
    
    # Convert to response model
    response = ContactMethod(
        type=method.method_type.value,
        value=method.value,
        is_primary=method.is_primary,
        is_verified=method.is_verified,
        verification_date=method.verification_date
    ).dict()
    
    # Add HATEOAS links
    response = add_resource_links(
        response,
        resource_id=method.id,
        resource_type="contact_method",
        self_route=f"/customers/portal/me/contact-methods/{method.id}",
        parent_route="/customers/portal/me"
    )
    
    return response


@router.get("/custom-fields", response_model=List[CustomFieldResponse])
@handle_exceptions
async def get_my_custom_fields(
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """Get all API-visible custom fields for the current customer."""
    # Get custom fields from database
    fields_result = await session.execute(
        select(CustomerCustomField).where(
            CustomerCustomField.customer_id == current_customer["id"],
            CustomerCustomField.is_api_visible == True
        )
    )
    fields = fields_result.scalars().all()
    
    # Convert to response models
    response_items = []
    for field in fields:
        item = CustomFieldResponse.from_orm(field).dict()
        item = add_resource_links(
            item,
            resource_id=field.id,
            resource_type="custom_field",
            self_route=f"/customers/portal/me/custom-fields/{field.id}",
            parent_route="/customers/portal/me"
        )
        response_items.append(item)
    
    # Add collection links
    response_items = add_collection_links(
        response_items,
        collection_route=f"/customers/portal/me/custom-fields",
        parent_route="/customers/portal/me"
    )
    
    return response_items


@router.get("/custom-fields/{field_id}", response_model=CustomFieldResponse)
@handle_exceptions
async def get_my_custom_field(
    field_id: int = Path(..., description="Custom field ID"),
    session: AsyncSession = Depends(get_session),
    current_customer: Dict[str, Any] = Depends(get_current_active_customer)
):
    """Get a specific API-visible custom field for the current customer."""
    # Get custom field from database
    field_result = await session.execute(
        select(CustomerCustomField).where(
            CustomerCustomField.id == field_id,
            CustomerCustomField.customer_id == current_customer["id"],
            CustomerCustomField.is_api_visible == True
        )
    )
    field = field_result.scalars().first()
    
    if not field:
        raise NotFoundException(f"Custom field with ID {field_id} not found or not visible")
    
    # Convert to response model
    response = CustomFieldResponse.from_orm(field).dict()
    
    # Add HATEOAS links
    response = add_resource_links(
        response,
        resource_id=field.id,
        resource_type="custom_field",
        self_route=f"/customers/portal/me/custom-fields/{field.id}",
        parent_route="/customers/portal/me"
    )
    
    return response
