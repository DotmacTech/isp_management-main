"""
Announcement service for the Communications module.

This module provides the AnnouncementService class for handling announcement-related operations
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


class AnnouncementService:
    """Service for handling system announcements."""

    @staticmethod
    async def create_announcement(
        db: Session,
        announcement_data: schemas.AnnouncementCreate,
        created_by: int,
        background_tasks: BackgroundTasks = None
    ) -> models.Announcement:
        """
        Create a new announcement.

        Args:
            db: Database session
            announcement_data: Announcement data
            created_by: ID of the user creating the announcement
            background_tasks: Background tasks runner

        Returns:
            The created announcement
        """
        # Create the announcement
        announcement = models.Announcement(
            title=announcement_data.title,
            content=announcement_data.content,
            announcement_type=announcement_data.announcement_type,
            created_by=created_by,
            start_date=announcement_data.start_date,
            end_date=announcement_data.end_date
        )
        
        # Add targeted recipients if any
        if announcement_data.targeted_recipient_ids:
            for recipient_id in announcement_data.targeted_recipient_ids:
                user = db.query(User).filter(User.id == recipient_id).first()
                if user:
                    announcement.targeted_recipients.append(user)
        
        # Save to database
        db.add(announcement)
        db.commit()
        db.refresh(announcement)
        
        # Trigger webhook in background if available
        if background_tasks:
            background_tasks.add_task(
                WebhookService.trigger_event,
                "announcement.created",
                {
                    "announcement_id": announcement.id,
                    "title": announcement.title,
                    "announcement_type": announcement.announcement_type.value,
                    "is_public": announcement.is_public,
                    "created_at": announcement.created_at.isoformat()
                }
            )
        
        return announcement

    @staticmethod
    async def _trigger_announcement_webhook(
        db: Session,
        announcement_id: int,
        event_type: str
    ) -> None:
        """
        Trigger a webhook for an announcement event.

        Args:
            db: Database session
            announcement_id: ID of the announcement
            event_type: Type of event (created, updated, etc.)
        """
        # Get the announcement
        announcement = await AnnouncementService.get_announcement(db, announcement_id=announcement_id)
        if not announcement:
            logger.error(f"Announcement {announcement_id} not found for webhook trigger")
            return
        
        # Prepare webhook payload
        payload = {
            "id": announcement.id,
            "title": announcement.title,
            "announcement_type": announcement.announcement_type.value,
            "created_by": announcement.created_by,
            "created_at": announcement.created_at.isoformat(),
            "event_type": event_type
        }
        
        # Trigger webhook
        await WebhookService.trigger_event(
            event_type=event_type,
            payload=payload
        )

    @staticmethod
    async def get_announcement(
        db: Session,
        announcement_id: int,
        user_id: int = None
    ) -> Optional[models.Announcement]:
        """
        Get an announcement by ID.

        Args:
            db: Database session
            announcement_id: ID of the announcement to retrieve
            user_id: ID of the user requesting the announcement (for permission check)

        Returns:
            The announcement if found and user has permission, None otherwise
        """
        announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
        
        # Check if announcement exists
        if not announcement:
            return None
        
        # Check if user has permission to view this announcement
        if user_id:
            # Creator can always view
            if user_id == announcement.created_by:
                return announcement
            
            # Public announcements can be viewed by anyone
            if announcement.is_public:
                return announcement
            
            # Check if user is in targeted recipients
            if hasattr(announcement, 'targeted_recipients') and announcement.targeted_recipients:
                for recipient in announcement.targeted_recipients:
                    if recipient.id == user_id:
                        return announcement
                return None
        
        return announcement

    @staticmethod
    async def update_announcement(
        db: Session,
        announcement_id: int,
        update_data: schemas.AnnouncementUpdate,
        user_id: int,
        background_tasks: BackgroundTasks = None
    ) -> Optional[models.Announcement]:
        """
        Update an announcement.

        Args:
            db: Database session
            announcement_id: ID of the announcement to update
            update_data: Updated announcement data
            user_id: ID of the user updating the announcement
            background_tasks: Background tasks runner

        Returns:
            The updated announcement if successful, None otherwise
        """
        announcement = await AnnouncementService.get_announcement(db, announcement_id=announcement_id)
        
        # Check if announcement exists
        if not announcement:
            return None
        
        # Only creator can update
        if user_id != announcement.created_by:
            return None
        
        # Update fields
        if update_data.title is not None:
            announcement.title = update_data.title
        if update_data.content is not None:
            announcement.content = update_data.content
        if update_data.announcement_type is not None:
            announcement.announcement_type = update_data.announcement_type
        if update_data.start_date is not None:
            announcement.start_date = update_data.start_date
        if update_data.end_date is not None:
            announcement.end_date = update_data.end_date
        if update_data.is_active is not None:
            announcement.is_active = update_data.is_active
        
        # Update targeted recipients if provided
        if update_data.targeted_recipient_ids is not None:
            # Clear existing recipients
            announcement.targeted_recipients = []
            
            # Add new recipients
            for recipient_id in update_data.targeted_recipient_ids:
                user = db.query(User).filter(User.id == recipient_id).first()
                if user:
                    announcement.targeted_recipients.append(user)
        
        # Save changes
        announcement.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(announcement)
        
        # Trigger webhook in background if available
        if background_tasks:
            background_tasks.add_task(
                WebhookService.trigger_event,
                "announcement.updated",
                {
                    "announcement_id": announcement.id,
                    "title": announcement.title,
                    "announcement_type": announcement.announcement_type.value,
                    "is_public": announcement.is_public,
                    "is_active": announcement.is_active,
                    "created_at": announcement.created_at.isoformat(),
                    "updated_at": announcement.updated_at.isoformat()
                }
            )
        
        return announcement

    @staticmethod
    async def delete_announcement(
        db: Session,
        announcement_id: int,
        user_id: int
    ) -> bool:
        """
        Delete an announcement.

        Args:
            db: Database session
            announcement_id: ID of the announcement to delete
            user_id: ID of the user deleting the announcement

        Returns:
            True if successful, False otherwise
        """
        announcement = await AnnouncementService.get_announcement(db, announcement_id=announcement_id)
        
        # Check if announcement exists
        if not announcement:
            return False
        
        # Only creator can delete
        if user_id != announcement.created_by:
            return False
        
        # Delete announcement
        db.delete(announcement)
        db.commit()
        
        return True

    @staticmethod
    async def get_active_announcements(
        db: Session,
        user_id: int = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[models.Announcement]:
        """
        Get active announcements for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of announcements to skip (for pagination)
            limit: Maximum number of announcements to return

        Returns:
            List of active announcements
        """
        current_time = datetime.utcnow()
        
        # Base query for active announcements
        query = db.query(models.Announcement).filter(
            (models.Announcement.start_date <= current_time) &
            (models.Announcement.end_date >= current_time)
        )
        
        if user_id:
            # Include public announcements and targeted announcements for this user
            public_announcements = query.filter(
                models.Announcement.announcement_type == models.AnnouncementType.PUBLIC
            )
            
            # This is a simplified approach - in a real system you'd use a more efficient query
            # with joins to get targeted announcements
            targeted_announcements = []
            for announcement in query.filter(
                models.Announcement.announcement_type == models.AnnouncementType.TARGETED
            ).all():
                for recipient in announcement.targeted_recipients:
                    if recipient.id == user_id:
                        targeted_announcements.append(announcement)
                        break
            
            # Combine results
            announcements = list(public_announcements) + targeted_announcements
            
            # Sort by creation date (newest first)
            announcements.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply pagination manually
            announcements = announcements[skip:skip+limit]
        else:
            # Order by creation date (newest first)
            query = query.order_by(desc(models.Announcement.created_at))
            
            # Apply pagination
            announcements = query.offset(skip).limit(limit).all()
        
        return announcements
