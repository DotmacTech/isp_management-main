"""
API endpoints for the Communications module.

This module provides API endpoints for handling communications-related operations
in the ISP Management Platform, including messages, notifications, announcements,
and support tickets.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user
from backend_core.models import User
from modules.communications import models, schemas, services
from modules.communications.external_services import ExternalServiceManager

# Create routers for different communication types
message_router = APIRouter(prefix="/messages", tags=["Messages"])
notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])
announcement_router = APIRouter(prefix="/announcements", tags=["Announcements"])
ticket_router = APIRouter(prefix="/tickets", tags=["Support Tickets"])
template_router = APIRouter(prefix="/templates", tags=["Message Templates"])

# Message endpoints
@message_router.post("/", response_model=schemas.Message)
async def create_message(
    message_data: schemas.MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new message.
    """
    # Check if the user has permission to send messages
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to send messages")
    
    # If delivery method is not IN_APP, check if there's an active external service for that method
    if message_data.delivery_method != models.DeliveryMethod.IN_APP:
        # Check if there's an active service for this delivery method
        service_type = message_data.delivery_method.value.lower()
        services, _ = await ExternalServiceManager.get_services(
            db=db,
            service_type=service_type,
            active_only=True,
            limit=1
        )
        
        if not services:
            raise HTTPException(
                status_code=400, 
                detail=f"No active external service found for delivery method: {message_data.delivery_method.value}"
            )
    
    # Create the message
    return await services.MessageService.create_message(
        db=db,
        message_data=message_data,
        sender_id=current_user.id,
        background_tasks=background_tasks
    )


@message_router.get("/{message_id}", response_model=schemas.Message)
async def get_message(
    message_id: int = Path(..., description="The ID of the message to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a message by ID.
    """
    return await services.MessageService.get_message(
        db=db,
        message_id=message_id,
        user_id=current_user.id
    )


@message_router.put("/{message_id}/read", response_model=schemas.Message)
async def mark_message_as_read(
    message_id: int = Path(..., description="The ID of the message to mark as read"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark a message as read.
    """
    return await services.MessageService.mark_as_read(
        db=db,
        message_id=message_id,
        user_id=current_user.id
    )


@message_router.delete("/{message_id}", response_model=schemas.MessageResponse)
async def delete_message(
    message_id: int = Path(..., description="The ID of the message to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a message.
    """
    result = await services.MessageService.delete_message(
        db=db,
        message_id=message_id,
        user_id=current_user.id
    )
    if result:
        return {"message": "Message deleted successfully"}
    return {"message": "Failed to delete message"}


@message_router.get("/", response_model=schemas.PaginatedResponse)
async def get_messages(
    folder: str = Query("inbox", description="Message folder (inbox, sent, drafts)"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get messages for the current user.
    """
    messages, total = await services.MessageService.get_user_messages(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        folder=folder
    )
    return schemas.PaginatedResponse.create(
        items=messages,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@message_router.post("/attachments/upload", response_model=schemas.FileUploadResponse)
async def upload_message_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file attachment for a message.
    """
    result = await services.MessageService.upload_attachment(
        file=file,
        user_id=current_user.id
    )
    return schemas.FileUploadResponse(
        file_name=result["file_name"],
        file_path=result["file_path"],
        file_size=result["file_size"],
        content_type=result["content_type"]
    )


# Notification endpoints
@notification_router.post("/", response_model=schemas.Notification)
async def create_notification(
    notification_data: schemas.NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new notification.
    Admin or support role required.
    """
    # Check if the user has permission to send notifications
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to send notifications")
    
    # If notification type is not IN_APP, check if there's an active external service for that type
    if notification_data.notification_type != models.NotificationType.IN_APP:
        # Check if there's an active service for this notification type
        service_type = notification_data.notification_type.value.lower()
        services, _ = await ExternalServiceManager.get_services(
            db=db,
            service_type=service_type,
            active_only=True,
            limit=1
        )
        
        if not services:
            raise HTTPException(
                status_code=400, 
                detail=f"No active external service found for notification type: {notification_data.notification_type.value}"
            )
    
    # Create the notification
    return await services.NotificationService.create_notification(
        db=db,
        notification_data=notification_data,
        sender_id=current_user.id,
        background_tasks=background_tasks
    )


@notification_router.get("/{notification_id}", response_model=schemas.Notification)
async def get_notification(
    notification_id: int = Path(..., description="The ID of the notification to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a notification by ID.
    """
    return await services.NotificationService.get_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )


@notification_router.put("/{notification_id}/read", response_model=schemas.Notification)
async def mark_notification_as_read(
    notification_id: int = Path(..., description="The ID of the notification to mark as read"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark a notification as read.
    """
    return await services.NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )


@notification_router.delete("/{notification_id}", response_model=schemas.MessageResponse)
async def delete_notification(
    notification_id: int = Path(..., description="The ID of the notification to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a notification.
    """
    result = await services.NotificationService.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    if result:
        return {"message": "Notification deleted successfully"}
    return {"message": "Failed to delete notification"}


@notification_router.get("/", response_model=schemas.PaginatedResponse)
async def get_notifications(
    unread_only: bool = Query(False, description="If True, only return unread notifications"),
    notification_type: Optional[schemas.NotificationTypeEnum] = Query(None, description="Filter by notification type"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get notifications for the current user.
    """
    notifications, total = await services.NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
        notification_type=notification_type
    )
    return schemas.PaginatedResponse.create(
        items=notifications,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@notification_router.get("/count/unread", response_model=Dict[str, int])
async def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the count of unread notifications for the current user.
    """
    count = await services.NotificationService.get_unread_count(
        db=db,
        user_id=current_user.id
    )
    return {"count": count}


# Announcement endpoints
@announcement_router.post("/", response_model=schemas.Announcement)
async def create_announcement(
    announcement_data: schemas.AnnouncementCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new announcement.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to create announcements")
    
    return await services.AnnouncementService.create_announcement(
        db=db,
        announcement_data=announcement_data,
        created_by=current_user.id,
        background_tasks=background_tasks
    )


@announcement_router.put("/{announcement_id}", response_model=schemas.Announcement)
async def update_announcement(
    announcement_data: schemas.AnnouncementUpdate,
    background_tasks: BackgroundTasks,
    announcement_id: int = Path(..., description="The ID of the announcement to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an announcement.
    Admin role or creator required.
    """
    return await services.AnnouncementService.update_announcement(
        db=db,
        announcement_id=announcement_id,
        announcement_data=announcement_data,
        user_id=current_user.id,
        background_tasks=background_tasks
    )


@announcement_router.get("/{announcement_id}", response_model=schemas.Announcement)
async def get_announcement(
    announcement_id: int = Path(..., description="The ID of the announcement to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get an announcement by ID.
    """
    return await services.AnnouncementService.get_announcement(
        db=db,
        announcement_id=announcement_id
    )


@announcement_router.delete("/{announcement_id}", response_model=schemas.MessageResponse)
async def delete_announcement(
    background_tasks: BackgroundTasks,
    announcement_id: int = Path(..., description="The ID of the announcement to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an announcement.
    Admin role or creator required.
    """
    result = await services.AnnouncementService.delete_announcement(
        db=db,
        announcement_id=announcement_id,
        user_id=current_user.id,
        background_tasks=background_tasks
    )
    
    return {"message": "Announcement deleted successfully"}


@announcement_router.get("/", response_model=schemas.PaginatedResponse)
async def get_announcements(
    announcement_type: Optional[schemas.AnnouncementTypeEnum] = Query(None, description="Filter by announcement type"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get active announcements for the current user.
    """
    announcements, total = await services.AnnouncementService.get_active_announcements(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        announcement_type=announcement_type
    )
    return schemas.PaginatedResponse.create(
        items=announcements,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


# Support ticket endpoints
@ticket_router.post("/", response_model=schemas.SupportTicket)
async def create_ticket(
    ticket_data: schemas.SupportTicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new support ticket.
    """
    return await services.SupportTicketService.create_ticket(
        db=db,
        ticket_data=ticket_data,
        customer_id=current_user.id,
        background_tasks=background_tasks
    )


@ticket_router.put("/{ticket_id}", response_model=schemas.SupportTicket)
async def update_ticket(
    ticket_data: schemas.SupportTicketUpdate,
    background_tasks: BackgroundTasks,
    ticket_id: int = Path(..., description="The ID of the ticket to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a support ticket.
    """
    return await services.SupportTicketService.update_ticket(
        db=db,
        ticket_id=ticket_id,
        ticket_data=ticket_data,
        user_id=current_user.id,
        background_tasks=background_tasks
    )


@ticket_router.post("/{ticket_id}/responses", response_model=schemas.TicketResponse)
async def add_ticket_response(
    response_data: schemas.TicketResponseCreate,
    background_tasks: BackgroundTasks,
    ticket_id: int = Path(..., description="The ID of the ticket to respond to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a response to a support ticket.
    """
    return await services.SupportTicketService.add_response(
        db=db,
        ticket_id=ticket_id,
        response_data=response_data,
        responder_id=current_user.id,
        background_tasks=background_tasks
    )


@ticket_router.get("/{ticket_id}", response_model=schemas.SupportTicket)
async def get_ticket(
    ticket_id: int = Path(..., description="The ID of the ticket to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a support ticket by ID.
    """
    return await services.SupportTicketService.get_ticket(
        db=db,
        ticket_id=ticket_id,
        user_id=current_user.id
    )


@ticket_router.get("/", response_model=schemas.PaginatedResponse)
async def get_tickets(
    status: Optional[schemas.TicketStatusEnum] = Query(None, description="Filter by ticket status"),
    category: Optional[schemas.TicketCategoryEnum] = Query(None, description="Filter by ticket category"),
    priority: Optional[schemas.TicketPriorityEnum] = Query(None, description="Filter by ticket priority"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get support tickets for the current user based on their role.
    """
    tickets, total = await services.SupportTicketService.get_tickets(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        category=category,
        priority=priority,
        role=current_user.role
    )
    return schemas.PaginatedResponse.create(
        items=tickets,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@ticket_router.get("/statistics", response_model=schemas.TicketStatistics)
async def get_ticket_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get statistics about support tickets.
    """
    return await services.SupportTicketService.get_ticket_statistics(
        db=db,
        user_id=current_user.id,
        role=current_user.role
    )


@ticket_router.post("/attachments/upload", response_model=schemas.FileUploadResponse)
async def upload_ticket_attachment(
    file: UploadFile = File(...),
    attachment_type: str = Query("ticket", description="Type of attachment (ticket or response)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file attachment for a ticket or response.
    """
    result = await services.SupportTicketService.upload_attachment(
        file=file,
        user_id=current_user.id,
        attachment_type=attachment_type
    )
    return schemas.FileUploadResponse(
        file_name=result["file_name"],
        file_path=result["file_path"],
        file_size=result["file_size"],
        content_type=result["content_type"]
    )


# Template endpoints
@template_router.post("/", response_model=schemas.Template)
async def create_template(
    template_data: schemas.TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new template.
    Admin or support role required.
    """
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to create templates")
    
    return await services.TemplateService.create_template(
        db=db,
        template_data=template_data,
        created_by=current_user.id
    )


@template_router.put("/{template_id}", response_model=schemas.Template)
async def update_template(
    template_data: schemas.TemplateUpdate,
    template_id: int = Path(..., description="The ID of the template to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a template.
    Admin role or creator required.
    """
    return await services.TemplateService.update_template(
        db=db,
        template_id=template_id,
        template_data=template_data,
        user_id=current_user.id
    )


@template_router.get("/{template_id}", response_model=schemas.Template)
async def get_template(
    template_id: int = Path(..., description="The ID of the template to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a template by ID.
    """
    # Check if user has permission to view templates
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to view templates")
    
    return await services.TemplateService.get_template(
        db=db,
        template_id=template_id
    )


@template_router.delete("/{template_id}", response_model=schemas.MessageResponse)
async def delete_template(
    template_id: int = Path(..., description="The ID of the template to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a template.
    Admin role or creator required.
    """
    result = await services.TemplateService.delete_template(
        db=db,
        template_id=template_id,
        user_id=current_user.id
    )
    if result:
        return {"message": "Template deleted successfully"}
    return {"message": "Failed to delete template"}


@template_router.get("/", response_model=schemas.PaginatedResponse)
async def get_templates(
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    active_only: bool = Query(False, description="If True, only return active templates"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get templates based on filters.
    Admin or support role required.
    """
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to view templates")
    
    templates, total = await services.TemplateService.get_templates(
        db=db,
        skip=skip,
        limit=limit,
        template_type=template_type,
        active_only=active_only
    )
    return schemas.PaginatedResponse.create(
        items=templates,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@template_router.post("/{template_id}/render", response_model=Dict[str, str])
async def render_template(
    context: Dict[str, Any],
    template_id: int = Path(..., description="The ID of the template to render"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Render a template with the provided context.
    Admin or support role required.
    """
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to render templates")
    
    return await services.TemplateService.render_template(
        db=db,
        template_id=template_id,
        context=context
    )
