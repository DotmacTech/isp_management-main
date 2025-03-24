"""
Notification service for the CRM & Ticketing module.

This service provides functionality for sending notifications to users and customers
about ticket events, SLA breaches, and other important updates.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import json
import os
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks

from backend_core.database import get_db
from modules.monitoring.services import LoggingService
from ..models.ticket import Ticket, TicketComment
from ..models.customer import Customer
from ..models.common import TicketStatus, TicketPriority


class NotificationService:
    """Service for sending notifications related to tickets and CRM activities."""
    
    def __init__(self, db: Session):
        """Initialize the notification service with a database session."""
        self.db = db
        self.logging_service = LoggingService(db)
        
        # Load notification settings from environment or config
        self.email_enabled = os.environ.get("ENABLE_EMAIL_NOTIFICATIONS", "true").lower() == "true"
        self.sms_enabled = os.environ.get("ENABLE_SMS_NOTIFICATIONS", "false").lower() == "true"
        self.push_enabled = os.environ.get("ENABLE_PUSH_NOTIFICATIONS", "true").lower() == "true"
        self.internal_enabled = os.environ.get("ENABLE_INTERNAL_NOTIFICATIONS", "true").lower() == "true"
    
    def notify_ticket_created(self, ticket: Ticket, user_id: int) -> None:
        """
        Send notifications when a ticket is created.
        
        Args:
            ticket: The created ticket
            user_id: The ID of the user who created the ticket
        """
        # Get customer information if available
        customer_name = "Unknown"
        customer_email = None
        customer_phone = None
        
        if ticket.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if customer:
                customer_name = customer.company_name or f"{customer.first_name} {customer.last_name}"
                customer_email = customer.email
                customer_phone = customer.phone
        
        # Prepare notification data
        notification_data = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "customer_id": ticket.customer_id,
            "customer_name": customer_name,
            "created_by": user_id,
            "created_at": ticket.created_at.isoformat()
        }
        
        # Notify assigned staff if applicable
        if ticket.assigned_to:
            self._send_staff_notification(
                user_id=ticket.assigned_to,
                notification_type="ticket_assigned",
                title=f"Ticket {ticket.ticket_number} assigned to you",
                message=f"A new ticket has been assigned to you: {ticket.subject}",
                data=notification_data
            )
        
        # Notify assigned team if applicable
        if ticket.assigned_team:
            self._send_team_notification(
                team_id=ticket.assigned_team,
                notification_type="ticket_assigned_team",
                title=f"Ticket {ticket.ticket_number} assigned to your team",
                message=f"A new ticket has been assigned to your team: {ticket.subject}",
                data=notification_data
            )
        
        # Notify customer if applicable
        if customer_email and ticket.customer_id:
            self._send_customer_notification(
                customer_id=ticket.customer_id,
                notification_type="ticket_created",
                title=f"Ticket {ticket.ticket_number} created",
                message=f"Your ticket has been created: {ticket.subject}",
                data=notification_data,
                email=customer_email,
                phone=customer_phone
            )
        
        # Log notification
        self.logging_service.log_event(
            "notification_sent",
            f"Ticket creation notifications sent for ticket {ticket.ticket_number}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "notification_type": "ticket_created"
            }
        )
    
    def notify_ticket_updated(
        self, 
        ticket: Ticket, 
        user_id: int,
        changes: List[Tuple[str, Any, Any]]
    ) -> None:
        """
        Send notifications when a ticket is updated.
        
        Args:
            ticket: The updated ticket
            user_id: The ID of the user who updated the ticket
            changes: List of changes made to the ticket (field_name, old_value, new_value)
        """
        # Get customer information if available
        customer_name = "Unknown"
        customer_email = None
        customer_phone = None
        
        if ticket.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if customer:
                customer_name = customer.company_name or f"{customer.first_name} {customer.last_name}"
                customer_email = customer.email
                customer_phone = customer.phone
        
        # Prepare notification data
        notification_data = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "customer_id": ticket.customer_id,
            "customer_name": customer_name,
            "updated_by": user_id,
            "updated_at": ticket.updated_at.isoformat(),
            "changes": [(c[0], str(c[1]), str(c[2])) for c in changes]
        }
        
        # Check for assignment change
        assignment_change = next((c for c in changes if c[0] == "assigned_to"), None)
        if assignment_change and assignment_change[2]:
            # Notify newly assigned staff
            self._send_staff_notification(
                user_id=assignment_change[2],
                notification_type="ticket_assigned",
                title=f"Ticket {ticket.ticket_number} assigned to you",
                message=f"A ticket has been assigned to you: {ticket.subject}",
                data=notification_data
            )
        
        # Check for team assignment change
        team_change = next((c for c in changes if c[0] == "assigned_team"), None)
        if team_change and team_change[2]:
            # Notify newly assigned team
            self._send_team_notification(
                team_id=team_change[2],
                notification_type="ticket_assigned_team",
                title=f"Ticket {ticket.ticket_number} assigned to your team",
                message=f"A ticket has been assigned to your team: {ticket.subject}",
                data=notification_data
            )
        
        # Notify customer about relevant changes if applicable
        customer_relevant_fields = ["status", "priority", "subject", "description"]
        customer_relevant_changes = [c for c in changes if c[0] in customer_relevant_fields]
        
        if customer_email and ticket.customer_id and customer_relevant_changes:
            self._send_customer_notification(
                customer_id=ticket.customer_id,
                notification_type="ticket_updated",
                title=f"Ticket {ticket.ticket_number} updated",
                message=f"Your ticket has been updated: {ticket.subject}",
                data=notification_data,
                email=customer_email,
                phone=customer_phone
            )
        
        # Notify assigned staff (if not the updater)
        if ticket.assigned_to and ticket.assigned_to != user_id:
            self._send_staff_notification(
                user_id=ticket.assigned_to,
                notification_type="ticket_updated",
                title=f"Ticket {ticket.ticket_number} updated",
                message=f"A ticket assigned to you has been updated: {ticket.subject}",
                data=notification_data
            )
        
        # Log notification
        self.logging_service.log_event(
            "notification_sent",
            f"Ticket update notifications sent for ticket {ticket.ticket_number}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "notification_type": "ticket_updated",
                "changes": [(c[0], str(c[1]), str(c[2])) for c in changes]
            }
        )
    
    def notify_ticket_status_changed(
        self, 
        ticket: Ticket, 
        user_id: int,
        old_status: TicketStatus,
        new_status: TicketStatus
    ) -> None:
        """
        Send notifications when a ticket's status changes.
        
        Args:
            ticket: The ticket with the changed status
            user_id: The ID of the user who changed the status
            old_status: The previous status
            new_status: The new status
        """
        # Get customer information if available
        customer_name = "Unknown"
        customer_email = None
        customer_phone = None
        
        if ticket.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if customer:
                customer_name = customer.company_name or f"{customer.first_name} {customer.last_name}"
                customer_email = customer.email
                customer_phone = customer.phone
        
        # Prepare notification data
        notification_data = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "priority": ticket.priority.value,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "customer_id": ticket.customer_id,
            "customer_name": customer_name,
            "updated_by": user_id,
            "updated_at": ticket.updated_at.isoformat()
        }
        
        # Notify customer about status change
        if customer_email and ticket.customer_id:
            # Customize message based on status
            message = f"Your ticket status has changed from {old_status.value} to {new_status.value}: {ticket.subject}"
            
            if new_status == TicketStatus.RESOLVED:
                message = f"Your ticket has been resolved: {ticket.subject}"
            elif new_status == TicketStatus.CLOSED:
                message = f"Your ticket has been closed: {ticket.subject}"
            elif new_status == TicketStatus.IN_PROGRESS:
                message = f"Your ticket is now being worked on: {ticket.subject}"
            
            self._send_customer_notification(
                customer_id=ticket.customer_id,
                notification_type="ticket_status_changed",
                title=f"Ticket {ticket.ticket_number} status changed to {new_status.value}",
                message=message,
                data=notification_data,
                email=customer_email,
                phone=customer_phone
            )
        
        # Notify assigned staff (if not the updater)
        if ticket.assigned_to and ticket.assigned_to != user_id:
            self._send_staff_notification(
                user_id=ticket.assigned_to,
                notification_type="ticket_status_changed",
                title=f"Ticket {ticket.ticket_number} status changed to {new_status.value}",
                message=f"A ticket assigned to you has changed status from {old_status.value} to {new_status.value}: {ticket.subject}",
                data=notification_data
            )
        
        # Notify assigned team (if applicable)
        if ticket.assigned_team:
            self._send_team_notification(
                team_id=ticket.assigned_team,
                notification_type="ticket_status_changed",
                title=f"Ticket {ticket.ticket_number} status changed to {new_status.value}",
                message=f"A ticket assigned to your team has changed status from {old_status.value} to {new_status.value}: {ticket.subject}",
                data=notification_data
            )
        
        # Log notification
        self.logging_service.log_event(
            "notification_sent",
            f"Ticket status change notifications sent for ticket {ticket.ticket_number}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "notification_type": "ticket_status_changed",
                "old_status": old_status.value,
                "new_status": new_status.value
            }
        )
    
    def notify_ticket_comment_added(
        self, 
        ticket: Ticket, 
        comment: TicketComment, 
        user_id: int
    ) -> None:
        """
        Send notifications when a comment is added to a ticket.
        
        Args:
            ticket: The ticket that received the comment
            comment: The comment that was added
            user_id: The ID of the user who added the comment
        """
        # Skip notifications for system comments if configured to do so
        if comment.is_system and os.environ.get("NOTIFY_SYSTEM_COMMENTS", "false").lower() != "true":
            return
        
        # Get customer information if available
        customer_name = "Unknown"
        customer_email = None
        customer_phone = None
        
        if ticket.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if customer:
                customer_name = customer.company_name or f"{customer.first_name} {customer.last_name}"
                customer_email = customer.email
                customer_phone = customer.phone
        
        # Prepare notification data
        notification_data = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "comment_id": comment.id,
            "comment_content": comment.content[:100] + "..." if len(comment.content) > 100 else comment.content,
            "is_internal": comment.is_internal,
            "is_system": comment.is_system,
            "customer_id": ticket.customer_id,
            "customer_name": customer_name,
            "created_by": user_id,
            "created_at": comment.created_at.isoformat()
        }
        
        # Notify customer about comment (if not internal and not from the customer)
        if customer_email and ticket.customer_id and not comment.is_internal and comment.created_by != ticket.customer_id:
            self._send_customer_notification(
                customer_id=ticket.customer_id,
                notification_type="ticket_comment_added",
                title=f"New comment on ticket {ticket.ticket_number}",
                message=f"A new comment has been added to your ticket: {ticket.subject}",
                data=notification_data,
                email=customer_email,
                phone=customer_phone
            )
        
        # Notify assigned staff (if not the commenter)
        if ticket.assigned_to and ticket.assigned_to != user_id:
            self._send_staff_notification(
                user_id=ticket.assigned_to,
                notification_type="ticket_comment_added",
                title=f"New comment on ticket {ticket.ticket_number}",
                message=f"A new comment has been added to a ticket assigned to you: {ticket.subject}",
                data=notification_data
            )
        
        # Notify assigned team (if applicable and not from a team member)
        if ticket.assigned_team:
            self._send_team_notification(
                team_id=ticket.assigned_team,
                notification_type="ticket_comment_added",
                title=f"New comment on ticket {ticket.ticket_number}",
                message=f"A new comment has been added to a ticket assigned to your team: {ticket.subject}",
                data=notification_data,
                exclude_user_id=user_id
            )
        
        # Log notification
        self.logging_service.log_event(
            "notification_sent",
            f"Ticket comment notifications sent for ticket {ticket.ticket_number}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "notification_type": "ticket_comment_added",
                "comment_id": comment.id,
                "is_internal": comment.is_internal
            }
        )
    
    def notify_sla_breach(self, ticket: Ticket, breach_type: str) -> None:
        """
        Send notifications when an SLA is breached.
        
        Args:
            ticket: The ticket with the breached SLA
            breach_type: The type of breach (e.g., 'first_response', 'resolution')
        """
        # Get customer information if available
        customer_name = "Unknown"
        
        if ticket.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if customer:
                customer_name = customer.company_name or f"{customer.first_name} {customer.last_name}"
        
        # Prepare notification data
        notification_data = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "customer_id": ticket.customer_id,
            "customer_name": customer_name,
            "breach_type": breach_type,
            "breach_time": datetime.utcnow().isoformat()
        }
        
        # Format breach type for display
        breach_type_display = breach_type.replace("_", " ").title()
        
        # Notify assigned staff
        if ticket.assigned_to:
            self._send_staff_notification(
                user_id=ticket.assigned_to,
                notification_type="sla_breach",
                title=f"SLA Breach: {ticket.ticket_number}",
                message=f"SLA {breach_type_display} has been breached for ticket: {ticket.subject}",
                data=notification_data,
                priority="high"
            )
        
        # Notify assigned team
        if ticket.assigned_team:
            self._send_team_notification(
                team_id=ticket.assigned_team,
                notification_type="sla_breach",
                title=f"SLA Breach: {ticket.ticket_number}",
                message=f"SLA {breach_type_display} has been breached for ticket: {ticket.subject}",
                data=notification_data,
                priority="high"
            )
        
        # Notify management
        self._send_management_notification(
            notification_type="sla_breach",
            title=f"SLA Breach: {ticket.ticket_number}",
            message=f"SLA {breach_type_display} has been breached for ticket: {ticket.subject} (Priority: {ticket.priority.value})",
            data=notification_data,
            priority="high"
        )
        
        # Log notification
        self.logging_service.log_event(
            "notification_sent",
            f"SLA breach notifications sent for ticket {ticket.ticket_number}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "notification_type": "sla_breach",
                "breach_type": breach_type
            }
        )
    
    def notify_sla_approaching(self, ticket: Ticket, threshold_type: str, hours_remaining: float) -> None:
        """
        Send notifications when an SLA threshold is approaching.
        
        Args:
            ticket: The ticket with the approaching SLA threshold
            threshold_type: The type of threshold (e.g., 'first_response', 'resolution')
            hours_remaining: The number of hours remaining before breach
        """
        # Get customer information if available
        customer_name = "Unknown"
        
        if ticket.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if customer:
                customer_name = customer.company_name or f"{customer.first_name} {customer.last_name}"
        
        # Prepare notification data
        notification_data = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "customer_id": ticket.customer_id,
            "customer_name": customer_name,
            "threshold_type": threshold_type,
            "hours_remaining": hours_remaining,
            "notification_time": datetime.utcnow().isoformat()
        }
        
        # Format threshold type for display
        threshold_type_display = threshold_type.replace("_", " ").title()
        
        # Notify assigned staff
        if ticket.assigned_to:
            self._send_staff_notification(
                user_id=ticket.assigned_to,
                notification_type="sla_approaching",
                title=f"SLA Approaching: {ticket.ticket_number}",
                message=f"SLA {threshold_type_display} will be breached in {hours_remaining:.1f} hours for ticket: {ticket.subject}",
                data=notification_data,
                priority="medium"
            )
        
        # Notify assigned team
        if ticket.assigned_team:
            self._send_team_notification(
                team_id=ticket.assigned_team,
                notification_type="sla_approaching",
                title=f"SLA Approaching: {ticket.ticket_number}",
                message=f"SLA {threshold_type_display} will be breached in {hours_remaining:.1f} hours for ticket: {ticket.subject}",
                data=notification_data,
                priority="medium"
            )
        
        # Log notification
        self.logging_service.log_event(
            "notification_sent",
            f"SLA approaching notifications sent for ticket {ticket.ticket_number}",
            {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "notification_type": "sla_approaching",
                "threshold_type": threshold_type,
                "hours_remaining": hours_remaining
            }
        )
    
    def _send_staff_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any],
        priority: str = "normal"
    ) -> None:
        """
        Send a notification to a staff member.
        
        Args:
            user_id: The ID of the user to notify
            notification_type: The type of notification
            title: The notification title
            message: The notification message
            data: Additional data for the notification
            priority: The priority of the notification (low, normal, high)
        """
        # In a real implementation, this would send to the user's preferred notification channels
        # For now, we'll just log it
        
        # Get user preferences (mock implementation)
        user_preferences = {
            "email": True,
            "push": True,
            "sms": False
        }
        
        # Send internal notification
        if self.internal_enabled:
            try:
                # In a real implementation, this would create a notification in the database
                # and potentially trigger a real-time notification via WebSockets
                self.logging_service.log_event(
                    "internal_notification",
                    f"Internal notification sent to user {user_id}: {title}",
                    {
                        "user_id": user_id,
                        "notification_type": notification_type,
                        "title": title,
                        "message": message,
                        "priority": priority,
                        "data": data
                    }
                )
            except Exception as e:
                self.logging_service.log_event(
                    "error",
                    f"Error sending internal notification to user {user_id}",
                    {"error": str(e)}
                )
        
        # Send email notification
        if self.email_enabled and user_preferences.get("email", False):
            try:
                # In a real implementation, this would send an email
                self.logging_service.log_event(
                    "email_notification",
                    f"Email notification sent to user {user_id}: {title}",
                    {
                        "user_id": user_id,
                        "notification_type": notification_type,
                        "title": title,
                        "message": message,
                        "priority": priority
                    }
                )
            except Exception as e:
                self.logging_service.log_event(
                    "error",
                    f"Error sending email notification to user {user_id}",
                    {"error": str(e)}
                )
        
        # Send push notification
        if self.push_enabled and user_preferences.get("push", False):
            try:
                # In a real implementation, this would send a push notification
                self.logging_service.log_event(
                    "push_notification",
                    f"Push notification sent to user {user_id}: {title}",
                    {
                        "user_id": user_id,
                        "notification_type": notification_type,
                        "title": title,
                        "message": message,
                        "priority": priority
                    }
                )
            except Exception as e:
                self.logging_service.log_event(
                    "error",
                    f"Error sending push notification to user {user_id}",
                    {"error": str(e)}
                )
        
        # Send SMS notification for high priority
        if self.sms_enabled and user_preferences.get("sms", False) and priority == "high":
            try:
                # In a real implementation, this would send an SMS
                self.logging_service.log_event(
                    "sms_notification",
                    f"SMS notification sent to user {user_id}: {title}",
                    {
                        "user_id": user_id,
                        "notification_type": notification_type,
                        "title": title,
                        "message": message,
                        "priority": priority
                    }
                )
            except Exception as e:
                self.logging_service.log_event(
                    "error",
                    f"Error sending SMS notification to user {user_id}",
                    {"error": str(e)}
                )
    
    def _send_team_notification(
        self,
        team_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any],
        priority: str = "normal",
        exclude_user_id: Optional[int] = None
    ) -> None:
        """
        Send a notification to all members of a team.
        
        Args:
            team_id: The ID of the team to notify
            notification_type: The type of notification
            title: The notification title
            message: The notification message
            data: Additional data for the notification
            priority: The priority of the notification (low, normal, high)
            exclude_user_id: Optional user ID to exclude from the notification
        """
        # In a real implementation, this would get team members from the database
        # and send notifications to each member
        
        # For now, we'll just log it
        self.logging_service.log_event(
            "team_notification",
            f"Team notification sent to team {team_id}: {title}",
            {
                "team_id": team_id,
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "priority": priority,
                "exclude_user_id": exclude_user_id,
                "data": data
            }
        )
    
    def _send_customer_notification(
        self,
        customer_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any],
        email: Optional[str] = None,
        phone: Optional[str] = None,
        priority: str = "normal"
    ) -> None:
        """
        Send a notification to a customer.
        
        Args:
            customer_id: The ID of the customer to notify
            notification_type: The type of notification
            title: The notification title
            message: The notification message
            data: Additional data for the notification
            email: The customer's email address
            phone: The customer's phone number
            priority: The priority of the notification (low, normal, high)
        """
        # Get customer preferences (mock implementation)
        customer_preferences = {
            "email": True,
            "sms": False
        }
        
        # Send email notification
        if self.email_enabled and customer_preferences.get("email", False) and email:
            try:
                # In a real implementation, this would send an email
                self.logging_service.log_event(
                    "customer_email_notification",
                    f"Email notification sent to customer {customer_id}: {title}",
                    {
                        "customer_id": customer_id,
                        "notification_type": notification_type,
                        "title": title,
                        "message": message,
                        "priority": priority,
                        "email": email
                    }
                )
            except Exception as e:
                self.logging_service.log_event(
                    "error",
                    f"Error sending email notification to customer {customer_id}",
                    {"error": str(e)}
                )
        
        # Send SMS notification for high priority
        if self.sms_enabled and customer_preferences.get("sms", False) and phone and priority == "high":
            try:
                # In a real implementation, this would send an SMS
                self.logging_service.log_event(
                    "customer_sms_notification",
                    f"SMS notification sent to customer {customer_id}: {title}",
                    {
                        "customer_id": customer_id,
                        "notification_type": notification_type,
                        "title": title,
                        "message": message,
                        "priority": priority,
                        "phone": phone
                    }
                )
            except Exception as e:
                self.logging_service.log_event(
                    "error",
                    f"Error sending SMS notification to customer {customer_id}",
                    {"error": str(e)}
                )
    
    def _send_management_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any],
        priority: str = "normal"
    ) -> None:
        """
        Send a notification to management users.
        
        Args:
            notification_type: The type of notification
            title: The notification title
            message: The notification message
            data: Additional data for the notification
            priority: The priority of the notification (low, normal, high)
        """
        # In a real implementation, this would get management users from the database
        # and send notifications to each one
        
        # For now, we'll just log it
        self.logging_service.log_event(
            "management_notification",
            f"Management notification sent: {title}",
            {
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "priority": priority,
                "data": data
            }
        )
