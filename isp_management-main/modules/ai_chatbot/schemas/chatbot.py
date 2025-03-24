"""
Pydantic schemas for the AI Chatbot Integration Module.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime


class ChatbotQueryBase(BaseModel):
    """Base schema for chatbot queries."""
    query: str = Field(..., description="The natural language query text")
    customer_id: Optional[int] = Field(None, description="Optional customer ID for context")
    tenant_id: Optional[int] = Field(None, description="Tenant ID for multi-tenant support")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the query")
    language: Optional[str] = Field("en", description="Language code for the query")


class ChatbotQueryCreate(ChatbotQueryBase):
    """Schema for creating a new chatbot query."""
    pass


class Entity(BaseModel):
    """Schema for named entities extracted from queries."""
    entity_type: str = Field(..., description="Type of entity (e.g., customer, ticket, service)")
    value: str = Field(..., description="Value of the entity")
    confidence: float = Field(..., description="Confidence score for entity extraction")
    start_pos: Optional[int] = Field(None, description="Start position in original text")
    end_pos: Optional[int] = Field(None, description="End position in original text")


class AIModelRequest(BaseModel):
    """Schema for requests to AI model API."""
    query: str = Field(..., description="The natural language query text")
    context: Optional[Dict[str, Any]] = Field(None, description="Conversation context")
    tenant_id: int = Field(..., description="Tenant ID for customization")
    user_id: int = Field(..., description="User ID for personalization")
    language: Optional[str] = Field("en", description="Language code")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")


class AIModelResponse(BaseModel):
    """Schema for responses from AI model API."""
    intent: str = Field(..., description="Detected intent")
    confidence: float = Field(..., description="Confidence score for intent detection")
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    response: str = Field(..., description="Generated response text")
    suggested_queries: Optional[List[str]] = Field(None, description="Suggested follow-up queries")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SuggestedAction(BaseModel):
    """Schema for suggested actions."""
    action_type: str = Field(..., description="Type of action (e.g., view, update, create)")
    module: str = Field(..., description="Target module for the action")
    description: str = Field(..., description="Description of the action")
    endpoint: Optional[str] = Field(None, description="API endpoint for the action if applicable")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for the action")
    requires_confirmation: bool = Field(False, description="Whether the action requires confirmation")


class ChatbotResponse(BaseModel):
    """Schema for chatbot responses."""
    response: str = Field(..., description="The natural language response text")
    data: Optional[Dict[str, Any]] = Field(None, description="Structured data related to the response")
    follow_up_questions: List[str] = Field(default_factory=list, description="Suggested follow-up questions")
    suggested_actions: List[SuggestedAction] = Field(default_factory=list, description="Suggested actions")
    intent: Optional[str] = Field(None, description="Detected intent of the query")
    confidence_score: Optional[float] = Field(None, description="Confidence score of the intent detection")
    entities: Optional[List[Entity]] = Field(None, description="Entities extracted from the query")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    query_id: Optional[int] = Field(None, description="ID of the stored query")


class ChatbotQuery(ChatbotQueryBase):
    """Schema for a complete chatbot query with response."""
    id: int
    user_id: int
    tenant_id: int
    response_text: str
    intent: Optional[str] = None
    confidence_score: Optional[float] = None
    entities: Optional[List[Dict[str, Any]]] = None
    processing_time_ms: Optional[int] = None
    ai_service_name: Optional[str] = None
    ai_model_version: Optional[str] = None
    is_successful: bool = True
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ChatbotFeedbackBase(BaseModel):
    """Base schema for chatbot feedback."""
    query_id: int = Field(..., description="ID of the query being rated")
    rating: int = Field(..., description="Rating from 1-5", ge=1, le=5)
    is_helpful: Optional[bool] = Field(None, description="Whether the response was helpful")
    comments: Optional[str] = Field(None, description="Optional feedback comments")

    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class ChatbotFeedbackCreate(ChatbotFeedbackBase):
    """Schema for creating new feedback."""
    pass


class ChatbotFeedback(ChatbotFeedbackBase):
    """Schema for a complete feedback record."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class FeedbackResponse(BaseModel):
    """Schema for feedback submission response."""
    message: str = Field(..., description="Confirmation message")
    feedback_id: int = Field(..., description="ID of the recorded feedback")


class ChatbotActionCreate(BaseModel):
    """Schema for creating a new chatbot action."""
    query_id: int = Field(..., description="ID of the associated query")
    action_type: str = Field(..., description="Type of action performed")
    module_name: str = Field(..., description="Name of the module the action was performed on")
    endpoint: Optional[str] = Field(None, description="API endpoint used for the action")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters used for the action")
    result: Optional[Dict[str, Any]] = Field(None, description="Result of the action")
    is_successful: bool = Field(True, description="Whether the action was successful")
    error_message: Optional[str] = Field(None, description="Error message if the action failed")


class ChatbotAction(ChatbotActionCreate):
    """Schema for a complete chatbot action."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class AIServiceConfigBase(BaseModel):
    """Base schema for AI service configuration."""
    tenant_id: int = Field(..., description="Tenant ID")
    service_name: str = Field(..., description="Name of the AI service")
    service_url: str = Field(..., description="URL of the AI service API")
    api_key: str = Field(..., description="API key for authentication")
    model_name: Optional[str] = Field(None, description="Name of the AI model to use")
    is_active: bool = Field(True, description="Whether the service is active")
    config_params: Optional[Dict[str, Any]] = Field(None, description="Additional configuration parameters")


class AIServiceConfigCreate(AIServiceConfigBase):
    """Schema for creating a new AI service configuration."""
    pass


class AIServiceConfig(AIServiceConfigBase):
    """Schema for a complete AI service configuration."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        
    @property
    def api_key_masked(self) -> str:
        """Return a masked version of the API key for display purposes."""
        if not self.api_key:
            return ""
        if len(self.api_key) <= 8:
            return "****"
        return self.api_key[:4] + "****" + self.api_key[-4:]
