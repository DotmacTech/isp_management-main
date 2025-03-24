"""
API endpoints for customer notes.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend_core.database import get_session
from backend_core.auth import get_current_user, RoleChecker
from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import Customer, CustomerNote
from modules.customer.schemas import NoteCreate, NoteUpdate, NoteResponse

# Initialize router
router = APIRouter(
    prefix="/{customer_id}/notes",
    tags=["customer-notes"],
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


# Note endpoints
@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
@handle_exceptions
async def create_note(
    note_data: NoteCreate,
    customer_id: int = Path(..., description="Customer ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Create a new note for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Create note
    note = CustomerNote(
        customer_id=customer_id,
        **note_data.dict()
    )
    
    session.add(note)
    await session.commit()
    await session.refresh(note)
    
    return NoteResponse.from_orm(note)


@router.get("/", response_model=List[NoteResponse])
@handle_exceptions
async def get_customer_notes(
    customer_id: int = Path(..., description="Customer ID"),
    important_only: bool = Query(False, description="Filter by important notes only"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get all notes for a customer."""
    # Check if customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalars().first()
    
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found")
    
    # Build query
    query = select(CustomerNote).where(CustomerNote.customer_id == customer_id)
    
    # Apply filter
    if important_only:
        query = query.where(CustomerNote.is_important == True)
    
    # Execute query
    result = await session.execute(query)
    notes = result.scalars().all()
    
    return [NoteResponse.from_orm(note) for note in notes]


@router.get("/{note_id}", response_model=NoteResponse)
@handle_exceptions
async def get_note(
    customer_id: int = Path(..., description="Customer ID"),
    note_id: int = Path(..., description="Note ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Get a specific note for a customer."""
    # Check if note exists and belongs to customer
    result = await session.execute(
        select(CustomerNote)
        .where(
            CustomerNote.id == note_id,
            CustomerNote.customer_id == customer_id
        )
    )
    note = result.scalars().first()
    
    if not note:
        raise NotFoundException(f"Note with ID {note_id} not found for customer {customer_id}")
    
    return NoteResponse.from_orm(note)


@router.put("/{note_id}", response_model=NoteResponse)
@handle_exceptions
async def update_note(
    note_data: NoteUpdate,
    customer_id: int = Path(..., description="Customer ID"),
    note_id: int = Path(..., description="Note ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Update a note for a customer."""
    # Check if note exists and belongs to customer
    result = await session.execute(
        select(CustomerNote)
        .where(
            CustomerNote.id == note_id,
            CustomerNote.customer_id == customer_id
        )
    )
    note = result.scalars().first()
    
    if not note:
        raise NotFoundException(f"Note with ID {note_id} not found for customer {customer_id}")
    
    # Update note
    for key, value in note_data.dict(exclude_unset=True).items():
        setattr(note, key, value)
    
    await session.commit()
    await session.refresh(note)
    
    return NoteResponse.from_orm(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_exceptions
async def delete_note(
    customer_id: int = Path(..., description="Customer ID"),
    note_id: int = Path(..., description="Note ID"),
    session: AsyncSession = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: bool = Depends(allow_customer_agent)
):
    """Delete a note for a customer."""
    # Check if note exists and belongs to customer
    result = await session.execute(
        select(CustomerNote)
        .where(
            CustomerNote.id == note_id,
            CustomerNote.customer_id == customer_id
        )
    )
    note = result.scalars().first()
    
    if not note:
        raise NotFoundException(f"Note with ID {note_id} not found for customer {customer_id}")
    
    # Delete note
    await session.delete(note)
    await session.commit()
    
    return None
