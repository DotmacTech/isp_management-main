"""
API endpoints for customer addresses.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import AddressType
from modules.customer.schemas import AddressCreate, AddressUpdate, AddressResponse

# Initialize router
router = APIRouter(
    prefix="/{customer_id}/addresses",
    tags=["customer-addresses"],
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
from modules.customer.models import Customer, CustomerAddress


# Address endpoints
@router.post("/", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_address(
    address_data: AddressCreate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new address for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # If this is set as default, unset any existing default of the same type
    if address_data.is_default:
        await session.execute(
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.address_type == address_data.address_type,
                CustomerAddress.is_default == True
            )
            .values(is_default=False)
        )
    
    # Create address
    address = CustomerAddress(
        customer_id=customer_id,
        **address_data.dict()
    )
    
    session.add(address)
    await session.commit()
    await session.refresh(address)
    
    return AddressResponse.from_orm(address)


@router.get("/", response_model=List[AddressResponse])
@handle_exceptions
async def get_customer_addresses(
    customer_id: int = Path(..., description="Customer ID"),
    address_type: AddressType = Query(None, description="Filter by address type"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all addresses for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Build query
    query = select(CustomerAddress).where(CustomerAddress.customer_id == customer_id)
    
    # Apply filter
    if address_type:
        query = query.where(CustomerAddress.address_type == address_type)
    
    # Execute query
    result = await session.execute(query)
    addresses = result.scalars().all()
    
    return [AddressResponse.from_orm(address) for address in addresses]


@router.get("/{address_id}", response_model=AddressResponse)
@handle_exceptions
async def get_address(
    customer_id: int = Path(..., description="Customer ID"),
    address_id: int = Path(..., description="Address ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific address for a customer."""
    # Check if address exists and belongs to customer
    result = await session.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id
        )
    )
    address = result.scalars().first()
    
    if not address:
        raise NotFoundException(f"Address with ID {address_id} not found for customer {customer_id}")
    
    return AddressResponse.from_orm(address)


@router.put("/{address_id}", response_model=AddressResponse)
@handle_exceptions
async def update_address(
    address_data: AddressUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    address_id: int = Path(..., description="Address ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Update an address for a customer."""
    # Check if address exists and belongs to customer
    result = await session.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id
        )
    )
    address = result.scalars().first()
    
    if not address:
        raise NotFoundException(f"Address with ID {address_id} not found for customer {customer_id}")
    
    # If setting as default, unset any existing default of the same type
    if address_data.is_default and address_data.address_type:
        await session.execute(
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.address_type == address_data.address_type,
                CustomerAddress.id != address_id,
                CustomerAddress.is_default == True
            )
            .values(is_default=False)
        )
    elif address_data.is_default and not address_data.address_type:
        await session.execute(
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.address_type == address.address_type,
                CustomerAddress.id != address_id,
                CustomerAddress.is_default == True
            )
            .values(is_default=False)
        )
    
    # Update address
    for key, value in address_data.dict(exclude_unset=True).items():
        setattr(address, key, value)
    
    await session.commit()
    await session.refresh(address)
    
    return AddressResponse.from_orm(address)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_address(
    customer_id: int = Path(..., description="Customer ID"),
    address_id: int = Path(..., description="Address ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Delete an address for a customer."""
    # Check if address exists and belongs to customer
    result = await session.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id
        )
    )
    address = result.scalars().first()
    
    if not address:
        raise NotFoundException(f"Address with ID {address_id} not found for customer {customer_id}")
    
    # Delete address
    await session.delete(address)
    await session.commit()
    
    return None


@router.post("/{address_id}/verify", response_model=AddressResponse)
@handle_exceptions
async def verify_address(
    customer_id: int = Path(..., description="Customer ID"),
    address_id: int = Path(..., description="Address ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Mark an address as verified."""
    # Check if address exists and belongs to customer
    result = await session.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id
        )
    )
    address = result.scalars().first()
    
    if not address:
        raise NotFoundException(f"Address with ID {address_id} not found for customer {customer_id}")
    
    # Update verification status
    from datetime import datetime
    address.is_verified = True
    address.verification_date = datetime.utcnow()
    
    await session.commit()
    await session.refresh(address)
    
    return AddressResponse.from_orm(address)
