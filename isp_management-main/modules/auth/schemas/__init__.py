"""
Schemas for the auth module.

This package contains schemas for the auth module and follows the authentication workflow
as defined in the authentication_workflow.md documentation.
"""

# Import and export schema classes directly from the schemas.py file
import os
import sys
import importlib.util

# Import directly from the schemas.py file in the parent directory
schemas_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schemas.py')
spec = importlib.util.spec_from_file_location("auth_schemas", schemas_path)
auth_schemas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_schemas)

# Make all schema classes available directly from this module
UserBase = auth_schemas.UserBase
UserCreate = auth_schemas.UserCreate
UserUpdate = auth_schemas.UserUpdate
UserInDB = auth_schemas.UserInDB
UserResponse = auth_schemas.UserResponse
UserList = auth_schemas.UserList
Token = auth_schemas.Token
TokenData = auth_schemas.TokenData
LoginResponse = auth_schemas.LoginResponse
LoginRequest = auth_schemas.LoginRequest
PasswordReset = auth_schemas.PasswordReset
PasswordResetConfirm = auth_schemas.PasswordResetConfirm
PasswordChange = auth_schemas.PasswordChange
TwoFactorSetup = auth_schemas.TwoFactorSetup
TwoFactorVerify = auth_schemas.TwoFactorVerify
TwoFactorSetupResponse = auth_schemas.TwoFactorSetupResponse
TwoFactorVerifyResponse = auth_schemas.TwoFactorVerifyResponse
TwoFactorDisable = auth_schemas.TwoFactorDisable
RefreshToken = auth_schemas.RefreshToken
MfaLoginRequest = auth_schemas.MfaLoginRequest
SessionInfo = auth_schemas.SessionInfo
SessionList = auth_schemas.SessionList
SessionTerminate = auth_schemas.SessionTerminate
MessageResponse = auth_schemas.MessageResponse
AuditLogList = auth_schemas.AuditLogList
AccountStatus = auth_schemas.AccountStatus
AuditLog = auth_schemas.AuditLog
AuditLogCreate = auth_schemas.AuditLogCreate
AuditLogBase = auth_schemas.AuditLogBase
EmailVerification = auth_schemas.EmailVerification

__all__ = [
    'UserBase',
    'UserCreate', 
    'UserUpdate', 
    'UserInDB',
    'UserResponse', 
    'UserList', 
    'Token', 
    'TokenData', 
    'LoginResponse',
    'LoginRequest', 
    'PasswordReset', 
    'PasswordResetConfirm', 
    'PasswordChange',
    'TwoFactorSetup', 
    'TwoFactorVerify', 
    'TwoFactorSetupResponse', 
    'TwoFactorVerifyResponse',
    'TwoFactorDisable', 
    'RefreshToken', 
    'MfaLoginRequest', 
    'SessionInfo', 
    'SessionList', 
    'SessionTerminate',
    'MessageResponse', 
    'AuditLogList',
    'AccountStatus',
    'AuditLog',
    'AuditLogCreate',
    'AuditLogBase',
    'EmailVerification'
]
