"""
API endpoints for the Integration Management Module.

This module provides RESTful API endpoints for managing integrations,
webhook endpoints, and performing integration-related operations.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Body, Path, Query
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth import get_current_user, RoleChecker
from modules.integration_management.models.integration import Integration, WebhookEndpoint, WebhookEvent, IntegrationType
from modules.integration_management.schemas.integration import (
    IntegrationCreate, IntegrationUpdate, IntegrationResponse, IntegrationListResponse,
    WebhookEndpointCreate, WebhookEndpointUpdate, WebhookEndpointResponse, WebhookEventResponse
)
from modules.integration_management.utils.security import CredentialEncryptor, WebhookSignatureValidator, generate_webhook_secret
from modules.integration_management.utils.adapters import IntegrationAdapter
from modules.integration_management.services.integration_service import IntegrationService

# Create router
router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)

# Define role checkers
admin_role = RoleChecker(["admin"])
integration_manager_role = RoleChecker(["admin", "integration_manager"])


@router.post("/integrations/", response_model=IntegrationResponse, status_code=201)
async def create_integration(
    integration: IntegrationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Create a new integration.
    
    Args:
        integration: Integration data
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Created integration
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Create the integration
        new_integration = integration_service.create_integration(integration, current_user.id)
        
        # Test the connection in the background
        background_tasks.add_task(
            integration_service.test_integration_connection,
            new_integration.id
        )
        
        return new_integration
    except Exception as e:
        logger.error(f"Error creating integration: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error creating integration: {str(e)}")


@router.get("/integrations/", response_model=IntegrationListResponse)
async def list_integrations(
    type: Optional[IntegrationType] = None,
    status: Optional[str] = None,
    environment: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    List integrations with optional filtering.
    
    Args:
        type: Filter by integration type
        status: Filter by integration status
        environment: Filter by integration environment
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        List of integrations
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get integrations with filters
        integrations, total = integration_service.get_integrations(
            type=type,
            status=status,
            environment=environment,
            skip=skip,
            limit=limit
        )
        
        return {
            "items": integrations,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error listing integrations: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error listing integrations: {str(e)}")


@router.get("/integrations/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: int = Path(..., title="The ID of the integration to get"),
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Get a specific integration by ID.
    
    Args:
        integration_id: Integration ID
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Integration details
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the integration
        integration = integration_service.get_integration(integration_id)
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return integration
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error getting integration: {str(e)}")


@router.put("/integrations/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_update: IntegrationUpdate,
    integration_id: int = Path(..., title="The ID of the integration to update"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Update an existing integration.
    
    Args:
        integration_update: Updated integration data
        integration_id: Integration ID
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Updated integration
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the existing integration
        existing_integration = integration_service.get_integration(integration_id)
        
        if not existing_integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Update the integration
        updated_integration = integration_service.update_integration(
            integration_id,
            integration_update,
            current_user.id
        )
        
        # If credentials or configuration changed, test the connection in the background
        if (integration_update.credentials is not None or 
            integration_update.configuration is not None):
            background_tasks.add_task(
                integration_service.test_integration_connection,
                integration_id
            )
        
        return updated_integration
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating integration: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error updating integration: {str(e)}")


@router.delete("/integrations/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: int = Path(..., title="The ID of the integration to delete"),
    db: Session = Depends(get_db),
    current_user = Depends(admin_role)
):
    """
    Delete an integration.
    
    Args:
        integration_id: Integration ID
        db: Database session
        current_user: Current authenticated user with admin role
        
    Returns:
        No content
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the existing integration
        existing_integration = integration_service.get_integration(integration_id)
        
        if not existing_integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Delete the integration
        integration_service.delete_integration(integration_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting integration: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error deleting integration: {str(e)}")


@router.post("/integrations/{integration_id}/test", status_code=200)
async def test_integration(
    integration_id: int = Path(..., title="The ID of the integration to test"),
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Test the connection to an integration.
    
    Args:
        integration_id: Integration ID
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Test result
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the existing integration
        existing_integration = integration_service.get_integration(integration_id)
        
        if not existing_integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Test the integration connection
        success, message = integration_service.test_integration_connection(integration_id)
        
        return {
            "success": success,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing integration: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error testing integration: {str(e)}")


@router.get("/integrations/{integration_id}/status", status_code=200)
async def get_integration_status(
    integration_id: int = Path(..., title="The ID of the integration to get status for"),
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Get the status of an integration.
    
    Args:
        integration_id: Integration ID
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Integration status
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the existing integration
        existing_integration = integration_service.get_integration(integration_id)
        
        if not existing_integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Get the integration status
        status = integration_service.get_integration_status(integration_id)
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration status: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error getting integration status: {str(e)}")


# Webhook endpoints
@router.post("/webhooks/", response_model=WebhookEndpointResponse, status_code=201)
async def create_webhook_endpoint(
    webhook: WebhookEndpointCreate,
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Create a new webhook endpoint.
    
    Args:
        webhook: Webhook endpoint data
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Created webhook endpoint
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Create the webhook endpoint
        new_webhook = integration_service.create_webhook_endpoint(webhook, current_user.id)
        
        return new_webhook
    except Exception as e:
        logger.error(f"Error creating webhook endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error creating webhook endpoint: {str(e)}")


@router.get("/webhooks/", response_model=List[WebhookEndpointResponse])
async def list_webhook_endpoints(
    integration_id: Optional[int] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    List webhook endpoints with optional filtering.
    
    Args:
        integration_id: Filter by integration ID
        active: Filter by active status
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        List of webhook endpoints
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get webhook endpoints with filters
        webhooks = integration_service.get_webhook_endpoints(
            integration_id=integration_id,
            active=active
        )
        
        return webhooks
    except Exception as e:
        logger.error(f"Error listing webhook endpoints: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error listing webhook endpoints: {str(e)}")


@router.get("/webhooks/{webhook_id}", response_model=WebhookEndpointResponse)
async def get_webhook_endpoint(
    webhook_id: int = Path(..., title="The ID of the webhook endpoint to get"),
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Get a specific webhook endpoint by ID.
    
    Args:
        webhook_id: Webhook endpoint ID
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Webhook endpoint details
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the webhook endpoint
        webhook = integration_service.get_webhook_endpoint(webhook_id)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return webhook
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error getting webhook endpoint: {str(e)}")


@router.put("/webhooks/{webhook_id}", response_model=WebhookEndpointResponse)
async def update_webhook_endpoint(
    webhook_update: WebhookEndpointUpdate,
    webhook_id: int = Path(..., title="The ID of the webhook endpoint to update"),
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Update an existing webhook endpoint.
    
    Args:
        webhook_update: Updated webhook endpoint data
        webhook_id: Webhook endpoint ID
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        Updated webhook endpoint
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the existing webhook endpoint
        existing_webhook = integration_service.get_webhook_endpoint(webhook_id)
        
        if not existing_webhook:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        # Update the webhook endpoint
        updated_webhook = integration_service.update_webhook_endpoint(
            webhook_id,
            webhook_update,
            current_user.id
        )
        
        return updated_webhook
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating webhook endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error updating webhook endpoint: {str(e)}")


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook_endpoint(
    webhook_id: int = Path(..., title="The ID of the webhook endpoint to delete"),
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Delete a webhook endpoint.
    
    Args:
        webhook_id: Webhook endpoint ID
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        No content
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the existing webhook endpoint
        existing_webhook = integration_service.get_webhook_endpoint(webhook_id)
        
        if not existing_webhook:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        # Delete the webhook endpoint
        integration_service.delete_webhook_endpoint(webhook_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error deleting webhook endpoint: {str(e)}")


@router.post("/webhooks/{webhook_id}/rotate-secret", response_model=Dict[str, str])
async def rotate_webhook_secret(
    webhook_id: int = Path(..., title="The ID of the webhook endpoint to rotate secret for"),
    db: Session = Depends(get_db),
    current_user = Depends(integration_manager_role)
):
    """
    Rotate the secret for a webhook endpoint.
    
    Args:
        webhook_id: Webhook endpoint ID
        db: Database session
        current_user: Current authenticated user with appropriate role
        
    Returns:
        New webhook secret
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the existing webhook endpoint
        existing_webhook = integration_service.get_webhook_endpoint(webhook_id)
        
        if not existing_webhook:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        # Generate a new webhook secret
        new_secret = generate_webhook_secret()
        
        # Update the webhook endpoint with the new secret
        integration_service.update_webhook_endpoint(
            webhook_id,
            WebhookEndpointUpdate(secret=new_secret),
            current_user.id
        )
        
        return {"secret": new_secret}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating webhook secret: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error rotating webhook secret: {str(e)}")


@router.post("/webhooks/receive/{webhook_path:path}")
async def receive_webhook(
    request: Request,
    webhook_path: str = Path(..., title="The path of the webhook endpoint"),
    db: Session = Depends(get_db)
):
    """
    Receive and process a webhook event.
    
    Args:
        request: FastAPI request object
        webhook_path: Webhook path
        db: Database session
        
    Returns:
        Acknowledgement response
    """
    try:
        # Initialize the integration service
        integration_service = IntegrationService(db)
        
        # Get the webhook endpoint by path
        webhook_endpoint = integration_service.get_webhook_endpoint_by_path(webhook_path)
        
        if not webhook_endpoint or not webhook_endpoint.active:
            # Return 404 to avoid leaking information about webhook paths
            raise HTTPException(status_code=404, detail="Not found")
        
        # Get the request headers and body
        headers = dict(request.headers)
        body = await request.body()
        
        # Validate the webhook signature if required
        if webhook_endpoint.verify_signature:
            # Get the signature from the headers
            signature_header = webhook_endpoint.signature_header or "X-Signature"
            signature = headers.get(signature_header)
            
            if not signature:
                logger.warning(f"Missing signature header: {signature_header}")
                raise HTTPException(status_code=401, detail="Missing signature")
            
            # Validate the signature
            is_valid = WebhookSignatureValidator.validate_signature(
                body,
                signature,
                webhook_endpoint.secret
            )
            
            if not is_valid:
                logger.warning(f"Invalid webhook signature for webhook ID: {webhook_endpoint.id}")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Process the webhook event
        event = integration_service.process_webhook_event(
            webhook_endpoint.id,
            headers,
            body
        )
        
        # Return a success response
        return {"status": "success", "event_id": event.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")
