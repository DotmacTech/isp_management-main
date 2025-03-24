"""
Webhook functionality for the Communications module.

This module provides functionality for registering, managing, and triggering webhooks
for various communication events in the ISP Management Platform.
"""

import json
import hmac
import hashlib
import logging
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks

from backend_core.config import get_settings
from modules.communications import models, schemas

logger = logging.getLogger(__name__)
settings = get_settings()


class WebhookService:
    """Service for managing and triggering webhooks."""

    @staticmethod
    async def register_webhook(
        db: Session, 
        webhook_data: schemas.WebhookCreate,
        user_id: int
    ) -> models.Webhook:
        """
        Register a new webhook.
        
        Args:
            db: Database session
            webhook_data: Webhook data
            user_id: ID of the user registering the webhook
            
        Returns:
            The created webhook
        """
        webhook = models.Webhook(
            name=webhook_data.name,
            url=webhook_data.url,
            events=webhook_data.events,
            is_active=webhook_data.is_active,
            secret=webhook_data.secret,
            headers=webhook_data.headers,
            description=webhook_data.description,
            created_by=user_id
        )
        
        db.add(webhook)
        db.commit()
        db.refresh(webhook)
        
        logger.info(f"Webhook registered: {webhook.name} for events {webhook.events}")
        return webhook

    @staticmethod
    async def update_webhook(
        db: Session, 
        webhook_id: int, 
        webhook_data: schemas.WebhookUpdate,
        user_id: int
    ) -> Optional[models.Webhook]:
        """
        Update an existing webhook.
        
        Args:
            db: Database session
            webhook_id: ID of the webhook to update
            webhook_data: Updated webhook data
            user_id: ID of the user updating the webhook
            
        Returns:
            The updated webhook or None if not found
        """
        webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
        
        if not webhook:
            logger.warning(f"Webhook with ID {webhook_id} not found")
            return None
        
        # Check if user has permission to update this webhook
        if webhook.created_by != user_id:
            logger.warning(f"User {user_id} not authorized to update webhook {webhook_id}")
            return None
        
        # Update webhook fields
        for field, value in webhook_data.dict(exclude_unset=True).items():
            setattr(webhook, field, value)
        
        webhook.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(webhook)
        
        logger.info(f"Webhook updated: {webhook.name}")
        return webhook

    @staticmethod
    async def delete_webhook(
        db: Session, 
        webhook_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a webhook.
        
        Args:
            db: Database session
            webhook_id: ID of the webhook to delete
            user_id: ID of the user deleting the webhook
            
        Returns:
            True if deleted, False otherwise
        """
        webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
        
        if not webhook:
            logger.warning(f"Webhook with ID {webhook_id} not found")
            return False
        
        # Check if user has permission to delete this webhook
        if webhook.created_by != user_id:
            logger.warning(f"User {user_id} not authorized to delete webhook {webhook_id}")
            return False
        
        db.delete(webhook)
        db.commit()
        
        logger.info(f"Webhook deleted: {webhook.name}")
        return True

    @staticmethod
    async def get_webhook(
        db: Session, 
        webhook_id: int
    ) -> Optional[models.Webhook]:
        """
        Get a webhook by ID.
        
        Args:
            db: Database session
            webhook_id: ID of the webhook to retrieve
            
        Returns:
            The webhook or None if not found
        """
        webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
        
        if not webhook:
            logger.warning(f"Webhook with ID {webhook_id} not found")
            return None
        
        return webhook

    @staticmethod
    async def get_webhooks(
        db: Session, 
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        event: Optional[str] = None,
        active_only: bool = False
    ) -> tuple[List[models.Webhook], int]:
        """
        Get webhooks for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return
            event: Filter by event type
            active_only: If True, only return active webhooks
            
        Returns:
            List of webhooks and total count
        """
        query = db.query(models.Webhook).filter(models.Webhook.created_by == user_id)
        
        if event:
            # Filter webhooks that have the specified event in their events list
            query = query.filter(models.Webhook.events.contains(event))
        
        if active_only:
            query = query.filter(models.Webhook.is_active == True)
        
        total = query.count()
        webhooks = query.order_by(models.Webhook.created_at.desc()).offset(skip).limit(limit).all()
        
        return webhooks, total

    @staticmethod
    async def get_webhooks_for_event(
        db: Session, 
        event: str
    ) -> List[models.Webhook]:
        """
        Get all active webhooks that are subscribed to a specific event.
        
        Args:
            db: Database session
            event: Event type
            
        Returns:
            List of webhooks
        """
        # Filter webhooks that have the specified event in their events list and are active
        webhooks = db.query(models.Webhook).filter(
            models.Webhook.events.contains(event),
            models.Webhook.is_active == True
        ).all()
        
        return webhooks

    @staticmethod
    def generate_signature(payload: Dict[str, Any], secret: str) -> str:
        """
        Generate HMAC signature for webhook payload.
        
        Args:
            payload: Webhook payload
            secret: Webhook secret
            
        Returns:
            HMAC signature
        """
        payload_str = json.dumps(payload, sort_keys=True)
        hmac_obj = hmac.new(
            key=secret.encode('utf-8'),
            msg=payload_str.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        return hmac_obj.hexdigest()

    @staticmethod
    async def trigger_webhook(
        webhook: models.Webhook,
        event: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Trigger a webhook by sending an HTTP request.
        
        Args:
            webhook: Webhook to trigger
            event: Event type
            payload: Event payload
            
        Returns:
            True if successful, False otherwise
        """
        if not webhook.is_active:
            logger.warning(f"Webhook {webhook.name} is not active")
            return False
        
        # Add event metadata to payload
        full_payload = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_id": webhook.id,
            "data": payload
        }
        
        # Prepare headers
        headers = {}
        if webhook.headers:
            headers.update(webhook.headers)
        
        # Add signature if secret is provided
        if webhook.secret:
            signature = WebhookService.generate_signature(full_payload, webhook.secret)
            headers["X-ISP-Signature"] = signature
        
        headers["X-ISP-Event"] = event
        headers["Content-Type"] = "application/json"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook.url,
                    json=full_payload,
                    headers=headers
                )
                
                # Log webhook delivery
                webhook_log = models.WebhookLog(
                    webhook_id=webhook.id,
                    event=event,
                    request_payload=full_payload,
                    response_status=response.status_code,
                    response_body=response.text,
                    success=200 <= response.status_code < 300
                )
                
                # This needs to be done in a separate database session
                # We'll use a background task to save the log
                
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook {webhook.name} triggered successfully for event {event}")
                    return True
                else:
                    logger.warning(f"Webhook {webhook.name} failed for event {event}: {response.status_code}")
                    return False
                
        except Exception as e:
            logger.error(f"Error triggering webhook {webhook.name}: {str(e)}")
            
            # Log webhook failure
            webhook_log = models.WebhookLog(
                webhook_id=webhook.id,
                event=event,
                request_payload=full_payload,
                response_status=0,
                response_body=str(e),
                success=False
            )
            
            # This needs to be done in a separate database session
            # We'll use a background task to save the log
            
            return False

    @staticmethod
    async def save_webhook_log(
        db: Session,
        webhook_log: models.WebhookLog
    ) -> models.WebhookLog:
        """
        Save a webhook log entry.
        
        Args:
            db: Database session
            webhook_log: Webhook log to save
            
        Returns:
            The saved webhook log
        """
        db.add(webhook_log)
        db.commit()
        db.refresh(webhook_log)
        return webhook_log

    @staticmethod
    async def trigger_event(
        db: Session,
        event: str,
        payload: Dict[str, Any]
    ) -> List[bool]:
        """
        Trigger all webhooks for a specific event.
        
        Args:
            db: Database session
            event: Event type
            payload: Event payload
            
        Returns:
            List of success/failure for each webhook
        """
        webhooks = await WebhookService.get_webhooks_for_event(db, event)
        
        if not webhooks:
            logger.info(f"No webhooks found for event {event}")
            return []
        
        logger.info(f"Triggering {len(webhooks)} webhooks for event {event}")
        
        # Trigger all webhooks concurrently
        tasks = [WebhookService.trigger_webhook(webhook, event, payload) for webhook in webhooks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to success/failure
        success_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error triggering webhook {webhooks[i].name}: {str(result)}")
                success_results.append(False)
            else:
                success_results.append(result)
        
        return success_results

    @staticmethod
    async def get_webhook_logs(
        db: Session,
        webhook_id: int,
        skip: int = 0,
        limit: int = 100,
        success_only: Optional[bool] = None
    ) -> tuple[List[models.WebhookLog], int]:
        """
        Get logs for a specific webhook.
        
        Args:
            db: Database session
            webhook_id: ID of the webhook
            skip: Number of records to skip
            limit: Maximum number of records to return
            success_only: If True, only return successful logs; if False, only return failed logs
            
        Returns:
            List of webhook logs and total count
        """
        query = db.query(models.WebhookLog).filter(models.WebhookLog.webhook_id == webhook_id)
        
        if success_only is not None:
            query = query.filter(models.WebhookLog.success == success_only)
        
        total = query.count()
        logs = query.order_by(models.WebhookLog.created_at.desc()).offset(skip).limit(limit).all()
        
        return logs, total

    @staticmethod
    async def trigger_event(
        db: Session,
        event: str,
        payload: Dict[str, Any],
        background_tasks: Optional[BackgroundTasks] = None
    ) -> bool:
        """
        Trigger webhooks for a specific event.
        
        Args:
            db: Database session
            event: Event type
            payload: Event payload
            background_tasks: Background tasks runner
            
        Returns:
            True if at least one webhook was triggered, False otherwise
        """
        # Find all active webhooks for this event
        webhooks = db.query(models.Webhook).filter(
            models.Webhook.is_active == True,
            models.Webhook.events.contains([event])
        ).all()
        
        if not webhooks:
            logger.info(f"No active webhooks found for event: {event}")
            return False
        
        # Add timestamp to payload
        payload["timestamp"] = datetime.utcnow().isoformat()
        payload["event"] = event
        
        # Trigger each webhook
        for webhook in webhooks:
            if background_tasks:
                background_tasks.add_task(
                    WebhookService.trigger_webhook,
                    webhook=webhook,
                    event=event,
                    payload=payload
                )
            else:
                await WebhookService.trigger_webhook(
                    webhook=webhook,
                    event=event,
                    payload=payload
                )
        
        return True
