"""
Notification service for the Communications module.

This module provides the NotificationService class for handling notification-related operations
in the ISP Management Platform.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend_core.config import settings
from modules.communications import models, schemas
from modules.communications.webhooks import WebhookService
from backend_core.models import User  # Import User from backend_core

# Configure logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling system notifications."""

    @staticmethod
    async def create_notification(
        db: Session,
        notification_data: schemas.NotificationCreate,
        sender_id: int,
        background_tasks: BackgroundTasks = None
    ) -> models.Notification:
        """
        Create a new notification.

        Args:
            db: Database session
            notification_data: Notification data
            sender_id: ID of the notification sender
            background_tasks: Background tasks runner

        Returns:
            The created notification
        """
        # Create the notification
        notification = models.Notification(
            sender_id=sender_id,
            title=notification_data.title,
            content=notification_data.content,
            notification_type=notification_data.notification_type,
            delivery_method=notification_data.delivery_method,
            action_url=notification_data.action_url
        )
        
        db.add(notification)
        db.flush()  # Get the notification ID without committing
        
        # Add recipients
        if notification_data.recipient_ids:
            for recipient_id in notification_data.recipient_ids:
                user = db.query(User).get(recipient_id)
                if user:
                    notification.recipients.append(user)
        
        # Save to database
        db.commit()
        db.refresh(notification)
        
        # Trigger webhook in background if available
        if background_tasks:
            background_tasks.add_task(
                WebhookService.trigger_event,
                "notification.created",
                {
                    "notification_id": notification.id,
                    "title": notification.title,
                    "sender_id": sender_id,
                    "recipient_ids": [r.id for r in notification.recipients],
                    "notification_type": notification.notification_type.value
                }
            )
        
        return notification

    @staticmethod
    async def _trigger_notification_webhook(
        db: Session,
        notification_id: int,
        event_type: str
    ) -> None:
        """
        Trigger a webhook for a notification event.

        Args:
            db: Database session
            notification_id: ID of the notification
            event_type: Type of event (created, updated, etc.)
        """
        # Get the notification
        notification = await NotificationService.get_notification(db, notification_id=notification_id)
        if not notification:
            logger.error(f"Notification {notification_id} not found for webhook trigger")
            return
        
        # Prepare webhook payload
        payload = {
            "id": notification.id,
            "sender_id": notification.sender_id,
            "recipient_ids": [r.id for r in notification.recipients],
            "title": notification.title,
            "notification_type": notification.notification_type.value,
            "created_at": notification.created_at.isoformat(),
            "event_type": event_type
        }
        
        # Trigger webhook
        await WebhookService.trigger_event(
            event_type=event_type,
            payload=payload
        )

    @staticmethod
    async def _send_notification(
        db: Session,
        notification_id: int
    ) -> models.Notification:
        """
        Send a notification via the specified delivery method.

        Args:
            db: Database session
            notification_id: ID of the notification to send

        Returns:
            The updated notification
        """
        # Get the notification
        notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
        if not notification:
            logger.error(f"Notification {notification_id} not found for sending")
            return None
        
        # Send via the appropriate delivery method
        if notification.delivery_method == models.DeliveryMethod.EMAIL:
            logger.info(f"Sending email notification {notification.id}")
            # Implement email sending logic here
            # ...
            
        elif notification.delivery_method == models.DeliveryMethod.SMS:
            logger.info(f"Sending SMS notification {notification.id}")
            # Implement SMS sending logic here
            # ...
            
        elif notification.delivery_method == models.DeliveryMethod.PUSH:
            logger.info(f"Sending push notification {notification.id}")
            # Implement push notification logic here
            # ...
            
        # Update notification status
        notification.is_sent = True
        notification.sent_at = datetime.utcnow()
        db.commit()
        db.refresh(notification)
        
        return notification

    @staticmethod
    async def get_notification(
        db: Session,
        notification_id: int,
        user_id: int = None
    ) -> Optional[models.Notification]:
        """
        Get a notification by ID.

        Args:
            db: Database session
            notification_id: ID of the notification to retrieve
            user_id: ID of the user requesting the notification (for permission check)

        Returns:
            The notification if found and user has permission, None otherwise
        """
        notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
        
        # Check if notification exists
        if not notification:
            return None
        
        # Check if user has permission to view this notification
        if user_id and user_id != notification.sender_id and user_id not in [r.id for r in notification.recipients]:
            return None
        
        return notification

    @staticmethod
    async def mark_as_read(
        db: Session,
        notification_id: int,
        user_id: int
    ) -> Optional[models.Notification]:
        """
        Mark a notification as read.

        Args:
            db: Database session
            notification_id: ID of the notification to mark as read
            user_id: ID of the user marking the notification as read

        Returns:
            The updated notification if successful, None otherwise
        """
        notification = await NotificationService.get_notification(db, notification_id=notification_id, user_id=user_id)
        
        # Check if notification exists and user has permission
        if not notification:
            return None
        
        # Only recipient can mark as read
        if user_id not in [r.id for r in notification.recipients]:
            return None
        
        # Update notification
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
        db.refresh(notification)
        
        return notification

    @staticmethod
    async def get_user_notifications(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False
    ) -> List[models.Notification]:
        """
        Get notifications for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of notifications to skip (for pagination)
            limit: Maximum number of notifications to return
            unread_only: Whether to only include unread notifications

        Returns:
            List of notifications
        """
        query = db.query(models.Notification).filter(models.Notification.recipients.any(User.id == user_id))
        
        # Filter by read status
        if unread_only:
            query = query.filter(models.Notification.is_read == False)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(models.Notification.created_at))
        
        # Apply pagination
        notifications = query.offset(skip).limit(limit).all()
        
        return notifications

    @staticmethod
    async def delete_notification(
        db: Session,
        notification_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a notification.

        Args:
            db: Database session
            notification_id: ID of the notification to delete
            user_id: ID of the user deleting the notification

        Returns:
            True if successful, False otherwise
        """
        notification = await NotificationService.get_notification(db, notification_id=notification_id, user_id=user_id)
        
        # Check if notification exists and user has permission
        if not notification:
            return False
        
        # Only recipient can delete their notification
        if user_id not in [r.id for r in notification.recipients]:
            return False
        
        # Delete notification
        db.delete(notification)
        db.commit()
        
        return True
