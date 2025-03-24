"""
Integration Service for the Integration Management Module.

This module provides services for managing integrations, webhook endpoints,
and performing integration-related operations.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.integration import (
    Integration, IntegrationVersion, IntegrationActivity, 
    WebhookEndpoint, WebhookEvent, IntegrationType, IntegrationStatus, 
    ActivityType, ActivityStatus
)
from ..schemas.integration import (
    IntegrationCreate, IntegrationUpdate, 
    WebhookEndpointCreate, WebhookEndpointUpdate, WebhookEventCreate
)
from ..utils.security import CredentialEncryptor, generate_webhook_secret
from ..utils.adapters import IntegrationAdapter

# Set up logging
logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for managing integrations and webhook endpoints."""
    
    def __init__(self, db: Session):
        """
        Initialize the integration service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.credential_encryptor = CredentialEncryptor()
    
    def create_integration(self, integration_data: IntegrationCreate, user_id: int) -> Integration:
        """
        Create a new integration.
        
        Args:
            integration_data: Integration data
            user_id: ID of the user creating the integration
            
        Returns:
            Created integration
        """
        try:
            # Encrypt the credentials
            encrypted_credentials = self.credential_encryptor.encrypt(integration_data.credentials)
            
            # Create the integration
            integration = Integration(
                name=integration_data.name,
                description=integration_data.description,
                type=integration_data.type,
                status=IntegrationStatus.PENDING,
                environment=integration_data.environment,
                configuration=integration_data.configuration,
                encrypted_credentials=encrypted_credentials,
                owner_id=user_id
            )
            
            # Add the integration to the database
            self.db.add(integration)
            self.db.flush()
            
            # Create the initial version
            version = IntegrationVersion(
                integration_id=integration.id,
                version="1.0.0",
                configuration=integration_data.configuration,
                encrypted_credentials=encrypted_credentials,
                created_by=user_id
            )
            
            # Add the version to the database
            self.db.add(version)
            
            # Create an activity record
            activity = IntegrationActivity(
                integration_id=integration.id,
                activity_type=ActivityType.CREATED,
                status=ActivityStatus.SUCCESS,
                details={"message": "Integration created"},
                user_id=user_id
            )
            
            # Add the activity to the database
            self.db.add(activity)
            self.db.commit()
            
            return integration
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating integration: {str(e)}")
            raise
    
    def get_integration(self, integration_id: int) -> Optional[Integration]:
        """
        Get an integration by ID.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Integration if found, None otherwise
        """
        return self.db.query(Integration).filter(Integration.id == integration_id).first()
    
    def get_integrations(
        self,
        type: Optional[IntegrationType] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Integration], int]:
        """
        Get integrations with optional filtering.
        
        Args:
            type: Filter by integration type
            status: Filter by integration status
            environment: Filter by integration environment
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple containing a list of integrations and the total count
        """
        # Build the query
        query = self.db.query(Integration)
        
        # Apply filters
        if type:
            query = query.filter(Integration.type == type)
        
        if status:
            query = query.filter(Integration.status == status)
        
        if environment:
            query = query.filter(Integration.environment == environment)
        
        # Get the total count
        total = query.count()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute the query
        integrations = query.all()
        
        return integrations, total
    
    def update_integration(
        self,
        integration_id: int,
        integration_data: IntegrationUpdate,
        user_id: int
    ) -> Integration:
        """
        Update an existing integration.
        
        Args:
            integration_id: Integration ID
            integration_data: Updated integration data
            user_id: ID of the user updating the integration
            
        Returns:
            Updated integration
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_id)
            
            if not integration:
                raise ValueError(f"Integration with ID {integration_id} not found")
            
            # Track if credentials or configuration changed
            credentials_changed = False
            configuration_changed = False
            
            # Update the integration fields
            if integration_data.name is not None:
                integration.name = integration_data.name
            
            if integration_data.description is not None:
                integration.description = integration_data.description
            
            if integration_data.status is not None:
                integration.status = integration_data.status
            
            if integration_data.environment is not None:
                integration.environment = integration_data.environment
            
            if integration_data.configuration is not None:
                integration.configuration = integration_data.configuration
                configuration_changed = True
            
            if integration_data.credentials is not None:
                # Encrypt the new credentials
                integration.encrypted_credentials = self.credential_encryptor.encrypt(
                    integration_data.credentials
                )
                credentials_changed = True
            
            # Update the updated_by and updated_at fields
            integration.updated_by = user_id
            integration.updated_at = datetime.utcnow()
            
            # Create a new version if credentials or configuration changed
            if credentials_changed or configuration_changed:
                # Get the latest version
                latest_version = self.db.query(IntegrationVersion).filter(
                    IntegrationVersion.integration_id == integration_id
                ).order_by(IntegrationVersion.version.desc()).first()
                
                # Create a new version
                version = IntegrationVersion(
                    integration_id=integration.id,
                    version=(latest_version.version + 1) if latest_version else 1,
                    configuration=integration.configuration,
                    encrypted_credentials=integration.encrypted_credentials,
                    created_by=user_id
                )
                
                # Add the version to the database
                self.db.add(version)
            
            # Create an activity record
            activity = IntegrationActivity(
                integration_id=integration.id,
                activity_type=ActivityType.UPDATED,
                details={"message": "Integration updated"},
                performed_by=user_id
            )
            
            # Add the activity to the database
            self.db.add(activity)
            self.db.commit()
            
            return integration
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating integration: {str(e)}")
            raise
    
    def delete_integration(self, integration_id: int) -> None:
        """
        Delete an integration.
        
        Args:
            integration_id: Integration ID
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_id)
            
            if not integration:
                raise ValueError(f"Integration with ID {integration_id} not found")
            
            # Delete the integration
            self.db.delete(integration)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting integration: {str(e)}")
            raise
    
    def test_integration_connection(self, integration_id: int) -> Tuple[bool, Optional[str]]:
        """
        Test the connection to an integration.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Tuple containing a boolean indicating success and an optional error message
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_id)
            
            if not integration:
                raise ValueError(f"Integration with ID {integration_id} not found")
            
            # Get the appropriate adapter for the integration
            adapter = IntegrationAdapter.get_adapter_for_integration(
                integration,
                self.credential_encryptor
            )
            
            # Test the connection
            success, message = adapter.test_connection()
            
            # Update the integration status based on the test result
            new_status = IntegrationStatus.ACTIVE if success else IntegrationStatus.ERROR
            
            # Update the integration status
            integration.status = new_status
            integration.last_connection_test = datetime.utcnow()
            
            # Create an activity record
            activity_type = ActivityType.CONNECTION_SUCCESS if success else ActivityType.CONNECTION_FAILURE
            activity = IntegrationActivity(
                integration_id=integration.id,
                activity_type=activity_type,
                details={"message": message or "Connection test completed"},
                performed_by=None  # System-generated activity
            )
            
            # Add the activity to the database
            self.db.add(activity)
            self.db.commit()
            
            return success, message
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error testing integration connection: {str(e)}")
            
            # Update the integration status to ERROR
            try:
                integration = self.get_integration(integration_id)
                if integration:
                    integration.status = IntegrationStatus.ERROR
                    integration.last_connection_test = datetime.utcnow()
                    
                    # Create an activity record
                    activity = IntegrationActivity(
                        integration_id=integration.id,
                        activity_type=ActivityType.CONNECTION_FAILURE,
                        details={"message": f"Error testing connection: {str(e)}"},
                        performed_by=None  # System-generated activity
                    )
                    
                    # Add the activity to the database
                    self.db.add(activity)
                    self.db.commit()
            except Exception as inner_e:
                self.db.rollback()
                logger.error(f"Error updating integration status: {str(inner_e)}")
            
            return False, str(e)
    
    def get_integration_status(self, integration_id: int) -> Dict[str, Any]:
        """
        Get the status of an integration.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Dictionary containing integration status information
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_id)
            if not integration:
                return {"status": "not_found"}
            
            # Get the integration status
            status = {
                "integration_id": integration.id,
                "integration_name": integration.name,
                "integration_type": integration.type.value,
                "integration_status": integration.status.value,
                "integration_environment": integration.environment.value,
                "last_health_check": integration.last_health_check,
                "health_status": integration.health_status,
                # Use last_health_check since last_connection_test doesn't exist
                "last_connection_test": integration.last_health_check,
                "connectivity": "unknown"
            }
            
            # Determine connectivity status
            if integration.health_status == "healthy":
                status["connectivity"] = "healthy"
            elif integration.health_status == "degraded":
                status["connectivity"] = "degraded"
            elif integration.health_status == "failing":
                status["connectivity"] = "failing"
            
            return status
        except Exception as e:
            logger.error(f"Error getting integration status: {str(e)}")
            raise
    
    def create_webhook_endpoint(
        self,
        webhook_data: WebhookEndpointCreate,
        user_id: int
    ) -> WebhookEndpoint:
        """
        Create a new webhook endpoint.
        
        Args:
            webhook_data: Webhook endpoint data
            user_id: ID of the user creating the webhook endpoint
            
        Returns:
            Created webhook endpoint
        """
        try:
            # Use the provided path
            path = webhook_data.path

            # Use the provided secret_key or generate one
            secret = None
            if webhook_data.secret_key is not None:
                # If it's a SecretStr, extract the value
                if hasattr(webhook_data.secret_key, 'get_secret_value'):
                    secret = webhook_data.secret_key.get_secret_value()
                else:
                    secret = webhook_data.secret_key
            else:
                secret = generate_webhook_secret()
            
            # Create the webhook endpoint
            webhook = WebhookEndpoint(
                integration_id=webhook_data.integration_id,
                name=webhook_data.name,
                description=webhook_data.description,
                path=path,
                secret_key=secret,
                is_active=webhook_data.is_active
            )
            
            # Add the webhook endpoint to the database
            self.db.add(webhook)
            self.db.commit()
            
            return webhook
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating webhook endpoint: {str(e)}")
            raise
    
    def get_webhook_endpoint(self, webhook_id: int) -> Optional[WebhookEndpoint]:
        """
        Get a webhook endpoint by ID.
        
        Args:
            webhook_id: Webhook endpoint ID
            
        Returns:
            Webhook endpoint if found, None otherwise
        """
        return self.db.query(WebhookEndpoint).filter(WebhookEndpoint.id == webhook_id).first()
    
    def get_webhook_endpoint_by_path(self, path: str) -> Optional[WebhookEndpoint]:
        """
        Get a webhook endpoint by path.
        
        Args:
            path: Webhook endpoint path
            
        Returns:
            Webhook endpoint if found, None otherwise
        """
        return self.db.query(WebhookEndpoint).filter(WebhookEndpoint.path == path).first()
    
    def get_webhook_endpoints(
        self,
        integration_id: Optional[int] = None,
        active: Optional[bool] = None
    ) -> List[WebhookEndpoint]:
        """
        Get webhook endpoints with optional filtering.
        
        Args:
            integration_id: Filter by integration ID
            active: Filter by active status
            
        Returns:
            List of webhook endpoints
        """
        # Build the query
        query = self.db.query(WebhookEndpoint)
        
        # Apply filters
        if integration_id is not None:
            query = query.filter(WebhookEndpoint.integration_id == integration_id)
        
        if active is not None:
            query = query.filter(WebhookEndpoint.is_active == active)
        
        # Execute the query
        webhooks = query.all()
        
        return webhooks
    
    def update_webhook_endpoint(
        self,
        webhook_id: int,
        webhook_data: WebhookEndpointUpdate,
        user_id: int
    ) -> Optional[WebhookEndpoint]:
        """
        Update an existing webhook endpoint.
        
        Args:
            webhook_id: Webhook endpoint ID
            webhook_data: Updated webhook endpoint data
            user_id: ID of the user updating the webhook endpoint
            
        Returns:
            Updated webhook endpoint
        """
        try:
            # Get the webhook endpoint
            webhook = self.get_webhook_endpoint(webhook_id)
            if not webhook:
                return None
            
            # Update the webhook endpoint fields
            if webhook_data.name is not None:
                webhook.name = webhook_data.name
            
            if webhook_data.description is not None:
                webhook.description = webhook_data.description
            
            if webhook_data.path is not None:
                webhook.path = webhook_data.path
            
            if webhook_data.secret_key is not None:
                webhook.secret_key = webhook_data.secret_key
            
            if webhook_data.is_active is not None:
                webhook.is_active = webhook_data.is_active
            
            # Update the updated_at field - updated_by doesn't exist in the model
            webhook.updated_at = datetime.utcnow()
            
            # Commit the changes
            self.db.commit()
            
            return webhook
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating webhook endpoint: {str(e)}")
            raise
    
    def delete_webhook_endpoint(self, webhook_id: int) -> None:
        """
        Delete a webhook endpoint.
        
        Args:
            webhook_id: Webhook endpoint ID
        """
        try:
            # Get the webhook endpoint
            webhook = self.get_webhook_endpoint(webhook_id)
            
            if not webhook:
                raise ValueError(f"Webhook endpoint with ID {webhook_id} not found")
            
            # Delete the webhook endpoint
            self.db.delete(webhook)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting webhook endpoint: {str(e)}")
            raise
    
    def process_webhook_event(
        self,
        endpoint_id: int,
        headers: Dict[str, str],
        payload: Union[str, bytes]
    ) -> Optional[WebhookEvent]:
        """
        Process a webhook event.
        
        Args:
            endpoint_id: Webhook endpoint ID
            headers: Request headers
            payload: Request payload
            
        Returns:
            Created webhook event
        """
        try:
            # Get the webhook endpoint
            webhook = self.get_webhook_endpoint(endpoint_id)
            if not webhook:
                return None
            
            # Parse the payload if it's a string
            if isinstance(payload, str):
                try:
                    parsed_payload = json.loads(payload)
                except json.JSONDecodeError:
                    parsed_payload = {"raw_payload": payload}
            elif isinstance(payload, bytes):
                try:
                    parsed_payload = json.loads(payload.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    parsed_payload = {"raw_payload": payload.decode("utf-8", errors="replace")}
            else:
                parsed_payload = payload
            
            # Create the webhook event
            event = WebhookEvent(
                endpoint_id=endpoint_id,
                event_type=headers.get("X-Event-Type", "unknown"),
                payload=parsed_payload,
                headers=headers,
                signature=headers.get("X-Signature"),
                status=ActivityStatus.PENDING,
                ip_address=headers.get("X-Forwarded-For", headers.get("X-Real-IP")),
                created_at=datetime.utcnow()
            )
            
            # Add the webhook event to the database
            self.db.add(event)
            self.db.commit()
            
            return event
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing webhook event: {str(e)}")
            raise
