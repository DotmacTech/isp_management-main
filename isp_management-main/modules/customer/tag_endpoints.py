"""
API endpoints for customer tags.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import Customer, CustomerTagDefinition, customer_tags
from modules.customer.schemas import TagCreate, TagUpdate, TagResponse

# Initialize router
router = APIRouter(
    tags=["customer-tags"],
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


# Tag endpoints
@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_tag(
    tag_data: TagCreate,
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Create a new tag."""
    # Check if tag with the same name already exists
    result = await session.execute(
        select(CustomerTagDefinition).where(CustomerTagDefinition.name == tag_data.name)
    )
    existing_tag = result.scalars().first()
    
    if existing_tag:
        raise ValidationException(f"Tag with name '{tag_data.name}' already exists")
    
    # Create tag
    tag = CustomerTagDefinition(**tag_data.dict())
    
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    
    return TagResponse.from_orm(tag)


@router.get("/tags", response_model=List[TagResponse])
@handle_exceptions
async def get_tags(
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all tags."""
    result = await session.execute(select(CustomerTagDefinition))
    tags = result.scalars().all()
    
    return [TagResponse.from_orm(tag) for tag in tags]


@router.get("/tags/{tag_id}", response_model=TagResponse)
@handle_exceptions
async def get_tag(
    tag_id: int = Path(..., description="Tag ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific tag."""
    result = await session.execute(
        select(CustomerTagDefinition).where(CustomerTagDefinition.id == tag_id)
    )
    tag = result.scalars().first()
    
    if not tag:
        raise NotFoundException(f"Tag with ID {tag_id} not found")
    
    return TagResponse.from_orm(tag)


@router.put("/tags/{tag_id}", response_model=TagResponse)
@handle_exceptions
async def update_tag(
    tag_data: TagUpdate,
    tag_id: int = Path(..., description="Tag ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Update a tag."""
    # Check if tag exists
    result = await session.execute(
        select(CustomerTagDefinition).where(CustomerTagDefinition.id == tag_id)
    )
    tag = result.scalars().first()
    
    if not tag:
        raise NotFoundException(f"Tag with ID {tag_id} not found")
    
    # If name is being updated, check for conflicts
    if tag_data.name and tag_data.name != tag.name:
        name_check = await session.execute(
            select(CustomerTagDefinition).where(CustomerTagDefinition.name == tag_data.name)
        )
        existing_tag = name_check.scalars().first()
        
        if existing_tag:
            raise ValidationException(f"Tag with name '{tag_data.name}' already exists")
    
    # Update tag
    for key, value in tag_data.dict(exclude_unset=True).items():
        setattr(tag, key, value)
    
    await session.commit()
    await session.refresh(tag)
    
    return TagResponse.from_orm(tag)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_tag(
    tag_id: int = Path(..., description="Tag ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Delete a tag."""
    # Check if tag exists
    result = await session.execute(
        select(CustomerTagDefinition).where(CustomerTagDefinition.id == tag_id)
    )
    tag = result.scalars().first()
    
    if not tag:
        raise NotFoundException(f"Tag with ID {tag_id} not found")
    
    # Delete tag
    await session.delete(tag)
    await session.commit()
    
    return None


# Customer tag association endpoints
@router.post("/{customer_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def add_tag_to_customer(
    customer_id: int = Path(..., description="Customer ID"),
    tag_id: int = Path(..., description="Tag ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Add a tag to a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Check if tag exists
    tag_result = await session.execute(
        select(CustomerTagDefinition).where(CustomerTagDefinition.id == tag_id)
    )
    tag = tag_result.scalars().first()
    
    if not tag:
        raise NotFoundException(f"Tag with ID {tag_id} not found")
    
    # Check if association already exists
    association_result = await session.execute(
        select(customer_tags)
        .where(
            customer_tags.c.customer_id == customer_id,
            customer_tags.c.tag_id == tag_id
        )
    )
    
    if association_result.first():
        # Tag already associated with customer, nothing to do
        return None
    
    # Add association
    await session.execute(
        customer_tags.insert().values(
            customer_id=customer_id,
            tag_id=tag_id
        )
    )
    
    await session.commit()
    return None


@router.delete("/{customer_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def remove_tag_from_customer(
    customer_id: int = Path(..., description="Customer ID"),
    tag_id: int = Path(..., description="Tag ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Remove a tag from a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Check if tag exists
    tag_result = await session.execute(
        select(CustomerTagDefinition).where(CustomerTagDefinition.id == tag_id)
    )
    tag = tag_result.scalars().first()
    
    if not tag:
        raise NotFoundException(f"Tag with ID {tag_id} not found")
    
    # Remove association
    await session.execute(
        customer_tags.delete()
        .where(
            customer_tags.c.customer_id == customer_id,
            customer_tags.c.tag_id == tag_id
        )
    )
    
    await session.commit()
    return None


@router.get("/{customer_id}/tags", response_model=List[TagResponse])
@handle_exceptions
async def get_customer_tags(
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all tags for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Get tags for customer
    result = await session.execute(
        select(CustomerTagDefinition)
        .join(customer_tags, CustomerTagDefinition.id == customer_tags.c.tag_id)
        .where(customer_tags.c.customer_id == customer_id)
    )
    
    tags = result.scalars().all()
    
    return [TagResponse.from_orm(tag) for tag in tags]
