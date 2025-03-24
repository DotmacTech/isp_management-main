"""
Customer service for the CRM & Ticketing module.

This service provides functionality for managing customer data in the CRM system,
including customer contacts, notes, and interaction history.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from fastapi import HTTPException, status

from backend_core.database import get_db
from modules.customer_management.services import CustomerService as CoreCustomerService
from ..models.customer import Customer, CustomerContact, CustomerNote
from ..schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerContactCreate, CustomerContactUpdate, CustomerContactResponse,
    CustomerNoteCreate, CustomerNoteUpdate, CustomerNoteResponse
)
from ..models.common import ContactType, ContactMethod


class CustomerService:
    """Service for managing customer data in the CRM system."""
    
    def __init__(self, db: Session):
        """Initialize the customer service with a database session."""
        self.db = db
        self.core_customer_service = CoreCustomerService(db)
    
    def get_customer(self, customer_id: int) -> Customer:
        """
        Get a customer by ID.
        
        Args:
            customer_id: The ID of the customer to retrieve
            
        Returns:
            The customer object
            
        Raises:
            HTTPException: If the customer is not found
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found"
            )
        return customer
    
    def get_customer_by_core_id(self, core_customer_id: int) -> Optional[Customer]:
        """
        Get a customer by core customer ID.
        
        Args:
            core_customer_id: The ID of the core customer record
            
        Returns:
            The customer object or None if not found
        """
        return self.db.query(Customer).filter(Customer.core_customer_id == core_customer_id).first()
    
    def list_customers(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Customer]:
        """
        List customers with optional filtering, sorting, and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search term to filter by
            sort_by: Field to sort by
            sort_desc: Whether to sort in descending order
            filters: Additional filters to apply
            
        Returns:
            List of customer objects
        """
        query = self.db.query(Customer)
        
        # Apply search filter
        if search:
            # Join with core customer to search by name, email, etc.
            # This depends on your core customer model structure
            pass
        
        # Apply additional filters
        if filters:
            for field, value in filters.items():
                if hasattr(Customer, field):
                    query = query.filter(getattr(Customer, field) == value)
        
        # Apply sorting
        if sort_by and hasattr(Customer, sort_by):
            order_func = desc if sort_desc else asc
            query = query.order_by(order_func(getattr(Customer, sort_by)))
        else:
            # Default sort by updated_at
            query = query.order_by(desc(Customer.updated_at))
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()
    
    def count_customers(
        self, 
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count customers with optional filtering.
        
        Args:
            search: Search term to filter by
            filters: Additional filters to apply
            
        Returns:
            Total count of matching customers
        """
        query = self.db.query(func.count(Customer.id))
        
        # Apply search filter
        if search:
            # Join with core customer to search by name, email, etc.
            pass
        
        # Apply additional filters
        if filters:
            for field, value in filters.items():
                if hasattr(Customer, field):
                    query = query.filter(getattr(Customer, field) == value)
        
        return query.scalar()
    
    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """
        Create a new customer.
        
        Args:
            customer_data: Data for the new customer
            
        Returns:
            The created customer object
            
        Raises:
            HTTPException: If the core customer does not exist or if a CRM customer
                          already exists for the core customer
        """
        # Check if core customer exists
        core_customer = self.core_customer_service.get_customer(customer_data.core_customer_id)
        if not core_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Core customer with ID {customer_data.core_customer_id} not found"
            )
        
        # Check if CRM customer already exists for this core customer
        existing = self.get_customer_by_core_id(customer_data.core_customer_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"CRM customer already exists for core customer ID {customer_data.core_customer_id}"
            )
        
        # Create new customer
        customer = Customer(**customer_data.dict())
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer
    
    def update_customer(self, customer_id: int, customer_data: CustomerUpdate) -> Customer:
        """
        Update an existing customer.
        
        Args:
            customer_id: The ID of the customer to update
            customer_data: New data for the customer
            
        Returns:
            The updated customer object
            
        Raises:
            HTTPException: If the customer is not found
        """
        customer = self.get_customer(customer_id)
        
        # Update fields
        for field, value in customer_data.dict(exclude_unset=True).items():
            setattr(customer, field, value)
        
        # Update last_contact_date if not set
        if not customer.last_contact_date:
            customer.last_contact_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(customer)
        return customer
    
    def delete_customer(self, customer_id: int) -> bool:
        """
        Delete a customer.
        
        Args:
            customer_id: The ID of the customer to delete
            
        Returns:
            True if the customer was deleted
            
        Raises:
            HTTPException: If the customer is not found
        """
        customer = self.get_customer(customer_id)
        self.db.delete(customer)
        self.db.commit()
        return True
    
    # Customer contact methods
    
    def get_customer_contact(self, contact_id: int) -> CustomerContact:
        """
        Get a customer contact by ID.
        
        Args:
            contact_id: The ID of the contact to retrieve
            
        Returns:
            The contact object
            
        Raises:
            HTTPException: If the contact is not found
        """
        contact = self.db.query(CustomerContact).filter(CustomerContact.id == contact_id).first()
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer contact with ID {contact_id} not found"
            )
        return contact
    
    def list_customer_contacts(
        self, 
        customer_id: int,
        contact_type: Optional[ContactType] = None,
        contact_method: Optional[ContactMethod] = None
    ) -> List[CustomerContact]:
        """
        List contacts for a customer with optional filtering.
        
        Args:
            customer_id: The ID of the customer
            contact_type: Filter by contact type
            contact_method: Filter by contact method
            
        Returns:
            List of contact objects
        """
        query = self.db.query(CustomerContact).filter(CustomerContact.customer_id == customer_id)
        
        if contact_type:
            query = query.filter(CustomerContact.contact_type == contact_type)
        
        if contact_method:
            query = query.filter(CustomerContact.contact_method == contact_method)
        
        return query.all()
    
    def create_customer_contact(self, contact_data: CustomerContactCreate) -> CustomerContact:
        """
        Create a new customer contact.
        
        Args:
            contact_data: Data for the new contact
            
        Returns:
            The created contact object
            
        Raises:
            HTTPException: If the customer is not found
        """
        # Check if customer exists
        self.get_customer(contact_data.customer_id)
        
        # If this is a primary contact, update existing primary contacts of the same type
        if contact_data.is_primary:
            existing_primary = self.db.query(CustomerContact).filter(
                CustomerContact.customer_id == contact_data.customer_id,
                CustomerContact.contact_type == contact_data.contact_type,
                CustomerContact.is_primary == True
            ).all()
            
            for contact in existing_primary:
                contact.is_primary = False
        
        # Create new contact
        contact = CustomerContact(**contact_data.dict())
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        
        # Update customer's last_contact_date
        customer = self.get_customer(contact_data.customer_id)
        customer.last_contact_date = datetime.utcnow()
        self.db.commit()
        
        return contact
    
    def update_customer_contact(
        self, 
        contact_id: int, 
        contact_data: CustomerContactUpdate
    ) -> CustomerContact:
        """
        Update an existing customer contact.
        
        Args:
            contact_id: The ID of the contact to update
            contact_data: New data for the contact
            
        Returns:
            The updated contact object
            
        Raises:
            HTTPException: If the contact is not found
        """
        contact = self.get_customer_contact(contact_id)
        
        # If setting as primary, update existing primary contacts
        if contact_data.is_primary and contact_data.is_primary != contact.is_primary:
            existing_primary = self.db.query(CustomerContact).filter(
                CustomerContact.customer_id == contact.customer_id,
                CustomerContact.contact_type == (contact_data.contact_type or contact.contact_type),
                CustomerContact.is_primary == True,
                CustomerContact.id != contact_id
            ).all()
            
            for other_contact in existing_primary:
                other_contact.is_primary = False
        
        # Update fields
        for field, value in contact_data.dict(exclude_unset=True).items():
            setattr(contact, field, value)
        
        self.db.commit()
        self.db.refresh(contact)
        return contact
    
    def delete_customer_contact(self, contact_id: int) -> bool:
        """
        Delete a customer contact.
        
        Args:
            contact_id: The ID of the contact to delete
            
        Returns:
            True if the contact was deleted
            
        Raises:
            HTTPException: If the contact is not found
        """
        contact = self.get_customer_contact(contact_id)
        self.db.delete(contact)
        self.db.commit()
        return True
    
    # Customer note methods
    
    def get_customer_note(self, note_id: int) -> CustomerNote:
        """
        Get a customer note by ID.
        
        Args:
            note_id: The ID of the note to retrieve
            
        Returns:
            The note object
            
        Raises:
            HTTPException: If the note is not found
        """
        note = self.db.query(CustomerNote).filter(CustomerNote.id == note_id).first()
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer note with ID {note_id} not found"
            )
        return note
    
    def list_customer_notes(
        self, 
        customer_id: int,
        include_private: bool = False,
        user_id: Optional[int] = None
    ) -> List[CustomerNote]:
        """
        List notes for a customer.
        
        Args:
            customer_id: The ID of the customer
            include_private: Whether to include private notes
            user_id: The ID of the user making the request (for private note access)
            
        Returns:
            List of note objects
        """
        query = self.db.query(CustomerNote).filter(CustomerNote.customer_id == customer_id)
        
        # Filter out private notes if needed
        if not include_private:
            query = query.filter(CustomerNote.is_private == False)
        elif user_id:
            # Include private notes created by the user
            query = query.filter(
                (CustomerNote.is_private == False) | 
                ((CustomerNote.is_private == True) & (CustomerNote.created_by == user_id))
            )
        
        # Order by creation date, newest first
        query = query.order_by(desc(CustomerNote.created_at))
        
        return query.all()
    
    def create_customer_note(self, note_data: CustomerNoteCreate, user_id: int) -> CustomerNote:
        """
        Create a new customer note.
        
        Args:
            note_data: Data for the new note
            user_id: The ID of the user creating the note
            
        Returns:
            The created note object
            
        Raises:
            HTTPException: If the customer is not found
        """
        # Check if customer exists
        self.get_customer(note_data.customer_id)
        
        # Create new note
        note = CustomerNote(**note_data.dict(), created_by=user_id)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        
        # Update customer's last_contact_date
        customer = self.get_customer(note_data.customer_id)
        customer.last_contact_date = datetime.utcnow()
        self.db.commit()
        
        return note
    
    def update_customer_note(
        self, 
        note_id: int, 
        note_data: CustomerNoteUpdate,
        user_id: int
    ) -> CustomerNote:
        """
        Update an existing customer note.
        
        Args:
            note_id: The ID of the note to update
            note_data: New data for the note
            user_id: The ID of the user updating the note
            
        Returns:
            The updated note object
            
        Raises:
            HTTPException: If the note is not found or if the user is not authorized
        """
        note = self.get_customer_note(note_id)
        
        # Check if user is authorized to update the note
        if note.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this note"
            )
        
        # Update fields
        for field, value in note_data.dict(exclude_unset=True).items():
            setattr(note, field, value)
        
        self.db.commit()
        self.db.refresh(note)
        return note
    
    def delete_customer_note(self, note_id: int, user_id: int) -> bool:
        """
        Delete a customer note.
        
        Args:
            note_id: The ID of the note to delete
            user_id: The ID of the user deleting the note
            
        Returns:
            True if the note was deleted
            
        Raises:
            HTTPException: If the note is not found or if the user is not authorized
        """
        note = self.get_customer_note(note_id)
        
        # Check if user is authorized to delete the note
        if note.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this note"
            )
        
        self.db.delete(note)
        self.db.commit()
        return True
