"""
API endpoints for customer custom fields.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import Customer, CustomerCustomField
from modules.customer.schemas import CustomFieldCreate, CustomFieldUpdate, CustomFieldResponse
from sqlalchemy import select, update, delete

# Initialize router
router = APIRouter(
    prefix="/{customer_id}/custom-fields",
    tags=["customer-custom-fields"],
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


@router.post("/", response_model=CustomFieldResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_custom_field(
    field_data: CustomFieldCreate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new custom field for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Check if field with same name already exists
    existing_field = await session.execute(
        select(CustomerCustomField).where(
            CustomerCustomField.customer_id == customer_id,
            CustomerCustomField.field_name == field_data.field_name
        )
    )
    
    if existing_field.scalars().first():
        raise ValidationException(f"Custom field with name '{field_data.field_name}' already exists for this customer")
    
    # Create custom field
    custom_field = CustomerCustomField(
        customer_id=customer_id,
        **field_data.dict()
    )
    
    session.add(custom_field)
    await session.commit()
    await session.refresh(custom_field)
    
    return CustomFieldResponse.from_orm(custom_field)


@router.get("/", response_model=List[CustomFieldResponse])
@handle_exceptions
async def get_custom_fields(
    customer_id: int = Path(..., description="Customer ID"),
    api_visible_only: bool = Query(False, description="Only return fields visible via API"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all custom fields for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Build query
    query = select(CustomerCustomField).where(CustomerCustomField.customer_id == customer_id)
    
    # Apply filters
    if api_visible_only:
        query = query.where(CustomerCustomField.is_api_visible == True)
    
    # Execute query
    result = await session.execute(query)
    custom_fields = result.scalars().all()
    
    return [CustomFieldResponse.from_orm(field) for field in custom_fields]


@router.get("/{field_id}", response_model=CustomFieldResponse)
@handle_exceptions
async def get_custom_field(
    customer_id: int = Path(..., description="Customer ID"),
    field_id: int = Path(..., description="Custom field ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific custom field for a customer."""
    # Check if field exists and belongs to customer
    result = await session.execute(
        select(CustomerCustomField)
        .where(
            CustomerCustomField.id == field_id,
            CustomerCustomField.customer_id == customer_id
        )
    )
    custom_field = result.scalars().first()
    
    if not custom_field:
        raise NotFoundException(f"Custom field with ID {field_id} not found for customer {customer_id}")
    
    return CustomFieldResponse.from_orm(custom_field)


@router.put("/{field_id}", response_model=CustomFieldResponse)
@handle_exceptions
async def update_custom_field(
    field_data: CustomFieldUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    field_id: int = Path(..., description="Custom field ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Update a custom field for a customer."""
    # Check if field exists and belongs to customer
    result = await session.execute(
        select(CustomerCustomField)
        .where(
            CustomerCustomField.id == field_id,
            CustomerCustomField.customer_id == customer_id
        )
    )
    custom_field = result.scalars().first()
    
    if not custom_field:
        raise NotFoundException(f"Custom field with ID {field_id} not found for customer {customer_id}")
    
    # Check if updating to a name that already exists
    if field_data.field_name and field_data.field_name != custom_field.field_name:
        existing_field = await session.execute(
            select(CustomerCustomField).where(
                CustomerCustomField.customer_id == customer_id,
                CustomerCustomField.field_name == field_data.field_name,
                CustomerCustomField.id != field_id
            )
        )
        
        if existing_field.scalars().first():
            raise ValidationException(f"Custom field with name '{field_data.field_name}' already exists for this customer")
    
    # Update field with provided data
    update_data = {k: v for k, v in field_data.dict().items() if v is not None}
    
    for key, value in update_data.items():
        setattr(custom_field, key, value)
    
    await session.commit()
    await session.refresh(custom_field)
    
    return CustomFieldResponse.from_orm(custom_field)


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_custom_field(
    customer_id: int = Path(..., description="Customer ID"),
    field_id: int = Path(..., description="Custom field ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Delete a custom field for a customer."""
    # Check if field exists and belongs to customer
    result = await session.execute(
        select(CustomerCustomField)
        .where(
            CustomerCustomField.id == field_id,
            CustomerCustomField.customer_id == customer_id
        )
    )
    custom_field = result.scalars().first()
    
    if not custom_field:
        raise NotFoundException(f"Custom field with ID {field_id} not found for customer {customer_id}")
    
    # Delete the field
    await session.execute(
        delete(CustomerCustomField)
        .where(
            CustomerCustomField.id == field_id
        )
    )
    
    await session.commit()
    
    return None
