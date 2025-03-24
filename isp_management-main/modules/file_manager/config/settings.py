"""
Configuration for the File Manager module.

This module provides configuration settings for the File Manager module,
including storage paths, S3 settings, and other module-specific settings.
"""

import os
from pydantic import BaseSettings
from typing import Optional, List


class FileManagerSettings(BaseSettings):
    """Settings for the File Manager module."""
    
    # Local storage settings
    LOCAL_STORAGE_PATH: str = os.getenv("FILE_MANAGER_LOCAL_STORAGE_PATH", "./storage/files")
    
    # S3 storage settings
    S3_BUCKET_NAME: str = os.getenv("FILE_MANAGER_S3_BUCKET_NAME", "isp-management-files")
    S3_ACCESS_KEY: Optional[str] = os.getenv("FILE_MANAGER_S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = os.getenv("FILE_MANAGER_S3_SECRET_KEY")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("FILE_MANAGER_S3_ENDPOINT_URL")
    S3_REGION: str = os.getenv("FILE_MANAGER_S3_REGION", "us-east-1")
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = int(os.getenv("FILE_MANAGER_MAX_UPLOAD_SIZE", "104857600"))  # 100 MB
    ALLOWED_EXTENSIONS: List[str] = os.getenv(
        "FILE_MANAGER_ALLOWED_EXTENSIONS", 
        ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.rar,.jpg,.jpeg,.png,.gif"
    ).split(",")
    
    # Security settings
    ENCRYPT_FILES: bool = os.getenv("FILE_MANAGER_ENCRYPT_FILES", "False").lower() == "true"
    ENCRYPTION_KEY: Optional[str] = os.getenv("FILE_MANAGER_ENCRYPTION_KEY")
    
    # Elasticsearch integration
    ENABLE_ELASTICSEARCH: bool = os.getenv("FILE_MANAGER_ENABLE_ELASTICSEARCH", "False").lower() == "true"
    ELASTICSEARCH_INDEX: str = os.getenv("FILE_MANAGER_ELASTICSEARCH_INDEX", "isp_management_files")
    
    # Default storage backend (local or s3)
    DEFAULT_STORAGE_BACKEND: str = os.getenv("FILE_MANAGER_DEFAULT_STORAGE_BACKEND", "local")
    
    # Temporary directory for file processing
    TEMP_DIR: str = os.getenv("FILE_MANAGER_TEMP_DIR", "/tmp/isp_management_files")
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


# Create settings instance
file_manager_settings = FileManagerSettings()
