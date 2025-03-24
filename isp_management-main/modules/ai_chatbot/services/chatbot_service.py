"""
Chatbot Service for the AI Chatbot Integration Module.

This service coordinates between the AI Service Client and the Business Logic Processor
to handle chatbot queries and responses.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.config import settings
from core.metrics import MetricsCollector
from core.security import get_current_user
from ..models.chatbot import ChatbotQuery, ChatbotFeedback
from ..schemas.chatbot import (
    ChatbotQueryCreate, ChatbotResponse, AIModelRequest,
    ChatbotFeedbackCreate, FeedbackResponse
)
from .ai_service_client import AIServiceClient
from .business_logic_processor import BusinessLogicProcessor

# Initialize metrics collector
metrics = MetricsCollector("ai_chatbot.chatbot_service")

# Initialize logger
logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Chatbot Service for handling queries and responses.
    
    This class coordinates between the AI Service Client and the Business Logic Processor
    to handle chatbot queries and responses.
    """
    
    def __init__(self, db: Session):
        """Initialize the Chatbot Service."""
        self.db = db
        self.ai_service_client = AIServiceClient(db)
        self.business_logic_processor = BusinessLogicProcessor(db)
    
    async def close(self):
        """Close any open connections."""
        await self.ai_service_client.close()
    
    async def process_query(
        self,
        query: ChatbotQueryCreate,
        user_id: int,
        tenant_id: int,
        service_name: Optional[str] = None
    ) -> ChatbotResponse:
        """
        Process a chatbot query.
        
        Args:
            query: The query to process
            user_id: The ID of the user making the query
            tenant_id: The ID of the tenant
            service_name: Optional name of the AI service to use
            
        Returns:
            ChatbotResponse: The chatbot response
        """
        start_time = time.time()
        
        try:
            # Create AI model request
            ai_request = AIModelRequest(
                query=query.query,
                context=query.context,
                tenant_id=tenant_id,
                user_id=user_id,
                language=query.language,
                session_id=None  # TODO: Implement session tracking
            )
            
            # Process the query with the AI service
            ai_response, ai_processing_time = await self.ai_service_client.process_query(
                ai_request, service_name
            )
            
            # Get the AI service configuration
            service_config = await self.ai_service_client.get_service_config(
                tenant_id, service_name
            )
            
            # Process the intent with the business logic processor
            response, db_query = await self.business_logic_processor.process_intent(
                ai_response,
                query,
                user_id,
                tenant_id,
                ai_processing_time,
                service_config.service_name,
                service_config.model_name
            )
            
            # Calculate total processing time
            total_processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Record metrics
            metrics.increment(
                "query_processed",
                tags={
                    "tenant_id": str(tenant_id),
                    "intent": ai_response.intent,
                    "service": service_config.service_name
                }
            )
            metrics.timing(
                "query_processing_time",
                total_processing_time,
                tags={
                    "tenant_id": str(tenant_id),
                    "service": service_config.service_name
                }
            )
            
            return response
            
        except Exception as e:
            # Record metrics
            metrics.increment(
                "query_processing_error",
                tags={
                    "tenant_id": str(tenant_id),
                    "error_type": type(e).__name__
                }
            )
            
            logger.error(
                f"Error processing chatbot query: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "query": query.query
                },
                exc_info=True
            )
            
            # Create a failed query record
            db_query = ChatbotQuery(
                user_id=user_id,
                tenant_id=tenant_id,
                query_text=query.query,
                response_text=f"Error: {str(e)}",
                context_data=query.context,
                is_successful=False,
                error_message=str(e)
            )
            self.db.add(db_query)
            self.db.commit()
            
            # Re-raise the exception
            raise
    
    async def submit_feedback(
        self,
        feedback: ChatbotFeedbackCreate,
        user_id: int
    ) -> FeedbackResponse:
        """
        Submit feedback for a chatbot query.
        
        Args:
            feedback: The feedback to submit
            user_id: The ID of the user submitting the feedback
            
        Returns:
            FeedbackResponse: The feedback response
        """
        try:
            # Check if the query exists
            query = self.db.query(ChatbotQuery).filter(
                ChatbotQuery.id == feedback.query_id
            ).first()
            
            if not query:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Query with ID {feedback.query_id} not found"
                )
            
            # Create the feedback record
            db_feedback = ChatbotFeedback(
                query_id=feedback.query_id,
                user_id=user_id,
                rating=feedback.rating,
                is_helpful=feedback.is_helpful,
                comments=feedback.comments
            )
            self.db.add(db_feedback)
            self.db.commit()
            self.db.refresh(db_feedback)
            
            # Record metrics
            metrics.increment(
                "feedback_submitted",
                tags={
                    "tenant_id": str(query.tenant_id),
                    "rating": str(feedback.rating),
                    "is_helpful": str(feedback.is_helpful) if feedback.is_helpful is not None else "none"
                }
            )
            
            return FeedbackResponse(
                message="Feedback submitted successfully",
                feedback_id=db_feedback.id
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
            
        except Exception as e:
            logger.error(
                f"Error submitting feedback: {str(e)}",
                extra={
                    "user_id": user_id,
                    "query_id": feedback.query_id
                },
                exc_info=True
            )
            
            # Record metrics
            metrics.increment(
                "feedback_submission_error",
                tags={
                    "error_type": type(e).__name__
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error submitting feedback: {str(e)}"
            )
