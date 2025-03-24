"""
Notification Service for the Field Services Module.

This service handles notifications for field technicians, dispatchers, and customers
regarding job status updates, SLA alerts, and other important events.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload

from ..models import (
    Job, JobStatusEnum, Technician, TechnicianStatusEnum,
    TechnicianNotification, NotificationTypeEnum, NotificationPriorityEnum
)
from ..schemas import (
    TechnicianNotificationCreate, TechnicianNotificationUpdate, TechnicianNotificationResponse
)
from backend_core.utils.hateoas import add_resource_links


class NotificationService:
    """Service for managing field service notifications."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_notification(self, notification_data: TechnicianNotificationCreate) -> TechnicianNotificationResponse:
        """Create a new notification for a technician."""
        # Create notification object from schema
        notification = TechnicianNotification(
            technician_id=notification_data.technician_id,
            title=notification_data.title,
            message=notification_data.message,
            notification_type=self._get_notification_type_enum(notification_data.notification_type),
            priority=self._get_notification_priority_enum(notification_data.priority),
            job_id=notification_data.job_id,
            is_read=False,
            expiry_date=notification_data.expiry_date
        )
        
        # Add to database
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # Convert to response model
        return self._to_response(notification)
    
    def get_technician_notifications(
        self, 
        technician_id: int,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[TechnicianNotificationResponse]:
        """Get notifications for a technician."""
        query = self.db.query(TechnicianNotification).filter(
            TechnicianNotification.technician_id == technician_id
        )
        
        # Apply filters
        if unread_only:
            query = query.filter(TechnicianNotification.is_read == False)
        
        if notification_type:
            query = query.filter(TechnicianNotification.notification_type == NotificationTypeEnum[notification_type.upper()])
        
        # Filter out expired notifications
        query = query.filter(
            or_(
                TechnicianNotification.expiry_date == None,
                TechnicianNotification.expiry_date > datetime.utcnow()
            )
        )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(TechnicianNotification.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        notifications = query.all()
        
        # Convert to response models
        notification_responses = [self._to_response(notification) for notification in notifications]
        
        return notification_responses, total
    
    def mark_notification_as_read(self, notification_id: int) -> Optional[TechnicianNotificationResponse]:
        """Mark a notification as read."""
        notification = self.db.query(TechnicianNotification).filter(
            TechnicianNotification.id == notification_id
        ).first()
        
        if not notification:
            return None
        
        # Update notification
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        # Commit changes
        self.db.commit()
        self.db.refresh(notification)
        
        # Convert to response model
        return self._to_response(notification)
    
    def mark_all_notifications_as_read(self, technician_id: int) -> int:
        """Mark all notifications for a technician as read."""
        # Update all unread notifications
        result = self.db.query(TechnicianNotification).filter(
            TechnicianNotification.technician_id == technician_id,
            TechnicianNotification.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        
        # Commit changes
        self.db.commit()
        
        return result
    
    def delete_notification(self, notification_id: int) -> bool:
        """Delete a notification."""
        notification = self.db.query(TechnicianNotification).filter(
            TechnicianNotification.id == notification_id
        ).first()
        
        if not notification:
            return False
        
        # Delete notification
        self.db.delete(notification)
        self.db.commit()
        
        return True
    
    def create_job_assigned_notification(self, job_id: int, technician_id: int) -> TechnicianNotificationResponse:
        """Create a notification for a job assignment."""
        # Get job details
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")
        
        # Create notification
        notification_data = TechnicianNotificationCreate(
            technician_id=technician_id,
            title="New Job Assigned",
            message=f"You have been assigned to job: {job.title}. Please review the details and confirm.",
            notification_type="JOB_ASSIGNMENT",
            priority="HIGH",
            job_id=job_id,
            expiry_date=job.scheduled_end_time if job.scheduled_end_time else None
        )
        
        return self.create_notification(notification_data)
    
    def create_job_updated_notification(self, job_id: int) -> List[TechnicianNotificationResponse]:
        """Create notifications for job updates."""
        # Get job details
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job or not job.technician_id:
            return []
        
        # Create notification
        notification_data = TechnicianNotificationCreate(
            technician_id=job.technician_id,
            title="Job Updated",
            message=f"Job '{job.title}' has been updated. Please review the changes.",
            notification_type="JOB_UPDATE",
            priority="MEDIUM",
            job_id=job_id,
            expiry_date=job.scheduled_end_time if job.scheduled_end_time else None
        )
        
        notification = self.create_notification(notification_data)
        
        return [notification]
    
    def create_sla_alert_notifications(self) -> List[TechnicianNotificationResponse]:
        """Create notifications for jobs approaching SLA deadlines."""
        # Find jobs approaching SLA deadline (within next 2 hours)
        jobs_at_risk = self.db.query(Job).filter(
            Job.status.in_([JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS]),
            Job.sla_deadline.between(datetime.utcnow(), datetime.utcnow() + timedelta(hours=2))
        ).all()
        
        notifications = []
        
        for job in jobs_at_risk:
            if not job.technician_id:
                continue
            
            # Calculate time remaining
            time_remaining = (job.sla_deadline - datetime.utcnow()).total_seconds() / 60  # minutes
            
            # Create notification
            notification_data = TechnicianNotificationCreate(
                technician_id=job.technician_id,
                title="SLA Alert",
                message=f"Job '{job.title}' is approaching its SLA deadline. Only {int(time_remaining)} minutes remaining.",
                notification_type="SLA_ALERT",
                priority="HIGH",
                job_id=job.id,
                expiry_date=job.sla_deadline
            )
            
            notification = self.create_notification(notification_data)
            notifications.append(notification)
        
        return notifications
    
    def create_inventory_alert_notification(
        self, 
        technician_id: int, 
        inventory_id: int, 
        inventory_name: str, 
        quantity: int
    ) -> TechnicianNotificationResponse:
        """Create a notification for low inventory."""
        # Create notification
        notification_data = TechnicianNotificationCreate(
            technician_id=technician_id,
            title="Low Inventory Alert",
            message=f"Your inventory of {inventory_name} is running low. Only {quantity} units remaining.",
            notification_type="INVENTORY_ALERT",
            priority="MEDIUM",
            job_id=None,
            expiry_date=datetime.utcnow() + timedelta(days=3)  # Expire after 3 days
        )
        
        return self.create_notification(notification_data)
    
    def get_notification_statistics(self, technician_id: int) -> Dict[str, Any]:
        """Get notification statistics for a technician."""
        # Get count of unread notifications
        unread_count = self.db.query(TechnicianNotification).filter(
            TechnicianNotification.technician_id == technician_id,
            TechnicianNotification.is_read == False,
            or_(
                TechnicianNotification.expiry_date == None,
                TechnicianNotification.expiry_date > datetime.utcnow()
            )
        ).count()
        
        # Get counts by notification type
        type_counts = self.db.query(
            TechnicianNotification.notification_type,
            func.count(TechnicianNotification.id).label('count')
        ).filter(
            TechnicianNotification.technician_id == technician_id,
            TechnicianNotification.is_read == False,
            or_(
                TechnicianNotification.expiry_date == None,
                TechnicianNotification.expiry_date > datetime.utcnow()
            )
        ).group_by(TechnicianNotification.notification_type).all()
        
        type_stats = {}
        for notification_type, count in type_counts:
            # Handle both string and enum types
            if hasattr(notification_type, 'value'):
                type_stats[notification_type.value] = count
            else:
                type_stats[notification_type] = count
        
        # Get counts by priority
        priority_counts = self.db.query(
            TechnicianNotification.priority,
            func.count(TechnicianNotification.id).label('count')
        ).filter(
            TechnicianNotification.technician_id == technician_id,
            TechnicianNotification.is_read == False,
            or_(
                TechnicianNotification.expiry_date == None,
                TechnicianNotification.expiry_date > datetime.utcnow()
            )
        ).group_by(TechnicianNotification.priority).all()
        
        priority_stats = {}
        for priority, count in priority_counts:
            # Handle both string and enum types
            if hasattr(priority, 'value'):
                priority_stats[priority.value] = count
            else:
                priority_stats[priority] = count
        
        # Return statistics
        return {
            "technician_id": technician_id,
            "total_unread": unread_count,
            "by_type": type_stats,
            "by_priority": priority_stats
        }
    
    def _get_notification_type_enum(self, notification_type):
        """Convert string or enum to NotificationTypeEnum."""
        if isinstance(notification_type, NotificationTypeEnum):
            return notification_type
        
        if isinstance(notification_type, str):
            try:
                return NotificationTypeEnum[notification_type.upper()]
            except KeyError:
                # Try to match by value
                for enum_type in NotificationTypeEnum:
                    if enum_type.value == notification_type.lower():
                        return enum_type
                
                raise ValueError(f"Invalid notification type: {notification_type}")
        
        return notification_type
        
    def _get_notification_priority_enum(self, priority):
        """Convert string or enum to NotificationPriorityEnum."""
        if isinstance(priority, NotificationPriorityEnum):
            return priority
        
        if isinstance(priority, str):
            try:
                return NotificationPriorityEnum[priority.upper()]
            except KeyError:
                # Try to match by value
                for enum_priority in NotificationPriorityEnum:
                    if enum_priority.value == priority.lower():
                        return enum_priority
                
                raise ValueError(f"Invalid notification priority: {priority}")
        
        return priority
    
    def _to_response(self, notification: TechnicianNotification) -> TechnicianNotificationResponse:
        """Convert TechnicianNotification model to TechnicianNotificationResponse schema."""
        response_dict = {
            "id": notification.id,
            "technician_id": notification.technician_id,
            "title": notification.title,
            "message": notification.message,
            "notification_type": notification.notification_type.value,
            "priority": notification.priority.value,
            "job_id": notification.job_id,
            "is_read": notification.is_read,
            "read_at": notification.read_at,
            "expiry_date": notification.expiry_date,
            "created_at": notification.created_at
        }
        
        # Add HATEOAS links
        links = [
            {"rel": "self", "href": f"/api/field-services/technicians/{notification.technician_id}/notifications/{notification.id}"},
            {"rel": "technician", "href": f"/api/field-services/technicians/{notification.technician_id}"}
        ]
        
        if notification.job_id:
            links.append({"rel": "job", "href": f"/api/field-services/jobs/{notification.job_id}"})
        
        response_dict["links"] = links
        
        return TechnicianNotificationResponse(**response_dict)
