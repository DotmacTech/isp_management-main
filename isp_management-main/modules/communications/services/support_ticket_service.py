"""
Support Ticket service for the Communications module.

This module provides the SupportTicketService class for handling support ticket operations
in the ISP Management Platform.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend_core.config import settings
from modules.communications import models, schemas
from modules.communications.webhooks import WebhookService
from backend_core.models import User  # Import User from backend_core

# Configure logging
logger = logging.getLogger(__name__)


class SupportTicketService:
    """Service for handling support tickets."""

    @staticmethod
    async def create_ticket(
        db: Session,
        ticket_data: schemas.SupportTicketCreate,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> models.SupportTicket:
        """
        Create a new support ticket.

        Args:
            db: Database session
            ticket_data: Ticket data
            user_id: ID of the user creating the ticket
            background_tasks: Background tasks runner

        Returns:
            The created support ticket
        """
        # Create the ticket
        ticket = models.SupportTicket(
            subject=ticket_data.subject,
            description=ticket_data.description,
            category=ticket_data.category,
            priority=ticket_data.priority,
            status=models.TicketStatus.OPEN,
            created_by=user_id
        )
        
        # Add attachments if any
        if ticket_data.attachments:
            for attachment_data in ticket_data.attachments:
                attachment = models.TicketAttachment(
                    ticket_id=ticket.id,
                    file_name=attachment_data.file_name,
                    file_path=attachment_data.file_path,
                    file_size=attachment_data.file_size,
                    content_type=attachment_data.content_type
                )
                db.add(attachment)
        
        # Save to database
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        # Trigger webhook in background if available
        if background_tasks:
            background_tasks.add_task(
                WebhookService.trigger_event,
                "ticket.created",
                {
                    "ticket_id": ticket.id,
                    "subject": ticket.subject,
                    "user_id": user_id,
                    "category": ticket.category.value,
                    "priority": ticket.priority.value,
                    "status": ticket.status.value
                }
            )
        
        return ticket

    @staticmethod
    async def _trigger_ticket_webhook(
        db: Session,
        ticket_id: int,
        event_type: str
    ) -> None:
        """
        Trigger a webhook for a ticket event.

        Args:
            db: Database session
            ticket_id: ID of the ticket
            event_type: Type of event (created, updated, etc.)
        """
        # Get the ticket
        ticket = await SupportTicketService.get_ticket(db, ticket_id=ticket_id)
        if not ticket:
            logger.error(f"Ticket {ticket_id} not found for webhook trigger")
            return
        
        # Prepare webhook payload
        payload = {
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "category": ticket.category.value,
            "created_by": ticket.created_by,
            "created_at": ticket.created_at.isoformat(),
            "event_type": event_type
        }
        
        # Trigger webhook
        await WebhookService.trigger_event(
            event_type=event_type,
            payload=payload
        )

    @staticmethod
    async def get_ticket(
        db: Session,
        ticket_id: int,
        user_id: int = None
    ) -> Optional[models.SupportTicket]:
        """
        Get a support ticket by ID.

        Args:
            db: Database session
            ticket_id: ID of the ticket to retrieve
            user_id: ID of the user requesting the ticket (for permission check)

        Returns:
            The support ticket if found and user has permission, None otherwise
        """
        ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
        
        # Check if ticket exists
        if not ticket:
            return None
        
        # Check if user has permission to view this ticket
        if user_id:
            # Creator can always view
            if user_id == ticket.created_by:
                return ticket
            
            # Assigned staff can view
            if ticket.assigned_to == user_id:
                return ticket
            
            # Admin users can view all tickets
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.is_staff:
                return ticket
                
            return None
        
        return ticket

    @staticmethod
    async def update_ticket_status(
        db: Session,
        ticket_id: int,
        status: models.TicketStatus,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> Optional[models.SupportTicket]:
        """
        Update a support ticket's status.

        Args:
            db: Database session
            ticket_id: ID of the ticket to update
            status: New status
            user_id: ID of the user updating the ticket
            background_tasks: Background tasks runner

        Returns:
            The updated support ticket if successful, None otherwise
        """
        ticket = await SupportTicketService.get_ticket(db, ticket_id=ticket_id, user_id=user_id)
        
        # Check if ticket exists and user has permission
        if not ticket:
            return None
        
        # Check if user has permission to update status
        user = db.query(User).filter(User.id == user_id).first()
        if not user or (not user.is_staff and user_id != ticket.created_by):
            return None
        
        # Update status
        ticket.status = status
        ticket.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ticket)
        
        # Trigger webhook in background if available
        if background_tasks:
            background_tasks.add_task(
                SupportTicketService._trigger_ticket_webhook,
                db,
                ticket.id,
                "ticket.status_updated"
            )
        
        return ticket

    @staticmethod
    async def add_ticket_response(
        db: Session,
        ticket_id: int,
        response_data: schemas.TicketResponseCreate,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> Optional[models.TicketResponse]:
        """
        Add a response to a support ticket.

        Args:
            db: Database session
            ticket_id: ID of the ticket to respond to
            response_data: Response data
            user_id: ID of the user adding the response
            background_tasks: Background tasks runner

        Returns:
            The created ticket response if successful, None otherwise
        """
        ticket = await SupportTicketService.get_ticket(db, ticket_id=ticket_id, user_id=user_id)
        
        # Check if ticket exists and user has permission
        if not ticket:
            return None
        
        # Create the response
        response = models.TicketResponse(
            ticket_id=ticket_id,
            response_text=response_data.response_text,
            created_by=user_id,
            is_internal=response_data.is_internal
        )
        
        # Save to database
        db.add(response)
        
        # Update ticket
        ticket.updated_at = datetime.utcnow()
        
        # If staff is responding and ticket is waiting for customer, update status
        if user_id != ticket.customer_id and ticket.status == models.TicketStatus.WAITING_CUSTOMER:
            ticket.status = models.TicketStatus.IN_PROGRESS
        
        # If customer is responding and ticket is waiting for staff, update status
        if user_id == ticket.customer_id and ticket.status in [models.TicketStatus.WAITING_THIRD_PARTY, models.TicketStatus.IN_PROGRESS]:
            ticket.status = models.TicketStatus.WAITING_CUSTOMER
        
        db.commit()
        db.refresh(response)
        
        # Trigger webhook in background if available
        if background_tasks:
            background_tasks.add_task(
                WebhookService.trigger_event,
                "ticket.response_added",
                {
                    "ticket_id": ticket.id,
                    "response_id": response.id,
                    "responder_id": user_id,
                    "is_internal": response_data.is_internal
                }
            )
        
        return response

    @staticmethod
    async def assign_ticket(
        db: Session,
        ticket_id: int,
        staff_id: int,
        assigner_id: int,
        background_tasks: BackgroundTasks = None
    ) -> Optional[models.SupportTicket]:
        """
        Assign a support ticket to a staff member.

        Args:
            db: Database session
            ticket_id: ID of the ticket to assign
            staff_id: ID of the staff member to assign the ticket to
            assigner_id: ID of the user making the assignment
            background_tasks: Background tasks runner

        Returns:
            The updated support ticket if successful, None otherwise
        """
        ticket = await SupportTicketService.get_ticket(db, ticket_id=ticket_id, user_id=assigner_id)
        
        # Check if ticket exists and user has permission
        if not ticket:
            return None
        
        # Check if assigner has permission to assign tickets
        assigner = db.query(User).filter(User.id == assigner_id).first()
        if not assigner or not assigner.is_staff:
            return None
        
        # Check if assignee is a staff member
        staff = db.query(User).filter(User.id == staff_id).first()
        if not staff or not staff.is_staff:
            return None
        
        # Assign ticket
        ticket.assigned_to = staff_id
        ticket.updated_at = datetime.utcnow()
        
        # If ticket was unassigned, update status
        if ticket.status == models.TicketStatus.OPEN:
            ticket.status = models.TicketStatus.IN_PROGRESS
        
        db.commit()
        db.refresh(ticket)
        
        # Trigger webhook in background if available
        if background_tasks:
            background_tasks.add_task(
                SupportTicketService._trigger_ticket_webhook,
                db,
                ticket.id,
                "ticket.assigned"
            )
        
        return ticket

    @staticmethod
    async def get_user_tickets(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[models.TicketStatus] = None
    ) -> List[models.SupportTicket]:
        """
        Get support tickets for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of tickets to skip (for pagination)
            limit: Maximum number of tickets to return
            status: Filter by ticket status

        Returns:
            List of support tickets
        """
        query = db.query(models.SupportTicket).filter(models.SupportTicket.created_by == user_id)
        
        # Filter by status if provided
        if status:
            query = query.filter(models.SupportTicket.status == status)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(models.SupportTicket.created_at))
        
        # Apply pagination
        tickets = query.offset(skip).limit(limit).all()
        
        return tickets

    @staticmethod
    async def get_staff_tickets(
        db: Session,
        staff_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[models.TicketStatus] = None,
        include_unassigned: bool = False
    ) -> List[models.SupportTicket]:
        """
        Get support tickets assigned to a staff member.

        Args:
            db: Database session
            staff_id: ID of the staff member
            skip: Number of tickets to skip (for pagination)
            limit: Maximum number of tickets to return
            status: Filter by ticket status
            include_unassigned: Whether to include unassigned tickets

        Returns:
            List of support tickets
        """
        if include_unassigned:
            query = db.query(models.SupportTicket).filter(
                (models.SupportTicket.assigned_to == staff_id) | 
                (models.SupportTicket.assigned_to.is_(None))
            )
        else:
            query = db.query(models.SupportTicket).filter(models.SupportTicket.assigned_to == staff_id)
        
        # Filter by status if provided
        if status:
            query = query.filter(models.SupportTicket.status == status)
        
        # Order by priority (highest first) and then by creation date (oldest first)
        query = query.order_by(
            models.SupportTicket.priority.desc(),
            models.SupportTicket.created_at
        )
        
        # Apply pagination
        tickets = query.offset(skip).limit(limit).all()
        
        return tickets
