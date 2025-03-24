"""
Ticket endpoints for the CRM & Ticketing module.

This module provides API endpoints for managing tickets, including creation,
updates, comments, attachments, and tags.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, File, UploadFile, Form
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth import get_current_user, require_permissions
from ..services.ticket_service import TicketService
from ..schemas.ticket import (
    Ticket, TicketCreate, TicketUpdate, TicketComment, TicketCommentCreate,
    TicketAttachment, Tag, TagCreate, TagUpdate
)
from ..schemas.common import TicketStatus, TicketPriority, TicketType

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[Ticket])
async def list_tickets(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    ticket_type: Optional[TicketType] = None,
    assigned_to: Optional[int] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List tickets with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional filter by ticket status
        priority: Optional filter by ticket priority
        ticket_type: Optional filter by ticket type
        assigned_to: Optional filter by assigned user ID
        customer_id: Optional filter by customer ID
        
    Returns:
        List of ticket objects
    """
    require_permissions(current_user, ["crm.view_ticket"])
    ticket_service = TicketService(db)
    return ticket_service.list_tickets(
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        ticket_type=ticket_type,
        assigned_to=assigned_to,
        customer_id=customer_id
    )


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(
    ticket_id: int = Path(..., description="The ID of the ticket to retrieve"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a ticket by ID.
    
    Args:
        ticket_id: The ID of the ticket to retrieve
        
    Returns:
        The ticket object
    """
    require_permissions(current_user, ["crm.view_ticket"])
    ticket_service = TicketService(db)
    return ticket_service.get_ticket(ticket_id)


@router.post("/", response_model=Ticket, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new ticket.
    
    Args:
        ticket_data: Data for the new ticket
        
    Returns:
        The created ticket object
    """
    require_permissions(current_user, ["crm.add_ticket"])
    ticket_service = TicketService(db)
    return ticket_service.create_ticket(ticket_data, current_user.id)


@router.put("/{ticket_id}", response_model=Ticket)
async def update_ticket(
    ticket_data: TicketUpdate,
    ticket_id: int = Path(..., description="The ID of the ticket to update"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update an existing ticket.
    
    Args:
        ticket_id: The ID of the ticket to update
        ticket_data: New data for the ticket
        
    Returns:
        The updated ticket object
    """
    require_permissions(current_user, ["crm.change_ticket"])
    ticket_service = TicketService(db)
    return ticket_service.update_ticket(ticket_id, ticket_data, current_user.id)


@router.patch("/{ticket_id}/status", response_model=Ticket)
async def change_ticket_status(
    ticket_id: int = Path(..., description="The ID of the ticket to update"),
    status: TicketStatus = Query(..., description="The new status for the ticket"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Change the status of a ticket.
    
    Args:
        ticket_id: The ID of the ticket to update
        status: The new status for the ticket
        
    Returns:
        The updated ticket object
    """
    require_permissions(current_user, ["crm.change_ticket"])
    ticket_service = TicketService(db)
    return ticket_service.change_ticket_status(ticket_id, status, current_user.id)


@router.patch("/{ticket_id}/priority", response_model=Ticket)
async def change_ticket_priority(
    ticket_id: int = Path(..., description="The ID of the ticket to update"),
    priority: TicketPriority = Query(..., description="The new priority for the ticket"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Change the priority of a ticket.
    
    Args:
        ticket_id: The ID of the ticket to update
        priority: The new priority for the ticket
        
    Returns:
        The updated ticket object
    """
    require_permissions(current_user, ["crm.change_ticket"])
    ticket_service = TicketService(db)
    return ticket_service.change_ticket_priority(ticket_id, priority, current_user.id)


@router.patch("/{ticket_id}/assign", response_model=Ticket)
async def assign_ticket(
    ticket_id: int = Path(..., description="The ID of the ticket to update"),
    assigned_to: Optional[int] = Query(None, description="The ID of the user to assign the ticket to"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Assign a ticket to a user.
    
    Args:
        ticket_id: The ID of the ticket to update
        assigned_to: The ID of the user to assign the ticket to, or None to unassign
        
    Returns:
        The updated ticket object
    """
    require_permissions(current_user, ["crm.change_ticket"])
    ticket_service = TicketService(db)
    return ticket_service.assign_ticket(ticket_id, assigned_to, current_user.id)


@router.post("/{ticket_id}/comments", response_model=TicketComment, status_code=status.HTTP_201_CREATED)
async def add_comment(
    comment_data: TicketCommentCreate,
    ticket_id: int = Path(..., description="The ID of the ticket to add a comment to"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Add a comment to a ticket.
    
    Args:
        ticket_id: The ID of the ticket to add a comment to
        comment_data: Data for the new comment
        
    Returns:
        The created comment object
    """
    require_permissions(current_user, ["crm.add_comment"])
    ticket_service = TicketService(db)
    # Ensure the comment is associated with the correct ticket
    comment_data.ticket_id = ticket_id
    return ticket_service.add_comment(comment_data, current_user.id)


@router.post("/{ticket_id}/attachments", response_model=TicketAttachment, status_code=status.HTTP_201_CREATED)
async def add_attachment(
    ticket_id: int = Path(..., description="The ID of the ticket to add an attachment to"),
    file: UploadFile = File(..., description="The file to upload"),
    description: Optional[str] = Form(None, description="Optional description for the attachment"),
    is_internal: bool = Form(False, description="Whether the attachment is internal only"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Add an attachment to a ticket.
    
    Args:
        ticket_id: The ID of the ticket to add an attachment to
        file: The file to upload
        description: Optional description for the attachment
        is_internal: Whether the attachment is internal only
        
    Returns:
        The created attachment object
    """
    require_permissions(current_user, ["crm.add_attachment"])
    ticket_service = TicketService(db)
    return await ticket_service.add_attachment(
        ticket_id=ticket_id,
        file=file,
        description=description,
        is_internal=is_internal,
        user_id=current_user.id
    )


@router.get("/tags/", response_model=List[Tag])
async def list_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List all tags.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of tag objects
    """
    require_permissions(current_user, ["crm.view_tag"])
    ticket_service = TicketService(db)
    return ticket_service.list_tags(skip=skip, limit=limit)


@router.post("/tags/", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new tag.
    
    Args:
        tag_data: Data for the new tag
        
    Returns:
        The created tag object
    """
    require_permissions(current_user, ["crm.add_tag"])
    ticket_service = TicketService(db)
    return ticket_service.create_tag(tag_data, current_user.id)


@router.put("/tags/{tag_id}", response_model=Tag)
async def update_tag(
    tag_data: TagUpdate,
    tag_id: int = Path(..., description="The ID of the tag to update"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update an existing tag.
    
    Args:
        tag_id: The ID of the tag to update
        tag_data: New data for the tag
        
    Returns:
        The updated tag object
    """
    require_permissions(current_user, ["crm.change_tag"])
    ticket_service = TicketService(db)
    return ticket_service.update_tag(tag_id, tag_data, current_user.id)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int = Path(..., description="The ID of the tag to delete"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a tag.
    
    Args:
        tag_id: The ID of the tag to delete
    """
    require_permissions(current_user, ["crm.delete_tag"])
    ticket_service = TicketService(db)
    ticket_service.delete_tag(tag_id, current_user.id)
    return None


@router.post("/{ticket_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_tag_to_ticket(
    ticket_id: int = Path(..., description="The ID of the ticket to add a tag to"),
    tag_id: int = Path(..., description="The ID of the tag to add"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Add a tag to a ticket.
    
    Args:
        ticket_id: The ID of the ticket to add a tag to
        tag_id: The ID of the tag to add
    """
    require_permissions(current_user, ["crm.change_ticket"])
    ticket_service = TicketService(db)
    ticket_service.add_tag_to_ticket(ticket_id, tag_id, current_user.id)
    return None


@router.delete("/{ticket_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag_from_ticket(
    ticket_id: int = Path(..., description="The ID of the ticket to remove a tag from"),
    tag_id: int = Path(..., description="The ID of the tag to remove"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Remove a tag from a ticket.
    
    Args:
        ticket_id: The ID of the ticket to remove a tag from
        tag_id: The ID of the tag to remove
    """
    require_permissions(current_user, ["crm.change_ticket"])
    ticket_service = TicketService(db)
    ticket_service.remove_tag_from_ticket(ticket_id, tag_id, current_user.id)
    return None
