"""
API endpoints for customer communication preferences.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import CommunicationType
from modules.customer.schemas import (
    CommunicationPreferenceCreate, 
    CommunicationPreferenceUpdate, 
    CommunicationPreferenceResponse
)
from modules.customer.communication_service import CommunicationService

# Initialize router
router = APIRouter(
    prefix="/{customer_id}/communication-preferences",
    tags=["customer-communication"],
)

# Initialize service
communication_service = CommunicationService()

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


# Communication preference endpoints
@router.post("/", response_model=CommunicationPreferenceResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_communication_preference(
    preference_data: CommunicationPreferenceCreate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new communication preference for a customer."""
    preference = await communication_service.create_preference(
        session=session,
        customer_id=customer_id,
        **preference_data.dict()
    )
    
    await session.commit()
    return CommunicationPreferenceResponse.from_orm(preference)


@router.get("/", response_model=List[CommunicationPreferenceResponse])
@handle_exceptions
async def get_customer_communication_preferences(
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all communication preferences for a customer."""
    preferences = await communication_service.get_customer_preferences(
        session=session,
        customer_id=customer_id
    )
    
    return [CommunicationPreferenceResponse.from_orm(pref) for pref in preferences]


@router.get("/{preference_id}", response_model=CommunicationPreferenceResponse)
@handle_exceptions
async def get_communication_preference(
    customer_id: int = Path(..., description="Customer ID"),
    preference_id: int = Path(..., description="Preference ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific communication preference for a customer."""
    preference = await communication_service.get_preference(
        session=session,
        preference_id=preference_id
    )
    
    # Verify that preference belongs to the specified customer
    if preference.customer_id != customer_id:
        raise NotFoundException(
            f"Communication preference with ID {preference_id} not found for customer {customer_id}"
        )
    
    return CommunicationPreferenceResponse.from_orm(preference)


@router.put("/{preference_id}", response_model=CommunicationPreferenceResponse)
@handle_exceptions
async def update_communication_preference(
    preference_data: CommunicationPreferenceUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    preference_id: int = Path(..., description="Preference ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Update a communication preference for a customer."""
    # Get preference to verify it belongs to the customer
    preference = await communication_service.get_preference(
        session=session,
        preference_id=preference_id
    )
    
    if preference.customer_id != customer_id:
        raise NotFoundException(
            f"Communication preference with ID {preference_id} not found for customer {customer_id}"
        )
    
    # Update preference
    updated_preference = await communication_service.update_preference(
        session=session,
        preference_id=preference_id,
        **preference_data.dict(exclude_unset=True)
    )
    
    await session.commit()
    return CommunicationPreferenceResponse.from_orm(updated_preference)


@router.delete("/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_communication_preference(
    customer_id: int = Path(..., description="Customer ID"),
    preference_id: int = Path(..., description="Preference ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_manager)
):
    """Delete a communication preference for a customer."""
    # Get preference to verify it belongs to the customer
    preference = await communication_service.get_preference(
        session=session,
        preference_id=preference_id
    )
    
    if preference.customer_id != customer_id:
        raise NotFoundException(
            f"Communication preference with ID {preference_id} not found for customer {customer_id}"
        )
    
    # Delete preference
    await communication_service.delete_preference(
        session=session,
        preference_id=preference_id
    )
    
    await session.commit()
    return None


@router.get("/by-type/{communication_type}", response_model=CommunicationPreferenceResponse)
@handle_exceptions
async def get_preference_by_type(
    customer_id: int = Path(..., description="Customer ID"),
    communication_type: CommunicationType = Path(..., description="Communication type"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a communication preference by type for a customer."""
    # Get all preferences for the customer
    preferences = await communication_service.get_customer_preferences(
        session=session,
        customer_id=customer_id
    )
    
    # Find preference with matching type
    for preference in preferences:
        if preference.communication_type == communication_type:
            return CommunicationPreferenceResponse.from_orm(preference)
    
    raise NotFoundException(
        f"Communication preference of type {communication_type.value} not found for customer {customer_id}"
    )
