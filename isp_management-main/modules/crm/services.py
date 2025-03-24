from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend_core.models import Customer, Ticket, TicketComment, User
from .schemas import (
    CustomerCreate,
    CustomerResponse,
    TicketCreate,
    TicketResponse,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketAssignmentUpdate,
    TicketStatusUpdate,
    CustomerSearch,
    CustomerStatus,
    TicketStatus
)

class CRMService:
    def __init__(self, db: Session):
        self.db = db

    # Customer Management
    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer profile."""
        # Check if user exists
        user = self.db.query(User).filter(User.id == customer_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {customer_data.user_id} not found"
            )
        
        # Check if customer already exists for this user
        existing_customer = self.db.query(Customer).filter(
            Customer.user_id == customer_data.user_id
        ).first()
        
        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer profile already exists for user ID {customer_data.user_id}"
            )
        
        # Create new customer
        customer = Customer(**customer_data.dict())
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def get_customer(self, customer_id: int) -> Customer:
        """Get a customer by ID."""
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        return customer

    def get_customer_by_user_id(self, user_id: int) -> Customer:
        """Get a customer by user ID."""
        customer = self.db.query(Customer).filter(Customer.user_id == user_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer profile not found for user ID {user_id}"
            )
        return customer

    def update_customer(self, customer_id: int, customer_data: Dict[str, Any]) -> Customer:
        """Update a customer's information."""
        customer = self.get_customer(customer_id)
        
        for key, value in customer_data.items():
            setattr(customer, key, value)
        
        customer.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def search_customers(self, search_params: CustomerSearch) -> List[Customer]:
        """Search for customers based on query and status."""
        query = self.db.query(Customer)
        
        if search_params.status:
            query = query.filter(Customer.status == search_params.status)
        
        if search_params.query:
            search_term = f"%{search_params.query}%"
            query = query.filter(
                or_(
                    Customer.full_name.ilike(search_term),
                    Customer.email.ilike(search_term),
                    Customer.phone.ilike(search_term)
                )
            )
        
        return query.offset(search_params.offset).limit(search_params.limit).all()

    # Ticket Management
    def create_ticket(self, ticket_data: TicketCreate) -> Ticket:
        """Create a new support ticket."""
        # Check if customer exists
        customer = self.db.query(Customer).filter(Customer.id == ticket_data.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {ticket_data.customer_id} not found"
            )
        
        # Create new ticket
        ticket = Ticket(**ticket_data.dict(), status=TicketStatus.NEW)
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def get_ticket(self, ticket_id: int) -> Ticket:
        """Get a ticket by ID."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        return ticket

    def get_customer_tickets(self, customer_id: int) -> List[Ticket]:
        """Get all tickets for a customer."""
        return self.db.query(Ticket).filter(Ticket.customer_id == customer_id).all()

    def assign_ticket(self, ticket_id: int, assignment_data: TicketAssignmentUpdate) -> Ticket:
        """Assign a ticket to an agent."""
        ticket = self.get_ticket(ticket_id)
        
        # Check if agent exists
        agent = self.db.query(User).filter(User.id == assignment_data.assigned_to).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {assignment_data.assigned_to} not found"
            )
        
        ticket.assigned_to = assignment_data.assigned_to
        ticket.status = TicketStatus.ASSIGNED
        ticket.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def update_ticket_status(self, ticket_id: int, status_data: TicketStatusUpdate, user_id: int) -> Ticket:
        """Update a ticket's status."""
        ticket = self.get_ticket(ticket_id)
        
        # Update status
        ticket.status = status_data.status
        ticket.updated_at = datetime.utcnow()
        
        # If resolving, set resolved_at
        if status_data.status == TicketStatus.RESOLVED and not ticket.resolved_at:
            ticket.resolved_at = datetime.utcnow()
        
        # If closing, set closed_at
        if status_data.status == TicketStatus.CLOSED and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(ticket)
        
        # Add a comment if provided
        if status_data.comment:
            self.add_ticket_comment(
                TicketCommentCreate(
                    ticket_id=ticket_id,
                    user_id=user_id,
                    comment=status_data.comment,
                    is_internal=True
                )
            )
        
        return ticket

    def add_ticket_comment(self, comment_data: TicketCommentCreate) -> TicketComment:
        """Add a comment to a ticket."""
        # Check if ticket exists
        ticket = self.db.query(Ticket).filter(Ticket.id == comment_data.ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {comment_data.ticket_id} not found"
            )
        
        # Check if user exists
        user = self.db.query(User).filter(User.id == comment_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {comment_data.user_id} not found"
            )
        
        # Create comment
        comment = TicketComment(**comment_data.dict())
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_ticket_comments(self, ticket_id: int, include_internal: bool = False) -> List[TicketComment]:
        """Get all comments for a ticket."""
        query = self.db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id)
        
        if not include_internal:
            query = query.filter(TicketComment.is_internal == False)
        
        return query.order_by(TicketComment.created_at).all()

    def get_ticket_statistics(self) -> Dict[str, Any]:
        """Get statistics about tickets."""
        total_tickets = self.db.query(func.count(Ticket.id)).scalar()
        open_tickets = self.db.query(func.count(Ticket.id)).filter(
            Ticket.status.in_([
                TicketStatus.NEW, 
                TicketStatus.ASSIGNED, 
                TicketStatus.IN_PROGRESS
            ])
        ).scalar()
        
        tickets_by_priority = {}
        for priority in ["p1", "p2", "p3", "p4"]:
            count = self.db.query(func.count(Ticket.id)).filter(Ticket.priority == priority).scalar()
            tickets_by_priority[priority] = count
        
        tickets_by_status = {}
        for status in [
            TicketStatus.NEW, 
            TicketStatus.ASSIGNED, 
            TicketStatus.IN_PROGRESS, 
            TicketStatus.PENDING_CUSTOMER, 
            TicketStatus.RESOLVED, 
            TicketStatus.CLOSED
        ]:
            count = self.db.query(func.count(Ticket.id)).filter(Ticket.status == status).scalar()
            tickets_by_status[status] = count
        
        # Average resolution time (in hours) for tickets resolved in the last 30 days
        thirty_days_ago = datetime.utcnow() - datetime.timedelta(days=30)
        avg_resolution_time = self.db.query(
            func.avg(
                func.extract('epoch', Ticket.resolved_at) - 
                func.extract('epoch', Ticket.created_at)
            ) / 3600  # Convert seconds to hours
        ).filter(
            Ticket.resolved_at != None,
            Ticket.resolved_at >= thirty_days_ago
        ).scalar() or 0
        
        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "tickets_by_priority": tickets_by_priority,
            "tickets_by_status": tickets_by_status,
            "avg_resolution_time_hours": round(avg_resolution_time, 2)
        }
