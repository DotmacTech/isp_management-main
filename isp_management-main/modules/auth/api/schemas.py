<<<<<<< HEAD
"""
Re-exports schemas from the auth module for API endpoints.
"""

# Import directly from the schemas module file 
import sys
import os
from importlib.util import spec_from_file_location, module_from_spec

# Get the absolute path to the schemas.py file
schemas_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schemas.py')

# Dynamically load the schemas.py module
spec = spec_from_file_location("schemas_module", schemas_path)
schemas_module = module_from_spec(spec)
spec.loader.exec_module(schemas_module)

# Re-export all schema classes
UserCreate = schemas_module.UserCreate
UserUpdate = schemas_module.UserUpdate
UserResponse = schemas_module.UserResponse
UserList = schemas_module.UserList
Token = schemas_module.Token
LoginResponse = schemas_module.LoginResponse
LoginRequest = schemas_module.LoginRequest
PasswordReset = schemas_module.PasswordReset
PasswordResetConfirm = schemas_module.PasswordResetConfirm
PasswordChange = schemas_module.PasswordChange
TwoFactorSetup = schemas_module.TwoFactorSetup
TwoFactorVerify = schemas_module.TwoFactorVerify
TwoFactorSetupResponse = schemas_module.TwoFactorSetupResponse
TwoFactorVerifyResponse = schemas_module.TwoFactorVerifyResponse
TwoFactorDisable = schemas_module.TwoFactorDisable
RefreshToken = schemas_module.RefreshToken
MfaLoginRequest = schemas_module.MfaLoginRequest
SessionInfo = schemas_module.SessionInfo
SessionList = schemas_module.SessionList
SessionTerminate = schemas_module.SessionTerminate
MessageResponse = schemas_module.MessageResponse
AuditLogList = schemas_module.AuditLogList
=======
from pydantic import BaseModel
from typing import List, Optional


class UserCreate(BaseModel):
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool


class UserList(BaseModel):
    users: List[UserResponse]


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordReset(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class TwoFactorSetup(BaseModel):
    email: str


class TwoFactorVerify(BaseModel):
    token: str
    email: str


class TwoFactorSetupResponse(BaseModel):
    setup_url: str


class TwoFactorVerifyResponse(BaseModel):
    success: bool


class TwoFactorDisable(BaseModel):
    email: str


class RefreshToken(BaseModel):
    refresh_token: str


class MfaLoginRequest(BaseModel):
    email: str
    mfa_code: str


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_activity: str


class SessionList(BaseModel):
    sessions: List[SessionInfo]


class SessionTerminate(BaseModel):
    session_id: str


class MessageResponse(BaseModel):
    message: str


class AuditLogList(BaseModel):
    logs: List[str]  # You can customize the log entries here based on your system.
>>>>>>> 7e0a2fe (Saving local changes before pulling)
