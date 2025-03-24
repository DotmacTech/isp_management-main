"""
Services for the Communications module.

This module provides service classes for handling communications-related operations
in the ISP Management Platform, including messages, notifications, announcements,
and support tickets.
"""

import os
import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union
from fastapi import HTTPException, UploadFile, File, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_
from redis import Redis

from backend_core.database import get_db
from backend_core.config import settings
from backend_core.cache import get_redis
from modules.communications import models, schemas
from modules.communications.webhooks import WebhookService

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
            subject=message_data.subject,
            body=message_data.body,
            sender_id=sender_id,
            priority=message_data.priority,
            status=message_data.status if message_data.status else models.MessageStatus.DRAFT,
            delivery_method=message_data.delivery_method
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        # Add recipients
        for recipient_id in message_data.recipient_ids:
            # Check if recipient exists
            recipient = db.query(models.User).filter(models.User.id == recipient_id).first()
            if recipient:
                message.recipients.append(recipient)

        db.commit()
        db.refresh(message)

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

        # If message status is SENT, send the message
        if message.status == models.MessageStatus.SENT:
            # Update status to SENT
            message.status = models.MessageStatus.SENT
            db.commit()

            # Send the message in the background if delivery method is not IN_APP
            if message.delivery_method != models.DeliveryMethod.IN_APP and background_tasks:
                background_tasks.add_task(
                    MessageService._send_message,
                    db,
                    message.id
                )

        # Trigger webhook for message creation
        if background_tasks:
            background_tasks.add_task(
                MessageService._trigger_message_webhook,
                db,
                message.id,
                "message.created"
            )

        return message

    @staticmethod
    async def _trigger_message_webhook(
        db: Session,
        message_id: int,
        event: str
    ):
        """
        Trigger webhook for message events.

        Args:
            db: Database session
            message_id: ID of the message
            event: Event type
        """
        message = await MessageService.get_message(db, message_id)
        if not message:
            logger.warning(f"Message with ID {message_id} not found for webhook trigger")
            return

        # Prepare payload
        payload = {
            "message_id": message.id,
            "subject": message.subject,
            "sender_id": message.sender_id,
            "recipient_ids": [recipient.id for recipient in message.recipients],
            "status": message.status.value if hasattr(message.status, 'value') else message.status,
            "priority": message.priority.value if hasattr(message.priority, 'value') else message.priority,
            "created_at": message.created_at.isoformat() if message.created_at else None
        }

        # Trigger webhook
        await WebhookService.trigger_event(db, event, payload)

    @staticmethod
    async def _send_message(
        db: Session,
        message_id: int
    ):
        """
        Send a message via the specified delivery method.

        Args:
            db: Database session
            message_id: ID of the message to send
        """
        message = db.query(models.Message).filter(models.Message.id == message_id).first()
        if not message:
            logger.warning(f"Message with ID {message_id} not found for sending")
            return

        try:
            # Implement sending logic based on delivery method
            if message.delivery_method == models.DeliveryMethod.EMAIL:
                # TODO: Implement email sending
                logger.info(f"Sending email message {message_id}")
                # Update status to DELIVERED on success
                message.status = models.MessageStatus.DELIVERED
            elif message.delivery_method == models.DeliveryMethod.SMS:
                # TODO: Implement SMS sending
                logger.info(f"Sending SMS message {message_id}")
                # Update status to DELIVERED on success
                message.status = models.MessageStatus.DELIVERED
            elif message.delivery_method == models.DeliveryMethod.PUSH:
                # TODO: Implement push notification
                logger.info(f"Sending push message {message_id}")
                # Update status to DELIVERED on success
                message.status = models.MessageStatus.DELIVERED

            db.commit()

            # Trigger webhook for message status change
            await MessageService._trigger_message_webhook(db, message_id, "message.status_changed")

        except Exception as e:
            logger.error(f"Error sending message {message_id}: {str(e)}")
            message.status = models.MessageStatus.FAILED
            db.commit()

            # Trigger webhook for message status change
            await MessageService._trigger_message_webhook(db, message_id, "message.status_changed")

    @staticmethod
    async def get_message(
        db: Session,
        message_id: int,
        user_id: Optional[int] = None
    ) -> Optional[models.Message]:
        """
        Get a message by ID.

        Args:
            db: Database session
            message_id: ID of the message to retrieve
            user_id: ID of the user retrieving the message

        Returns:
            The message or None if not found or user doesn't have access
        """
        message = db.query(models.Message).filter(models.Message.id == message_id).first()

        if not message:
            return None

        # Check if user has access to this message
        if user_id:
            # User can access if they are the sender or a recipient
            if message.sender_id != user_id and user_id not in [r.id for r in message.recipients]:
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
            The updated message or None if not found or user doesn't have access
        """
        message = await MessageService.get_message(db, message_id, user_id)

        if not message:
            return None

        # Check if user is a recipient
        if user_id not in [r.id for r in message.recipients]:
            return None

        # Update message status
        message.is_read = True
        message.read_at = datetime.utcnow()
        message.status = models.MessageStatus.READ

        db.commit()
        db.refresh(message)

        # Trigger webhook for message status change
        await MessageService._trigger_message_webhook(db, message_id, "message.status_changed")

        return message

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
            True if deleted, False otherwise
        """
        message = await MessageService.get_message(db, message_id, user_id)

        if not message:
            return False

        # Check if user has permission to delete this message
        if message.sender_id != user_id and user_id not in [r.id for r in message.recipients]:
            return False

        # Trigger webhook before deleting
        await MessageService._trigger_message_webhook(db, message_id, "message.deleted")

        db.delete(message)
        db.commit()

        return True

    @staticmethod
    async def get_user_messages(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        folder: str = "inbox"
    ) -> Tuple[List[models.Message], int]:
        """
        Get messages for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            folder: Message folder (inbox, sent, drafts)

        Returns:
            A tuple containing the list of messages and the total count
        """
        if folder == "inbox":
            # Get messages where the user is a recipient
            query = db.query(models.Message).join(
                models.message_recipients,
                models.Message.id == models.message_recipients.c.message_id
            ).filter(
                models.message_recipients.c.user_id == user_id
            ).order_by(desc(models.Message.created_at))

            total = query.count()
            messages = query.offset(skip).limit(limit).all()

        elif folder == "sent":
            # Get messages sent by the user
            query = db.query(models.Message).filter(
                models.Message.sender_id == user_id,
                models.Message.status != models.MessageStatus.DRAFT
            ).order_by(desc(models.Message.created_at))

            total = query.count()
            messages = query.offset(skip).limit(limit).all()

        elif folder == "drafts":
            # Get draft messages
            query = db.query(models.Message).filter(
                models.Message.sender_id == user_id,
                models.Message.status == models.MessageStatus.DRAFT
            ).order_by(desc(models.Message.created_at))

            total = query.count()
            messages = query.offset(skip).limit(limit).all()

        else:
            raise HTTPException(status_code=400, detail=f"Invalid folder: {folder}")

        return messages, total

    @staticmethod
    async def upload_attachment(
        file: UploadFile,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Upload a file attachment for a message.

        Args:
            file: The file to upload
            user_id: ID of the user uploading the file

        Returns:
            A dictionary with the file information
        """
        try:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join("uploads", "messages", str(user_id))
            os.makedirs(upload_dir, exist_ok=True)

            # Generate a unique filename
            file_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)

            # Save the file
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            # Return file information
            return {
                "file_name": file.filename,
                "file_path": file_path,
                "file_size": len(contents),
                "content_type": file.content_type
            }

        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


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
            title=notification_data.title,
            content=notification_data.content,
            sender_id=sender_id,
            notification_type=notification_data.notification_type,
            priority=notification_data.priority,
            is_read=False,
            expires_at=notification_data.expires_at
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Add recipients
        for recipient_id in notification_data.recipient_ids:
            # Check if recipient exists
            recipient = db.query(models.User).filter(models.User.id == recipient_id).first()
            if recipient:
                notification.recipients.append(recipient)

        db.commit()
        db.refresh(notification)

        # Send the notification in the background
        if background_tasks:
            background_tasks.add_task(
                NotificationService._send_notification,
                db,
                notification.id
            )

            # Trigger webhook for notification creation
            background_tasks.add_task(
                NotificationService._trigger_notification_webhook,
                db,
                notification.id,
                "notification.created"
            )

        return notification

    @staticmethod
    async def _trigger_notification_webhook(
        db: Session,
        notification_id: int,
        event: str
    ):
        """
        Trigger webhook for notification events.

        Args:
            db: Database session
            notification_id: ID of the notification
            event: Event type
        """
        notification = await NotificationService.get_notification(db, notification_id)
        if not notification:
            logger.warning(f"Notification with ID {notification_id} not found for webhook trigger")
            return

        # Prepare payload
        payload = {
            "notification_id": notification.id,
            "title": notification.title,
            "sender_id": notification.sender_id,
            "recipient_ids": [recipient.id for recipient in notification.recipients],
            "notification_type": notification.notification_type.value if hasattr(notification.notification_type, 'value') else notification.notification_type,
            "priority": notification.priority.value if hasattr(notification.priority, 'value') else notification.priority,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
        }

        # Trigger webhook
        await WebhookService.trigger_event(db, event, payload)

    @staticmethod
    async def _send_notification(
        db: Session,
        notification_id: int
    ):
        """
        Send a notification to recipients.

        Args:
            db: Database session
            notification_id: ID of the notification to send
        """
        notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
        if not notification:
            logger.warning(f"Notification with ID {notification_id} not found for sending")
            return

        try:
            # Implement sending logic based on notification type
            if notification.notification_type == models.NotificationType.PUSH:
                # TODO: Implement push notification
                logger.info(f"Sending push notification {notification_id}")
            elif notification.notification_type == models.NotificationType.EMAIL:
                # TODO: Implement email notification
                logger.info(f"Sending email notification {notification_id}")
            elif notification.notification_type == models.NotificationType.SMS:
                # TODO: Implement SMS notification
                logger.info(f"Sending SMS notification {notification_id}")
            else:
                # In-app notification doesn't need additional delivery
                logger.info(f"In-app notification {notification_id} is available")

            # Trigger webhook for notification sent
            await NotificationService._trigger_notification_webhook(db, notification_id, "notification.sent")

        except Exception as e:
            logger.error(f"Error sending notification {notification_id}: {str(e)}")

            # Trigger webhook for notification error
            await NotificationService._trigger_notification_webhook(db, notification_id, "notification.error")

    @staticmethod
    async def get_notification(
        db: Session,
        notification_id: int,
        user_id: Optional[int] = None
    ) -> Optional[models.Notification]:
        """
        Get a notification by ID.

        Args:
            db: Database session
            notification_id: ID of the notification to retrieve
            user_id: ID of the user retrieving the notification

        Returns:
            The notification or None if not found or user doesn't have access
        """
        notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()

        if not notification:
            return None

        # Check if user has access to this notification
        if user_id and user_id not in [r.id for r in notification.recipients]:
            return None

        return notification

    @staticmethod
    async def mark_as_read(
        db: Session,
        notification_id: int,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> Optional[models.Notification]:
        """
        Mark a notification as read.

        Args:
            db: Database session
            notification_id: ID of the notification to mark as read
            user_id: ID of the user marking the notification as read
            background_tasks: Background tasks runner

        Returns:
            The updated notification or None if not found or user doesn't have access
        """
        notification = await NotificationService.get_notification(db, notification_id, user_id)

        if not notification:
            return None

        # Only update if the notification is not already read
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)

            # Trigger webhook for notification read
            if background_tasks:
                background_tasks.add_task(
                    NotificationService._trigger_notification_webhook,
                    db,
                    notification_id,
                    "notification.read"
                )

        return notification

    @staticmethod
    async def get_user_notifications(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False,
        notification_type: Optional[models.NotificationType] = None
    ) -> Tuple[List[models.Notification], int]:
        """
        Get notifications for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            unread_only: If True, only return unread notifications
            notification_type: Filter by notification type

        Returns:
            A tuple containing the list of notifications and the total count
        """
        # Base query for user's notifications
        query = db.query(models.Notification).join(
            models.notification_recipients,
            models.Notification.id == models.notification_recipients.c.notification_id
        ).filter(
            models.notification_recipients.c.user_id == user_id
        )

        # Apply filters
        if unread_only:
            query = query.filter(models.Notification.is_read == False)

        if notification_type:
            query = query.filter(models.Notification.notification_type == notification_type)

        # Filter out expired notifications
        now = datetime.utcnow()
        query = query.filter(
            or_(
                models.Notification.expires_at.is_(None),
                models.Notification.expires_at > now
            )
        )

        # Order by creation date, newest first
        query = query.order_by(desc(models.Notification.created_at))

        # Get total count and paginated results
        total = query.count()
        notifications = query.offset(skip).limit(limit).all()

        return notifications, total

    @staticmethod
    async def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
        """
        Delete a notification for a user.

        Args:
            db: Database session
            notification_id: ID of the notification to delete
            user_id: ID of the user deleting the notification

        Returns:
            True if the notification was deleted, False otherwise

        Raises:
            HTTPException: If the notification doesn't exist or the user doesn't have access
        """
        notification = await NotificationService.get_notification(db, notification_id, user_id)

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        # Check if user has permission to delete (recipient or admin)
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user_id not in [r.id for r in notification.recipients] and user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to delete this notification")

        # Remove the user from the recipients
        notification.recipients = [r for r in notification.recipients if r.id != user_id]

        # If no recipients left, delete the notification
        if not notification.recipients:
            db.delete(notification)
        else:
            db.commit()

        db.commit()
        return True

    @staticmethod
    async def get_unread_count(db: Session, user_id: int) -> int:
        """
        Get the count of unread notifications for a user.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            The count of unread notifications
        """
        # Get count of unread notifications
        now = datetime.utcnow()
        count = db.query(func.count(models.Notification.id)).join(
            models.notification_recipients,
            models.Notification.id == models.notification_recipients.c.notification_id
        ).filter(
            models.notification_recipients.c.user_id == user_id,
            models.Notification.is_read == False,
            or_(
                models.Notification.expires_at.is_(None),
                models.Notification.expires_at > now
            )
        ).scalar()

        return count


class AnnouncementService:
    """Service for handling system announcements."""

    @staticmethod
    async def create_announcement(
        db: Session,
        announcement_data: schemas.AnnouncementCreate,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> models.Announcement:
        """
        Create a new announcement.

        Args:
            db: Database session
            announcement_data: Announcement data
            user_id: ID of the user creating the announcement
            background_tasks: Background tasks runner

        Returns:
            The created announcement
        """
        # Create new announcement
        announcement = models.Announcement(
            title=announcement_data.title,
            content=announcement_data.content,
            announcement_type=announcement_data.announcement_type,
            is_active=announcement_data.is_active,
            is_public=announcement_data.is_public,
            start_date=announcement_data.start_date,
            end_date=announcement_data.end_date,
            created_by=user_id
        )

        db.add(announcement)
        db.commit()
        db.refresh(announcement)

        # Add targeted recipients if any
        if announcement_data.targeted_recipient_ids:
            for recipient_id in announcement_data.targeted_recipient_ids:
                recipient = db.query(models.User).filter(models.User.id == recipient_id).first()
                if recipient:
                    announcement.targeted_recipients.append(recipient)

            db.commit()
            db.refresh(announcement)

        # Trigger webhook for announcement creation
        if background_tasks:
            background_tasks.add_task(
                AnnouncementService._trigger_announcement_webhook,
                db,
                announcement.id,
                "announcement.created"
            )

        return announcement

    @staticmethod
    async def _trigger_announcement_webhook(
        db: Session,
        announcement_id: int,
        event: str
    ):
        """
        Trigger webhook for announcement events.

        Args:
            db: Database session
            announcement_id: ID of the announcement
            event: Event type
        """
        announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
        if not announcement:
            logger.warning(f"Announcement with ID {announcement_id} not found for webhook trigger")
            return

        # Prepare payload
        payload = {
            "announcement_id": announcement.id,
            "title": announcement.title,
            "announcement_type": announcement.announcement_type.value if hasattr(announcement.announcement_type, 'value') else announcement.announcement_type,
            "is_active": announcement.is_active,
            "is_public": announcement.is_public,
            "start_date": announcement.start_date.isoformat() if announcement.start_date else None,
            "end_date": announcement.end_date.isoformat() if announcement.end_date else None,
            "created_by": announcement.created_by,
            "created_at": announcement.created_at.isoformat() if announcement.created_at else None,
            "targeted_recipient_ids": [recipient.id for recipient in announcement.targeted_recipients] if announcement.targeted_recipients else []
        }

        # Trigger webhook
        await WebhookService.trigger_event(db, event, payload)

    @staticmethod
    async def update_announcement(
        db: Session,
        announcement_id: int,
        announcement_data: schemas.AnnouncementUpdate,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> Optional[models.Announcement]:
        """
        Update an existing announcement.

        Args:
            db: Database session
            announcement_id: ID of the announcement to update
            announcement_data: Updated announcement data
            user_id: ID of the user updating the announcement
            background_tasks: Background tasks runner

        Returns:
            The updated announcement or None if not found or user doesn't have permission
        """
        announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")

        # Check if user has permission to update (creator or admin)
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if announcement.created_by != user_id and user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to update this announcement")

        # Update fields if provided
        if announcement_data.title is not None:
            announcement.title = announcement_data.title

        if announcement_data.content is not None:
            announcement.content = announcement_data.content

        if announcement_data.announcement_type is not None:
            announcement.announcement_type = announcement_data.announcement_type

        if announcement_data.is_active is not None:
            announcement.is_active = announcement_data.is_active

        if announcement_data.is_public is not None:
            announcement.is_public = announcement_data.is_public

        if announcement_data.start_date is not None:
            announcement.start_date = announcement_data.start_date

        if announcement_data.end_date is not None:
            announcement.end_date = announcement_data.end_date

        # Update targeted recipients if provided
        if announcement_data.targeted_recipient_ids is not None:
            # Clear existing recipients
            announcement.targeted_recipients = []

            # Add new recipients
            for recipient_id in announcement_data.targeted_recipient_ids:
                recipient = db.query(models.User).filter(models.User.id == recipient_id).first()
                if recipient:
                    announcement.targeted_recipients.append(recipient)

        db.commit()
        db.refresh(announcement)

        # Trigger webhook for announcement update
        if background_tasks:
            background_tasks.add_task(
                AnnouncementService._trigger_announcement_webhook,
                db,
                announcement.id,
                "announcement.updated"
            )

        return announcement

    @staticmethod
    async def delete_announcement(
        db: Session,
        announcement_id: int,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> bool:
        """
        Delete an announcement.

        Args:
            db: Database session
            announcement_id: ID of the announcement to delete
            user_id: ID of the user deleting the announcement
            background_tasks: Background tasks runner

        Returns:
            True if deleted, False otherwise
        """
        announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")

        # Check if user has permission to delete (creator or admin)
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if announcement.created_by != user_id and user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to delete this announcement")

        # Trigger webhook before deleting the announcement
        if background_tasks:
            background_tasks.add_task(
                AnnouncementService._trigger_announcement_webhook,
                db,
                announcement.id,
                "announcement.deleted"
            )

        # Remove targeted recipients association
        announcement.targeted_recipients = []

        # Delete the announcement
        db.delete(announcement)
        db.commit()

        return True

    @staticmethod
    async def get_announcement(db: Session, announcement_id: int) -> models.Announcement:
        """
        Get an announcement by ID.

        Args:
            db: Database session
            announcement_id: ID of the announcement to retrieve

        Returns:
            The requested announcement

        Raises:
            HTTPException: If the announcement doesn't exist
        """
        announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        return announcement

    @staticmethod
    async def get_active_announcements(
        db: Session,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        announcement_type: Optional[models.AnnouncementType] = None
    ) -> Tuple[List[models.Announcement], int]:
        """
        Get active announcements.

        Args:
            db: Database session
            user_id: ID of the user (optional, for targeted announcements)
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            announcement_type: Filter by announcement type

        Returns:
            A tuple containing the list of announcements and the total count
        """
        # Current date for filtering
        now = datetime.utcnow()

        # Base query for active announcements
        query = db.query(models.Announcement).filter(
            models.Announcement.is_active == True,
            models.Announcement.start_date <= now,
            or_(
                models.Announcement.end_date.is_(None),
                models.Announcement.end_date >= now
            )
        )

        # Filter by type if specified
        if announcement_type:
            query = query.filter(models.Announcement.announcement_type == announcement_type)

        # If user_id is provided, include both public and targeted announcements
        if user_id:
            query = query.filter(
                or_(
                    models.Announcement.is_public == True,
                    models.Announcement.targeted_recipients.any(models.User.id == user_id)
                )
            )
        else:
            # If no user_id, only include public announcements
            query = query.filter(models.Announcement.is_public == True)

        # Order by start date, newest first
        query = query.order_by(desc(models.Announcement.start_date))

        # Get total count and paginated results
        total = query.count()
        announcements = query.offset(skip).limit(limit).all()

        return announcements, total


class SupportTicketService:
    """Service for handling support tickets."""

    @staticmethod
    async def create_ticket(
        db: Session,
        ticket_data: schemas.SupportTicketCreate,
        customer_id: int,
        background_tasks: BackgroundTasks = None
    ) -> models.SupportTicket:
        """
        Create a new support ticket.

        Args:
            db: Database session
            ticket_data: Ticket data
            customer_id: ID of the customer creating the ticket
            background_tasks: Background tasks runner

        Returns:
            The created support ticket
        """
        # Generate a ticket number
        ticket_number = f"TICKET-{uuid.uuid4().hex[:8].upper()}"

        # Create new ticket
        ticket = models.SupportTicket(
            ticket_number=ticket_number,
            subject=ticket_data.subject,
            description=ticket_data.description,
            category=ticket_data.category,
            priority=ticket_data.priority,
            status=models.TicketStatus.OPEN,
            customer_id=customer_id,
            assigned_to=ticket_data.assigned_to
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

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

            db.commit()
            db.refresh(ticket)

        # Trigger webhook for ticket creation
        if background_tasks:
            background_tasks.add_task(
                SupportTicketService._trigger_ticket_webhook,
                db,
                ticket.id,
                "ticket.created"
            )

        return ticket

    @staticmethod
    async def _trigger_ticket_webhook(
        db: Session,
        ticket_id: int,
        event: str
    ):
        """
        Trigger webhook for ticket events.

        Args:
            db: Database session
            ticket_id: ID of the ticket
            event: Event type
        """
        ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket with ID {ticket_id} not found for webhook trigger")
            return

        # Prepare payload
        payload = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "category": ticket.category.value if hasattr(ticket.category, 'value') else ticket.category,
            "priority": ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority,
            "status": ticket.status.value if hasattr(ticket.status, 'value') else ticket.status,
            "customer_id": ticket.customer_id,
            "assigned_to": ticket.assigned_to,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None
        }

        # Trigger webhook
        await WebhookService.trigger_event(db, event, payload)

    @staticmethod
    async def update_ticket(
        db: Session,
        ticket_id: int,
        ticket_data: schemas.SupportTicketUpdate,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> Optional[models.SupportTicket]:
        """
        Update an existing support ticket.

        Args:
            db: Database session
            ticket_id: ID of the ticket to update
            ticket_data: Updated ticket data
            user_id: ID of the user updating the ticket
            background_tasks: Background tasks runner

        Returns:
            The updated ticket or None if not found or user doesn't have permission
        """
        ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")

        # Check if user has permission to update (customer, assignee, or admin)
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if ticket.customer_id != user_id and ticket.assigned_to != user_id and user.role not in ["admin", "support"]:
            raise HTTPException(status_code=403, detail="You don't have permission to update this ticket")

        # Update fields if provided
        if ticket_data.subject is not None:
            ticket.subject = ticket_data.subject

        if ticket_data.description is not None:
            ticket.description = ticket_data.description

        if ticket_data.category is not None:
            ticket.category = ticket_data.category

        if ticket_data.status is not None:
            # If status is changing to closed, set closed_at timestamp
            if ticket_data.status == models.TicketStatus.CLOSED and ticket.status != models.TicketStatus.CLOSED:
                ticket.closed_at = datetime.utcnow()
            ticket.status = ticket_data.status

        if ticket_data.priority is not None:
            ticket.priority = ticket_data.priority

        if ticket_data.assigned_to is not None:
            # Check if the assigned user exists and is staff
            if ticket_data.assigned_to:
                assigned_user = db.query(models.User).filter(models.User.id == ticket_data.assigned_to).first()
                if not assigned_user:
                    raise HTTPException(status_code=404, detail="Assigned user not found")
                if assigned_user.role not in ["admin", "support"]:
                    raise HTTPException(status_code=400, detail="Can only assign tickets to staff users")
            ticket.assigned_to = ticket_data.assigned_to

        db.commit()
        db.refresh(ticket)

        # Trigger webhook for ticket update
        if background_tasks:
            background_tasks.add_task(
                SupportTicketService._trigger_ticket_webhook,
                db,
                ticket.id,
                "ticket.updated"
            )

        return ticket

    @staticmethod
    async def add_response(
        db: Session,
        ticket_id: int,
        response_data: schemas.TicketResponseCreate,
        responder_id: int,
        background_tasks: BackgroundTasks = None
    ) -> models.TicketResponse:
        """
        Add a response to a support ticket.

        Args:
            db: Database session
            ticket_id: ID of the ticket to respond to
            response_data: Response data
            responder_id: ID of the user responding
            background_tasks: Background tasks runner

        Returns:
            The created ticket response
        """
        ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")

        # Check if user has permission to respond (customer, assignee, or admin)
        user = db.query(models.User).filter(models.User.id == responder_id).first()
        if ticket.customer_id != responder_id and ticket.assigned_to != responder_id and user.role not in ["admin", "support"]:
            raise HTTPException(status_code=403, detail="You don't have permission to respond to this ticket")

        # Create new response
        response = models.TicketResponse(
            ticket_id=ticket_id,
            responder_id=responder_id,
            content=response_data.content,
            is_internal=response_data.is_internal
        )

        db.add(response)

        # Add attachments if any
        if response_data.attachments:
            for attachment_data in response_data.attachments:
                attachment = models.TicketAttachment(
                    ticket_id=ticket_id,
                    response_id=response.id,
                    file_name=attachment_data.file_name,
                    file_path=attachment_data.file_path,
                    file_size=attachment_data.file_size,
                    content_type=attachment_data.content_type
                )
                db.add(attachment)

        # Update ticket status based on who responded
        if user.role in ["admin", "support"]:
            # If staff responded, set status to waiting for customer
            ticket.status = models.TicketStatus.WAITING_CUSTOMER
        else:
            # If customer responded, set status to in progress
            ticket.status = models.TicketStatus.IN_PROGRESS

        db.commit()
        db.refresh(response)

        # Trigger webhook for ticket response
        if background_tasks:
            # Prepare response payload
            response_payload = {
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "response_id": response.id,
                "responder_id": responder_id,
                "is_internal": response.is_internal,
                "created_at": response.created_at.isoformat() if response.created_at else None
            }

            # Trigger webhook
            await WebhookService.trigger_event(db, "ticket.response_added", response_payload)

            # Also trigger ticket updated webhook
            await SupportTicketService._trigger_ticket_webhook(db, ticket.id, "ticket.updated")

        return response

    @staticmethod
    async def get_ticket(
        db: Session,
        ticket_id: int,
        user_id: int
    ) -> models.SupportTicket:
        """
        Get a support ticket by ID, ensuring the user has access to it.

        Args:
            db: Database session
            ticket_id: ID of the ticket to retrieve
            user_id: ID of the user requesting the ticket

        Returns:
            The requested support ticket

        Raises:
            HTTPException: If the ticket doesn't exist or the user doesn't have access
        """
        ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found")

        # Check if user has permission to view (customer, assignee, or admin/support)
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if ticket.customer_id != user_id and ticket.assigned_to != user_id and user.role not in ["admin", "support"]:
            raise HTTPException(status_code=403, detail="You don't have permission to view this ticket")

        return ticket

    @staticmethod
    async def get_tickets(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[models.TicketStatus] = None,
        category: Optional[models.TicketCategory] = None,
        priority: Optional[models.TicketPriority] = None,
        role: str = "customer"
    ) -> Tuple[List[models.SupportTicket], int]:
        """
        Get support tickets based on user role and filters.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            status: Filter by ticket status
            category: Filter by ticket category
            priority: Filter by ticket priority
            role: User role (customer, support, admin)

        Returns:
            A tuple containing the list of tickets and the total count
        """
        # Base query depends on user role
        if role == "customer":
            # Customers can only see their own tickets
            query = db.query(models.SupportTicket).filter(models.SupportTicket.customer_id == user_id)
        elif role == "support":
            # Support staff can see tickets assigned to them and unassigned tickets
            query = db.query(models.SupportTicket).filter(
                or_(
                    models.SupportTicket.assigned_to == user_id,
                    models.SupportTicket.assigned_to.is_(None)
                )
            )
        else:  # admin
            # Admins can see all tickets
            query = db.query(models.SupportTicket)

        # Apply filters
        if status:
            query = query.filter(models.SupportTicket.status == status)

        if category:
            query = query.filter(models.SupportTicket.category == category)

        if priority:
            query = query.filter(models.SupportTicket.priority == priority)

        # Order by creation date, newest first
        query = query.order_by(desc(models.SupportTicket.created_at))

        # Get total count and paginated results
        total = query.count()
        tickets = query.offset(skip).limit(limit).all()

        return tickets, total

    @staticmethod
    async def get_ticket_statistics(db: Session, user_id: int, role: str) -> schemas.TicketStatistics:
        """
        Get statistics about support tickets.

        Args:
            db: Database session
            user_id: ID of the user
            role: User role (customer, support, admin)

        Returns:
            Ticket statistics
        """
        # Base query depends on user role
        if role == "customer":
            # Customers can only see stats for their own tickets
            base_query = db.query(models.SupportTicket).filter(models.SupportTicket.customer_id == user_id)
        elif role == "support":
            # Support staff can see stats for tickets assigned to them and unassigned tickets
            base_query = db.query(models.SupportTicket).filter(
                or_(
                    models.SupportTicket.assigned_to == user_id,
                    models.SupportTicket.assigned_to.is_(None)
                )
            )
        else:  # admin
            # Admins can see stats for all tickets
            base_query = db.query(models.SupportTicket)

        # Get counts for each status
        total = base_query.count()
        open_count = base_query.filter(models.SupportTicket.status == models.TicketStatus.OPEN).count()
        in_progress_count = base_query.filter(models.SupportTicket.status == models.TicketStatus.IN_PROGRESS).count()
        waiting_customer_count = base_query.filter(models.SupportTicket.status == models.TicketStatus.WAITING_CUSTOMER).count()
        waiting_third_party_count = base_query.filter(models.SupportTicket.status == models.TicketStatus.WAITING_THIRD_PARTY).count()
        resolved_count = base_query.filter(models.SupportTicket.status == models.TicketStatus.RESOLVED).count()
        closed_count = base_query.filter(models.SupportTicket.status == models.TicketStatus.CLOSED).count()

        return schemas.TicketStatistics(
            total=total,
            open=open_count,
            in_progress=in_progress_count,
            waiting_customer=waiting_customer_count,
            waiting_third_party=waiting_third_party_count,
            resolved=resolved_count,
            closed=closed_count
        )

    @staticmethod
    async def upload_attachment(
        file: UploadFile,
        user_id: int,
        attachment_type: str = "ticket"
    ) -> Dict[str, Any]:
        """
        Upload a file attachment for a ticket or response.

        Args:
            file: The file to upload
            user_id: ID of the user uploading the file
            attachment_type: Type of attachment (ticket or response)

        Returns:
            A dictionary with the file information
        """
        try:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join("uploads", "tickets", str(user_id))
            os.makedirs(upload_dir, exist_ok=True)

            # Generate a unique filename
            file_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)

            # Save the file
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            # Return file information
            return {
                "file_name": file.filename,
                "file_path": file_path,
                "file_size": len(contents),
                "content_type": file.content_type
            }

        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


class TemplateService:
    """Service for handling message and notification templates."""

    @staticmethod
    async def create_template(
        db: Session,
        template_data: schemas.TemplateCreate,
        created_by: int
    ) -> models.Template:
        """
        Create a new template.

        Args:
            db: Database session
            template_data: Template data
            created_by: ID of the user creating the template

        Returns:
            The created template
        """
        # Create new template
        db_template = models.Template(
            name=template_data.name,
            subject=template_data.subject,
            body=template_data.body,
            template_type=template_data.template_type,
            is_active=template_data.is_active,
            created_by=created_by
        )
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        return db_template

    @staticmethod
    async def update_template(
        db: Session,
        template_id: int,
        template_data: schemas.TemplateUpdate,
        user_id: int
    ) -> models.Template:
        """
        Update a template.

        Args:
            db: Database session
            template_id: ID of the template to update
            template_data: Updated template data
            user_id: ID of the user updating the template

        Returns:
            The updated template

        Raises:
            HTTPException: If the template doesn't exist or the user doesn't have permission
        """
        # Get the template
        template = db.query(models.Template).filter(models.Template.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Check if user has permission to update (creator or admin)
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if template.created_by != user_id and user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to update this template")

        # Update fields if provided
        if template_data.name is not None:
            template.name = template_data.name

        if template_data.subject is not None:
            template.subject = template_data.subject

        if template_data.body is not None:
            template.body = template_data.body

        if template_data.template_type is not None:
            template.template_type = template_data.template_type

        if template_data.is_active is not None:
            template.is_active = template_data.is_active

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    async def get_template(db: Session, template_id: int) -> models.Template:
        """
        Get a template by ID.

        Args:
            db: Database session
            template_id: ID of the template to retrieve

        Returns:
            The requested template

        Raises:
            HTTPException: If the template doesn't exist
        """
        template = db.query(models.Template).filter(models.Template.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template

    @staticmethod
    async def delete_template(db: Session, template_id: int, user_id: int) -> bool:
        """
        Delete a template.

        Args:
            db: Database session
            template_id: ID of the template to delete
            user_id: ID of the user deleting the template

        Returns:
            True if the template was deleted, False otherwise

        Raises:
            HTTPException: If the template doesn't exist or the user doesn't have permission
        """
        # Get the template
        template = db.query(models.Template).filter(models.Template.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Check if user has permission to delete (creator or admin)
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if template.created_by != user_id and user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to delete this template")

        # Delete the template
        db.delete(template)
        db.commit()
        return True

    @staticmethod
    async def get_templates(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        template_type: Optional[str] = None,
        active_only: bool = False
    ) -> Tuple[List[models.Template], int]:
        """
        Get templates based on filters.

        Args:
            db: Database session
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            template_type: Filter by template type
            active_only: If True, only return active templates

        Returns:
            A tuple containing the list of templates and the total count
        """
        # Base query
        query = db.query(models.Template)

        # Apply filters
        if template_type:
            query = query.filter(models.Template.template_type == template_type)

        if active_only:
            query = query.filter(models.Template.is_active == True)

        # Order by name
        query = query.order_by(models.Template.name)

        # Get total count and paginated results
        total = query.count()
        templates = query.offset(skip).limit(limit).all()

        return templates, total

    @staticmethod
    async def render_template(
        db: Session,
        template_id: int,
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render a template with the provided context.

        Args:
            db: Database session
            template_id: ID of the template to render
            context: Context variables for rendering

        Returns:
            A dictionary with the rendered subject and body

        Raises:
            HTTPException: If the template doesn't exist
        """
        from jinja2 import Template as JinjaTemplate

        # Get the template
        template = await TemplateService.get_template(db, template_id)

        try:
            # Render subject and body with Jinja2
            subject_template = JinjaTemplate(template.subject)
            body_template = JinjaTemplate(template.body)

            rendered_subject = subject_template.render(**context)
            rendered_body = body_template.render(**context)

            return {
                "subject": rendered_subject,
                "body": rendered_body
            }

        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error rendering template: {str(e)}")

    @staticmethod
    async def get_template_by_name(
        db: Session,
        template_name: str,
        template_type: Optional[str] = None
    ) -> models.Template:
        """
        Get a template by name and optionally type.

        Args:
            db: Database session
            template_name: Name of the template
            template_type: Type of the template

        Returns:
            The requested template

        Raises:
            HTTPException: If the template doesn't exist
        """
        query = db.query(models.Template).filter(models.Template.name == template_name)

        if template_type:
            query = query.filter(models.Template.template_type == template_type)

        template = query.first()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return template
