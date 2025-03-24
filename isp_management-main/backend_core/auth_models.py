"""
Authentication and Authorization Models.

This module contains Pydantic models used by the authentication and authorization services.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class Token(BaseModel):
    """Model for JWT token."""
    access_token: str
    token_type: str
    model_config = {"from_attributes": True}

class TokenData(BaseModel):
    """Model for JWT token data."""
    sub: str
    id: Optional[int] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None
    model_config = {"from_attributes": True}

class UserSession(BaseModel):
    """Model for user session."""
    user_id: int
    session_id: str
    is_active: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    termination_reason: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    model_config = {"from_attributes": True}

class User(BaseModel):
    """Model for user data."""
    id: int
    email: str
    email_verified: bool
    email_verification_token: Optional[str] = None
    email_verification_token_expires_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class MFADeviceToken(BaseModel):
    """Model for MFA device token."""
    user_id: int
    token: str
    expires_at: datetime
    model_config = {"from_attributes": True}
