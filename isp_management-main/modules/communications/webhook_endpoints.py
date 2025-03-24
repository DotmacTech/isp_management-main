"""
API endpoints for webhooks in the Communications module.

This module provides API endpoints for managing webhooks and webhook logs
in the ISP Management Platform.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user
from backend_core.models import User
from modules.communications import models, schemas
from modules.communications.webhooks import WebhookService

# Create router for webhooks
webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhook_router.post("/", response_model=schemas.Webhook)
async def register_webhook(
    webhook_data: schemas.WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Register a new webhook.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to register webhooks")
    
    return await WebhookService.register_webhook(
        db=db,
        webhook_data=webhook_data,
        user_id=current_user.id
    )


@webhook_router.put("/{webhook_id}", response_model=schemas.Webhook)
async def update_webhook(
    webhook_data: schemas.WebhookUpdate,
    webhook_id: int = Path(..., description="The ID of the webhook to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing webhook.
    Admin role or creator required.
    """
    webhook = await WebhookService.update_webhook(
        db=db,
        webhook_id=webhook_id,
        webhook_data=webhook_data,
        user_id=current_user.id
    )
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found or you're not authorized to update it")
    
    return webhook


@webhook_router.get("/{webhook_id}", response_model=schemas.Webhook)
async def get_webhook(
    webhook_id: int = Path(..., description="The ID of the webhook to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a webhook by ID.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view webhooks")
    
    webhook = await WebhookService.get_webhook(
        db=db,
        webhook_id=webhook_id
    )
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return webhook


@webhook_router.delete("/{webhook_id}", response_model=schemas.MessageResponse)
async def delete_webhook(
    webhook_id: int = Path(..., description="The ID of the webhook to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a webhook.
    Admin role or creator required.
    """
    result = await WebhookService.delete_webhook(
        db=db,
        webhook_id=webhook_id,
        user_id=current_user.id
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Webhook not found or you're not authorized to delete it")
    
    return {"message": "Webhook deleted successfully"}


@webhook_router.get("/", response_model=schemas.PaginatedResponse)
async def get_webhooks(
    event: Optional[str] = Query(None, description="Filter by event type"),
    active_only: bool = Query(False, description="If True, only return active webhooks"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get webhooks based on filters.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view webhooks")
    
    webhooks, total = await WebhookService.get_webhooks(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        event=event,
        active_only=active_only
    )
    
    return schemas.PaginatedResponse.create(
        items=webhooks,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@webhook_router.get("/{webhook_id}/logs", response_model=schemas.PaginatedResponse)
async def get_webhook_logs(
    webhook_id: int = Path(..., description="The ID of the webhook to get logs for"),
    success_only: Optional[bool] = Query(None, description="Filter by success status"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get logs for a specific webhook.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view webhook logs")
    
    # First check if the webhook exists
    webhook = await WebhookService.get_webhook(db, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    logs, total = await WebhookService.get_webhook_logs(
        db=db,
        webhook_id=webhook_id,
        skip=skip,
        limit=limit,
        success_only=success_only
    )
    
    return schemas.PaginatedResponse.create(
        items=logs,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@webhook_router.post("/test", response_model=Dict[str, Any])
async def test_webhook(
    webhook_data: schemas.WebhookCreate,
    event: str = Query(..., description="Event type to test"),
    payload: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Test a webhook by sending a test event.
    Admin role required.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to test webhooks")
    
    # Create a temporary webhook instance
    webhook = models.Webhook(
        id=0,  # Temporary ID
        name=webhook_data.name,
        url=str(webhook_data.url),
        events=[event],
        is_active=True,
        secret=webhook_data.secret,
        headers=webhook_data.headers,
        description=webhook_data.description,
        created_by=current_user.id
    )
    
    # Use a sample payload if none provided
    if not payload:
        payload = {
            "test": True,
            "message": "This is a test webhook event",
            "timestamp": str(datetime.utcnow())
        }
    
    # Trigger the webhook
    success = await WebhookService.trigger_webhook(
        webhook=webhook,
        event=event,
        payload=payload
    )
    
    if success:
        return {"status": "success", "message": "Webhook test successful"}
    else:
        return {"status": "error", "message": "Webhook test failed"}
