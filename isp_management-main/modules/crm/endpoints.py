from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user, get_current_user_role
from .schemas import (
    CustomerCreate,
    CustomerResponse,
    TicketCreate,
    TicketResponse,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketAssignmentUpdate,
    TicketStatusUpdate,
    CustomerSearch
)
from .services import CRMService

router = APIRouter(
    prefix="/crm",
    tags=["crm"],
    dependencies=[Depends(get_current_active_user)]
)

# Customer endpoints
@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Create a new customer profile."""
    if current_user_role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    crm_service = CRMService(db)
    return crm_service.create_customer(customer_data)

@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Get a customer by ID."""
    crm_service = CRMService(db)
    return crm_service.get_customer(customer_id)

@router.get("/customers/user/{user_id}", response_model=CustomerResponse)
async def get_customer_by_user_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Get a customer by user ID."""
    crm_service = CRMService(db)
    return crm_service.get_customer_by_user_id(user_id)

@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Update a customer's information."""
    if current_user_role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    crm_service = CRMService(db)
    return crm_service.update_customer(customer_id, customer_data)

@router.post("/customers/search", response_model=List[CustomerResponse])
async def search_customers(
    search_params: CustomerSearch,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Search for customers."""
    if current_user_role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    crm_service = CRMService(db)
    return crm_service.search_customers(search_params)

# Ticket endpoints
@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db)
):
    """Create a new support ticket."""
    crm_service = CRMService(db)
    return crm_service.create_ticket(ticket_data)

@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    """Get a ticket by ID."""
    crm_service = CRMService(db)
    return crm_service.get_ticket(ticket_id)

@router.get("/customers/{customer_id}/tickets", response_model=List[TicketResponse])
async def get_customer_tickets(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Get all tickets for a customer."""
    crm_service = CRMService(db)
    return crm_service.get_customer_tickets(customer_id)

@router.patch("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: int,
    assignment_data: TicketAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Assign a ticket to an agent."""
    if current_user_role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    crm_service = CRMService(db)
    return crm_service.assign_ticket(ticket_id, assignment_data)

@router.patch("/tickets/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: int,
    status_data: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Update a ticket's status."""
    crm_service = CRMService(db)
    return crm_service.update_ticket_status(ticket_id, status_data, current_user["id"])

@router.post("/tickets/{ticket_id}/comments", response_model=TicketCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_ticket_comment(
    ticket_id: int,
    comment_data: TicketCommentCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Add a comment to a ticket."""
    # Override the user_id with the current user's ID for security
    comment_data.user_id = current_user["id"]
    comment_data.ticket_id = ticket_id
    
    crm_service = CRMService(db)
    return crm_service.add_ticket_comment(comment_data)

@router.get("/tickets/{ticket_id}/comments", response_model=List[TicketCommentResponse])
async def get_ticket_comments(
    ticket_id: int,
    include_internal: bool = Query(False, description="Include internal comments (staff only)"),
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Get all comments for a ticket."""
    # Only staff can see internal comments
    if include_internal and current_user_role not in ["admin", "support"]:
        include_internal = False
    
    crm_service = CRMService(db)
    return crm_service.get_ticket_comments(ticket_id, include_internal)

@router.get("/tickets/statistics", response_model=Dict[str, Any])
async def get_ticket_statistics(
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Get statistics about tickets."""
    if current_user_role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    crm_service = CRMService(db)
    return crm_service.get_ticket_statistics()
