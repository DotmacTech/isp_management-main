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
from modules.communications import models
from modules.communications.services.message_service import MessageService
from modules.communications.services.notification_service import NotificationService
from modules.communications.services.announcement_service import AnnouncementService
from modules.communications.services.support_ticket_service import SupportTicketService
from modules.communications.services.template_service import TemplateService
from modules.communications.external_services import ExternalServiceManager
from backend_core.utils.hateoas import add_resource_links, generate_collection_links, add_link
from backend_core.schemas import PaginatedResponse, HateoasResponse

# Import schemas at the top - update to include all needed schemas
from modules.communications.schemas import (
    Message, MessageCreate, MessageUpdate, MessageAttachment, MessageAttachmentCreate,
    Notification, NotificationCreate, NotificationUpdate, NotificationTypeEnum,
    Announcement, AnnouncementCreate, AnnouncementUpdate, AnnouncementTypeEnum,
    SupportTicket, SupportTicketCreate, SupportTicketUpdate,
    TicketResponse, TicketResponseCreate, TicketStatusEnum, TicketCategoryEnum, TicketPriorityEnum,
    Template, TemplateCreate, TemplateUpdate,
    FileUploadResponse, MessagePriorityEnum, DeliveryMethodEnum,
    TicketStatistics, TicketAttachment, ResponseAttachment
)

# Create routers for different communication types
message_router = APIRouter(prefix="/messages", tags=["Messages"])
notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])
announcement_router = APIRouter(prefix="/announcements", tags=["Announcements"])
ticket_router = APIRouter(prefix="/tickets", tags=["Support Tickets"])
template_router = APIRouter(prefix="/templates", tags=["Message Templates"])

# Message endpoints
@message_router.post("/", response_model=Message)
async def create_message(
    message_data: MessageCreate,
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
        )
    
    # Create the message
    message = await MessageService.create_message(
        db=db,
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id,
        subject=message_data.subject,
        content=message_data.content,
        delivery_method=message_data.delivery_method,
        attachment_ids=message_data.attachment_ids,
        background_tasks=background_tasks
    )
    
    # Convert to response model
    response = Message.from_orm(message)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/messages",
        resource_id=message.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="read",
        href=f"/api/v1/communications/messages/{message.id}/read",
        method="POST",
        title="Mark message as read"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/messages/{message.id}",
        method="DELETE",
        title="Delete message"
    )
    
    if message.attachments:
        for attachment in message.attachments:
            add_link(
                response=response,
                rel=f"attachment_{attachment.id}",
                href=f"/api/v1/communications/messages/attachments/{attachment.id}",
                method="GET",
                title=f"Download attachment: {attachment.filename}"
            )
    
    return response

@message_router.get("/{message_id}", response_model=Message)
async def get_message(
    message_id: int = Path(..., description="The ID of the message to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a message by ID.
    """
    message = await MessageService.get_message(db, message_id, current_user.id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Convert to response model
    response = Message.from_orm(message)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/messages",
        resource_id=message.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="read",
        href=f"/api/v1/communications/messages/{message.id}/read",
        method="POST",
        title="Mark message as read"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/messages/{message.id}",
        method="DELETE",
        title="Delete message"
    )
    
    if message.attachments:
        for attachment in message.attachments:
            add_link(
                response=response,
                rel=f"attachment_{attachment.id}",
                href=f"/api/v1/communications/messages/attachments/{attachment.id}",
                method="GET",
                title=f"Download attachment: {attachment.filename}"
            )
    
    return response

@message_router.post("/{message_id}/read", response_model=Message)
async def mark_message_as_read(
    message_id: int = Path(..., description="The ID of the message to mark as read"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark a message as read.
    """
    message = await MessageService.mark_as_read(db, message_id, current_user.id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Convert to response model
    response = Message.from_orm(message)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/messages",
        resource_id=message.id
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/messages/{message.id}",
        method="DELETE",
        title="Delete message"
    )
    
    return response

@message_router.delete("/{message_id}", response_model=Dict[str, str])
async def delete_message(
    message_id: int = Path(..., description="The ID of the message to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a message.
    """
    success = await MessageService.delete_message(db, message_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or you don't have permission to delete it")
    
    # Create a response with HATEOAS links
    response = HateoasResponse()
    
    # Add link to messages collection
    add_link(
        response=response,
        rel="messages",
        href="/api/v1/communications/messages",
        method="GET",
        title="View all messages"
    )
    
    return {"status": "Message deleted successfully"}

@message_router.get("/", response_model=PaginatedResponse)
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
    messages, total = await MessageService.get_messages(
        db=db,
        user_id=current_user.id,
        folder=folder,
        skip=skip,
        limit=limit
    )
    
    # Convert to response models
    message_responses = [Message.from_orm(message) for message in messages]
    
    # Create paginated response
    response = PaginatedResponse(
        items=message_responses,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Calculate pagination
    page = skip // limit + 1 if limit > 0 else 1
    
    # Add collection links
    collection_links = generate_collection_links(
        resource_path=f"/api/v1/communications/messages?folder={folder}",
        page=page,
        limit=limit,
        total=total
    )
    
    for rel, link in collection_links.items():
        response.links[rel] = link
    
    # Add links to each message
    for message_response in message_responses:
        add_resource_links(
            response=message_response,
            resource_path="/api/v1/communications/messages",
            resource_id=message_response.id
        )
        
        # Add specific action links
        add_link(
            response=message_response,
            rel="read",
            href=f"/api/v1/communications/messages/{message_response.id}/read",
            method="POST",
            title="Mark message as read"
        )
        
        add_link(
            response=message_response,
            rel="delete",
            href=f"/api/v1/communications/messages/{message_response.id}",
            method="DELETE",
            title="Delete message"
        )
    
    return response

@message_router.post("/attachments", response_model=MessageAttachment)
async def upload_message_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file attachment for a message.
    """
    attachment = await MessageService.upload_attachment(
        db=db,
        file=file,
        uploader_id=current_user.id
    )
    
    # Convert to response model
    response = MessageAttachment.from_orm(attachment)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/messages/attachments",
        resource_id=attachment.id
    )
    
    add_link(
        response=response,
        rel="download",
        href=f"/api/v1/communications/messages/attachments/{attachment.id}/download",
        method="GET",
        title="Download attachment"
    )
    
    return response

# Notification endpoints
@notification_router.post("/", response_model=Notification)
async def create_notification(
    notification_data: NotificationCreate,
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
    
    # Create the notification
    notification = await NotificationService.create_notification(
        db=db,
        user_id=notification_data.user_id,
        notification_type=notification_data.notification_type,
        title=notification_data.title,
        content=notification_data.content,
        link=notification_data.link,
        background_tasks=background_tasks
    )
    
    # Convert to response model
    response = Notification.from_orm(notification)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/notifications",
        resource_id=notification.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="read",
        href=f"/api/v1/communications/notifications/{notification.id}/read",
        method="POST",
        title="Mark notification as read"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/notifications/{notification.id}",
        method="DELETE",
        title="Delete notification"
    )
    
    return response

@notification_router.get("/{notification_id}", response_model=Notification)
async def get_notification(
    notification_id: int = Path(..., description="The ID of the notification to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a notification by ID.
    """
    notification = await NotificationService.get_notification(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Convert to response model
    response = Notification.from_orm(notification)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/notifications",
        resource_id=notification.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="read",
        href=f"/api/v1/communications/notifications/{notification.id}/read",
        method="POST",
        title="Mark notification as read"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/notifications/{notification.id}",
        method="DELETE",
        title="Delete notification"
    )
    
    return response

@notification_router.post("/{notification_id}/read", response_model=Notification)
async def mark_notification_as_read(
    notification_id: int = Path(..., description="The ID of the notification to mark as read"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark a notification as read.
    """
    notification = await NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Convert to response model
    response = Notification.from_orm(notification)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/notifications",
        resource_id=notification.id
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/notifications/{notification.id}",
        method="DELETE",
        title="Delete notification"
    )
    
    return response

@notification_router.delete("/{notification_id}", response_model=Dict[str, str])
async def delete_notification(
    notification_id: int = Path(..., description="The ID of the notification to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a notification.
    """
    success = await NotificationService.delete_notification(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or you don't have permission to delete it")
    
    # Create a response with HATEOAS links
    response = HateoasResponse()
    
    # Add link to notifications collection
    add_link(
        response=response,
        rel="notifications",
        href="/api/v1/communications/notifications",
        method="GET",
        title="View all notifications"
    )
    
    return {"status": "Notification deleted successfully"}

@notification_router.get("/", response_model=PaginatedResponse)
async def get_notifications(
    unread_only: bool = Query(False, description="If True, only return unread notifications"),
    notification_type: Optional[NotificationTypeEnum] = Query(None, description="Filter by notification type"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get notifications for the current user.
    """
    notifications, total = await NotificationService.get_notifications(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
        notification_type=notification_type
    )
    
    # Convert to response models
    notification_responses = [Notification.from_orm(notification) for notification in notifications]
    
    # Create paginated response
    response = PaginatedResponse(
        items=notification_responses,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Calculate pagination
    page = skip // limit + 1 if limit > 0 else 1
    
    # Add collection links
    collection_links = generate_collection_links(
        resource_path="/api/v1/communications/notifications",
        page=page,
        limit=limit,
        total=total
    )
    
    for rel, link in collection_links.items():
        response.links[rel] = link
    
    # Add links to each notification
    for notification_response in notification_responses:
        add_resource_links(
            response=notification_response,
            resource_path="/api/v1/communications/notifications",
            resource_id=notification_response.id
        )
        
        # Add specific action links
        add_link(
            response=notification_response,
            rel="read",
            href=f"/api/v1/communications/notifications/{notification_response.id}/read",
            method="POST",
            title="Mark notification as read"
        )
        
        add_link(
            response=notification_response,
            rel="delete",
            href=f"/api/v1/communications/notifications/{notification_response.id}",
            method="DELETE",
            title="Delete notification"
        )
    
    return response

@notification_router.get("/count/unread", response_model=Dict[str, int])
async def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the count of unread notifications for the current user.
    """
    count = await NotificationService.get_unread_count(db, current_user.id)
    return {"count": count}

# Announcement endpoints
@announcement_router.post("/", response_model=Announcement)
async def create_announcement(
    announcement_data: AnnouncementCreate,
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
    
    announcement = await AnnouncementService.create_announcement(
        db=db,
        announcement_data=announcement_data,
        created_by=current_user.id,
        background_tasks=background_tasks
    )
    
    # Convert to response model
    response = Announcement.from_orm(announcement)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/announcements",
        resource_id=announcement.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/communications/announcements/{announcement.id}",
        method="PUT",
        title="Update announcement"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/announcements/{announcement.id}",
        method="DELETE",
        title="Delete announcement"
    )
    
    return response

@announcement_router.put("/{announcement_id}", response_model=Announcement)
async def update_announcement(
    announcement_data: AnnouncementUpdate,
    background_tasks: BackgroundTasks,
    announcement_id: int = Path(..., description="The ID of the announcement to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an announcement.
    Admin role or creator required.
    """
    announcement = await AnnouncementService.update_announcement(
        db=db,
        announcement_id=announcement_id,
        announcement_data=announcement_data,
        user_id=current_user.id,
        background_tasks=background_tasks
    )
    
    # Convert to response model
    response = Announcement.from_orm(announcement)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/announcements",
        resource_id=announcement.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/announcements/{announcement.id}",
        method="DELETE",
        title="Delete announcement"
    )
    
    return response

@announcement_router.get("/{announcement_id}", response_model=Announcement)
async def get_announcement(
    announcement_id: int = Path(..., description="The ID of the announcement to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get an announcement by ID.
    """
    announcement = await AnnouncementService.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Convert to response model
    response = Announcement.from_orm(announcement)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/announcements",
        resource_id=announcement.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/communications/announcements/{announcement.id}",
        method="PUT",
        title="Update announcement"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/announcements/{announcement.id}",
        method="DELETE",
        title="Delete announcement"
    )
    
    return response

@announcement_router.delete("/{announcement_id}", response_model=Dict[str, str])
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
    success = await AnnouncementService.delete_announcement(
        db=db,
        announcement_id=announcement_id,
        user_id=current_user.id,
        background_tasks=background_tasks
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Announcement not found or you don't have permission to delete it")
    
    # Create a response with HATEOAS links
    response = HateoasResponse()
    
    # Add link to announcements collection
    add_link(
        response=response,
        rel="announcements",
        href="/api/v1/communications/announcements",
        method="GET",
        title="View all announcements"
    )
    
    return {"status": "Announcement deleted successfully"}

@announcement_router.get("/", response_model=PaginatedResponse)
async def get_announcements(
    announcement_type: Optional[AnnouncementTypeEnum] = Query(None, description="Filter by announcement type"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get active announcements for the current user.
    """
    announcements, total = await AnnouncementService.get_active_announcements(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        announcement_type=announcement_type
    )
    
    # Convert to response models
    announcement_responses = [Announcement.from_orm(announcement) for announcement in announcements]
    
    # Create paginated response
    response = PaginatedResponse(
        items=announcement_responses,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Calculate pagination
    page = skip // limit + 1 if limit > 0 else 1
    
    # Add collection links
    collection_links = generate_collection_links(
        resource_path="/api/v1/communications/announcements",
        page=page,
        limit=limit,
        total=total
    )
    
    for rel, link in collection_links.items():
        response.links[rel] = link
    
    # Add links to each announcement
    for announcement_response in announcement_responses:
        add_resource_links(
            response=announcement_response,
            resource_path="/api/v1/communications/announcements",
            resource_id=announcement_response.id
        )
        
        # Add specific action links
        add_link(
            response=announcement_response,
            rel="update",
            href=f"/api/v1/communications/announcements/{announcement_response.id}",
            method="PUT",
            title="Update announcement"
        )
        
        add_link(
            response=announcement_response,
            rel="delete",
            href=f"/api/v1/communications/announcements/{announcement_response.id}",
            method="DELETE",
            title="Delete announcement"
        )
    
    return response

# Support ticket endpoints
@ticket_router.post("/", response_model=SupportTicket)
async def create_ticket(
    ticket_data: SupportTicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new support ticket.
    """
    ticket = await SupportTicketService.create_ticket(
        db=db,
        ticket_data=ticket_data,
        customer_id=current_user.id,
        background_tasks=background_tasks
    )
    
    # Convert to response model
    response = SupportTicket.from_orm(ticket)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/tickets",
        resource_id=ticket.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/communications/tickets/{ticket.id}",
        method="PUT",
        title="Update ticket"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/tickets/{ticket.id}",
        method="DELETE",
        title="Delete ticket"
    )
    
    return response

@ticket_router.put("/{ticket_id}", response_model=SupportTicket)
async def update_ticket(
    ticket_data: SupportTicketUpdate,
    background_tasks: BackgroundTasks,
    ticket_id: int = Path(..., description="The ID of the ticket to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a support ticket.
    """
    ticket = await SupportTicketService.update_ticket(
        db=db,
        ticket_id=ticket_id,
        ticket_data=ticket_data,
        user_id=current_user.id,
        background_tasks=background_tasks
    )
    
    # Convert to response model
    response = SupportTicket.from_orm(ticket)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/tickets",
        resource_id=ticket.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/tickets/{ticket.id}",
        method="DELETE",
        title="Delete ticket"
    )
    
    return response

@ticket_router.post("/{ticket_id}/responses", response_model=TicketResponse)
async def add_ticket_response(
    response_data: TicketResponseCreate,
    background_tasks: BackgroundTasks,
    ticket_id: int = Path(..., description="The ID of the ticket to respond to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a response to a support ticket.
    """
    response = await SupportTicketService.add_response(
        db=db,
        ticket_id=ticket_id,
        response_data=response_data,
        responder_id=current_user.id,
        background_tasks=background_tasks
    )
    
    # Convert to response model
    response_model = TicketResponse.from_orm(response)
    
    # Add HATEOAS links
    add_resource_links(
        response=response_model,
        resource_path="/api/v1/communications/tickets/responses",
        resource_id=response.id
    )
    
    return response_model

@ticket_router.get("/{ticket_id}", response_model=SupportTicket)
async def get_ticket(
    ticket_id: int = Path(..., description="The ID of the ticket to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a support ticket by ID.
    """
    ticket = await SupportTicketService.get_ticket(db, ticket_id, current_user.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Convert to response model
    response = SupportTicket.from_orm(ticket)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/tickets",
        resource_id=ticket.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/communications/tickets/{ticket.id}",
        method="PUT",
        title="Update ticket"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/tickets/{ticket.id}",
        method="DELETE",
        title="Delete ticket"
    )
    
    return response

@ticket_router.get("/", response_model=PaginatedResponse)
async def get_tickets(
    status: Optional[TicketStatusEnum] = Query(None, description="Filter by ticket status"),
    category: Optional[TicketCategoryEnum] = Query(None, description="Filter by ticket category"),
    priority: Optional[TicketPriorityEnum] = Query(None, description="Filter by ticket priority"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get support tickets for the current user based on their role.
    """
    tickets, total = await SupportTicketService.get_tickets(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        category=category,
        priority=priority,
        role=current_user.role
    )
    
    # Convert to response models
    ticket_responses = [SupportTicket.from_orm(ticket) for ticket in tickets]
    
    # Create paginated response
    response = PaginatedResponse(
        items=ticket_responses,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Calculate pagination
    page = skip // limit + 1 if limit > 0 else 1
    
    # Add collection links
    collection_links = generate_collection_links(
        resource_path="/api/v1/communications/tickets",
        page=page,
        limit=limit,
        total=total
    )
    
    for rel, link in collection_links.items():
        response.links[rel] = link
    
    # Add links to each ticket
    for ticket_response in ticket_responses:
        add_resource_links(
            response=ticket_response,
            resource_path="/api/v1/communications/tickets",
            resource_id=ticket_response.id
        )
        
        # Add specific action links
        add_link(
            response=ticket_response,
            rel="update",
            href=f"/api/v1/communications/tickets/{ticket_response.id}",
            method="PUT",
            title="Update ticket"
        )
        
        add_link(
            response=ticket_response,
            rel="delete",
            href=f"/api/v1/communications/tickets/{ticket_response.id}",
            method="DELETE",
            title="Delete ticket"
        )
    
    return response

@ticket_router.get("/statistics", response_model=TicketStatistics)
async def get_ticket_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get statistics about support tickets.
    """
    statistics = await SupportTicketService.get_ticket_statistics(db, current_user.id, current_user.role)
    return statistics

@ticket_router.post("/attachments/upload", response_model=FileUploadResponse)
async def upload_ticket_attachment(
    file: UploadFile = File(...),
    attachment_type: str = Query("ticket", description="Type of attachment (ticket or response)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file attachment for a ticket or response.
    """
    result = await SupportTicketService.upload_attachment(
        file=file,
        user_id=current_user.id,
        attachment_type=attachment_type
    )
    return FileUploadResponse(
        file_name=result["file_name"],
        file_path=result["file_path"],
        file_size=result["file_size"],
        content_type=result["content_type"]
    )

# Template endpoints
@template_router.post("/", response_model=Template)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new template.
    Admin or support role required.
    """
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to create templates")
    
    template = await TemplateService.create_template(
        db=db,
        template_data=template_data,
        created_by=current_user.id
    )
    
    # Convert to response model
    response = Template.from_orm(template)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/templates",
        resource_id=template.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/communications/templates/{template.id}",
        method="PUT",
        title="Update template"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/templates/{template.id}",
        method="DELETE",
        title="Delete template"
    )
    
    return response

@template_router.put("/{template_id}", response_model=Template)
async def update_template(
    template_data: TemplateUpdate,
    template_id: int = Path(..., description="The ID of the template to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a template.
    Admin role or creator required.
    """
    template = await TemplateService.update_template(
        db=db,
        template_id=template_id,
        template_data=template_data,
        user_id=current_user.id
    )
    
    # Convert to response model
    response = Template.from_orm(template)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/templates",
        resource_id=template.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/templates/{template.id}",
        method="DELETE",
        title="Delete template"
    )
    
    return response

@template_router.get("/{template_id}", response_model=Template)
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
    
    template = await TemplateService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Convert to response model
    response = Template.from_orm(template)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/communications/templates",
        resource_id=template.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/communications/templates/{template.id}",
        method="PUT",
        title="Update template"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/communications/templates/{template.id}",
        method="DELETE",
        title="Delete template"
    )
    
    return response

@template_router.delete("/{template_id}", response_model=Dict[str, str])
async def delete_template(
    template_id: int = Path(..., description="The ID of the template to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a template.
    Admin role or creator required.
    """
    success = await TemplateService.delete_template(db, template_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found or you don't have permission to delete it")
    
    # Create a response with HATEOAS links
    response = HateoasResponse()
    
    # Add link to templates collection
    add_link(
        response=response,
        rel="templates",
        href="/api/v1/communications/templates",
        method="GET",
        title="View all templates"
    )
    
    return {"status": "Template deleted successfully"}

@template_router.get("/", response_model=PaginatedResponse)
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
    
    templates, total = await TemplateService.get_templates(
        db=db,
        skip=skip,
        limit=limit,
        template_type=template_type,
        active_only=active_only
    )
    
    # Convert to response models
    template_responses = [Template.from_orm(template) for template in templates]
    
    # Create paginated response
    response = PaginatedResponse(
        items=template_responses,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Calculate pagination
    page = skip // limit + 1 if limit > 0 else 1
    
    # Add collection links
    collection_links = generate_collection_links(
        resource_path="/api/v1/communications/templates",
        page=page,
        limit=limit,
        total=total
    )
    
    for rel, link in collection_links.items():
        response.links[rel] = link
    
    # Add links to each template
    for template_response in template_responses:
        add_resource_links(
            response=template_response,
            resource_path="/api/v1/communications/templates",
            resource_id=template_response.id
        )
        
        # Add specific action links
        add_link(
            response=template_response,
            rel="update",
            href=f"/api/v1/communications/templates/{template_response.id}",
            method="PUT",
            title="Update template"
        )
        
        add_link(
            response=template_response,
            rel="delete",
            href=f"/api/v1/communications/templates/{template_response.id}",
            method="DELETE",
            title="Delete template"
        )
    
    return response

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
    
    rendered_template = await TemplateService.render_template(db, template_id, context)
    return {"rendered_template": rendered_template}

# Create a combined router that includes all the individual routers
router = APIRouter(prefix="/communications", tags=["Communications"])
router.include_router(message_router)
router.include_router(notification_router)
router.include_router(announcement_router)
router.include_router(ticket_router)
router.include_router(template_router)
