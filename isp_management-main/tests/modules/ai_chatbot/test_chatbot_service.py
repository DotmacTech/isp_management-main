"""
Tests for the AI Chatbot Integration Module's ChatbotService.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from modules.ai_chatbot.services.chatbot_service import ChatbotService
from modules.ai_chatbot.schemas.chatbot import (
    ChatbotQueryCreate, ChatbotResponse, AIModelRequest, AIModelResponse,
    ChatbotFeedbackCreate, FeedbackResponse
)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def chatbot_service(mock_db):
    """Create a ChatbotService instance with mocked dependencies."""
    service = ChatbotService(mock_db)
    service.ai_service_client = AsyncMock()
    service.business_logic_processor = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_process_query_success(chatbot_service):
    """Test successful query processing."""
    # Arrange
    query = ChatbotQueryCreate(
        query="What is my current bill?",
        context={"user_id": 1, "tenant_id": 1},
        language="en"
    )
    user_id = 1
    tenant_id = 1
    
    # Mock AI service client response
    ai_response = AIModelResponse(
        intent="get_billing_info",
        confidence=0.95,
        entities={"bill_type": "current"},
        response_text="Your current bill is $50.00",
        follow_up_questions=["When is my payment due?"],
        suggested_actions=[{"action": "view_bill", "params": {"bill_id": 123}}]
    )
    chatbot_service.ai_service_client.process_query.return_value = (ai_response, 150.0)
    
    # Mock service config
    service_config = MagicMock()
    service_config.service_name = "openai"
    service_config.model_name = "gpt-3.5-turbo"
    chatbot_service.ai_service_client.get_service_config.return_value = service_config
    
    # Mock business logic processor response
    expected_response = ChatbotResponse(
        response_text="Your current bill is $50.00",
        intent="get_billing_info",
        confidence=0.95,
        follow_up_questions=["When is my payment due?"],
        suggested_actions=[{"action": "view_bill", "params": {"bill_id": 123}}],
        query_id=1
    )
    db_query = MagicMock()
    db_query.id = 1
    chatbot_service.business_logic_processor.process_intent.return_value = (expected_response, db_query)
    
    # Act
    response = await chatbot_service.process_query(query, user_id, tenant_id)
    
    # Assert
    assert response == expected_response
    chatbot_service.ai_service_client.process_query.assert_called_once()
    chatbot_service.business_logic_processor.process_intent.assert_called_once()


@pytest.mark.asyncio
async def test_process_query_error(chatbot_service, mock_db):
    """Test query processing with an error."""
    # Arrange
    query = ChatbotQueryCreate(
        query="What is my current bill?",
        context={"user_id": 1, "tenant_id": 1},
        language="en"
    )
    user_id = 1
    tenant_id = 1
    
    # Mock AI service client to raise an exception
    error_message = "AI service unavailable"
    chatbot_service.ai_service_client.process_query.side_effect = Exception(error_message)
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await chatbot_service.process_query(query, user_id, tenant_id)
    
    assert str(exc_info.value) == error_message
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_submit_feedback_success(chatbot_service, mock_db):
    """Test successful feedback submission."""
    # Arrange
    feedback = ChatbotFeedbackCreate(
        query_id=1,
        rating=5,
        is_helpful=True,
        comments="Very helpful response!"
    )
    user_id = 1
    
    # Mock query retrieval
    query = MagicMock()
    query.tenant_id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = query
    
    # Mock feedback creation
    db_feedback = MagicMock()
    db_feedback.id = 1
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda x: setattr(x, 'id', 1)
    
    # Act
    response = await chatbot_service.submit_feedback(feedback, user_id)
    
    # Assert
    assert response.message == "Feedback submitted successfully"
    assert response.feedback_id == 1
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_submit_feedback_query_not_found(chatbot_service, mock_db):
    """Test feedback submission with query not found."""
    # Arrange
    feedback = ChatbotFeedbackCreate(
        query_id=999,
        rating=5,
        is_helpful=True,
        comments="Very helpful response!"
    )
    user_id = 1
    
    # Mock query retrieval to return None
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await chatbot_service.submit_feedback(feedback, user_id)
    
    assert exc_info.value.status_code == 404
    assert f"Query with ID {feedback.query_id} not found" in exc_info.value.detail
