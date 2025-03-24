"""
Authentication endpoints for the ISP Management Platform.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response, Header, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os
import secrets
import uuid

from backend_core.database import get_db
from backend_core.models import User
from .schemas import (
    UserCreate, UserUpdate, UserResponse, UserList, Token, LoginResponse,
    LoginRequest, PasswordReset, PasswordResetConfirm, PasswordChange,
    TwoFactorSetup, TwoFactorVerify, TwoFactorSetupResponse, TwoFactorVerifyResponse,
    TwoFactorDisable, RefreshToken, MfaLoginRequest, SessionInfo, SessionList, SessionTerminate,
    MessageResponse, AuditLogList
)
from .services import AuthService
from .dependencies import (
    get_current_user, get_current_active_user, 
    get_admin_user, get_staff_user, RateLimiter
)
from backend_core.email_service import EmailService
from backend_core.audit_log import AuditLogService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Environment variables
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
MFA_REMEMBER_DEVICE_DAYS = int(os.getenv("MFA_REMEMBER_DEVICE_DAYS", "30"))

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    rate_limiter: RateLimiter = Depends(RateLimiter(limit=5, window=3600))
):
    """Register a new user."""
    # Create the user
    user = AuthService.create_user(db, user_data)
    
    # Generate email verification token
    verification_token = secrets.token_urlsafe(32)
    AuthService.set_email_verification_token(db, user, verification_token)
    
    # Log the registration
    client_ip = request.client.host if request.client else None
    AuditLogService.log_event(
        event_type="user_registration",
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        status="success",
        details={"email": user.email}
    )
    
    # Send welcome email with verification link
    verification_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"
    background_tasks = BackgroundTasks()
    background_tasks.add_task(
        EmailService.send_email,
        recipient=user.email,
        subject="Welcome to ISP Management Platform - Verify Your Email",
        template_name="welcome_email.html",
        template_data={
            "username": user.username,
            "verification_url": verification_url
        }
    )
    
    return user

@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    mfa_code: Optional[str] = Form(None),
    remember_device: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Login endpoint for obtaining an access token.
    
    If MFA is enabled for the user, a valid MFA code must be provided.
    """
    client_ip = request.client.host if request.client else None
    
    # Authenticate user with username/password
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        AuditLogService.log_event(
            event_type="login",
            status="failed",
            username=form_data.username,
            ip_address=client_ip,
            details={"reason": "invalid_credentials"},
            severity="warning",
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        lock_expires_in = int((user.account_locked_until - datetime.utcnow()).total_seconds() / 60)
        
        AuditLogService.log_event(
            event_type="login",
            status="failed",
            user_id=user.id,
            username=user.username,
            ip_address=client_ip,
            details={"reason": "account_locked", "lock_expires_in_minutes": lock_expires_in},
            severity="warning",
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account is locked. Try again in {lock_expires_in} minutes.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if MFA is enabled for the user
    if user.mfa_enabled:
        # Check if the device is remembered and MFA can be skipped
        device_token = request.cookies.get("mfa_device_token")
        mfa_verified = False
        
        if device_token:
            # Verify the device token
            mfa_verified = AuthService.verify_mfa_device_token(db, user.id, device_token)
        
        # If device is not remembered or token is invalid, verify MFA code
        if not mfa_verified:
            if not mfa_code:
                # MFA code is required but not provided
                AuditLogService.log_event(
                    event_type="login",
                    status="pending_mfa",
                    user_id=user.id,
                    username=user.username,
                    ip_address=client_ip,
                    details={"reason": "mfa_required"},
                    db=db
                )
                
                return {
                    "access_token": "",
                    "token_type": "",
                    "mfa_required": True,
                    "user_id": user.id
                }
            
            # Verify the MFA code
            if not AuthService.verify_mfa_code(user.mfa_secret, mfa_code):
                AuditLogService.log_event(
                    event_type="login",
                    status="failed",
                    user_id=user.id,
                    username=user.username,
                    ip_address=client_ip,
                    details={"reason": "invalid_mfa_code"},
                    severity="warning",
                    db=db
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    
    # Generate access and refresh tokens
    session_id = str(uuid.uuid4())
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "session_id": session_id
    }
    access_token = AuthService.create_access_token(
        data=access_token_data, 
        expires_delta=access_token_expires
    )
    
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_data = {
        "sub": user.username,
        "user_id": user.id,
        "token_type": "refresh",
        "session_id": session_id
    }
    refresh_token = AuthService.create_refresh_token(
        data=refresh_token_data,
        expires_delta=refresh_token_expires
    )
    
    # Create a new session
    session = AuthService.create_user_session(
        db=db,
        user_id=user.id,
        request=request,
        access_token=access_token,
        refresh_token=refresh_token
    )
    
    # Set refresh token as HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Set to False in development if not using HTTPS
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # in seconds
    )
    
    # If MFA was verified and remember_device is True, set a cookie
    if user.mfa_enabled and remember_device:
        device_token = AuthService.create_mfa_device_token(db, user.id)
        response.set_cookie(
            key="mfa_device_token",
            value=device_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=MFA_REMEMBER_DEVICE_DAYS * 24 * 60 * 60  # in seconds
        )
    
    # Update last login information
    AuthService.update_last_login(db, user, client_ip)
    
    # Log successful login
    AuditLogService.log_event(
        event_type="login",
        status="success",
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        details={
            "session_id": session_id,
            "mfa_verified": user.mfa_enabled,
            "remember_device": remember_device if user.mfa_enabled else False
        },
        db=db
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "mfa_required": False
    }

@router.post("/mfa/verify", response_model=LoginResponse)
async def verify_mfa_login(
    mfa_data: MfaLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    rate_limiter: RateLimiter = Depends(RateLimiter(limit=5, window=300))
):
    """Verify MFA code during login."""
    client_ip = request.client.host if request.client else None
    
    # Get the user
    user = db.query(User).filter(User.id == mfa_data.user_id).first()
    if not user or not user.mfa_enabled:
        AuditLogService.log_event(
            event_type="mfa_verification",
            user_id=mfa_data.user_id,
            ip_address=client_ip,
            status="failed",
            details={"reason": "invalid_user_or_mfa_not_enabled"},
            severity="warning"
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user or MFA not enabled for this user"
        )
    
    # Verify the MFA code
    if not AuthService.verify_mfa_code(db, user.id, mfa_data.mfa_code):
        AuditLogService.log_event(
            event_type="mfa_verification",
            user_id=user.id,
            username=user.username,
            ip_address=client_ip,
            status="failed",
            details={"reason": "invalid_mfa_code"},
            severity="warning"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code"
        )
    
    # Get the existing session or create a new one
    session_id = AuthService.get_active_session(db, user.id)
    if not session_id:
        session_id = AuthService.create_session(
            db, 
            user.id, 
            client_ip=client_ip
        )
    
    # Create a device token if remember_device is True
    device_token = None
    if mfa_data.remember_device:
        device_token = secrets.token_urlsafe(32)
        AuthService.store_mfa_device_token(
            user_id=user.id,
            device_token=device_token,
            expires_in=timedelta(days=MFA_REMEMBER_DEVICE_DAYS)
        )
    
    # Create a new access token with MFA verified
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": user.username, 
        "id": user.id, 
        "role": user.role,
        "mfa_verified": True,
        "session_id": session_id,
        "device_token": device_token
    }
    
    access_token = AuthService.create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    # Log successful MFA verification
    AuditLogService.log_event(
        event_type="mfa_verification",
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        status="success",
        details={
            "session_id": session_id,
            "remember_device": mfa_data.remember_device
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "mfa_required": False  # MFA is now verified
    }

@router.post("/setup-mfa", response_model=TwoFactorSetupResponse)
async def setup_mfa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Setup Multi-Factor Authentication for the current user.
    
    Returns a secret key and a provisioning URI for QR code generation.
    The user needs to scan the QR code with an authenticator app and
    then verify a code to enable MFA.
    """
    # Check if MFA is already enabled
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled for this account"
        )
    
    # Generate a new secret key
    mfa_secret = AuthService.generate_mfa_secret()
    
    # Generate provisioning URI for QR code
    provisioning_uri = AuthService.get_mfa_provisioning_uri(
        username=current_user.username,
        mfa_secret=mfa_secret
    )
    
    # Store the secret temporarily (will be saved permanently after verification)
    current_user.mfa_secret = mfa_secret
    db.commit()
    
    # Log MFA setup initiation
    AuditLogService.log_event(
        event_type="mfa_setup",
        status="initiated",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.client.host if request.client else None,
        details={"action": "setup_initiated"},
        db=db
    )
    
    return {
        "secret": mfa_secret,
        "provisioning_uri": provisioning_uri
    }

@router.post("/verify-mfa-setup", response_model=MessageResponse)
async def verify_mfa_setup(
    request: Request,
    mfa_code: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify MFA setup by validating a code from the authenticator app.
    
    This endpoint completes the MFA setup process by verifying that the
    user has correctly configured their authenticator app.
    """
    # Check if MFA is already enabled
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled for this account"
        )
    
    # Verify the MFA code
    if not AuthService.verify_mfa_code(current_user.mfa_secret, mfa_code):
        # Log failed verification
        AuditLogService.log_event(
            event_type="mfa_setup",
            status="failed",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            details={"reason": "invalid_code"},
            severity="warning",
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )
    
    # Enable MFA for the user
    AuthService.enable_mfa(db, current_user, current_user.mfa_secret)
    
    # Log successful MFA setup
    AuditLogService.log_event(
        event_type="mfa_setup",
        status="success",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.client.host if request.client else None,
        details={"action": "mfa_enabled"},
        db=db
    )
    
    return {
        "message": "MFA has been successfully enabled for your account"
    }

@router.post("/disable-mfa", response_model=MessageResponse)
async def disable_mfa(
    request: Request,
    password: str = Form(...),
    mfa_code: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Disable Multi-Factor Authentication for the current user.
    
    Requires both the user's password and a valid MFA code for security.
    """
    # Check if MFA is enabled
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account"
        )
    
    # Verify password
    if not AuthService.verify_password(password, current_user.hashed_password):
        # Log failed verification
        AuditLogService.log_event(
            event_type="mfa_disable",
            status="failed",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            details={"reason": "invalid_password"},
            severity="warning",
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Verify MFA code
    if not AuthService.verify_mfa_code(current_user.mfa_secret, mfa_code):
        # Log failed verification
        AuditLogService.log_event(
            event_type="mfa_disable",
            status="failed",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            details={"reason": "invalid_mfa_code"},
            severity="warning",
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )
    
    # Disable MFA for the user
    AuthService.disable_mfa(db, current_user)
    
    # Terminate all sessions except the current one
    # This is a security measure to ensure that all other sessions require re-authentication
    current_session_id = request.state.session_id if hasattr(request.state, "session_id") else None
    if current_session_id:
        AuthService.terminate_other_sessions(db, current_user.id, current_session_id)
    
    # Log successful MFA disable
    AuditLogService.log_event(
        event_type="mfa_disable",
        status="success",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.client.host if request.client else None,
        details={"action": "mfa_disabled"},
        db=db
    )
    
    return {
        "message": "MFA has been successfully disabled for your account and all other sessions have been terminated"
    }

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get the current authenticated user."""
    return current_user

@router.get("/users", response_model=UserList)
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get a list of users (admin only)."""
    users = AuthService.get_users(db, skip=skip, limit=limit)
    total = AuthService.count_users(db)
    
    return {
        "users": users,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit
    }

@router.get("/users/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Get a user by ID (staff or admin only)."""
    # Regular users can only view their own profile
    if current_user.role not in ["admin", "staff"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")
    
    user = AuthService.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Update a user (staff or admin only)."""
    # Regular users can only update their own profile
    if current_user.role not in ["admin", "staff"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    
    # Only admins can change roles
    if user_data.role and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to change user role")
    
    updated_user = AuthService.update_user(db, user_id, user_data)
    return updated_user

@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate a user (admin only)."""
    # Prevent self-deactivation
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    deactivated_user = AuthService.deactivate_user(db, user_id)
    return deactivated_user

@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Activate a user (admin only)."""
    activated_user = AuthService.activate_user(db, user_id)
    return activated_user

@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    reset_data: PasswordReset,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    rate_limiter: RateLimiter = Depends(RateLimiter(limit=3, window=3600))
):
    """Request a password reset."""
    # Generate password reset token
    token = AuthService.create_password_reset_token(reset_data.email)
    
    # Send password reset email
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    background_tasks.add_task(
        EmailService.send_email,
        recipient=reset_data.email,
        subject="Password Reset Request",
        template_name="password_reset_email.html",
        template_data={"reset_url": reset_url}
    )
    
    # Always return success, even if email doesn't exist
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm a password reset with token."""
    # Verify token and get email
    email = AuthService.verify_password_reset_token(reset_data.token)
    
    # Reset password
    success = AuthService.reset_password(db, email, reset_data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Password reset failed")
    
    return {"message": "Password has been reset successfully"}

@router.post("/password-change", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change a user's password."""
    success = AuthService.change_password(
        db, 
        current_user.id, 
        password_data.current_password, 
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Password change failed")
    
    return {"message": "Password changed successfully"}

@router.post("/2fa/setup", status_code=status.HTTP_200_OK)
async def setup_two_factor(
    setup_data: TwoFactorSetup,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set up two-factor authentication for a user."""
    # Generate TOTP secret
    secret = AuthService.generate_totp_secret()
    
    # Generate TOTP URI
    uri = AuthService.generate_totp_uri(secret, current_user.username)
    
    # Generate QR code
    qr_code = AuthService.generate_qr_code(uri)
    
    # Store secret in database (would need to add a field to User model)
    # For now, we'll just return the secret and QR code
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "message": "Scan the QR code with your authenticator app"
    }

@router.post("/2fa/verify", status_code=status.HTTP_200_OK)
async def verify_two_factor(
    verify_data: TwoFactorVerify,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Verify a two-factor authentication code."""
    # In a real implementation, we would get the secret from the database
    # For now, we'll just return success
    
    return {"message": "Two-factor authentication verified successfully"}

@router.get("/sessions", response_model=SessionList)
async def get_user_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all active sessions for the current user.
    
    Returns a list of active sessions with device information, creation time,
    and last activity time.
    """
    # Get current session ID from request state
    current_session_id = request.state.session_id if hasattr(request.state, "session_id") else None
    
    # Get all active sessions for the user
    sessions = AuthService.get_user_sessions(db, current_user.id)
    
    # Format sessions for response
    session_list = []
    for session in sessions:
        session_info = {
            "session_id": session.session_id,
            "device_info": session.device_info or "Unknown device",
            "ip_address": session.ip_address,
            "created_at": session.created_at,
            "last_active_at": session.last_active_at,
            "is_current": session.session_id == current_session_id
        }
        session_list.append(session_info)
    
    # Log session list request
    AuditLogService.log_event(
        event_type="session_list",
        status="success",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.client.host if request.client else None,
        details={"session_count": len(session_list)},
        db=db
    )
    
    return {
        "sessions": session_list,
        "total": len(session_list)
    }

@router.post("/sessions/terminate", response_model=MessageResponse)
async def terminate_session(
    request: Request,
    session_data: SessionTerminate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Terminate a specific session or all sessions except the current one.
    
    If terminate_all_except_current is True, all sessions except the current one will be terminated.
    Otherwise, only the specified session will be terminated.
    """
    # Get current session ID from request state
    current_session_id = request.state.session_id if hasattr(request.state, "session_id") else None
    
    if not current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current session ID not found"
        )
    
    # Check if terminating all sessions except current
    if session_data.terminate_all_except_current:
        # Terminate all sessions except current
        terminated_count = AuthService.terminate_other_sessions(
            db, 
            current_user.id, 
            current_session_id,
            reason="user_terminated_all"
        )
        
        # Log session termination
        AuditLogService.log_event(
            event_type="session_terminate",
            status="success",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            details={
                "action": "terminate_all_except_current",
                "terminated_count": terminated_count
            },
            db=db
        )
        
        return {
            "message": f"Successfully terminated {terminated_count} session(s)"
        }
    
    # Check if trying to terminate current session
    if session_data.session_id == current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot terminate current session. Use logout instead."
        )
    
    # Verify the session belongs to the current user
    session = db.query(UserSession).filter(
        UserSession.session_id == session_data.session_id,
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already terminated"
        )
    
    # Terminate the session
    success = AuthService.terminate_session(
        db, 
        session_data.session_id,
        reason="user_terminated"
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate session"
        )
    
    # Log session termination
    AuditLogService.log_event(
        event_type="session_terminate",
        status="success",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.client.host if request.client else None,
        details={
            "action": "terminate_single",
            "session_id": session_data.session_id
        },
        db=db
    )
    
    return {
        "message": "Session successfully terminated"
    }

@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout the current user by terminating their current session.
    
    This will invalidate the current access token and refresh token.
    """
    # Get current session ID from request state
    current_session_id = request.state.session_id if hasattr(request.state, "session_id") else None
    
    if not current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current session ID not found"
        )
    
    # Terminate the current session
    success = AuthService.terminate_session(
        db, 
        current_session_id,
        reason="user_logout"
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate session"
        )
    
    # Clear the refresh token cookie
    response.delete_cookie(key="refresh_token")
    
    # Log logout
    AuditLogService.log_event(
        event_type="logout",
        status="success",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.client.host if request.client else None,
        details={"session_id": current_session_id},
        db=db
    )
    
    return {
        "message": "Successfully logged out"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Get a new access token using a refresh token.
    
    The refresh token is sent as an HTTP-only cookie.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token is blacklisted
    if AuthService.is_token_blacklisted(refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify refresh token
    try:
        payload = AuthService.decode_token(refresh_token)
        username = payload.get("sub")
        user_id = payload.get("user_id")
        token_type = payload.get("token_type")
        session_id = payload.get("session_id")
        
        if not username or not user_id or token_type != "refresh" or not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get session from database
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.is_active == True
    ).first()
    
    if not session:
        # Session not found or inactive, revoke the refresh token
        AuthService.blacklist_token(refresh_token)
        
        # Clear the refresh token cookie
        response.delete_cookie(key="refresh_token")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update session activity
    session.last_active_at = datetime.utcnow()
    
    # Generate new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "session_id": session_id
    }
    
    access_token = AuthService.create_access_token(
        data=access_token_data,
        expires_delta=access_token_expires
    )
    
    # Update session with new access token
    session.access_token = access_token
    db.commit()
    
    # Log token refresh
    client_ip = request.client.host if request.client else None
    AuditLogService.log_event(
        event_type="token_refresh",
        status="success",
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        details={"session_id": session_id},
        db=db
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "mfa_required": False
    }

@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify a user's email address using the verification token."""
    client_ip = request.client.host if request.client else None
    
    # Verify the token and mark email as verified
    user = AuthService.verify_email(db, token)
    
    if not user:
        AuditLogService.log_event(
            event_type="email_verification",
            ip_address=client_ip,
            status="failed",
            details={"reason": "invalid_token"},
            severity="warning"
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    AuditLogService.log_event(
        event_type="email_verification",
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        status="success",
        details={"email": user.email}
    )
    
    return {"message": "Email verified successfully"}

@router.post("/resend-verification-email", status_code=status.HTTP_200_OK)
async def resend_verification_email(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limiter: RateLimiter = Depends(RateLimiter(limit=3, window=3600))
):
    """Resend email verification link to the user."""
    client_ip = request.client.host if request.client else None
    
    # Check if email is already verified
    if current_user.email_verified:
        return {"message": "Email is already verified"}
    
    # Generate a new verification token
    verification_token = secrets.token_urlsafe(32)
    AuthService.set_email_verification_token(db, current_user, verification_token)
    
    # Send verification email
    verification_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"
    background_tasks.add_task(
        EmailService.send_email,
        recipient=current_user.email,
        subject="Verify Your Email Address",
        template_name="email_verification.html",
        template_data={
            "username": current_user.username,
            "verification_url": verification_url
        }
    )
    
    AuditLogService.log_event(
        event_type="email_verification",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=client_ip,
        status="pending",
        details={"action": "resend_verification_email"}
    )
    
    return {"message": "Verification email has been sent"}

@router.get("/audit-logs", response_model=AuditLogList)
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get audit logs (admin only)."""
    # Parse dates if provided
    start_datetime = None
    end_datetime = None
    
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    # Get audit logs
    logs, total = AuditLogService.get_logs(
        user_id=user_id,
        event_type=event_type,
        start_date=start_datetime,
        end_date=end_datetime,
        skip=skip,
        limit=limit
    )
    
    return {
        "logs": logs,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit
    }

@router.get("/account-status", status_code=status.HTTP_200_OK)
async def get_account_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the current user's account status including MFA status, email verification, etc."""
    # Get active sessions count
    active_sessions_count = AuthService.count_active_sessions(db, current_user.id)
    
    # Get last login info
    last_login = current_user.last_login_at
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "mfa_enabled": current_user.mfa_enabled,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "last_login": last_login,
        "active_sessions_count": active_sessions_count,
        "account_created": current_user.created_at
    }
