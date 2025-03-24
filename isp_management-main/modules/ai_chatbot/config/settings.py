"""
Configuration settings for the AI Chatbot Integration Module.
"""

import os
from typing import Dict, Any, List, Optional
from pydantic import BaseSettings, Field, validator


class ChatbotSettings(BaseSettings):
    """Settings for the AI Chatbot Integration Module."""
    
    # Default AI service settings
    DEFAULT_AI_SERVICE: str = Field(
        "openai",
        description="Default AI service to use"
    )
    DEFAULT_MODEL_NAME: str = Field(
        "gpt-3.5-turbo",
        description="Default model name to use"
    )
    
    # Request settings
    REQUEST_TIMEOUT_SECONDS: int = Field(
        30,
        description="Timeout for AI service requests in seconds"
    )
    MAX_RETRIES: int = Field(
        3,
        description="Maximum number of retries for failed requests"
    )
    RETRY_DELAY_SECONDS: int = Field(
        1,
        description="Delay between retries in seconds"
    )
    
    # Response settings
    MAX_RESPONSE_LENGTH: int = Field(
        1000,
        description="Maximum length of response text"
    )
    MAX_FOLLOW_UP_QUESTIONS: int = Field(
        3,
        description="Maximum number of follow-up questions to suggest"
    )
    MAX_SUGGESTED_ACTIONS: int = Field(
        5,
        description="Maximum number of suggested actions to include"
    )
    
    # Security settings
    MASK_SENSITIVE_DATA: bool = Field(
        True,
        description="Whether to mask sensitive data in responses"
    )
    SENSITIVE_FIELDS: List[str] = Field(
        ["password", "secret", "token", "key", "credit_card", "ssn", "social_security"],
        description="Fields to mask in responses"
    )
    
    # Cache settings
    ENABLE_RESPONSE_CACHE: bool = Field(
        True,
        description="Whether to cache responses"
    )
    CACHE_TTL_SECONDS: int = Field(
        3600,
        description="Time-to-live for cached responses in seconds"
    )
    
    # Logging settings
    LOG_QUERIES: bool = Field(
        True,
        description="Whether to log queries"
    )
    LOG_RESPONSES: bool = Field(
        True,
        description="Whether to log responses"
    )
    LOG_SENSITIVE_DATA: bool = Field(
        False,
        description="Whether to log sensitive data"
    )
    
    # Performance settings
    ASYNC_PROCESSING: bool = Field(
        True,
        description="Whether to process queries asynchronously"
    )
    MAX_CONCURRENT_REQUESTS: int = Field(
        10,
        description="Maximum number of concurrent requests"
    )
    
    # Feature flags
    ENABLE_FEEDBACK: bool = Field(
        True,
        description="Whether to enable feedback collection"
    )
    ENABLE_CONTEXT_TRACKING: bool = Field(
        True,
        description="Whether to enable conversation context tracking"
    )
    ENABLE_MULTI_LANGUAGE: bool = Field(
        True,
        description="Whether to enable multi-language support"
    )
    
    # Supported languages
    SUPPORTED_LANGUAGES: List[str] = Field(
        ["en", "es", "fr", "de", "ru", "zh", "ja", "ar"],
        description="List of supported language codes"
    )
    
    class Config:
        """Pydantic config."""
        env_prefix = "CHATBOT_"
        case_sensitive = True


# Create settings instance
chatbot_settings = ChatbotSettings()
