"""
Notification service for the Service Activation Module.

This module handles sending notifications to customers and staff
about service activation events.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend_core.exceptions import ServiceException
from modules.service_activation.models import (
    ServiceActivation,
    ActivationStatus
)


class NotificationService:
    """
    Service for sending notifications related to service activations.
    
    This class provides methods for:
    - Sending activation success notifications to customers
    - Sending activation failure notifications to customers
    - Sending status update notifications to customers
    - Sending alerts to staff for manual intervention
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize the notification service with a database session."""
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    async def send_activation_success_notification(
        self, activation_id: int, additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification to the customer about successful service activation.
        
        Args:
            activation_id: ID of the service activation
            additional_data: Additional data to include in the notification
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            # Get activation details
            result = await self.session.execute(
                select(ServiceActivation).where(ServiceActivation.id == activation_id)
            )
            activation = result.scalars().first()
            
            if not activation:
                self.logger.error(f"Activation {activation_id} not found for notification")
                return False
            
            # In a real implementation, this would call the notification module
            # to send an email, SMS, or other notification to the customer
            
            self.logger.info(
                f"Sent activation success notification to customer {activation.customer_id} "
                f"for service {activation.service_id}"
            )
            
            # For now, we'll simulate success
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending activation success notification: {str(e)}")
            return False
    
    async def send_activation_failure_notification(
        self, activation_id: int, reason: str, additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification to the customer about failed service activation.
        
        Args:
            activation_id: ID of the service activation
            reason: Reason for the failure
            additional_data: Additional data to include in the notification
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            # Get activation details
            result = await self.session.execute(
                select(ServiceActivation).where(ServiceActivation.id == activation_id)
            )
            activation = result.scalars().first()
            
            if not activation:
                self.logger.error(f"Activation {activation_id} not found for notification")
                return False
            
            # In a real implementation, this would call the notification module
            # to send an email, SMS, or other notification to the customer
            
            self.logger.info(
                f"Sent activation failure notification to customer {activation.customer_id} "
                f"for service {activation.service_id}: {reason}"
            )
            
            # For now, we'll simulate success
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending activation failure notification: {str(e)}")
            return False
    
    async def send_status_update_notification(
        self, activation_id: int, status: ActivationStatus, additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification to the customer about a status update.
        
        Args:
            activation_id: ID of the service activation
            status: New status of the activation
            additional_data: Additional data to include in the notification
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            # Get activation details
            result = await self.session.execute(
                select(ServiceActivation).where(ServiceActivation.id == activation_id)
            )
            activation = result.scalars().first()
            
            if not activation:
                self.logger.error(f"Activation {activation_id} not found for notification")
                return False
            
            # In a real implementation, this would call the notification module
            # to send an email, SMS, or other notification to the customer
            
            self.logger.info(
                f"Sent status update notification to customer {activation.customer_id} "
                f"for service {activation.service_id}: {status.value}"
            )
            
            # For now, we'll simulate success
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending status update notification: {str(e)}")
            return False
    
    async def send_staff_alert(
        self, activation_id: int, alert_type: str, message: str, 
        staff_roles: List[str], additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an alert to staff members for manual intervention.
        
        Args:
            activation_id: ID of the service activation
            alert_type: Type of alert (e.g., "manual_intervention", "approval_required")
            message: Alert message
            staff_roles: List of staff roles to notify
            additional_data: Additional data to include in the alert
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        try:
            # Get activation details
            result = await self.session.execute(
                select(ServiceActivation).where(ServiceActivation.id == activation_id)
            )
            activation = result.scalars().first()
            
            if not activation:
                self.logger.error(f"Activation {activation_id} not found for staff alert")
                return False
            
            # In a real implementation, this would call the notification module
            # to send alerts to staff members with the specified roles
            
            self.logger.info(
                f"Sent {alert_type} alert to staff roles {staff_roles} "
                f"for activation {activation_id}: {message}"
            )
            
            # For now, we'll simulate success
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending staff alert: {str(e)}")
            return False
