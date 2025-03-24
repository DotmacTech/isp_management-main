"""
API endpoints for external service integrations in the Communications module.

This module provides API endpoints for managing external service integrations
such as SMS providers, email services, and chat platforms.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user
from backend_core.models import User
from modules.communications import models, schemas
from modules.communications.external_services import ExternalServiceManager, ExternalServiceError

# Create router for external services
external_service_router = APIRouter(prefix="/external-services", tags=["External Services"])


@external_service_router.post("/", response_model=schemas.ExternalService)
async def register_external_service(
    service_data: schemas.ExternalServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Register a new external service.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to register external services")
    
    try:
        return await ExternalServiceManager.register_service(
            db=db,
            service_data=service_data,
            user_id=current_user.id
        )
    except ExternalServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@external_service_router.put("/{service_id}", response_model=schemas.ExternalService)
async def update_external_service(
    service_data: schemas.ExternalServiceUpdate,
    service_id: int = Path(..., description="The ID of the service to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing external service.
    Admin role or creator required.
    """
    try:
        service = await ExternalServiceManager.update_service(
            db=db,
            service_id=service_id,
            service_data=service_data,
            user_id=current_user.id
        )
        
        if not service:
            raise HTTPException(status_code=404, detail="Service not found or you're not authorized to update it")
        
        return service
    except ExternalServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@external_service_router.get("/{service_id}", response_model=schemas.ExternalService)
async def get_external_service(
    service_id: int = Path(..., description="The ID of the service to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get an external service by ID.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view external services")
    
    service = await ExternalServiceManager.get_service(
        db=db,
        service_id=service_id
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return service


@external_service_router.delete("/{service_id}", response_model=schemas.MessageResponse)
async def delete_external_service(
    service_id: int = Path(..., description="The ID of the service to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an external service.
    Admin role or creator required.
    """
    result = await ExternalServiceManager.delete_service(
        db=db,
        service_id=service_id,
        user_id=current_user.id
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Service not found or you're not authorized to delete it")
    
    return {"message": "External service deleted successfully"}


@external_service_router.get("/", response_model=schemas.PaginatedResponse)
async def get_external_services(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    active_only: bool = Query(False, description="If True, only return active services"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get external services based on filters.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view external services")
    
    services, total = await ExternalServiceManager.get_services(
        db=db,
        skip=skip,
        limit=limit,
        service_type=service_type,
        active_only=active_only
    )
    
    return schemas.PaginatedResponse.create(
        items=services,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@external_service_router.post("/{service_id}/send", response_model=Dict[str, Any])
async def send_message_via_service(
    message_data: Dict[str, Any],
    service_id: int = Path(..., description="The ID of the service to use"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a message using an external service.
    Admin or support role required.
    
    The message_data should include:
    - recipient: The recipient of the message
    - message: The message content
    - Additional fields depending on the service type:
      - For email: subject, html_content (optional), attachments (optional)
      - For SMS: No additional required fields
      - For chat: attachments (optional)
    """
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=403, detail="Not authorized to send messages via external services")
    
    # Extract required fields
    if "recipient" not in message_data:
        raise HTTPException(status_code=400, detail="Missing required field: recipient")
    if "message" not in message_data:
        raise HTTPException(status_code=400, detail="Missing required field: message")
    
    recipient = message_data.pop("recipient")
    message = message_data.pop("message")
    
    try:
        result = await ExternalServiceManager.send_message(
            db=db,
            service_id=service_id,
            recipient=recipient,
            message=message,
            **message_data
        )
        return {"status": "success", "result": result}
    except ExternalServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@external_service_router.post("/test-sms", response_model=Dict[str, Any])
async def test_sms_service(
    config: Dict[str, Any],
    recipient: str = Query(..., description="Phone number to send test SMS to"),
    message: str = Query(..., description="Message content"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Test an SMS service configuration by sending a test message.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to test external services")
    
    try:
        from modules.communications.external_services import SMSService
        
        service = SMSService(config)
        result = await service.send_message(recipient, message)
        
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@external_service_router.post("/test-email", response_model=Dict[str, Any])
async def test_email_service(
    config: Dict[str, Any],
    recipient: str = Query(..., description="Email address to send test email to"),
    subject: str = Query(..., description="Email subject"),
    message: str = Query(..., description="Email content"),
    html_content: Optional[str] = Query(None, description="HTML content"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Test an email service configuration by sending a test message.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to test external services")
    
    try:
        from modules.communications.external_services import EmailService
        
        service = EmailService(config)
        result = await service.send_message(
            recipient=recipient,
            message=message,
            subject=subject,
            html_content=html_content
        )
        
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@external_service_router.post("/test-chat", response_model=Dict[str, Any])
async def test_chat_service(
    config: Dict[str, Any],
    recipient: str = Query(..., description="Channel or user ID"),
    message: str = Query(..., description="Message content"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Test a chat service configuration by sending a test message.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to test external services")
    
    try:
        from modules.communications.external_services import ChatService
        
        service = ChatService(config)
        result = await service.send_message(recipient, message)
        
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
