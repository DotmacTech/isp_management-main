"""
Notification endpoints for the CRM & Ticketing module.

This module provides API endpoints for managing notification settings and preferences
for ticket-related events and updates.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth import get_current_user, require_permissions
from ..services.notification_service import NotificationService
from ..services.ticket_service import TicketService
from ..schemas.notification import NotificationPreference, NotificationPreferenceUpdate

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    responses={404: {"description": "Not found"}},
)


@router.get("/settings", response_model=Dict[str, bool])
async def get_notification_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get global notification settings.
    
    Returns:
        Dictionary of notification settings
    """
    require_permissions(current_user, ["crm.view_notification_settings"])
    
    notification_service = NotificationService(db)
    settings = {
        "email_enabled": notification_service.email_enabled,
        "sms_enabled": notification_service.sms_enabled,
        "push_enabled": notification_service.push_enabled,
        "internal_enabled": notification_service.internal_enabled
    }
    
    return settings


@router.get("/preferences", response_model=List[NotificationPreference])
async def get_user_notification_preferences(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get notification preferences for the current user.
    
    Returns:
        List of notification preference objects
    """
    # In a real implementation, this would retrieve user preferences from the database
    # For now, we'll return mock data
    
    # Mock preferences - in a real implementation, these would come from a database
    preferences = [
        {
            "id": 1,
            "user_id": current_user.id,
            "notification_type": "ticket_created",
            "email_enabled": True,
            "push_enabled": True,
            "sms_enabled": False
        },
        {
            "id": 2,
            "user_id": current_user.id,
            "notification_type": "ticket_updated",
            "email_enabled": True,
            "push_enabled": True,
            "sms_enabled": False
        },
        {
            "id": 3,
            "user_id": current_user.id,
            "notification_type": "ticket_comment_added",
            "email_enabled": True,
            "push_enabled": True,
            "sms_enabled": False
        },
        {
            "id": 4,
            "user_id": current_user.id,
            "notification_type": "sla_breach",
            "email_enabled": True,
            "push_enabled": True,
            "sms_enabled": True
        }
    ]
    
    return preferences


@router.put("/preferences/{preference_id}", response_model=NotificationPreference)
async def update_notification_preference(
    preference_data: NotificationPreferenceUpdate,
    preference_id: int = Path(..., description="The ID of the notification preference to update"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update a notification preference.
    
    Args:
        preference_id: The ID of the notification preference to update
        preference_data: New data for the notification preference
        
    Returns:
        The updated notification preference object
    """
    # In a real implementation, this would update the preference in the database
    # For now, we'll return mock data
    
    # Mock updated preference - in a real implementation, this would be updated in the database
    updated_preference = {
        "id": preference_id,
        "user_id": current_user.id,
        "notification_type": "ticket_updated",  # This would be retrieved from the database
        "email_enabled": preference_data.email_enabled,
        "push_enabled": preference_data.push_enabled,
        "sms_enabled": preference_data.sms_enabled
    }
    
    return updated_preference


@router.post("/test", status_code=status.HTTP_202_ACCEPTED)
async def send_test_notification(
    notification_type: str = Query(..., description="Type of notification to test"),
    background_tasks: BackgroundTasks = Depends(),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Send a test notification to the current user.
    
    Args:
        notification_type: Type of notification to test
        
    Returns:
        Success message
    """
    require_permissions(current_user, ["crm.send_test_notification"])
    
    notification_service = NotificationService(db)
    ticket_service = TicketService(db)
    
    # Get a sample ticket for testing
    sample_tickets = ticket_service.list_tickets(limit=1)
    
    if not sample_tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tickets found for testing notifications"
        )
    
    sample_ticket = sample_tickets[0]
    
    # Send the appropriate test notification based on the type
    if notification_type == "ticket_created":
        # Add as background task to avoid blocking the response
        background_tasks.add_task(
            notification_service.notify_ticket_created,
            ticket=sample_ticket,
            user_id=current_user.id
        )
    
    elif notification_type == "ticket_updated":
        # Mock changes for testing
        changes = [
            ("status", sample_ticket.status, sample_ticket.status),
            ("priority", sample_ticket.priority, sample_ticket.priority)
        ]
        
        # Add as background task to avoid blocking the response
        background_tasks.add_task(
            notification_service.notify_ticket_updated,
            ticket=sample_ticket,
            user_id=current_user.id,
            changes=changes
        )
    
    elif notification_type == "ticket_comment_added":
        # Get a sample comment if available
        if sample_ticket.comments:
            sample_comment = sample_ticket.comments[0]
            
            # Add as background task to avoid blocking the response
            background_tasks.add_task(
                notification_service.notify_ticket_comment_added,
                ticket=sample_ticket,
                comment=sample_comment,
                user_id=current_user.id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No comments found for testing notifications"
            )
    
    elif notification_type == "sla_breach":
        # Add as background task to avoid blocking the response
        background_tasks.add_task(
            notification_service.notify_sla_breach,
            ticket=sample_ticket,
            breach_type="first_response"
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported notification type: {notification_type}"
        )
    
    return {"message": f"Test {notification_type} notification sent successfully"}
