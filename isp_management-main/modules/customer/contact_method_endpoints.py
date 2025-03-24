"""
API endpoints for customer contact methods.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from backend_core.utils.hateoas import add_resource_links, add_collection_links
from modules.customer.models import Customer, CustomerContactMethod, ContactMethodType
from modules.customer.schemas import ContactMethod
from sqlalchemy import select, update, delete

# Initialize router
router = APIRouter(
    prefix="/{customer_id}/contact-methods",
    tags=["customer-contact-methods"],
)

# Role checkers
allow_admin = RoleChecker(["admin"])
allow_customer_manager = RoleChecker(["admin", "customer_manager"])
allow_customer_agent = RoleChecker(["admin", "customer_manager", "customer_agent"])


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


@router.post("/", response_model=ContactMethod, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_contact_method(
    contact_data: ContactMethod,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new contact method for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Check if this contact method already exists
    existing_method = await session.execute(
        select(CustomerContactMethod).where(
            CustomerContactMethod.customer_id == customer_id,
            CustomerContactMethod.method_type == contact_data.type,
            CustomerContactMethod.value == contact_data.value
        )
    )
    
    if existing_method.scalars().first():
        raise ValidationException(f"Contact method of type '{contact_data.type}' with value '{contact_data.value}' already exists for this customer")
    
    # If this is set as primary, unset any existing primary of the same type
    if contact_data.is_primary:
        await session.execute(
            update(CustomerContactMethod)
            .where(
                CustomerContactMethod.customer_id == customer_id,
                CustomerContactMethod.method_type == contact_data.type,
                CustomerContactMethod.is_primary == True
            )
            .values(is_primary=False)
        )
    
    # Create contact method
    contact_method = CustomerContactMethod(
        customer_id=customer_id,
        method_type=contact_data.type,
        value=contact_data.value,
        is_primary=contact_data.is_primary,
        is_verified=contact_data.is_verified,
        verification_date=contact_data.verification_date
    )
    
    session.add(contact_method)
    await session.commit()
    await session.refresh(contact_method)
    
    # Convert to response model
    response = ContactMethod(
        type=contact_method.method_type.value,
        value=contact_method.value,
        is_primary=contact_method.is_primary,
        is_verified=contact_method.is_verified,
        verification_date=contact_method.verification_date
    )
    
    # Add HATEOAS links
    response_dict = response.dict()
    response_dict = add_resource_links(
        response_dict,
        resource_id=contact_method.id,
        resource_type="contact_method",
        self_route=f"/customers/{customer_id}/contact-methods/{contact_method.id}",
        parent_route=f"/customers/{customer_id}"
    )
    
    return response_dict


@router.get("/", response_model=List[ContactMethod])
@handle_exceptions
async def get_contact_methods(
    customer_id: int = Path(..., description="Customer ID"),
    method_type: Optional[ContactMethodType] = Query(None, description="Filter by contact method type"),
    verified_only: bool = Query(False, description="Only return verified contact methods"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all contact methods for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Build query
    query = select(CustomerContactMethod).where(CustomerContactMethod.customer_id == customer_id)
    
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
        )
        item_dict = item.dict()
        item_dict = add_resource_links(
            item_dict,
            resource_id=method.id,
            resource_type="contact_method",
            self_route=f"/customers/{customer_id}/contact-methods/{method.id}",
            parent_route=f"/customers/{customer_id}"
        )
        response_items.append(item_dict)
    
    # Add collection links
    response_items = add_collection_links(
        response_items,
        collection_route=f"/customers/{customer_id}/contact-methods",
        parent_route=f"/customers/{customer_id}"
    )
    
    return response_items


@router.get("/{method_id}", response_model=ContactMethod)
@handle_exceptions
async def get_contact_method(
    customer_id: int = Path(..., description="Customer ID"),
    method_id: int = Path(..., description="Contact method ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific contact method for a customer."""
    # Check if method exists and belongs to customer
    result = await session.execute(
        select(CustomerContactMethod)
        .where(
            CustomerContactMethod.id == method_id,
            CustomerContactMethod.customer_id == customer_id
        )
    )
    contact_method = result.scalars().first()
    
    if not contact_method:
        raise NotFoundException(f"Contact method with ID {method_id} not found for customer {customer_id}")
    
    # Convert to response model
    response = ContactMethod(
        type=contact_method.method_type.value,
        value=contact_method.value,
        is_primary=contact_method.is_primary,
        is_verified=contact_method.is_verified,
        verification_date=contact_method.verification_date
    )
    
    # Add HATEOAS links
    response_dict = response.dict()
    response_dict = add_resource_links(
        response_dict,
        resource_id=contact_method.id,
        resource_type="contact_method",
        self_route=f"/customers/{customer_id}/contact-methods/{method_id}",
        parent_route=f"/customers/{customer_id}"
    )
    
    return response_dict


@router.put("/{method_id}", response_model=ContactMethod)
@handle_exceptions
async def update_contact_method(
    contact_data: ContactMethod,
    customer_id: int = Path(..., description="Customer ID"),
    method_id: int = Path(..., description="Contact method ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Update a contact method for a customer."""
    # Check if method exists and belongs to customer
    result = await session.execute(
        select(CustomerContactMethod)
        .where(
            CustomerContactMethod.id == method_id,
            CustomerContactMethod.customer_id == customer_id
        )
    )
    contact_method = result.scalars().first()
    
    if not contact_method:
        raise NotFoundException(f"Contact method with ID {method_id} not found for customer {customer_id}")
    
    # Check if updating to a value that already exists
    if contact_data.value != contact_method.value or contact_data.type != contact_method.method_type.value:
        existing_method = await session.execute(
            select(CustomerContactMethod).where(
                CustomerContactMethod.customer_id == customer_id,
                CustomerContactMethod.method_type == contact_data.type,
                CustomerContactMethod.value == contact_data.value,
                CustomerContactMethod.id != method_id
            )
        )
        
        if existing_method.scalars().first():
            raise ValidationException(f"Contact method of type '{contact_data.type}' with value '{contact_data.value}' already exists for this customer")
    
    # If setting as primary, unset any existing primary of the same type
    if contact_data.is_primary and not contact_method.is_primary:
        await session.execute(
            update(CustomerContactMethod)
            .where(
                CustomerContactMethod.customer_id == customer_id,
                CustomerContactMethod.method_type == contact_data.type,
                CustomerContactMethod.id != method_id,
                CustomerContactMethod.is_primary == True
            )
            .values(is_primary=False)
        )
    
    # Update method with provided data
    contact_method.method_type = contact_data.type
    contact_method.value = contact_data.value
    contact_method.is_primary = contact_data.is_primary
    contact_method.is_verified = contact_data.is_verified
    
    # Only update verification date if verification status changed
    if contact_data.is_verified and not contact_method.is_verified:
        contact_method.verification_date = datetime.utcnow()
    elif not contact_data.is_verified:
        contact_method.verification_date = None
    
    await session.commit()
    await session.refresh(contact_method)
    
    # Convert to response model
    response = ContactMethod(
        type=contact_method.method_type.value,
        value=contact_method.value,
        is_primary=contact_method.is_primary,
        is_verified=contact_method.is_verified,
        verification_date=contact_method.verification_date
    )
    
    # Add HATEOAS links
    response_dict = response.dict()
    response_dict = add_resource_links(
        response_dict,
        resource_id=contact_method.id,
        resource_type="contact_method",
        self_route=f"/customers/{customer_id}/contact-methods/{method_id}",
        parent_route=f"/customers/{customer_id}"
    )
    
    return response_dict


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_contact_method(
    customer_id: int = Path(..., description="Customer ID"),
    method_id: int = Path(..., description="Contact method ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Delete a contact method for a customer."""
    # Check if method exists and belongs to customer
    result = await session.execute(
        select(CustomerContactMethod)
        .where(
            CustomerContactMethod.id == method_id,
            CustomerContactMethod.customer_id == customer_id
        )
    )
    contact_method = result.scalars().first()
    
    if not contact_method:
        raise NotFoundException(f"Contact method with ID {method_id} not found for customer {customer_id}")
    
    # Delete the method
    await session.execute(
        delete(CustomerContactMethod)
        .where(
            CustomerContactMethod.id == method_id
        )
    )
    
    await session.commit()
    
    return None


@router.post("/{method_id}/verify", response_model=ContactMethod)
@handle_exceptions
async def verify_contact_method(
    customer_id: int = Path(..., description="Customer ID"),
    method_id: int = Path(..., description="Contact method ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Mark a contact method as verified."""
    # Check if method exists and belongs to customer
    result = await session.execute(
        select(CustomerContactMethod)
        .where(
            CustomerContactMethod.id == method_id,
            CustomerContactMethod.customer_id == customer_id
        )
    )
    contact_method = result.scalars().first()
    
    if not contact_method:
        raise NotFoundException(f"Contact method with ID {method_id} not found for customer {customer_id}")
    
    # Update verification status
    contact_method.is_verified = True
    contact_method.verification_date = datetime.utcnow()
    
    await session.commit()
    await session.refresh(contact_method)
    
    # Convert to response model
    response = ContactMethod(
        type=contact_method.method_type.value,
        value=contact_method.value,
        is_primary=contact_method.is_primary,
        is_verified=contact_method.is_verified,
        verification_date=contact_method.verification_date
    )
    
    # Add HATEOAS links
    response_dict = response.dict()
    response_dict = add_resource_links(
        response_dict,
        resource_id=contact_method.id,
        resource_type="contact_method",
        self_route=f"/customers/{customer_id}/contact-methods/{method_id}",
        parent_route=f"/customers/{customer_id}"
    )
    
    return response_dict
