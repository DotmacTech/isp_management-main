"""
Services for the Customer Management Module.
"""

import logging
import uuid
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import expression

from backend_core.exceptions import (
    NotFoundException, 
    ValidationException, 
    DuplicateException, 
    AuthenticationException
)
from backend_core.utils.security import hash_password, verify_password
from modules.customer.models import (
    Customer, 
    CustomerAddress, 
    CustomerContact, 
    SubscriptionState, 
    CommunicationPreference,
    CustomerDocument,
    CustomerNote,
    EmailVerification,
    CustomerTagDefinition,
    CustomerType,
    CustomerStatus,
    VerificationStatus,
    CommunicationType
)
from modules.customer.utils import (
    generate_customer_number,
    validate_email,
    validate_phone,
    generate_verification_token,
    generate_portal_id
)

logger = logging.getLogger(__name__)


class CustomerService:
    """Service for managing customer data."""
    
    async def create_customer(
        self,
        session: AsyncSession,
        customer_type: CustomerType,
        email: str = None,
        phone: str = None,
        first_name: str = None,
        last_name: str = None,
        company_name: str = None,
        tax_id: str = None,
        registration_number: str = None,
        username: str = None,
        password: str = None,
        status: CustomerStatus = CustomerStatus.PENDING,
        subscription_state: SubscriptionState = SubscriptionState.PENDING_ACTIVATION,
        marketing_consent: bool = False,
        referral_source: str = None,
        properties: Dict[str, Any] = None,
        **kwargs
    ) -> Customer:
        """
        Create a new customer.
        
        Args:
            session: Database session
            customer_type: Type of customer (individual, business, etc.)
            email: Customer email
            phone: Customer phone number
            first_name: Customer first name (for individuals)
            last_name: Customer last name (for individuals)
            company_name: Company name (for businesses)
            tax_id: Tax ID (for businesses)
            registration_number: Business registration number
            username: Username for customer portal
            password: Password for customer portal
            status: Customer status
            subscription_state: Subscription state
            marketing_consent: Whether customer consents to marketing
            referral_source: How the customer was referred
            properties: Additional properties
            
        Returns:
            Newly created customer
            
        Raises:
            ValidationException: If required fields are missing
            DuplicateException: If a customer with the same email or username exists
        """
        # Validate required fields based on customer type
        if customer_type == CustomerType.INDIVIDUAL:
            if not first_name or not last_name:
                raise ValidationException("First name and last name are required for individual customers")
        elif customer_type == CustomerType.BUSINESS:
            if not company_name:
                raise ValidationException("Company name is required for business customers")
        
        # Validate email if provided
        if email:
            if not validate_email(email):
                raise ValidationException(f"Invalid email format: {email}")
            
            # Check for duplicate email
            existing_customer = await session.execute(
                select(Customer).where(Customer.email == email)
            )
            if existing_customer.scalars().first():
                raise DuplicateException(f"Customer with email {email} already exists")
        
        # Validate phone if provided
        if phone and not validate_phone(phone):
            raise ValidationException(f"Invalid phone format: {phone}")
        
        # Check for duplicate username if provided
        if username:
            existing_username = await session.execute(
                select(Customer).where(Customer.username == username)
            )
            if existing_username.scalars().first():
                raise DuplicateException(f"Username {username} is already taken")
        
        # Generate customer number
        customer_number = generate_customer_number()
        
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = hash_password(password)
        
        # Create customer
        customer = Customer(
            uuid=uuid.uuid4(),
            customer_number=customer_number,
            customer_type=customer_type,
            status=status,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            tax_id=tax_id,
            registration_number=registration_number,
            email=email,
            phone=phone,
            username=username,
            password_hash=password_hash,
            subscription_state=subscription_state,
            marketing_consent=marketing_consent,
            marketing_consent_date=datetime.utcnow() if marketing_consent else None,
            referral_source=referral_source,
            properties=properties
        )
        
        session.add(customer)
        await session.flush()
        
        # Generate and set portal ID
        customer.portal_id = generate_portal_id(customer.id)
        
        # Create default communication preferences
        for comm_type in CommunicationType:
            preference = CommunicationPreference(
                customer_id=customer.id,
                communication_type=comm_type,
                enabled=True,
                marketing_communications=marketing_consent
            )
            session.add(preference)
        
        return customer
    
    async def get_customer(
        self,
        session: AsyncSession,
        customer_id: int,
        include_addresses: bool = False,
        include_contacts: bool = False,
        include_preferences: bool = False,
        include_documents: bool = False,
        include_notes: bool = False,
        include_tags: bool = False
    ) -> Customer:
        """
        Get a customer by ID.
        
        Args:
            session: Database session
            customer_id: Customer ID
            include_addresses: Whether to include customer addresses
            include_contacts: Whether to include customer contacts
            include_preferences: Whether to include communication preferences
            include_documents: Whether to include customer documents
            include_notes: Whether to include customer notes
            include_tags: Whether to include customer tags
            
        Returns:
            Customer object
            
        Raises:
            NotFoundException: If customer not found
        """
        query = select(Customer).where(Customer.id == customer_id)
        
        # Include related entities if requested
        if include_addresses:
            query = query.options(selectinload(Customer.addresses))
        if include_contacts:
            query = query.options(selectinload(Customer.contacts))
        if include_preferences:
            query = query.options(selectinload(Customer.communication_preferences))
        if include_documents:
            query = query.options(selectinload(Customer.documents))
        if include_notes:
            query = query.options(selectinload(Customer.customer_notes))
        if include_tags:
            query = query.options(selectinload(Customer.tags))
        
        result = await session.execute(query)
        customer = result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with ID {customer_id} not found")
        
        return customer
    
    async def get_customer_by_email(
        self,
        session: AsyncSession,
        email: str
    ) -> Customer:
        """
        Get a customer by email.
        
        Args:
            session: Database session
            email: Customer email
            
        Returns:
            Customer object
            
        Raises:
            NotFoundException: If customer not found
        """
        result = await session.execute(
            select(Customer).where(Customer.email == email)
        )
        customer = result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with email {email} not found")
        
        return customer
    
    async def get_customer_by_username(
        self,
        session: AsyncSession,
        username: str
    ) -> Customer:
        """
        Get a customer by username.
        
        Args:
            session: Database session
            username: Customer username
            
        Returns:
            Customer object
            
        Raises:
            NotFoundException: If customer not found
        """
        result = await session.execute(
            select(Customer).where(Customer.username == username)
        )
        customer = result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with username {username} not found")
        
        return customer
    
    async def get_customers(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        customer_type: Optional[CustomerType] = None,
        status: Optional[CustomerStatus] = None,
        subscription_state: Optional[SubscriptionState] = None,
        search: Optional[str] = None,
        tag_ids: Optional[List[int]] = None,
        include_addresses: bool = False,
        include_contacts: bool = False
    ) -> Tuple[List[Customer], int]:
        """
        Get a list of customers with optional filtering.
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            customer_type: Filter by customer type
            status: Filter by customer status
            subscription_state: Filter by subscription state
            search: Search term for name, email, phone, or customer number
            tag_ids: Filter by tag IDs
            include_addresses: Whether to include customer addresses
            include_contacts: Whether to include customer contacts
            
        Returns:
            Tuple of (list of customers, total count)
        """
        # Build query
        query = select(Customer)
        count_query = select(func.count(Customer.id))
        
        # Apply filters
        filters = []
        if customer_type:
            filters.append(Customer.customer_type == customer_type)
        if status:
            filters.append(Customer.status == status)
        if subscription_state:
            filters.append(Customer.subscription_state == subscription_state)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            search_filter = or_(
                Customer.first_name.ilike(search_term),
                Customer.last_name.ilike(search_term),
                Customer.company_name.ilike(search_term),
                Customer.email.ilike(search_term),
                Customer.phone.ilike(search_term),
                Customer.customer_number.ilike(search_term)
            )
            filters.append(search_filter)
        
        # Apply tag filter
        if tag_ids:
            # This requires a join with the association table
            query = query.join(Customer.tags).filter(CustomerTagDefinition.id.in_(tag_ids))
            count_query = count_query.join(Customer.tags).filter(CustomerTagDefinition.id.in_(tag_ids))
        
        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))
            count_query = count_query.filter(and_(*filters))
        
        # Include related entities if requested
        if include_addresses:
            query = query.options(selectinload(Customer.addresses))
        if include_contacts:
            query = query.options(selectinload(Customer.contacts))
        
        # Get total count
        count_result = await session.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await session.execute(query)
        customers = result.scalars().all()
        
        return customers, total_count
    
    async def update_customer(
        self,
        session: AsyncSession,
        customer_id: int,
        **kwargs
    ) -> Customer:
        """
        Update a customer.
        
        Args:
            session: Database session
            customer_id: Customer ID
            **kwargs: Fields to update
            
        Returns:
            Updated customer
            
        Raises:
            NotFoundException: If customer not found
            ValidationException: If validation fails
            DuplicateException: If update would create a duplicate
        """
        # Get customer
        customer = await self.get_customer(session, customer_id)
        
        # Check for duplicate email
        if 'email' in kwargs and kwargs['email'] != customer.email:
            if not validate_email(kwargs['email']):
                raise ValidationException(f"Invalid email format: {kwargs['email']}")
                
            existing_email = await session.execute(
                select(Customer).where(
                    Customer.email == kwargs['email'],
                    Customer.id != customer_id
                )
            )
            if existing_email.scalars().first():
                raise DuplicateException(f"Customer with email {kwargs['email']} already exists")
        
        # Check for duplicate username
        if 'username' in kwargs and kwargs['username'] != customer.username:
            existing_username = await session.execute(
                select(Customer).where(
                    Customer.username == kwargs['username'],
                    Customer.id != customer_id
                )
            )
            if existing_username.scalars().first():
                raise DuplicateException(f"Username {kwargs['username']} is already taken")
        
        # Handle password update
        if 'password' in kwargs:
            kwargs['password_hash'] = hash_password(kwargs.pop('password'))
        
        # Handle marketing consent update
        if 'marketing_consent' in kwargs and kwargs['marketing_consent'] != customer.marketing_consent:
            kwargs['marketing_consent_date'] = datetime.utcnow() if kwargs['marketing_consent'] else None
            
            # Update communication preferences
            await session.execute(
                update(CommunicationPreference)
                .where(
                    CommunicationPreference.customer_id == customer_id
                )
                .values(marketing_communications=kwargs['marketing_consent'])
            )
        
        # Update customer
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        return customer
    
    async def delete_customer(
        self,
        session: AsyncSession,
        customer_id: int
    ) -> None:
        """
        Delete a customer.
        
        Args:
            session: Database session
            customer_id: Customer ID
            
        Raises:
            NotFoundException: If customer not found
        """
        # Get customer to ensure it exists
        customer = await self.get_customer(session, customer_id)
        
        # Delete customer
        await session.delete(customer)
    
    async def authenticate_customer(
        self,
        session: AsyncSession,
        username_or_email: str,
        password: str
    ) -> Customer:
        """
        Authenticate a customer.
        
        Args:
            session: Database session
            username_or_email: Customer username or email
            password: Customer password
            
        Returns:
            Authenticated customer
            
        Raises:
            AuthenticationException: If authentication fails
        """
        # Check if input is email or username
        is_email = '@' in username_or_email
        
        # Query customer
        if is_email:
            query = select(Customer).where(Customer.email == username_or_email)
        else:
            query = select(Customer).where(Customer.username == username_or_email)
        
        result = await session.execute(query)
        customer = result.scalars().first()
        
        # Check if customer exists
        if not customer:
            raise AuthenticationException("Invalid credentials")
        
        # Check if customer is active
        if customer.status != CustomerStatus.ACTIVE:
            raise AuthenticationException("Account is not active")
        
        # Verify password
        if not customer.password_hash or not verify_password(password, customer.password_hash):
            raise AuthenticationException("Invalid credentials")
        
        return customer
    
    async def change_subscription_state(
        self,
        session: AsyncSession,
        customer_id: int,
        new_state: SubscriptionState,
        update_dates: bool = True
    ) -> Customer:
        """
        Change a customer's subscription state.
        
        Args:
            session: Database session
            customer_id: Customer ID
            new_state: New subscription state
            update_dates: Whether to update subscription dates
            
        Returns:
            Updated customer
            
        Raises:
            NotFoundException: If customer not found
        """
        # Get customer
        customer = await self.get_customer(session, customer_id)
        
        # Update subscription state
        customer.subscription_state = new_state
        
        # Update dates if requested
        if update_dates:
            now = datetime.utcnow()
            
            if new_state in [SubscriptionState.ACTIVE, SubscriptionState.TRIAL]:
                if not customer.subscription_start_date:
                    customer.subscription_start_date = now
            elif new_state == SubscriptionState.CANCELLED:
                customer.subscription_end_date = now
        
        return customer
    
    async def add_tag_to_customer(
        self,
        session: AsyncSession,
        customer_id: int,
        tag_id: int
    ) -> Customer:
        """
        Add a tag to a customer.
        
        Args:
            session: Database session
            customer_id: Customer ID
            tag_id: Tag ID
            
        Returns:
            Updated customer
            
        Raises:
            NotFoundException: If customer or tag not found
        """
        # Get customer
        customer = await self.get_customer(session, customer_id, include_tags=True)
        
        # Get tag
        tag_result = await session.execute(
            select(CustomerTagDefinition).where(CustomerTagDefinition.id == tag_id)
        )
        tag = tag_result.scalars().first()
        
        if not tag:
            raise NotFoundException(f"Tag with ID {tag_id} not found")
        
        # Add tag if not already added
        if tag not in customer.tags:
            customer.tags.append(tag)
        
        return customer
    
    async def remove_tag_from_customer(
        self,
        session: AsyncSession,
        customer_id: int,
        tag_id: int
    ) -> Customer:
        """
        Remove a tag from a customer.
        
        Args:
            session: Database session
            customer_id: Customer ID
            tag_id: Tag ID
            
        Returns:
            Updated customer
            
        Raises:
            NotFoundException: If customer or tag not found
        """
        # Get customer
        customer = await self.get_customer(session, customer_id, include_tags=True)
        
        # Get tag
        tag_result = await session.execute(
            select(CustomerTagDefinition).where(CustomerTagDefinition.id == tag_id)
        )
        tag = tag_result.scalars().first()
        
        if not tag:
            raise NotFoundException(f"Tag with ID {tag_id} not found")
        
        # Remove tag if present
        if tag in customer.tags:
            customer.tags.remove(tag)
        
        return customer
