"""
Communication service for the Customer Management Module.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend_core.exceptions import NotFoundException, ValidationException
from modules.customer.models import (
    Customer,
    CommunicationPreference,
    CommunicationType
)

logger = logging.getLogger(__name__)


class CommunicationService:
    """Service for managing customer communication preferences."""
    
    async def get_customer_preferences(
        self,
        session: AsyncSession,
        customer_id: int
    ) -> List[CommunicationPreference]:
        """
        Get communication preferences for a customer.
        
        Args:
            session: Database session
            customer_id: Customer ID
            
        Returns:
            List of communication preferences
            
        Raises:
            NotFoundException: If customer not found
        """
        # Check if customer exists
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with ID {customer_id} not found")
        
        # Get preferences
        result = await session.execute(
            select(CommunicationPreference)
            .where(CommunicationPreference.customer_id == customer_id)
        )
        preferences = result.scalars().all()
        
        return preferences
    
    async def get_preference(
        self,
        session: AsyncSession,
        preference_id: int
    ) -> CommunicationPreference:
        """
        Get a communication preference by ID.
        
        Args:
            session: Database session
            preference_id: Preference ID
            
        Returns:
            Communication preference
            
        Raises:
            NotFoundException: If preference not found
        """
        result = await session.execute(
            select(CommunicationPreference)
            .where(CommunicationPreference.id == preference_id)
        )
        preference = result.scalars().first()
        
        if not preference:
            raise NotFoundException(f"Communication preference with ID {preference_id} not found")
        
        return preference
    
    async def create_preference(
        self,
        session: AsyncSession,
        customer_id: int,
        communication_type: CommunicationType,
        enabled: bool = True,
        billing_notifications: bool = True,
        service_notifications: bool = True,
        marketing_communications: bool = False,
        technical_notifications: bool = True,
        emergency_alerts: bool = True
    ) -> CommunicationPreference:
        """
        Create a communication preference.
        
        Args:
            session: Database session
            customer_id: Customer ID
            communication_type: Type of communication
            enabled: Whether this communication type is enabled
            billing_notifications: Whether to send billing notifications
            service_notifications: Whether to send service notifications
            marketing_communications: Whether to send marketing communications
            technical_notifications: Whether to send technical notifications
            emergency_alerts: Whether to send emergency alerts
            
        Returns:
            Created communication preference
            
        Raises:
            NotFoundException: If customer not found
            ValidationException: If preference already exists for this type
        """
        # Check if customer exists
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise NotFoundException(f"Customer with ID {customer_id} not found")
        
        # Check if preference already exists for this type
        existing_result = await session.execute(
            select(CommunicationPreference)
            .where(
                CommunicationPreference.customer_id == customer_id,
                CommunicationPreference.communication_type == communication_type
            )
        )
        existing = existing_result.scalars().first()
        
        if existing:
            raise ValidationException(
                f"Communication preference for type {communication_type.value} already exists"
            )
        
        # Create preference
        preference = CommunicationPreference(
            customer_id=customer_id,
            communication_type=communication_type,
            enabled=enabled,
            billing_notifications=billing_notifications,
            service_notifications=service_notifications,
            marketing_communications=marketing_communications,
            technical_notifications=technical_notifications,
            emergency_alerts=emergency_alerts
        )
        
        session.add(preference)
        await session.flush()
        
        return preference
    
    async def update_preference(
        self,
        session: AsyncSession,
        preference_id: int,
        **kwargs
    ) -> CommunicationPreference:
        """
        Update a communication preference.
        
        Args:
            session: Database session
            preference_id: Preference ID
            **kwargs: Fields to update
            
        Returns:
            Updated communication preference
            
        Raises:
            NotFoundException: If preference not found
        """
        # Get preference
        preference = await self.get_preference(session, preference_id)
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(preference, key):
                setattr(preference, key, value)
        
        return preference
    
    async def delete_preference(
        self,
        session: AsyncSession,
        preference_id: int
    ) -> None:
        """
        Delete a communication preference.
        
        Args:
            session: Database session
            preference_id: Preference ID
            
        Raises:
            NotFoundException: If preference not found
        """
        # Get preference to ensure it exists
        preference = await self.get_preference(session, preference_id)
        
        # Delete preference
        await session.delete(preference)
    
    async def get_customers_by_preference(
        self,
        session: AsyncSession,
        communication_type: CommunicationType,
        enabled: bool = True,
        notification_type: Optional[str] = None
    ) -> List[Customer]:
        """
        Get customers who have a specific communication preference enabled.
        
        Args:
            session: Database session
            communication_type: Type of communication
            enabled: Whether the preference is enabled
            notification_type: Specific notification type to filter by
            
        Returns:
            List of customers
        """
        # Build query
        query = (
            select(Customer)
            .join(CommunicationPreference)
            .where(
                CommunicationPreference.communication_type == communication_type,
                CommunicationPreference.enabled == enabled
            )
        )
        
        # Add notification type filter if specified
        if notification_type:
            if hasattr(CommunicationPreference, notification_type):
                query = query.where(getattr(CommunicationPreference, notification_type) == True)
        
        # Execute query
        result = await session.execute(query)
        customers = result.scalars().all()
        
        return customers
