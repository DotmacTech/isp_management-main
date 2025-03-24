"""
Authentication schemas for the ISP Management Platform.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, root_validator, model_validator, ConfigDict
import re

class UserBase(BaseModel):
    """Base schema for user data."""
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    role: str = Field(default="customer", pattern="^(admin|staff|customer|reseller)$")
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v, info):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must be alphanumeric with only underscores and hyphens')
        return v

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v, info):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    username: Optional[str] = Field(None, min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(admin|staff|customer|reseller)$")
    is_active: Optional[bool] = None
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v, info):
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must be alphanumeric with only underscores and hyphens')
        return v

class UserInDB(UserBase):
    """Schema for user data stored in the database."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    mfa_enabled: bool = False
    email_verified: bool = False
    last_login_at: Optional[datetime] = None
    
<<<<<<< HEAD
    model_config = ConfigDict(from_attributes=True)
=======
    class Config:
        from_attributes = True
>>>>>>> 7e0a2fe (Saving local changes before pulling)

class UserResponse(UserBase):
    """Schema for user data returned by the API."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    mfa_enabled: bool = False
    email_verified: bool = False
    last_login_at: Optional[datetime] = None
    
<<<<<<< HEAD
    model_config = ConfigDict(from_attributes=True)
=======
    class Config:
        from_attributes = True
>>>>>>> 7e0a2fe (Saving local changes before pulling)

class UserList(BaseModel):
    """Schema for a list of users."""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    
<<<<<<< HEAD
    model_config = ConfigDict(from_attributes=True)
=======
    class Config:
        from_attributes = True
>>>>>>> 7e0a2fe (Saving local changes before pulling)

class Token(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    mfa_required: bool = False
    mfa_verified: bool = False
    session_id: Optional[str] = None

class TokenData(BaseModel):
    """Schema for token data."""
    sub: str
    id: Optional[int] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None
    mfa_verified: Optional[bool] = None
    device_token: Optional[str] = None
    session_id: Optional[str] = None

class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str
    remember_me: Optional[bool] = False
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str
    expires_in: int
    user_id: int
    username: str
    role: str
    mfa_required: bool = False
    session_id: Optional[str] = None

class MfaLoginRequest(BaseModel):
    """Schema for MFA login request."""
    user_id: int
    mfa_code: str = Field(..., min_length=6, max_length=6)
    remember_device: Optional[bool] = False

class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr

class PasswordChange(BaseModel):
    """Schema for password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v, info):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class PasswordResetConfirm(BaseModel):
    """Schema for confirming a password reset."""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v, info):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class TwoFactorSetup(BaseModel):
    """Schema for setting up two-factor authentication."""
    enable: bool = True

class TwoFactorSetupResponse(BaseModel):
    """Schema for two-factor authentication setup response."""
    secret: str
    uri: str
    qr_code: str

class TwoFactorVerify(BaseModel):
    """Schema for verifying two-factor authentication."""
    code: str = Field(..., min_length=6, max_length=6)
    remember_device: Optional[bool] = False

class TwoFactorVerifyResponse(BaseModel):
    """Schema for two-factor authentication verification response."""
    success: bool
    device_token: Optional[str] = None

class TwoFactorDisable(BaseModel):
    """Schema for disabling two-factor authentication."""
    password: str

class RefreshToken(BaseModel):
    """Schema for refreshing an authentication token."""
    refresh_token: str

class AuditLogBase(BaseModel):
    """Base schema for audit logs."""
    event_type: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    severity: str = "info"
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    """Schema for creating audit logs."""
    details: Optional[Dict[str, Any]] = None

class AuditLog(AuditLogBase):
    """Schema for audit log responses."""
    id: int
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
<<<<<<< HEAD
    
    model_config = ConfigDict(from_attributes=True)
=======

    class Config:
        from_attributes = True
>>>>>>> 7e0a2fe (Saving local changes before pulling)

class AuditLogList(BaseModel):
    """Schema for paginated audit log responses."""
    logs: List[AuditLog]
    total: int
    page: int
    size: int

class SessionInfo(BaseModel):
    """Session information schema."""
    session_id: str
    device_info: str
    ip_address: Optional[str] = None
    created_at: datetime
    last_active_at: datetime
    is_current: bool
<<<<<<< HEAD
    
    model_config = ConfigDict(from_attributes=True)
=======

    class Config:
        from_attributes = True
>>>>>>> 7e0a2fe (Saving local changes before pulling)

class SessionList(BaseModel):
    """List of sessions schema."""
    sessions: List[SessionInfo]
    total: int

class SessionTerminate(BaseModel):
    """Schema for terminating sessions."""
    session_id: Optional[str] = None
    terminate_all_except_current: bool = False

class AccountStatus(BaseModel):
    """Schema for account status information."""
    user_id: int
    username: str
    email: str
    email_verified: bool
    mfa_enabled: bool
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    active_sessions_count: int
    account_created: datetime

class EmailVerification(BaseModel):
    """Schema for email verification."""
    token: str

class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str
