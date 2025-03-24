"""
AI Service Client for the AI Chatbot Integration Module.

This service handles communication with external AI services for natural language
processing, intent recognition, and response generation.
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import httpx
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.security import get_api_key_hash
from core.metrics import MetricsCollector
from ..models.chatbot import AIServiceConfig
from ..schemas.chatbot import AIModelRequest, AIModelResponse, Entity

# Initialize metrics collector
metrics = MetricsCollector("ai_chatbot.ai_service_client")

# Initialize logger
logger = logging.getLogger(__name__)


class AIServiceClient:
    """
    Client for communicating with external AI services.
    
    This class handles:
    - Authentication with AI services
    - Sending requests to AI services
    - Processing responses from AI services
    - Error handling and retries
    """
    
    def __init__(self, db: Session):
        """Initialize the AI Service Client."""
        self.db = db
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
    
    async def get_service_config(self, tenant_id: int, service_name: Optional[str] = None) -> AIServiceConfig:
        """
        Get the AI service configuration for a tenant.
        
        Args:
            tenant_id: The ID of the tenant
            service_name: Optional name of the service to use
            
        Returns:
            AIServiceConfig: The service configuration
            
        Raises:
            HTTPException: If no active service configuration is found
        """
        query = self.db.query(AIServiceConfig).filter(
            AIServiceConfig.tenant_id == tenant_id,
            AIServiceConfig.is_active == True
        )
        
        if service_name:
            query = query.filter(AIServiceConfig.service_name == service_name)
        
        service_config = query.first()
        
        if not service_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active AI service configuration found for tenant {tenant_id}"
            )
        
        return service_config
    
    async def process_query(
        self, 
        request: AIModelRequest,
        service_name: Optional[str] = None
    ) -> Tuple[AIModelResponse, float]:
        """
        Process a natural language query using an AI service.
        
        Args:
            request: The request to process
            service_name: Optional name of the service to use
            
        Returns:
            Tuple[AIModelResponse, float]: The AI model response and processing time
            
        Raises:
            HTTPException: If the request fails
        """
        start_time = time.time()
        
        try:
            # Get the service configuration
            service_config = await self.get_service_config(request.tenant_id, service_name)
            
            # Prepare the request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {service_config.api_key}"
            }
            
            # Add custom headers from config if available
            if service_config.config_params and "headers" in service_config.config_params:
                headers.update(service_config.config_params["headers"])
            
            # Prepare the payload
            payload = {
                "query": request.query,
                "context": request.context or {},
                "tenant_id": request.tenant_id,
                "user_id": request.user_id,
                "language": request.language,
                "session_id": request.session_id
            }
            
            # Add model name if specified
            if service_config.model_name:
                payload["model"] = service_config.model_name
            
            # Add any additional parameters from config
            if service_config.config_params and "parameters" in service_config.config_params:
                payload.update(service_config.config_params["parameters"])
            
            # Send the request to the AI service
            response = await self.http_client.post(
                service_config.service_url,
                headers=headers,
                json=payload
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            
            # Create the AI model response
            ai_response = AIModelResponse(
                intent=response_data.get("intent", "unknown"),
                confidence=response_data.get("confidence", 0.0),
                entities=[
                    Entity(**entity) for entity in response_data.get("entities", [])
                ],
                response=response_data.get("response", ""),
                suggested_queries=response_data.get("suggested_queries", []),
                metadata=response_data.get("metadata", {})
            )
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Record metrics
            metrics.increment(
                "ai_service_request_success",
                tags={
                    "tenant_id": str(request.tenant_id),
                    "service": service_config.service_name,
                    "intent": ai_response.intent
                }
            )
            metrics.timing(
                "ai_service_request_time",
                processing_time,
                tags={
                    "tenant_id": str(request.tenant_id),
                    "service": service_config.service_name
                }
            )
            
            return ai_response, processing_time
            
        except httpx.HTTPStatusError as e:
            # Record metrics
            metrics.increment(
                "ai_service_request_error",
                tags={
                    "tenant_id": str(request.tenant_id),
                    "service": service_name or "unknown",
                    "status_code": str(e.response.status_code)
                }
            )
            
            logger.error(
                f"AI service request failed: {e.response.status_code} - {e.response.text}",
                extra={
                    "tenant_id": request.tenant_id,
                    "service": service_name,
                    "query": request.query
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service request failed: {e.response.status_code} - {e.response.text}"
            )
            
        except httpx.RequestError as e:
            # Record metrics
            metrics.increment(
                "ai_service_request_error",
                tags={
                    "tenant_id": str(request.tenant_id),
                    "service": service_name or "unknown",
                    "error_type": "request_error"
                }
            )
            
            logger.error(
                f"AI service request error: {str(e)}",
                extra={
                    "tenant_id": request.tenant_id,
                    "service": service_name,
                    "query": request.query
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service request error: {str(e)}"
            )
            
        except Exception as e:
            # Record metrics
            metrics.increment(
                "ai_service_request_error",
                tags={
                    "tenant_id": str(request.tenant_id),
                    "service": service_name or "unknown",
                    "error_type": "unknown"
                }
            )
            
            logger.error(
                f"Unexpected error processing AI service request: {str(e)}",
                extra={
                    "tenant_id": request.tenant_id,
                    "service": service_name,
                    "query": request.query
                },
                exc_info=True
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error processing AI service request: {str(e)}"
            )
