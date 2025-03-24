"""
API endpoints for the AI Chatbot Integration Module.
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_tenant_id
from core.models import User
from ..schemas.chatbot import (
    ChatbotQueryCreate, ChatbotResponse, ChatbotQuery,
    ChatbotFeedbackCreate, FeedbackResponse, AIServiceConfigCreate,
    AIServiceConfig
)
from ..services.chatbot_service import ChatbotService

# Initialize router
router = APIRouter(
    prefix="/chatbot",
    tags=["chatbot"],
    responses={404: {"description": "Not found"}}
)

# Initialize logger
logger = logging.getLogger(__name__)


@router.post("/query", response_model=ChatbotResponse)
async def process_query(
    query: ChatbotQueryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id),
    service_name: Optional[str] = None
):
    """
    Process a natural language query to the chatbot.
    
    Args:
        query: The query to process
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: The current authenticated user
        tenant_id: The current tenant ID
        service_name: Optional name of the AI service to use
        
    Returns:
        ChatbotResponse: The chatbot response
    """
    chatbot_service = ChatbotService(db)
    
    # Add cleanup task
    background_tasks.add_task(chatbot_service.close)
    
    try:
        response = await chatbot_service.process_query(
            query, current_user.id, tenant_id, service_name
        )
        return response
        
    except Exception as e:
        logger.error(
            f"Error processing query: {str(e)}",
            extra={
                "user_id": current_user.id,
                "tenant_id": tenant_id,
                "query": query.query
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: ChatbotFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit feedback on a chatbot response.
    
    Args:
        feedback: The feedback to submit
        db: Database session
        current_user: The current authenticated user
        
    Returns:
        FeedbackResponse: The feedback response
    """
    chatbot_service = ChatbotService(db)
    
    try:
        response = await chatbot_service.submit_feedback(
            feedback, current_user.id
        )
        return response
        
    except Exception as e:
        logger.error(
            f"Error submitting feedback: {str(e)}",
            extra={
                "user_id": current_user.id,
                "query_id": feedback.query_id
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting feedback: {str(e)}"
        )


@router.get("/history", response_model=List[ChatbotQuery])
async def get_query_history(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Get the query history for the current user.
    
    Args:
        limit: Maximum number of queries to return
        offset: Offset for pagination
        db: Database session
        current_user: The current authenticated user
        tenant_id: The current tenant ID
        
    Returns:
        List[ChatbotQuery]: The query history
    """
    queries = db.query(ChatbotQuery).filter(
        ChatbotQuery.user_id == current_user.id,
        ChatbotQuery.tenant_id == tenant_id
    ).order_by(
        ChatbotQuery.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return queries


@router.get("/config", response_model=List[AIServiceConfig])
async def get_ai_service_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Get the AI service configurations for the current tenant.
    
    Args:
        db: Database session
        current_user: The current authenticated user
        tenant_id: The current tenant ID
        
    Returns:
        List[AIServiceConfig]: The AI service configurations
    """
    configs = db.query(AIServiceConfig).filter(
        AIServiceConfig.tenant_id == tenant_id
    ).all()
    
    return configs


@router.post("/config", response_model=AIServiceConfig)
async def create_ai_service_config(
    config: AIServiceConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Create a new AI service configuration.
    
    Args:
        config: The configuration to create
        db: Database session
        current_user: The current authenticated user
        tenant_id: The current tenant ID
        
    Returns:
        AIServiceConfig: The created configuration
    """
    # Override tenant_id with the current tenant ID
    config_data = config.dict()
    config_data["tenant_id"] = tenant_id
    
    # Create the configuration
    db_config = AIServiceConfig(**config_data)
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config


@router.put("/config/{config_id}", response_model=AIServiceConfig)
async def update_ai_service_config(
    config_id: int,
    config: AIServiceConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Update an AI service configuration.
    
    Args:
        config_id: The ID of the configuration to update
        config: The updated configuration
        db: Database session
        current_user: The current authenticated user
        tenant_id: The current tenant ID
        
    Returns:
        AIServiceConfig: The updated configuration
    """
    # Check if the configuration exists
    db_config = db.query(AIServiceConfig).filter(
        AIServiceConfig.id == config_id,
        AIServiceConfig.tenant_id == tenant_id
    ).first()
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with ID {config_id} not found"
        )
    
    # Update the configuration
    config_data = config.dict(exclude_unset=True)
    
    # Ensure tenant_id is not changed
    config_data["tenant_id"] = tenant_id
    
    for key, value in config_data.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    
    return db_config


@router.delete("/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_service_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Delete an AI service configuration.
    
    Args:
        config_id: The ID of the configuration to delete
        db: Database session
        current_user: The current authenticated user
        tenant_id: The current tenant ID
    """
    # Check if the configuration exists
    db_config = db.query(AIServiceConfig).filter(
        AIServiceConfig.id == config_id,
        AIServiceConfig.tenant_id == tenant_id
    ).first()
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with ID {config_id} not found"
        )
    
    # Delete the configuration
    db.delete(db_config)
    db.commit()
    
    return None
