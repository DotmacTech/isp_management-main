"""
External service integration for the Communications module.

This module provides functionality for integrating with external services
such as SMS providers, email services, and chat platforms.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union, Tuple, TYPE_CHECKING
import httpx
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import sys
import os

from backend_core.config import get_settings
from backend_core.database import Base, get_db

logger = logging.getLogger(__name__)
settings = get_settings()


class ExternalServiceError(Exception):
    """Exception raised for errors in external service operations."""
    pass


class ExternalServiceFactory:
    """Factory for creating external service clients."""
    
    @staticmethod
    def create_client(service_type: str, config: Dict[str, Any]) -> 'BaseExternalService':
        """
        Create an external service client based on service type.
        
        Args:
            service_type: Type of service (e.g., 'sms', 'email', 'chat')
            config: Configuration for the service
            
        Returns:
            An instance of the appropriate external service client
            
        Raises:
            ExternalServiceError: If the service type is not supported
        """
        if service_type == "sms":
            return SMSService(config)
        elif service_type == "email":
            return EmailService(config)
        elif service_type == "chat":
            return ChatService(config)
        else:
            raise ExternalServiceError(f"Unsupported service type: {service_type}")


class BaseExternalService:
    """Base class for external service clients."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the external service client.
        
        Args:
            config: Configuration for the service
        """
        self.config = config
        self.validate_config()
    
    def validate_config(self):
        """
        Validate the service configuration.
        
        Raises:
            ExternalServiceError: If the configuration is invalid
        """
        raise NotImplementedError("Subclasses must implement validate_config()")
    
    async def send_message(self, recipient: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message using the external service.
        
        Args:
            recipient: Recipient of the message
            message: Message content
            **kwargs: Additional arguments for the service
            
        Returns:
            Response from the service
            
        Raises:
            ExternalServiceError: If the message could not be sent
        """
        raise NotImplementedError("Subclasses must implement send_message()")


class SMSService(BaseExternalService):
    """Client for SMS service providers."""
    
    def validate_config(self):
        """
        Validate the SMS service configuration.
        
        Raises:
            ExternalServiceError: If the configuration is invalid
        """
        required_fields = ["api_key", "api_url", "sender_id"]
        for field in required_fields:
            if field not in self.config:
                raise ExternalServiceError(f"Missing required field in SMS service config: {field}")
    
    async def send_message(self, recipient: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send an SMS message.
        
        Args:
            recipient: Phone number of the recipient
            message: SMS content
            **kwargs: Additional arguments for the SMS service
            
        Returns:
            Response from the SMS service
            
        Raises:
            ExternalServiceError: If the SMS could not be sent
        """
        try:
            # Prepare the request payload
            payload = {
                "api_key": self.config["api_key"],
                "sender_id": self.config["sender_id"],
                "to": recipient,
                "message": message,
                **kwargs
            }
            
            # Send the request to the SMS service
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.config["api_url"],
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 400:
                    raise ExternalServiceError(f"SMS service returned error: {response.text}")
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalServiceError(f"Error sending SMS: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Unexpected error sending SMS: {str(e)}")


class EmailService(BaseExternalService):
    """Client for email service providers."""
    
    def validate_config(self):
        """
        Validate the email service configuration.
        
        Raises:
            ExternalServiceError: If the configuration is invalid
        """
        required_fields = ["api_key", "api_url", "from_email", "from_name"]
        for field in required_fields:
            if field not in self.config:
                raise ExternalServiceError(f"Missing required field in email service config: {field}")
    
    async def send_message(
        self, 
        recipient: str, 
        message: str, 
        subject: str, 
        html_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an email message.
        
        Args:
            recipient: Email address of the recipient
            message: Plain text content of the email
            subject: Email subject
            html_content: HTML content of the email (optional)
            attachments: List of attachments (optional)
            **kwargs: Additional arguments for the email service
            
        Returns:
            Response from the email service
            
        Raises:
            ExternalServiceError: If the email could not be sent
        """
        try:
            # Prepare the request payload
            payload = {
                "api_key": self.config["api_key"],
                "from": {
                    "email": self.config["from_email"],
                    "name": self.config["from_name"]
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "text": message,
                **kwargs
            }
            
            if html_content:
                payload["html"] = html_content
                
            if attachments:
                payload["attachments"] = attachments
            
            # Send the request to the email service
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.config["api_url"],
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 400:
                    raise ExternalServiceError(f"Email service returned error: {response.text}")
                
                return response.json()
                
        except httpx.RequestError as e:
            raise ExternalServiceError(f"Error sending email: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Unexpected error sending email: {str(e)}")


class ChatService(BaseExternalService):
    """Client for chat service providers (e.g., Slack, Discord)."""
    
    def validate_config(self):
        """
        Validate the chat service configuration.
        
        Raises:
            ExternalServiceError: If the configuration is invalid
        """
        required_fields = ["webhook_url", "username"]
        for field in required_fields:
            if field not in self.config:
                raise ExternalServiceError(f"Missing required field in chat service config: {field}")
    
    async def send_message(
        self, 
        recipient: str,  # Channel or user ID
        message: str, 
        attachments: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat message.
        
        Args:
            recipient: Channel or user ID
            message: Message content
            attachments: List of attachments (optional)
            **kwargs: Additional arguments for the chat service
            
        Returns:
            Response from the chat service
            
        Raises:
            ExternalServiceError: If the message could not be sent
        """
        try:
            # Prepare the request payload
            payload = {
                "username": self.config["username"],
                "channel": recipient,
                "text": message,
                **kwargs
            }
            
            if attachments:
                payload["attachments"] = attachments
            
            # Send the request to the chat service
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.config["webhook_url"],
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 400:
                    raise ExternalServiceError(f"Chat service returned error: {response.text}")
                
                return {"status": "success", "response": response.text}
                
        except httpx.RequestError as e:
            raise ExternalServiceError(f"Error sending chat message: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Unexpected error sending chat message: {str(e)}")


class ExternalServiceManager:
    """Service for managing external service integrations."""
    
    @staticmethod
    async def register_service(
        db: Session, 
        service_data: dict,  
        user_id: int
    ):
        """
        Register a new external service.
        
        Args:
            db: Database session
            service_data: Service data dictionary with name, service_type, config, etc.
            user_id: ID of the user registering the service
            
        Returns:
            The created service
            
        Raises:
            ExternalServiceError: If the service configuration is invalid
        """
        # Import the model here to avoid circular imports
        from modules.communications.models import ExternalService
        
        try:
            # Validate configuration
            if not service_data.get("config"):
                logger.error("Invalid service configuration: Missing config")
                raise ExternalServiceError("Invalid service configuration")
        except Exception as e:
            logger.error(f"Invalid service configuration: {str(e)}")
            raise
        
        service = ExternalService(
            name=service_data["name"],
            service_type=service_data["service_type"],
            config=service_data["config"],
            is_active=service_data.get("is_active", False),
            created_by=user_id
        )
        
        try:
            db.add(service)
            db.commit()
            db.refresh(service)
            logger.info(f"Registered new external service: {service.name}")
            return service
        except Exception as e:
            db.rollback()
            logger.error(f"Error registering external service: {str(e)}")
            raise ExternalServiceError(f"Failed to register service: {str(e)}")

    @staticmethod
    async def update_service(
        db: Session, 
        service_id: int, 
        service_data: dict,
        user_id: int
    ):
        """
        Update an existing external service.
        
        Args:
            db: Database session
            service_id: ID of the service to update
            service_data: Updated service data
            user_id: ID of the user updating the service
            
        Returns:
            The updated service or None if not found
            
        Raises:
            ExternalServiceError: If the service configuration is invalid
        """
        # Import the model here to avoid circular imports
        from modules.communications.models import ExternalService
        
        service = db.query(ExternalService).filter(ExternalService.id == service_id).first()
        
        if not service:
            logger.warning(f"External service with ID {service_id} not found")
            return None
            
        # Update service attributes
        if "name" in service_data:
            service.name = service_data["name"]
            
        if "service_type" in service_data:
            service.service_type = service_data["service_type"]
            
        if "config" in service_data:
            try:
                # Validate configuration
                if not service_data["config"]:
                    logger.error("Invalid service configuration: Missing config")
                    raise ExternalServiceError("Invalid service configuration")
                service.config = service_data["config"]
            except Exception as e:
                logger.error(f"Invalid service configuration: {str(e)}")
                raise
                
        if "is_active" in service_data:
            service.is_active = service_data["is_active"]
            
        service.updated_at = datetime.utcnow()
        
        try:
            db.add(service)
            db.commit()
            db.refresh(service)
            logger.info(f"Updated external service: {service.name}")
            return service
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating external service: {str(e)}")
            raise ExternalServiceError(f"Failed to update service: {str(e)}")

    @staticmethod
    async def delete_service(
        db: Session, 
        service_id: int
    ) -> bool:
        """
        Delete an external service.
        
        Args:
            db: Database session
            service_id: ID of the service to delete
            
        Returns:
            True if deleted, False otherwise
        """
        # Import the model here to avoid circular imports
        from modules.communications.models import ExternalService
        
        service = db.query(ExternalService).filter(ExternalService.id == service_id).first()
        
        if not service:
            logger.warning(f"External service with ID {service_id} not found")
            return False
            
        try:
            db.delete(service)
            db.commit()
            logger.info(f"Deleted external service: {service.name}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting external service: {str(e)}")
            raise ExternalServiceError(f"Failed to delete service: {str(e)}")

    @staticmethod
    async def get_service(
        db: Session, 
        service_id: int
    ):
        """
        Get an external service by ID.
        
        Args:
            db: Database session
            service_id: ID of the service to get
            
        Returns:
            The service or None if not found
        """
        # Import the model here to avoid circular imports
        from modules.communications.models import ExternalService
        
        service = db.query(ExternalService).filter(ExternalService.id == service_id).first()
        
        if not service:
            logger.warning(f"External service with ID {service_id} not found")
            return None
            
        return service

    @staticmethod
    async def get_services(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        service_type: Optional[str] = None,
        active_only: bool = False
    ):
        """
        Get external services based on filters.
        
        Args:
            db: Database session
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            service_type: Filter by service type
            active_only: If True, only return active services
            
        Returns:
            List of services and total count
        """
        # Import the model here to avoid circular imports
        from modules.communications.models import ExternalService
        
        query = db.query(ExternalService)
        
        if service_type:
            query = query.filter(ExternalService.service_type == service_type)
        
        if active_only:
            query = query.filter(ExternalService.is_active == True)
        
        total = query.count()
        services = query.order_by(ExternalService.created_at.desc()).offset(skip).limit(limit).all()
        
        return services, total
    
    @staticmethod
    async def send_message(
        db: Session,
        service_id: int,
        recipient: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message using an external service.
        
        Args:
            db: Database session
            service_id: ID of the service to use
            recipient: Recipient of the message
            message: Message content
            **kwargs: Additional arguments for the service
            
        Returns:
            Response from the service
            
        Raises:
            ExternalServiceError: If the message could not be sent
        """
        # Import the model here to avoid circular imports
        from modules.communications.models import ExternalService
        
        service = await ExternalServiceManager.get_service(db, service_id)
        
        if not service:
            raise ExternalServiceError(f"External service with ID {service_id} not found")
        
        if not service.is_active:
            raise ExternalServiceError(f"External service {service.name} is not active")
        
        client = ExternalServiceFactory.create_client(service.service_type, service.config)
        return await client.send_message(recipient, message, **kwargs)
