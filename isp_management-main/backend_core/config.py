"""
Configuration settings for the ISP Management Platform.
"""
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/isp_management")
    
    # JWT Authentication
    secret_key: str = Field(default="your-secret-key-for-development-only")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    
    # Session Management
    session_expire_days: int = Field(default=7)
    max_sessions_per_user: int = Field(default=5)
    inactive_session_timeout_hours: int = Field(default=24)
    
    # MFA Settings
    mfa_issuer_name: str = Field(default="ISP Management Platform")
    mfa_code_expiry_seconds: int = Field(default=30)
    mfa_remember_device_days: int = Field(default=30)
    
    # Token Blacklisting
    token_blacklist_enabled: bool = Field(default=True)
    
    # Redis Cache
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: str = Field(default="")
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # Logging
    elasticsearch_url: str = Field(default="http://localhost:9200")
    audit_log_enabled: bool = Field(default=True)
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")
    
    # API Configuration
    api_title: str = "ISP Management Platform API"
    api_description: str = "API for managing Internet Service Provider operations"
    api_version: str = "1.0"
    supported_api_versions: dict = Field(default={"1.0": "/api/v1", "2.0": "/api/v2"})
    
    # Rate Limiting
    rate_limit: int = Field(default=100)  # Requests per window
    rate_limit_window: int = Field(default=60)  # Window in seconds
    rate_limit_enabled: bool = Field(default=True)
    
    # CORS Configuration
    allowed_origins: list = Field(default=["*"])
    
    # Model config
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Create settings instance
settings = Settings()

def get_settings():
    """
    Get the application settings.
    
    Returns:
        Settings: Application settings instance
    """
    return settings

# Export settings variables for easy import
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
DATABASE_URL = settings.database_url
API_TITLE = settings.api_title
API_DESCRIPTION = settings.api_description
API_VERSION = settings.api_version
SUPPORTED_API_VERSIONS = settings.supported_api_versions
ALLOWED_ORIGINS = settings.allowed_origins
RATE_LIMIT = settings.rate_limit
RATE_LIMIT_WINDOW = settings.rate_limit_window
REDIS_URL = settings.redis_url
