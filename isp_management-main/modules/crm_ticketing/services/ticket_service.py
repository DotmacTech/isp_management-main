"""
Ticket service for the CRM & Ticketing module.

This service provides functionality for managing support tickets, including
creation, updates, comments, attachments, and workflow transitions.
"""

from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime
import uuid
import os
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, and_, or_
from fastapi import HTTPException, status, UploadFile, File

from backend_core.database import get_db
from modules.monitoring.services import LoggingService
from ..models.ticket import Ticket, TicketComment, TicketAttachment, TicketHistory, Tag, ticket_tags
from ..models.customer import Customer
from ..models.sla import SLA
from ..models.common import (
    TicketStatus, TicketPriority, TicketType, ContactMethod,
    get_sla_target_datetime, calculate_sla_breach, get_sla_status
)
from ..schemas.ticket import (
    TicketCreate, TicketUpdate, TicketResponse,
    TicketCommentCreate, TicketCommentUpdate, TicketCommentResponse,
    TicketAttachmentCreate, TicketAttachmentResponse,
    TagCreate, TagUpdate
)
from .sla_service import SLAService
from .notification_service import NotificationService


class TicketService:
    """Service for managing support tickets."""
    
    def __init__(self, db: Session):
        """Initialize the ticket service with a database session."""
        self.db = db
        self.logging_service = LoggingService(db)
        self.sla_service = SLAService(db)
        self.notification_service = NotificationService(db)
        self.upload_dir = os.environ.get("TICKET_ATTACHMENT_DIR", "/tmp/ticket_attachments")
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def get_ticket(self, ticket_id: int) -> Ticket:
        """
        Get a ticket by ID.
        
        Args:
            ticket_id: The ID of the ticket to retrieve
            
        Returns:
            The ticket object
            
        Raises:
            HTTPException: If the ticket is not found
        """
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        return ticket
    
    def get_ticket_by_number(self, ticket_number: str) -> Ticket:
        """
        Get a ticket by its ticket number.
        
        Args:
            ticket_number: The ticket number
            
        Returns:
            The ticket object
            
        Raises:
            HTTPException: If the ticket is not found
        """
        ticket = self.db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with number {ticket_number} not found"
            )
        return ticket
    
    def list_tickets(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        status: Optional[List[TicketStatus]] = None,
        priority: Optional[List[TicketPriority]] = None,
        ticket_type: Optional[List[TicketType]] = None,
        customer_id: Optional[int] = None,
        assigned_to: Optional[int] = None,
        assigned_team: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        tags: Optional[List[int]] = None,
        is_overdue: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> List[Ticket]:
        """
        List tickets with optional filtering, sorting, and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search term to filter by
            status: Filter by ticket status
            priority: Filter by ticket priority
            ticket_type: Filter by ticket type
            customer_id: Filter by customer ID
            assigned_to: Filter by assigned user ID
            assigned_team: Filter by assigned team ID
            created_after: Filter by creation date (after)
            created_before: Filter by creation date (before)
            tags: Filter by tag IDs
            is_overdue: Filter by overdue status
            sort_by: Field to sort by
            sort_desc: Whether to sort in descending order
            
        Returns:
            List of ticket objects
        """
        query = self.db.query(Ticket)
        
        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    Ticket.subject.ilike(f"%{search}%"),
                    Ticket.description.ilike(f"%{search}%"),
                    Ticket.ticket_number.ilike(f"%{search}%")
                )
            )
        
        # Apply status filter
        if status:
            query = query.filter(Ticket.status.in_(status))
        
        # Apply priority filter
        if priority:
            query = query.filter(Ticket.priority.in_(priority))
        
        # Apply ticket type filter
        if ticket_type:
            query = query.filter(Ticket.ticket_type.in_(ticket_type))
        
        # Apply customer filter
        if customer_id:
            query = query.filter(Ticket.customer_id == customer_id)
        
        # Apply assignee filter
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)
        
        # Apply team filter
        if assigned_team:
            query = query.filter(Ticket.assigned_team == assigned_team)
        
        # Apply date filters
        if created_after:
            query = query.filter(Ticket.created_at >= created_after)
        
        if created_before:
            query = query.filter(Ticket.created_at <= created_before)
        
        # Apply tag filter
        if tags:
            for tag_id in tags:
                query = query.filter(Ticket.tags.any(Tag.id == tag_id))
        
        # Apply overdue filter
        if is_overdue is not None:
            now = datetime.utcnow()
            if is_overdue:
                # Tickets that are not closed/resolved/cancelled and have breached SLA
                query = query.filter(
                    and_(
                        Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED]),
                        or_(
                            and_(Ticket.first_response_at.is_(None), Ticket.first_response_target <= now),
                            Ticket.resolution_target <= now
                        )
                    )
                )
            else:
                # Tickets that are not overdue
                query = query.filter(
                    or_(
                        Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED]),
                        and_(
                            or_(
                                Ticket.first_response_at.is_not(None),
                                Ticket.first_response_target > now
                            ),
                            or_(
                                Ticket.resolution_target > now,
                                Ticket.resolution_target.is_(None)
                            )
                        )
                    )
                )
        
        # Apply sorting
        if sort_by and hasattr(Ticket, sort_by):
            order_func = desc if sort_desc else asc
            query = query.order_by(order_func(getattr(Ticket, sort_by)))
        else:
            # Default sort by updated_at
            query = query.order_by(desc(Ticket.updated_at))
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()
    
    def count_tickets(
        self, 
        search: Optional[str] = None,
        status: Optional[List[TicketStatus]] = None,
        priority: Optional[List[TicketPriority]] = None,
        ticket_type: Optional[List[TicketType]] = None,
        customer_id: Optional[int] = None,
        assigned_to: Optional[int] = None,
        assigned_team: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        tags: Optional[List[int]] = None,
        is_overdue: Optional[bool] = None
    ) -> int:
        """
        Count tickets with optional filtering.
        
        Args:
            search: Search term to filter by
            status: Filter by ticket status
            priority: Filter by ticket priority
            ticket_type: Filter by ticket type
            customer_id: Filter by customer ID
            assigned_to: Filter by assigned user ID
            assigned_team: Filter by assigned team ID
            created_after: Filter by creation date (after)
            created_before: Filter by creation date (before)
            tags: Filter by tag IDs
            is_overdue: Filter by overdue status
            
        Returns:
            Total count of matching tickets
        """
        query = self.db.query(func.count(Ticket.id))
        
        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    Ticket.subject.ilike(f"%{search}%"),
                    Ticket.description.ilike(f"%{search}%"),
                    Ticket.ticket_number.ilike(f"%{search}%")
                )
            )
        
        # Apply status filter
        if status:
            query = query.filter(Ticket.status.in_(status))
        
        # Apply priority filter
        if priority:
            query = query.filter(Ticket.priority.in_(priority))
        
        # Apply ticket type filter
        if ticket_type:
            query = query.filter(Ticket.ticket_type.in_(ticket_type))
        
        # Apply customer filter
        if customer_id:
            query = query.filter(Ticket.customer_id == customer_id)
        
        # Apply assignee filter
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)
        
        # Apply team filter
        if assigned_team:
            query = query.filter(Ticket.assigned_team == assigned_team)
        
        # Apply date filters
        if created_after:
            query = query.filter(Ticket.created_at >= created_after)
        
        if created_before:
            query = query.filter(Ticket.created_at <= created_before)
        
        # Apply tag filter
        if tags:
            for tag_id in tags:
                query = query.filter(Ticket.tags.any(Tag.id == tag_id))
        
        # Apply overdue filter
        if is_overdue is not None:
            now = datetime.utcnow()
            if is_overdue:
                # Tickets that are not closed/resolved/cancelled and have breached SLA
                query = query.filter(
                    and_(
                        Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED]),
                        or_(
                            and_(Ticket.first_response_at.is_(None), Ticket.first_response_target <= now),
                            Ticket.resolution_target <= now
                        )
                    )
                )
            else:
                # Tickets that are not overdue
                query = query.filter(
                    or_(
                        Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED]),
                        and_(
                            or_(
                                Ticket.first_response_at.is_not(None),
                                Ticket.first_response_target > now
                            ),
                            or_(
                                Ticket.resolution_target > now,
                                Ticket.resolution_target.is_(None)
                            )
                        )
                    )
                )
        
        return query.scalar()
    
    def generate_ticket_number(self) -> str:
        """
        Generate a unique ticket number.
        
        Returns:
            A unique ticket number
        """
        # Format: TKT-YYYYMMDD-XXXX where XXXX is a sequential number
        date_part = datetime.utcnow().strftime("%Y%m%d")
        
        # Get the highest ticket number for today
        latest_ticket = self.db.query(Ticket).filter(
            Ticket.ticket_number.like(f"TKT-{date_part}-%")
        ).order_by(desc(Ticket.ticket_number)).first()
        
        if latest_ticket:
            # Extract the sequential part and increment
            seq_part = int(latest_ticket.ticket_number.split("-")[-1])
            seq_part += 1
        else:
            # First ticket of the day
            seq_part = 1
        
        return f"TKT-{date_part}-{seq_part:04d}"
    
    def create_ticket(self, ticket_data: TicketCreate, user_id: int) -> Ticket:
        """
        Create a new ticket.
        
        Args:
            ticket_data: Data for the new ticket
            user_id: The ID of the user creating the ticket
            
        Returns:
            The created ticket object
        """
        # Generate ticket number
        ticket_number = self.generate_ticket_number()
        
        # Create ticket dict from schema
        ticket_dict = ticket_data.dict(exclude={"tag_ids"})
        ticket_dict["ticket_number"] = ticket_number
        
        # Set up SLA if provided or get default
        if ticket_data.sla_id:
            sla = self.sla_service.get_sla(ticket_data.sla_id)
        else:
            sla = self.sla_service.get_default_sla()
        
        if sla:
            ticket_dict["sla_id"] = sla.id
            
            # Calculate SLA targets
            ticket_dict["first_response_target"] = get_sla_target_datetime(
                ticket_data.priority, "first_response"
            )
            ticket_dict["next_update_target"] = get_sla_target_datetime(
                ticket_data.priority, "update"
            )
            ticket_dict["resolution_target"] = get_sla_target_datetime(
                ticket_data.priority, "resolution"
            )
        
        # Create ticket
        ticket = Ticket(**ticket_dict)
        
        # Add tags if provided
        if ticket_data.tag_ids:
            tags = self.db.query(Tag).filter(Tag.id.in_(ticket_data.tag_ids)).all()
            ticket.tags = tags
        
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        
        # Create initial history entry
        self._create_history_entry(ticket.id, "status", None, TicketStatus.NEW, user_id)
        
        # Log ticket creation
        self.logging_service.log_event(
            "ticket_created",
            f"Ticket {ticket.ticket_number} created by user {user_id}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "user_id": user_id
            }
        )
        
        # Send notifications
        self.notification_service.notify_ticket_created(ticket, user_id)
        
        return ticket
    
    def update_ticket(self, ticket_id: int, ticket_data: TicketUpdate, user_id: int) -> Ticket:
        """
        Update an existing ticket.
        
        Args:
            ticket_id: The ID of the ticket to update
            ticket_data: New data for the ticket
            user_id: The ID of the user updating the ticket
            
        Returns:
            The updated ticket object
            
        Raises:
            HTTPException: If the ticket is not found
        """
        ticket = self.get_ticket(ticket_id)
        
        # Track changes for history
        changes = []
        
        # Update fields
        for field, value in ticket_data.dict(exclude={"tag_ids"}, exclude_unset=True).items():
            if hasattr(ticket, field) and getattr(ticket, field) != value:
                old_value = getattr(ticket, field)
                setattr(ticket, field, value)
                changes.append((field, old_value, value))
        
        # Update tags if provided
        if ticket_data.tag_ids is not None:
            old_tags = [tag.id for tag in ticket.tags]
            new_tags = self.db.query(Tag).filter(Tag.id.in_(ticket_data.tag_ids)).all()
            ticket.tags = new_tags
            changes.append(("tags", old_tags, ticket_data.tag_ids))
        
        # Update SLA targets if priority changed
        priority_change = next((c for c in changes if c[0] == "priority"), None)
        if priority_change or ticket_data.sla_id:
            # If SLA ID was updated, get the new SLA
            if ticket_data.sla_id and ticket_data.sla_id != ticket.sla_id:
                sla = self.sla_service.get_sla(ticket_data.sla_id)
                ticket.sla_id = sla.id
            else:
                sla = self.sla_service.get_sla(ticket.sla_id) if ticket.sla_id else None
            
            if sla:
                # Use the new priority if it was changed
                priority = ticket_data.priority if priority_change else ticket.priority
                
                # Recalculate SLA targets
                ticket.first_response_target = get_sla_target_datetime(priority, "first_response")
                ticket.next_update_target = get_sla_target_datetime(priority, "update")
                ticket.resolution_target = get_sla_target_datetime(priority, "resolution")
        
        # Check for status change
        status_change = next((c for c in changes if c[0] == "status"), None)
        if status_change:
            old_status, new_status = status_change[1], status_change[2]
            self._handle_status_change(ticket, old_status, new_status, user_id)
        
        self.db.commit()
        self.db.refresh(ticket)
        
        # Create history entries for all changes
        for field, old_value, new_value in changes:
            self._create_history_entry(ticket.id, field, old_value, new_value, user_id)
        
        # Log ticket update
        self.logging_service.log_event(
            "ticket_updated",
            f"Ticket {ticket.ticket_number} updated by user {user_id}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "user_id": user_id,
                "changes": [(c[0], str(c[1]), str(c[2])) for c in changes]
            }
        )
        
        # Send notifications
        if changes:
            self.notification_service.notify_ticket_updated(ticket, user_id, changes)
        
        return ticket
    
    def change_ticket_status(
        self, 
        ticket_id: int, 
        new_status: TicketStatus, 
        user_id: int,
        comment: Optional[str] = None
    ) -> Ticket:
        """
        Change the status of a ticket.
        
        Args:
            ticket_id: The ID of the ticket to update
            new_status: The new status for the ticket
            user_id: The ID of the user changing the status
            comment: Optional comment explaining the status change
            
        Returns:
            The updated ticket object
            
        Raises:
            HTTPException: If the ticket is not found or if the status transition is invalid
        """
        ticket = self.get_ticket(ticket_id)
        old_status = ticket.status
        
        # Check if the status is actually changing
        if old_status == new_status:
            return ticket
        
        # Handle the status change
        self._handle_status_change(ticket, old_status, new_status, user_id)
        
        # Update the ticket status
        ticket.status = new_status
        self.db.commit()
        self.db.refresh(ticket)
        
        # Create history entry
        self._create_history_entry(ticket.id, "status", old_status, new_status, user_id)
        
        # Add a comment if provided
        if comment:
            self.add_comment(
                TicketCommentCreate(
                    ticket_id=ticket_id,
                    content=comment,
                    is_internal=False,
                    is_system=False
                ),
                user_id
            )
        
        # Log status change
        self.logging_service.log_event(
            "ticket_status_changed",
            f"Ticket {ticket.ticket_number} status changed from {old_status} to {new_status} by user {user_id}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "user_id": user_id,
                "old_status": old_status,
                "new_status": new_status
            }
        )
        
        # Send notifications
        self.notification_service.notify_ticket_status_changed(ticket, user_id, old_status, new_status)
        
        return ticket
    
    def _handle_status_change(
        self, 
        ticket: Ticket, 
        old_status: TicketStatus, 
        new_status: TicketStatus,
        user_id: int
    ) -> None:
        """
        Handle side effects of a ticket status change.
        
        Args:
            ticket: The ticket being updated
            old_status: The old status
            new_status: The new status
            user_id: The ID of the user changing the status
        """
        now = datetime.utcnow()
        
        # Handle specific status transitions
        if new_status == TicketStatus.RESOLVED:
            # Record resolution time
            ticket.resolved_at = now
            
            # Check for SLA breach
            if ticket.resolution_target and now > ticket.resolution_target:
                ticket.sla_breached = True
        
        elif new_status == TicketStatus.CLOSED:
            # Record closed time if not already set
            if not ticket.closed_at:
                ticket.closed_at = now
        
        elif new_status == TicketStatus.REOPENED:
            # Clear resolution and closed times
            ticket.resolved_at = None
            ticket.closed_at = None
            
            # Reset SLA targets if needed
            if ticket.sla_id:
                sla = self.sla_service.get_sla(ticket.sla_id)
                if sla:
                    # Recalculate SLA targets
                    ticket.first_response_target = get_sla_target_datetime(ticket.priority, "first_response")
                    ticket.next_update_target = get_sla_target_datetime(ticket.priority, "update")
                    ticket.resolution_target = get_sla_target_datetime(ticket.priority, "resolution")
        
        # Update first response time if this is the first staff response
        if not ticket.first_response_at and user_id and new_status != TicketStatus.NEW:
            ticket.first_response_at = now
            
            # Check for SLA breach
            if ticket.first_response_target and now > ticket.first_response_target:
                ticket.sla_breached = True
        
        # Update last update time
        ticket.last_update_at = now
    
    def get_comments(
        self,
        ticket_id: int,
        skip: int = 0,
        limit: int = 100,
        include_internal: bool = True
    ) -> List[TicketComment]:
        """
        Get comments for a ticket.
        
        Args:
            ticket_id: The ID of the ticket
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_internal: Whether to include internal comments
            
        Returns:
            List of comment objects
            
        Raises:
            HTTPException: If the ticket is not found
        """
        # Check that the ticket exists
        self.get_ticket(ticket_id)
        
        # Build query
        query = self.db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id)
        
        # Filter internal comments if needed
        if not include_internal:
            query = query.filter(TicketComment.is_internal == False)
        
        # Apply sorting and pagination
        comments = query.order_by(asc(TicketComment.created_at)).offset(skip).limit(limit).all()
        
        return comments
    
    async def add_attachment(
        self,
        ticket_id: int,
        file: UploadFile,
        description: Optional[str],
        is_internal: bool,
        user_id: int
    ) -> TicketAttachment:
        """
        Add an attachment to a ticket.
        
        Args:
            ticket_id: The ID of the ticket
            file: The uploaded file
            description: Optional description of the attachment
            is_internal: Whether the attachment is internal (staff-only)
            user_id: The ID of the user adding the attachment
            
        Returns:
            The created attachment object
            
        Raises:
            HTTPException: If the ticket is not found or if there's an error saving the file
        """
        # Check that the ticket exists
        ticket = self.get_ticket(ticket_id)
        
        # Generate a unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        # Create a subdirectory for the ticket if it doesn't exist
        ticket_dir = os.path.join(self.upload_dir, str(ticket_id))
        os.makedirs(ticket_dir, exist_ok=True)
        file_path = os.path.join(ticket_dir, unique_filename)
        
        # Save the file
        try:
            # Read file content
            contents = await file.read()
            
            # Write to disk
            with open(file_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file: {str(e)}"
            )
        
        # Create attachment record
        attachment = TicketAttachment(
            ticket_id=ticket_id,
            filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            content_type=file.content_type,
            description=description,
            is_internal=is_internal,
            uploaded_by=user_id
        )
        
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        
        # Log attachment creation
        self.logging_service.log_event(
            "ticket_attachment_added",
            f"Attachment added to ticket {ticket.ticket_number} by user {user_id}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "attachment_id": attachment.id,
                "filename": attachment.filename,
                "user_id": user_id,
                "is_internal": attachment.is_internal
            }
        )
        
        return attachment
    
    def delete_attachment(self, attachment_id: int, user_id: int) -> None:
        """
        Delete an attachment.
        
        Args:
            attachment_id: The ID of the attachment to delete
            user_id: The ID of the user deleting the attachment
            
        Raises:
            HTTPException: If the attachment is not found or if the user is not authorized
        """
        # Get the attachment
        attachment = self.db.query(TicketAttachment).filter(TicketAttachment.id == attachment_id).first()
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment with ID {attachment_id} not found"
            )
        
        # Check if the user is authorized to delete the attachment
        if attachment.uploaded_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this attachment"
            )
        
        # Get ticket info for logging
        ticket_id = attachment.ticket_id
        ticket_number = attachment.ticket.ticket_number
        filename = attachment.filename
        file_path = attachment.file_path
        
        # Delete the file from disk
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            # Log the error but continue with database deletion
            self.logging_service.log_event(
                "error",
                f"Error deleting attachment file: {str(e)}",
                {
                    "ticket_id": ticket_id,
                    "attachment_id": attachment_id,
                    "file_path": file_path
                }
            )
        
        # Delete the attachment record
        self.db.delete(attachment)
        self.db.commit()
        
        # Log attachment deletion
        self.logging_service.log_event(
            "ticket_attachment_deleted",
            f"Attachment deleted from ticket {ticket_number} by user {user_id}",
            {
                "ticket_id": ticket_id,
                "ticket_number": ticket_number,
                "attachment_id": attachment_id,
                "filename": filename,
                "user_id": user_id
            }
        )
    
    def get_attachments(
        self,
        ticket_id: int,
        skip: int = 0,
        limit: int = 100,
        include_internal: bool = True
    ) -> List[TicketAttachment]:
        """
        Get attachments for a ticket.
        
        Args:
            ticket_id: The ID of the ticket
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_internal: Whether to include internal attachments
            
        Returns:
            List of attachment objects
            
        Raises:
            HTTPException: If the ticket is not found
        """
        # Check that the ticket exists
        self.get_ticket(ticket_id)
        
        # Build query
        query = self.db.query(TicketAttachment).filter(TicketAttachment.ticket_id == ticket_id)
        
        # Filter internal attachments if needed
        if not include_internal:
            query = query.filter(TicketAttachment.is_internal == False)
        
        # Apply sorting and pagination
        attachments = query.order_by(desc(TicketAttachment.created_at)).offset(skip).limit(limit).all()
        
        return attachments
    
    def get_attachment(self, attachment_id: int) -> TicketAttachment:
        """
        Get an attachment by ID.
        
        Args:
            attachment_id: The ID of the attachment
            
        Returns:
            The attachment object
            
        Raises:
            HTTPException: If the attachment is not found
        """
        attachment = self.db.query(TicketAttachment).filter(TicketAttachment.id == attachment_id).first()
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment with ID {attachment_id} not found"
            )
        return attachment
    
    # Tag Management Methods
    
    def create_tag(self, tag_data: TagCreate, user_id: int) -> Tag:
        """
        Create a new tag.
        
        Args:
            tag_data: Data for the new tag
            user_id: The ID of the user creating the tag
            
        Returns:
            The created tag object
            
        Raises:
            HTTPException: If a tag with the same name already exists
        """
        # Check if a tag with the same name already exists
        existing_tag = self.db.query(Tag).filter(Tag.name == tag_data.name).first()
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag with name '{tag_data.name}' already exists"
            )
        
        # Create tag
        tag = Tag(
            name=tag_data.name,
            color=tag_data.color,
            description=tag_data.description,
            created_by=user_id
        )
        
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        
        # Log tag creation
        self.logging_service.log_event(
            "tag_created",
            f"Tag '{tag.name}' created by user {user_id}",
            {
                "tag_id": tag.id,
                "tag_name": tag.name,
                "user_id": user_id
            }
        )
        
        return tag
    
    def update_tag(self, tag_id: int, tag_data: TagUpdate, user_id: int) -> Tag:
        """
        Update an existing tag.
        
        Args:
            tag_id: The ID of the tag to update
            tag_data: New data for the tag
            user_id: The ID of the user updating the tag
            
        Returns:
            The updated tag object
            
        Raises:
            HTTPException: If the tag is not found or if a tag with the same name already exists
        """
        # Get the tag
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with ID {tag_id} not found"
            )
        
        # Check if name is being updated and if a tag with the same name already exists
        if tag_data.name and tag_data.name != tag.name:
            existing_tag = self.db.query(Tag).filter(Tag.name == tag_data.name).first()
            if existing_tag:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tag with name '{tag_data.name}' already exists"
                )
        
        # Update tag
        for field, value in tag_data.dict(exclude_unset=True).items():
            setattr(tag, field, value)
        
        tag.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(tag)
        
        # Log tag update
        self.logging_service.log_event(
            "tag_updated",
            f"Tag '{tag.name}' updated by user {user_id}",
            {
                "tag_id": tag.id,
                "tag_name": tag.name,
                "user_id": user_id
            }
        )
        
        return tag
    
    def delete_tag(self, tag_id: int, user_id: int) -> None:
        """
        Delete a tag.
        
        Args:
            tag_id: The ID of the tag to delete
            user_id: The ID of the user deleting the tag
            
        Raises:
            HTTPException: If the tag is not found
        """
        # Get the tag
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with ID {tag_id} not found"
            )
        
        # Get tag info for logging
        tag_name = tag.name
        
        # Delete the tag
        self.db.delete(tag)
        self.db.commit()
        
        # Log tag deletion
        self.logging_service.log_event(
            "tag_deleted",
            f"Tag '{tag_name}' deleted by user {user_id}",
            {
                "tag_id": tag_id,
                "tag_name": tag_name,
                "user_id": user_id
            }
        )
    
    def get_tag(self, tag_id: int) -> Tag:
        """
        Get a tag by ID.
        
        Args:
            tag_id: The ID of the tag
            
        Returns:
            The tag object
            
        Raises:
            HTTPException: If the tag is not found
        """
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with ID {tag_id} not found"
            )
        return tag
    
    def list_tags(self, skip: int = 0, limit: int = 100) -> List[Tag]:
        """
        List all tags.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tag objects
        """
        tags = self.db.query(Tag).order_by(asc(Tag.name)).offset(skip).limit(limit).all()
        return tags
    
    def add_tag_to_ticket(self, ticket_id: int, tag_id: int, user_id: int) -> Ticket:
        """
        Add a tag to a ticket.
        
        Args:
            ticket_id: The ID of the ticket
            tag_id: The ID of the tag to add
            user_id: The ID of the user adding the tag
            
        Returns:
            The updated ticket object
            
        Raises:
            HTTPException: If the ticket or tag is not found, or if the tag is already applied
        """
        # Get the ticket and tag
        ticket = self.get_ticket(ticket_id)
        tag = self.get_tag(tag_id)
        
        # Check if the tag is already applied
        if tag in ticket.tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag '{tag.name}' is already applied to this ticket"
            )
        
        # Add the tag
        ticket.tags.append(tag)
        self.db.commit()
        self.db.refresh(ticket)
        
        # Create history entry
        self._create_history_entry(ticket.id, "tags_added", None, tag.name, user_id)
        
        # Log tag addition
        self.logging_service.log_event(
            "ticket_tag_added",
            f"Tag '{tag.name}' added to ticket {ticket.ticket_number} by user {user_id}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "tag_id": tag.id,
                "tag_name": tag.name,
                "user_id": user_id
            }
        )
        
        return ticket
    
    def remove_tag_from_ticket(self, ticket_id: int, tag_id: int, user_id: int) -> Ticket:
        """
        Remove a tag from a ticket.
        
        Args:
            ticket_id: The ID of the ticket
            tag_id: The ID of the tag to remove
            user_id: The ID of the user removing the tag
            
        Returns:
            The updated ticket object
            
        Raises:
            HTTPException: If the ticket or tag is not found, or if the tag is not applied
        """
        # Get the ticket and tag
        ticket = self.get_ticket(ticket_id)
        tag = self.get_tag(tag_id)
        
        # Check if the tag is applied
        if tag not in ticket.tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag '{tag.name}' is not applied to this ticket"
            )
        
        # Remove the tag
        ticket.tags.remove(tag)
        self.db.commit()
        self.db.refresh(ticket)
        
        # Create history entry
        self._create_history_entry(ticket.id, "tags_removed", tag.name, None, user_id)
        
        # Log tag removal
        self.logging_service.log_event(
            "ticket_tag_removed",
            f"Tag '{tag.name}' removed from ticket {ticket.ticket_number} by user {user_id}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "tag_id": tag.id,
                "tag_name": tag.name,
                "user_id": user_id
            }
        )
        
        return ticket
