"""
Message service for the Communications module.

This module provides the MessageService class for handling message-related operations
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


class MessageService:
    """Service for handling messages between users."""

    @staticmethod
    async def create_message(
        db: Session,
        message_data: schemas.MessageCreate,
        sender_id: int,
        background_tasks: BackgroundTasks = None
    ) -> models.Message:
        """
        Create a new message.

        Args:
            db: Database session
            message_data: Message data
            sender_id: ID of the message sender
            background_tasks: Background tasks runner

        Returns:
            The created message
        """
        # Create the message
        message = models.Message(
            sender_id=sender_id,
            subject=message_data.subject,
            body=message_data.body,
            priority=message_data.priority,
            status=models.MessageStatus.DRAFT,
            delivery_method=message_data.delivery_method
        )
        
        db.add(message)
        db.flush()  # Get the message ID without committing
        
        # Add recipients
        if message_data.recipient_ids:
            for recipient_id in message_data.recipient_ids:
                # Add to the association table
                message.recipients.append(db.query(User).get(recipient_id))
        
        # Add attachments if any
        if message_data.attachments:
            for attachment_data in message_data.attachments:
                attachment = models.MessageAttachment(
                    message_id=message.id,
                    file_name=attachment_data.file_name,
                    file_path=attachment_data.file_path,
                    file_size=attachment_data.file_size,
                    content_type=attachment_data.content_type
                )
                db.add(attachment)
        
        db.commit()
        db.refresh(message)
        
        # Trigger webhooks in background if provided
        if background_tasks:
            background_tasks.add_task(
                WebhookService.trigger_event,
                "message.created",
                {
                    "message_id": message.id,
                    "subject": message.subject,
                    "sender_id": sender_id,
                    "recipient_ids": [r.id for r in message.recipients],
                    "status": message.status.value
                }
            )
        
        return message

    @staticmethod
    async def _trigger_message_webhook(
        db: Session,
        message_id: int,
        event_type: str
    ) -> None:
        """
        Trigger a webhook for a message event.

        Args:
            db: Database session
            message_id: ID of the message
            event_type: Type of event (created, updated, etc.)
        """
        # Get the message
        message = await MessageService.get_message(db, message_id=message_id)
        if not message:
            logger.error(f"Message {message_id} not found for webhook trigger")
            return
        
        # Prepare webhook payload
        payload = {
            "id": message.id,
            "sender_id": message.sender_id,
            "recipient_ids": [r.id for r in message.recipients],
            "subject": message.subject,
            "status": message.status.value,
            "priority": message.priority.value,
            "created_at": message.created_at.isoformat(),
            "event_type": event_type
        }
        
        # Trigger webhook
        await WebhookService.trigger_event(
            event_type=event_type,
            payload=payload
        )

    @staticmethod
    async def _send_message(
        db: Session,
        message_id: int
    ) -> models.Message:
        """
        Send a message via the specified delivery method.

        Args:
            db: Database session
            message_id: ID of the message to send

        Returns:
            The updated message
        """
        # Get the message
        message = db.query(models.Message).filter(models.Message.id == message_id).first()
        if not message:
            logger.error(f"Message {message_id} not found for sending")
            return None
        
        # Send via the appropriate delivery method
        if message.delivery_method == models.DeliveryMethod.EMAIL:
            logger.info(f"Sending email message {message.id}")
            # Implement email sending logic here
            # ...
            
        elif message.delivery_method == models.DeliveryMethod.SMS:
            logger.info(f"Sending SMS message {message.id}")
            # Implement SMS sending logic here
            # ...
            
        elif message.delivery_method == models.DeliveryMethod.PUSH:
            logger.info(f"Sending push message {message.id}")
            # Implement push notification logic here
            # ...
            
        # Update message status
        message.status = models.MessageStatus.DELIVERED
        message.delivered_at = datetime.utcnow()
        db.commit()
        db.refresh(message)
        
        # Trigger webhook for status change
        await MessageService._trigger_message_webhook(db, message.id, "message.status_changed")
        
        return message

    @staticmethod
    async def get_message(
        db: Session,
        message_id: int,
        user_id: int = None
    ) -> Optional[models.Message]:
        """
        Get a message by ID.

        Args:
            db: Database session
            message_id: ID of the message to retrieve
            user_id: ID of the user requesting the message (for permission check)

        Returns:
            The message if found and user has permission, None otherwise
        """
        message = db.query(models.Message).filter(models.Message.id == message_id).first()
        
        # Check if message exists
        if not message:
            return None
        
        # Check if user has permission to view this message
        if user_id and user_id != message.sender_id and user_id not in [r.id for r in message.recipients]:
            return None
        
        return message

    @staticmethod
    async def mark_as_read(
        db: Session,
        message_id: int,
        user_id: int
    ) -> Optional[models.Message]:
        """
        Mark a message as read.

        Args:
            db: Database session
            message_id: ID of the message to mark as read
            user_id: ID of the user marking the message as read

        Returns:
            The updated message if successful, None otherwise
        """
        message = await MessageService.get_message(db, message_id=message_id, user_id=user_id)
        
        # Check if message exists and user has permission
        if not message:
            return None
        
        # Only recipient can mark as read
        if user_id not in [r.id for r in message.recipients]:
            return None
        
        # Update message
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.commit()
        db.refresh(message)
        
        return message

    @staticmethod
    async def get_user_messages(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_sent: bool = False,
        include_received: bool = True,
        unread_only: bool = False
    ) -> List[models.Message]:
        """
        Get messages for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of messages to skip (for pagination)
            limit: Maximum number of messages to return
            include_sent: Whether to include messages sent by the user
            include_received: Whether to include messages received by the user
            unread_only: Whether to only include unread messages

        Returns:
            List of messages
        """
        query = db.query(models.Message)
        
        # Filter by user
        if include_sent and include_received:
            query = query.filter(
                (models.Message.sender_id == user_id) | 
                (models.Message.recipients.any(models.User.id == user_id))
            )
        elif include_sent:
            query = query.filter(models.Message.sender_id == user_id)
        elif include_received:
            query = query.filter(models.Message.recipients.any(models.User.id == user_id))
        
        # Filter by read status
        if unread_only:
            query = query.filter(models.Message.is_read == False)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(models.Message.created_at))
        
        # Apply pagination
        messages = query.offset(skip).limit(limit).all()
        
        return messages

    @staticmethod
    async def delete_message(
        db: Session,
        message_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a message.

        Args:
            db: Database session
            message_id: ID of the message to delete
            user_id: ID of the user deleting the message

        Returns:
            True if successful, False otherwise
        """
        message = await MessageService.get_message(db, message_id=message_id, user_id=user_id)
        
        # Check if message exists and user has permission
        if not message:
            return False
        
        # Only sender or recipient can delete
        if user_id != message.sender_id and user_id not in [r.id for r in message.recipients]:
            return False
        
        # Delete message
        db.delete(message)
        db.commit()
        
        return True
