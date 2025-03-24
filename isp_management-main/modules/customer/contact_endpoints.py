"""
API endpoints for customer contacts.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import ContactType
from modules.customer.schemas import ContactCreate, ContactUpdate, ContactResponse

# Initialize router
router = APIRouter(
    prefix="/{customer_id}/contacts",
    tags=["customer-contacts"],
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


# Import services
from sqlalchemy import select, update, delete
from modules.customer.models import Customer, CustomerContact


# Contact endpoints
@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_contact(
    contact_data: ContactCreate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new contact for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # If this is set as primary, unset any existing primary of the same type
    if contact_data.is_primary:
        await session.execute(
            update(CustomerContact)
            .where(
                CustomerContact.customer_id == customer_id,
                CustomerContact.contact_type == contact_data.contact_type,
                CustomerContact.is_primary == True
            )
            .values(is_primary=False)
        )
    
    # Create contact
    contact = CustomerContact(
        customer_id=customer_id,
        **contact_data.dict()
    )
    
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    
    return ContactResponse.from_orm(contact)


@router.get("/", response_model=List[ContactResponse])
@handle_exceptions
async def get_customer_contacts(
    customer_id: int = Path(..., description="Customer ID"),
    contact_type: ContactType = Query(None, description="Filter by contact type"),
    active_only: bool = Query(True, description="Only return active contacts"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all contacts for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Build query
    query = select(CustomerContact).where(CustomerContact.customer_id == customer_id)
    
    # Apply filters
    if contact_type:
        query = query.where(CustomerContact.contact_type == contact_type)
    
    if active_only:
        query = query.where(CustomerContact.is_active == True)
    
    # Execute query
    result = await session.execute(query)
    contacts = result.scalars().all()
    
    return [ContactResponse.from_orm(contact) for contact in contacts]


@router.get("/{contact_id}", response_model=ContactResponse)
@handle_exceptions
async def get_contact(
    customer_id: int = Path(..., description="Customer ID"),
    contact_id: int = Path(..., description="Contact ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific contact for a customer."""
    # Check if contact exists and belongs to customer
    result = await session.execute(
        select(CustomerContact)
        .where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id
        )
    )
    contact = result.scalars().first()
    
    if not contact:
        raise NotFoundException(f"Contact with ID {contact_id} not found for customer {customer_id}")
    
    return ContactResponse.from_orm(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
@handle_exceptions
async def update_contact(
    contact_data: ContactUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    contact_id: int = Path(..., description="Contact ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Update a contact for a customer."""
    # Check if contact exists and belongs to customer
    result = await session.execute(
        select(CustomerContact)
        .where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id
        )
    )
    contact = result.scalars().first()
    
    if not contact:
        raise NotFoundException(f"Contact with ID {contact_id} not found for customer {customer_id}")
    
    # If setting as primary, unset any existing primary of the same type
    if contact_data.is_primary and contact_data.is_primary != contact.is_primary:
        if contact_data.contact_type:
            await session.execute(
                update(CustomerContact)
                .where(
                    CustomerContact.customer_id == customer_id,
                    CustomerContact.contact_type == contact_data.contact_type,
                    CustomerContact.id != contact_id,
                    CustomerContact.is_primary == True
                )
                .values(is_primary=False)
            )
        else:
            await session.execute(
                update(CustomerContact)
                .where(
                    CustomerContact.customer_id == customer_id,
                    CustomerContact.contact_type == contact.contact_type,
                    CustomerContact.id != contact_id,
                    CustomerContact.is_primary == True
                )
                .values(is_primary=False)
            )
    
    # Update contact
    for key, value in contact_data.dict(exclude_unset=True).items():
        setattr(contact, key, value)
    
    await session.commit()
    await session.refresh(contact)
    
    return ContactResponse.from_orm(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_contact(
    customer_id: int = Path(..., description="Customer ID"),
    contact_id: int = Path(..., description="Contact ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Delete a contact for a customer."""
    # Check if contact exists and belongs to customer
    result = await session.execute(
        select(CustomerContact)
        .where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id
        )
    )
    contact = result.scalars().first()
    
    if not contact:
        raise NotFoundException(f"Contact with ID {contact_id} not found for customer {customer_id}")
    
    # Delete contact
    await session.delete(contact)
    await session.commit()
    
    return None
