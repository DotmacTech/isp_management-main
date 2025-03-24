"""
Celery tasks for the Integration Management Module.

This module provides asynchronous tasks for processing webhook events,
testing integration connections, and collecting integration metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from core.database import get_db
from core.metrics import MetricsCollector, timed
from .models.integration import (
    Integration, WebhookEvent, WebhookEndpoint, 
    IntegrationStatus, ActivityType, IntegrationType
)
from .services.integration_service import IntegrationService
from .utils.adapters import IntegrationAdapter
from .utils.security import CredentialEncryptor

# Set up logging
logger = logging.getLogger(__name__)

# Initialize metrics collector
metrics_collector = MetricsCollector(namespace="integration_management")


@shared_task(name="integration_management.process_webhook_event")
@timed("process_webhook_event_time")
def process_webhook_event(webhook_event_id: int) -> Dict[str, Any]:
    """
    Process a webhook event asynchronously.
    
    Args:
        webhook_event_id: ID of the webhook event to process
        
    Returns:
        Dictionary containing processing result
    """
    start_time = datetime.utcnow()
    result = {
        "success": False,
        "webhook_event_id": webhook_event_id,
        "processed_at": start_time.isoformat(),
        "error": None
    }
    
    try:
        # Create a new database session
        db = next(get_db())
        
        try:
            # Get the webhook event
            webhook_event = db.query(WebhookEvent).filter(WebhookEvent.id == webhook_event_id).first()
            
            if not webhook_event:
                raise ValueError(f"Webhook event with ID {webhook_event_id} not found")
            
            # Get the webhook endpoint
            webhook_endpoint = db.query(WebhookEndpoint).filter(
                WebhookEndpoint.id == webhook_event.webhook_id
            ).first()
            
            if not webhook_endpoint:
                raise ValueError(f"Webhook endpoint with ID {webhook_event.webhook_id} not found")
            
            # Get the integration
            integration = db.query(Integration).filter(
                Integration.id == webhook_endpoint.integration_id
            ).first()
            
            if not integration:
                raise ValueError(f"Integration with ID {webhook_endpoint.integration_id} not found")
            
            # Process the webhook event based on the integration type
            if integration.type == IntegrationType.PAYMENT_GATEWAY:
                _process_payment_gateway_webhook(db, webhook_event, webhook_endpoint, integration)
            elif integration.type == IntegrationType.SMS_PROVIDER:
                _process_sms_provider_webhook(db, webhook_event, webhook_endpoint, integration)
            elif integration.type == IntegrationType.EMAIL_PROVIDER:
                _process_email_provider_webhook(db, webhook_event, webhook_endpoint, integration)
            else:
                # For other integration types, just mark as processed
                logger.info(f"No specific processing for integration type {integration.type}")
            
            # Mark the webhook event as processed
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            db.commit()
            
            # Record success metrics
            metrics_collector.increment(
                "webhook_events_processed",
                tags={
                    "integration_type": integration.type.value,
                    "integration_name": integration.name,
                    "status": "success"
                }
            )
            
            # Record processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            metrics_collector.record(
                "webhook_processing_time",
                processing_time,
                tags={
                    "integration_type": integration.type.value,
                    "integration_name": integration.name
                }
            )
            
            result["success"] = True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing webhook event {webhook_event_id}: {str(e)}")
            
            # Record failure metrics
            metrics_collector.increment(
                "webhook_events_processed",
                tags={
                    "integration_type": integration.type.value if 'integration' in locals() else "unknown",
                    "integration_name": integration.name if 'integration' in locals() else "unknown",
                    "status": "failure"
                }
            )
            
            result["error"] = str(e)
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error setting up database session: {str(e)}")
        result["error"] = str(e)
    
    return result


def _process_payment_gateway_webhook(
    db: Session,
    webhook_event: WebhookEvent,
    webhook_endpoint: WebhookEndpoint,
    integration: Integration
) -> None:
    """
    Process a payment gateway webhook event.
    
    Args:
        db: Database session
        webhook_event: Webhook event to process
        webhook_endpoint: Webhook endpoint
        integration: Integration
    """
    logger.info(f"Processing payment gateway webhook event {webhook_event.id}")
    
    try:
        # Parse the payload
        payload = webhook_event.payload
        
        # Extract the event type
        event_type = payload.get("type")
        
        if not event_type:
            logger.warning(f"No event type in webhook payload: {webhook_event.id}")
            return
        
        # Process based on event type
        if event_type == "payment.succeeded":
            logger.info(f"Payment succeeded: {webhook_event.id}")
            # TODO: Update payment status in billing module
        elif event_type == "payment.failed":
            logger.info(f"Payment failed: {webhook_event.id}")
            # TODO: Update payment status in billing module
        elif event_type == "refund.succeeded":
            logger.info(f"Refund succeeded: {webhook_event.id}")
            # TODO: Process refund in billing module
        else:
            logger.info(f"Unhandled payment gateway event type: {event_type}")
    
    except Exception as e:
        logger.error(f"Error processing payment gateway webhook: {str(e)}")
        raise


def _process_sms_provider_webhook(
    db: Session,
    webhook_event: WebhookEvent,
    webhook_endpoint: WebhookEndpoint,
    integration: Integration
) -> None:
    """
    Process an SMS provider webhook event.
    
    Args:
        db: Database session
        webhook_event: Webhook event to process
        webhook_endpoint: Webhook endpoint
        integration: Integration
    """
    logger.info(f"Processing SMS provider webhook event {webhook_event.id}")
    
    try:
        # Parse the payload
        payload = webhook_event.payload
        
        # Extract the event type
        event_type = payload.get("type")
        
        if not event_type:
            logger.warning(f"No event type in webhook payload: {webhook_event.id}")
            return
        
        # Process based on event type
        if event_type == "message.sent":
            logger.info(f"Message sent: {webhook_event.id}")
            # TODO: Update message status in notification module
        elif event_type == "message.delivered":
            logger.info(f"Message delivered: {webhook_event.id}")
            # TODO: Update message status in notification module
        elif event_type == "message.failed":
            logger.info(f"Message failed: {webhook_event.id}")
            # TODO: Update message status in notification module
        else:
            logger.info(f"Unhandled SMS provider event type: {event_type}")
    
    except Exception as e:
        logger.error(f"Error processing SMS provider webhook: {str(e)}")
        raise


def _process_email_provider_webhook(
    db: Session,
    webhook_event: WebhookEvent,
    webhook_endpoint: WebhookEndpoint,
    integration: Integration
) -> None:
    """
    Process an email provider webhook event.
    
    Args:
        db: Database session
        webhook_event: Webhook event to process
        webhook_endpoint: Webhook endpoint
        integration: Integration
    """
    logger.info(f"Processing email provider webhook event {webhook_event.id}")
    
    try:
        # Parse the payload
        payload = webhook_event.payload
        
        # Extract the event type
        event_type = payload.get("type")
        
        if not event_type:
            logger.warning(f"No event type in webhook payload: {webhook_event.id}")
            return
        
        # Process based on event type
        if event_type == "email.sent":
            logger.info(f"Email sent: {webhook_event.id}")
            # TODO: Update email status in notification module
        elif event_type == "email.delivered":
            logger.info(f"Email delivered: {webhook_event.id}")
            # TODO: Update email status in notification module
        elif event_type == "email.opened":
            logger.info(f"Email opened: {webhook_event.id}")
            # TODO: Update email status in notification module
        elif event_type == "email.clicked":
            logger.info(f"Email clicked: {webhook_event.id}")
            # TODO: Update email status in notification module
        elif event_type == "email.bounced":
            logger.info(f"Email bounced: {webhook_event.id}")
            # TODO: Update email status in notification module
        elif event_type == "email.spam":
            logger.info(f"Email marked as spam: {webhook_event.id}")
            # TODO: Update email status in notification module
        else:
            logger.info(f"Unhandled email provider event type: {event_type}")
    
    except Exception as e:
        logger.error(f"Error processing email provider webhook: {str(e)}")
        raise


@shared_task(name="integration_management.test_integration_connection")
@timed("test_integration_connection_time")
def test_integration_connection(integration_id: int) -> Dict[str, Any]:
    """
    Test an integration connection asynchronously.
    
    Args:
        integration_id: ID of the integration to test
        
    Returns:
        Dictionary containing test result
    """
    start_time = datetime.utcnow()
    result = {
        "success": False,
        "integration_id": integration_id,
        "tested_at": start_time.isoformat(),
        "error": None
    }
    
    try:
        # Create a new database session
        db = next(get_db())
        
        try:
            # Initialize the integration service
            integration_service = IntegrationService(db)
            
            # Test the integration connection
            success, message = integration_service.test_integration_connection(integration_id)
            
            # Record metrics
            integration = db.query(Integration).filter(Integration.id == integration_id).first()
            if integration:
                metrics_collector.increment(
                    "integration_connection_tests",
                    tags={
                        "integration_type": integration.type.value,
                        "integration_name": integration.name,
                        "status": "success" if success else "failure"
                    }
                )
            
            result["success"] = success
            result["message"] = message
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error testing integration connection {integration_id}: {str(e)}")
            result["error"] = str(e)
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error setting up database session: {str(e)}")
        result["error"] = str(e)
    
    return result


@shared_task(name="integration_management.test_all_active_integrations")
def test_all_active_integrations() -> Dict[str, Any]:
    """
    Test all active integrations.
    
    Returns:
        Dictionary containing test results
    """
    start_time = datetime.utcnow()
    results = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "tested_at": start_time.isoformat(),
        "details": []
    }
    
    try:
        # Create a new database session
        db = next(get_db())
        
        try:
            # Get all active integrations
            active_integrations = db.query(Integration).filter(
                Integration.status == IntegrationStatus.ACTIVE
            ).all()
            
            results["total"] = len(active_integrations)
            
            # Test each integration
            for integration in active_integrations:
                try:
                    # Initialize the integration service
                    integration_service = IntegrationService(db)
                    
                    # Test the integration connection
                    success, message = integration_service.test_integration_connection(integration.id)
                    
                    # Record result
                    if success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                    
                    results["details"].append({
                        "integration_id": integration.id,
                        "integration_name": integration.name,
                        "integration_type": integration.type.value,
                        "success": success,
                        "message": message
                    })
                    
                except Exception as e:
                    logger.error(f"Error testing integration {integration.id}: {str(e)}")
                    results["failed"] += 1
                    results["details"].append({
                        "integration_id": integration.id,
                        "integration_name": integration.name,
                        "integration_type": integration.type.value,
                        "success": False,
                        "error": str(e)
                    })
            
        except Exception as e:
            logger.error(f"Error getting active integrations: {str(e)}")
            results["error"] = str(e)
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error setting up database session: {str(e)}")
        results["error"] = str(e)
    
    return results


@shared_task(name="integration_management.process_pending_webhook_events")
def process_pending_webhook_events(limit: int = 100) -> Dict[str, Any]:
    """
    Process pending webhook events.
    
    Args:
        limit: Maximum number of events to process
        
    Returns:
        Dictionary containing processing results
    """
    start_time = datetime.utcnow()
    results = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "processed_at": start_time.isoformat(),
        "details": []
    }
    
    try:
        # Create a new database session
        db = next(get_db())
        
        try:
            # Get pending webhook events
            pending_events = db.query(WebhookEvent).filter(
                WebhookEvent.processed == False
            ).order_by(WebhookEvent.created_at.asc()).limit(limit).all()
            
            results["total"] = len(pending_events)
            
            # Process each event
            for event in pending_events:
                try:
                    # Queue the event for processing
                    process_webhook_event.delay(event.id)
                    
                    results["successful"] += 1
                    results["details"].append({
                        "webhook_event_id": event.id,
                        "webhook_id": event.webhook_id,
                        "queued": True
                    })
                    
                except Exception as e:
                    logger.error(f"Error queuing webhook event {event.id}: {str(e)}")
                    results["failed"] += 1
                    results["details"].append({
                        "webhook_event_id": event.id,
                        "webhook_id": event.webhook_id,
                        "queued": False,
                        "error": str(e)
                    })
            
        except Exception as e:
            logger.error(f"Error getting pending webhook events: {str(e)}")
            results["error"] = str(e)
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error setting up database session: {str(e)}")
        results["error"] = str(e)
    
    return results


@shared_task(name="integration_management.collect_integration_metrics")
def collect_integration_metrics() -> Dict[str, Any]:
    """
    Collect metrics for all integrations.
    
    Returns:
        Dictionary containing metrics collection results
    """
    start_time = datetime.utcnow()
    results = {
        "total_integrations": 0,
        "metrics_collected": 0,
        "collected_at": start_time.isoformat()
    }
    
    try:
        # Create a new database session
        db = next(get_db())
        
        try:
            # Get all integrations
            integrations = db.query(Integration).all()
            
            results["total_integrations"] = len(integrations)
            
            # Collect integration status metrics
            status_counts = {}
            for status in IntegrationStatus:
                count = db.query(Integration).filter(Integration.status == status).count()
                status_counts[status.value] = count
                metrics_collector.gauge(
                    "integrations_by_status",
                    count,
                    tags={"status": status.value}
                )
            
            # Collect integration type metrics
            type_counts = {}
            for type_ in IntegrationType:
                count = db.query(Integration).filter(Integration.type == type_).count()
                type_counts[type_.value] = count
                metrics_collector.gauge(
                    "integrations_by_type",
                    count,
                    tags={"type": type_.value}
                )
            
            # Collect webhook metrics
            total_webhooks = db.query(WebhookEndpoint).count()
            active_webhooks = db.query(WebhookEndpoint).filter(WebhookEndpoint.active == True).count()
            metrics_collector.gauge("total_webhooks", total_webhooks)
            metrics_collector.gauge("active_webhooks", active_webhooks)
            
            # Collect webhook event metrics
            total_events = db.query(WebhookEvent).count()
            processed_events = db.query(WebhookEvent).filter(WebhookEvent.processed == True).count()
            pending_events = total_events - processed_events
            metrics_collector.gauge("total_webhook_events", total_events)
            metrics_collector.gauge("processed_webhook_events", processed_events)
            metrics_collector.gauge("pending_webhook_events", pending_events)
            
            # Collect recent activity metrics
            recent_time = datetime.utcnow() - timedelta(hours=24)
            recent_activities = db.query(WebhookEvent).filter(WebhookEvent.created_at >= recent_time).count()
            metrics_collector.gauge("webhook_events_last_24h", recent_activities)
            
            results["metrics_collected"] = 5  # Number of metric types collected
            results["status_counts"] = status_counts
            results["type_counts"] = type_counts
            results["webhook_counts"] = {
                "total": total_webhooks,
                "active": active_webhooks
            }
            results["event_counts"] = {
                "total": total_events,
                "processed": processed_events,
                "pending": pending_events,
                "last_24h": recent_activities
            }
            
        except Exception as e:
            logger.error(f"Error collecting integration metrics: {str(e)}")
            results["error"] = str(e)
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error setting up database session: {str(e)}")
        results["error"] = str(e)
    
    return results
