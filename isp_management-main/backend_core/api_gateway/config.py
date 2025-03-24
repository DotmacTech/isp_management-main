"""
Configuration settings for the API Gateway module.

This module provides configuration settings for the API Gateway,
including rate limiting, circuit breaking, CORS, and security settings.
"""

import json
import os
from typing import Dict, List, Any, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIGatewaySettings(BaseSettings):
    """
    Configuration settings for the API Gateway.
    
    This class defines all configuration settings for the API Gateway,
    with support for environment variable overrides.
    """
    
    # Rate limiting settings
    rate_limiting_enabled: bool = Field(True)
    default_rate_limit: int = Field(100)
    default_rate_limit_period: int = Field(60)
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = Field(True)
    default_circuit_breaker_threshold: int = Field(5)
    default_circuit_breaker_recovery_time: int = Field(30)
    
    # CORS settings
    cors_enabled: bool = Field(True)
    cors_allowed_origins: List[str] = Field(
        ["http://localhost:3000", "https://admin.ispmanagement.com"]
    )
    cors_allow_credentials: bool = Field(True)
    cors_allowed_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    )
    cors_allowed_headers: List[str] = Field(
        ["Authorization", "Content-Type", "X-API-Version", "X-Requested-With"]
    )
    
    # Security settings
    security_headers_enabled: bool = Field(True)
    ssl_redirect: bool = Field(True)
    mask_sensitive_data: bool = Field(True)
    custom_security_headers: Dict[str, str] = Field(default_factory=dict)
    
    # Logging settings
    log_requests: bool = Field(True)
    log_responses: bool = Field(True)
    
    # Versioning settings
    versioning_enabled: bool = Field(True)
    default_api_version: str = Field("1")
    API_VERSIONING_STRATEGY: str = Field("url_path")
    API_GATEWAY_VERSION: str = Field("1.0.0")
    API_VERSION_HEADER_NAME: str = Field("X-API-Version")
    API_VERSION_QUERY_PARAM: str = Field("version")
    
    # For backward compatibility with existing code
    API_DEFAULT_VERSION: str = Field("1")
    API_VERSIONS: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "1": {"description": "Initial API version", "deprecated": False},
            "2": {"description": "Enhanced API with additional features", "deprecated": False}
        }
    )
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "https://admin.ispmanagement.com"]
    )
    CORS_METHODS: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    )
    CORS_HEADERS: List[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type", "X-API-Version", "X-Requested-With"]
    )
    
    # Redis settings (optional)
    redis_enabled: bool = Field(False)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="API_GATEWAY_",
        case_sensitive=False,
        extra="ignore"
    )
    
    @model_validator(mode='before')
    @classmethod
    def parse_env_vars(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse environment variables before validation."""
        if not isinstance(data, dict):
            return data
            
        # Check environment variables directly
        for key, value in os.environ.items():
            if key.startswith("API_GATEWAY_"):
                field_name = key[12:].lower()
                
                # Handle list fields
                if field_name in ["cors_allowed_origins", "cors_allowed_methods", "cors_allowed_headers"]:
                    if value:
                        data[field_name] = [item.strip() for item in value.split(",")]
                
                # Handle dict fields
                elif field_name == "custom_security_headers":
                    try:
                        data[field_name] = json.loads(value)
                    except json.JSONDecodeError:
                        # In case of invalid JSON, use empty dict
                        if field_name not in data:
                            data[field_name] = {}
                
                # Handle boolean fields
                elif field_name in ["rate_limiting_enabled", "circuit_breaker_enabled", 
                                   "cors_enabled", "cors_allow_credentials", 
                                   "security_headers_enabled", "ssl_redirect", 
                                   "mask_sensitive_data", "log_requests", 
                                   "log_responses", "versioning_enabled", 
                                   "redis_enabled"]:
                    data[field_name] = value.lower() in ["true", "1", "yes", "y", "on"]
                
                # Handle integer fields
                elif field_name in ["default_rate_limit", "default_rate_limit_period",
                                   "default_circuit_breaker_threshold", 
                                   "default_circuit_breaker_recovery_time"]:
                    try:
                        data[field_name] = int(value)
                    except ValueError:
                        pass  # Let Pydantic handle the validation error
        
        return data
    
    @field_validator("default_rate_limit", "default_rate_limit_period")
    @classmethod
    def validate_rate_limit(cls, v):
        """Validate rate limit settings."""
        if v <= 0:
            raise ValueError("Rate limit settings must be positive")
        return v
    
    @field_validator("default_circuit_breaker_threshold", "default_circuit_breaker_recovery_time")
    @classmethod
    def validate_circuit_breaker(cls, v):
        """Validate circuit breaker settings."""
        if v <= 0:
            raise ValueError("Circuit breaker settings must be positive")
        return v


# Create a singleton instance of the settings
settings = APIGatewaySettings()
