"""
Authentication services for the ISP Management Platform.

This module implements the core authentication services as defined in the
authentication_workflow.md documentation.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List, Tuple
import os
import secrets
import uuid
import pyotp
import qrcode
from io import BytesIO
import base64
import json
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status, Depends, Request
from jose import jwt, JWTError
from passlib.context import CryptContext
from redis import Redis
from pydantic import ValidationError

from backend_core.models import User
from backend_core.database import get_db
from backend_core.audit_log import AuditLogService
# Use absolute imports to avoid circular references
from modules.auth.schemas import UserCreate, UserUpdate, TokenData

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-stored-in-env")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "your-refresh-secret-key-stored-in-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "24"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MFA_REMEMBER_DEVICE_DAYS = int(os.getenv("MFA_REMEMBER_DEVICE_DAYS", "30"))
ACCOUNT_LOCKOUT_ATTEMPTS = int(os.getenv("ACCOUNT_LOCKOUT_ATTEMPTS", "5"))
ACCOUNT_LOCKOUT_MINUTES = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for token blacklisting and rate limiting
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

class AuthService:
    """Service for handling authentication operations."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate a password hash."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a new JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str, secret_key: str = SECRET_KEY) -> Dict[str, Any]:
        """Decode a JWT token."""
        try:
            payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def blacklist_token(token: str, expires_in: int) -> None:
        """Add a token to the blacklist in Redis."""
        redis_client.setex(f"blacklisted_token:{token}", expires_in, "1")
    
    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        """Check if a token is blacklisted."""
        return redis_client.exists(f"blacklisted_token:{token}") == 1
    
    @staticmethod
    def create_password_reset_token(email: str) -> str:
        """Create a password reset token."""
        expire = datetime.utcnow() + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        token_data = {
            "sub": email,
            "exp": expire,
            "type": "password_reset"
        }
        return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_password_reset_token(token: str) -> str:
        """Verify a password reset token and return the email."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "password_reset":
                raise HTTPException(status_code=400, detail="Invalid token type")
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(status_code=400, detail="Invalid token")
            return email
        except JWTError:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate a new TOTP secret for 2FA."""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_totp_uri(secret: str, username: str) -> str:
        """Generate a TOTP URI for QR code generation."""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name="ISP Management Platform"
        )
    
    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """Generate a QR code image as a base64 encoded string."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """Verify a TOTP code."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    
    @staticmethod
    def rate_limit_login_attempts(username: str, max_attempts: int = 5, window_seconds: int = 300) -> bool:
        """
        Rate limit login attempts for a username.
        Returns True if the request should be blocked, False otherwise.
        """
        key = f"login_attempts:{username}"
        attempts = redis_client.incr(key)
        
        # Set expiry on first attempt
        if attempts == 1:
            redis_client.expire(key, window_seconds)
        
        return attempts > max_attempts
    
    @staticmethod
    def clear_login_attempts(username: str) -> None:
        """Clear login attempts for a username after successful login."""
        redis_client.delete(f"login_attempts:{username}")
    
    @staticmethod
    def generate_uuid() -> str:
        """Generate a random UUID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def store_mfa_secret(user_id: int, secret: str) -> None:
        """Store a MFA secret for a user."""
        redis_client.set(f"mfa_secret:{user_id}", secret)
    
    @staticmethod
    def get_mfa_secret(user_id: int) -> Optional[str]:
        """Get the MFA secret for a user."""
        return redis_client.get(f"mfa_secret:{user_id}")
    
    @staticmethod
    def delete_mfa_secret(user_id: int) -> None:
        """Delete the MFA secret for a user."""
        redis_client.delete(f"mfa_secret:{user_id}")
    
    @staticmethod
    def store_mfa_device_token(user_id: int, device_token: str) -> None:
        """Store a MFA device token for a user."""
        redis_client.setex(
            f"mfa_device:{user_id}:{device_token}",
            MFA_REMEMBER_DEVICE_DAYS * 24 * 60 * 60,
            "1"
        )
    
    @staticmethod
    def verify_mfa_device_token(user_id: int, device_token: str) -> bool:
        """Verify a MFA device token for a user."""
        return redis_client.exists(f"mfa_device:{user_id}:{device_token}") == 1
    
    @staticmethod
    def generate_mfa_device_token() -> str:
        """Generate a new MFA device token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def lock_account(user_id: int) -> None:
        """Lock a user account due to too many failed login attempts."""
        redis_client.setex(
            f"account_locked:{user_id}",
            ACCOUNT_LOCKOUT_MINUTES * 60,
            "1"
        )
    
    @staticmethod
    def is_account_locked(user_id: int) -> bool:
        """Check if a user account is locked."""
        return redis_client.exists(f"account_locked:{user_id}") == 1
    
    @staticmethod
    def unlock_account(user_id: int) -> None:
        """Unlock a user account."""
        redis_client.delete(f"account_locked:{user_id}")
    
    @staticmethod
    def increment_failed_login_attempts(user_id: int) -> int:
        """
        Increment the failed login attempts for a user.
        Returns the current number of failed attempts.
        """
        key = f"failed_login:{user_id}"
        attempts = redis_client.incr(key)
        
        # Set expiry on first attempt
        if attempts == 1:
            redis_client.expire(key, ACCOUNT_LOCKOUT_MINUTES * 60)
        
        # Lock account if too many attempts
        if attempts >= ACCOUNT_LOCKOUT_ATTEMPTS:
            AuthService.lock_account(user_id)
        
        return attempts
    
    @staticmethod
    def reset_failed_login_attempts(user_id: int) -> None:
        """Reset the failed login attempts for a user."""
        redis_client.delete(f"failed_login:{user_id}")
        
    @staticmethod
    def create_sso_state_token() -> str:
        """Create a state token for OAuth2 SSO flow."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def store_sso_state(state: str, redirect_uri: str) -> None:
        """Store a state token for OAuth2 SSO flow."""
        redis_client.setex(f"sso_state:{state}", 600, redirect_uri)  # 10 minutes expiry
    
    @staticmethod
    def verify_sso_state(state: str) -> Optional[str]:
        """
        Verify a state token for OAuth2 SSO flow.
        Returns the redirect URI if valid, None otherwise.
        """
        redirect_uri = redis_client.get(f"sso_state:{state}")
        if redirect_uri:
            redis_client.delete(f"sso_state:{state}")
        return redirect_uri
    
    # Session Management Methods
    @staticmethod
    def create_session(user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: ID of the user
            ip_address: IP address of the user
            user_agent: User agent string
            
        Returns:
            Session ID
        """
        session_id = AuthService.generate_uuid()
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        # Store session in Redis
        redis_client.setex(
            f"session:{session_id}",
            int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")) * 60,
            json.dumps(session_data)
        )
        
        # Store session ID in user's sessions list
        redis_client.sadd(f"user_sessions:{user_id}", session_id)
        
        return session_id
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data if found, None otherwise
        """
        session_data = redis_client.get(f"session:{session_id}")
        if not session_data:
            return None
        
        try:
            return json.loads(session_data)
        except json.JSONDecodeError:
            return None
    
    @staticmethod
    def update_session_activity(session_id: str) -> bool:
        """
        Update the last activity timestamp for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        session_data = AuthService.get_session(session_id)
        if not session_data:
            return False
        
        session_data["last_activity"] = datetime.utcnow().isoformat()
        
        # Update session in Redis
        redis_client.setex(
            f"session:{session_id}",
            int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")) * 60,
            json.dumps(session_data)
        )
        
        return True
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        session_data = AuthService.get_session(session_id)
        if not session_data:
            return False
        
        user_id = session_data.get("user_id")
        if user_id:
            # Remove session ID from user's sessions list
            redis_client.srem(f"user_sessions:{user_id}", session_id)
        
        # Delete session from Redis
        redis_client.delete(f"session:{session_id}")
        
        return True
    
    @staticmethod
    def get_user_sessions(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session data
        """
        session_ids = redis_client.smembers(f"user_sessions:{user_id}")
        sessions = []
        
        for session_id in session_ids:
            session_data = AuthService.get_session(session_id)
            if session_data:
                session_data["session_id"] = session_id
                sessions.append(session_data)
        
        return sessions
    
    @staticmethod
    def delete_user_sessions(user_id: int, exclude_session_id: Optional[str] = None) -> int:
        """
        Delete all sessions for a user, optionally excluding a specific session.
        
        Args:
            user_id: User ID
            exclude_session_id: Session ID to exclude from deletion
            
        Returns:
            Number of sessions deleted
        """
        session_ids = redis_client.smembers(f"user_sessions:{user_id}")
        count = 0
        
        for session_id in session_ids:
            if exclude_session_id and session_id == exclude_session_id:
                continue
            
            if AuthService.delete_session(session_id):
                count += 1
        
        return count
    
    @staticmethod
    def is_session_valid(session_id: str) -> bool:
        """
        Check if a session is valid.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if valid, False otherwise
        """
        return AuthService.get_session(session_id) is not None
    
    @staticmethod
    def get_user_id_from_session(session_id: str) -> Optional[int]:
        """
        Get the user ID associated with a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            User ID if found, None otherwise
        """
        session_data = AuthService.get_session(session_id)
        if not session_data:
            return None
        
        return session_data.get("user_id")
    
    @classmethod
    def authenticate_user(cls, db: Session, username: str, password: str, ip_address: Optional[str] = None) -> Tuple[Optional[User], str]:
        """
        Authenticate a user by username/email and password.
        
        Args:
            db: Database session
            username: Username or email
            password: Plain password
            ip_address: IP address of the user
            
        Returns:
            Tuple of (User, status) where status is one of:
            - "success": Authentication successful
            - "invalid_credentials": Invalid username or password
            - "account_locked": Account is locked due to too many failed attempts
            - "account_inactive": Account is inactive
            - "requires_mfa": Authentication requires MFA
        """
        user = db.query(User).filter(
            or_(User.username == username, User.email == username)
        ).first()
        
        # Log the authentication attempt
        log_details = {"username": username, "ip_address": ip_address}
        
        if not user:
            # Log failed login attempt with invalid username
            AuditLogService.log_auth_event(
                action="login",
                status="failure",
                username=username,
                ip_address=ip_address,
                details={"reason": "invalid_username"},
                severity="warning"
            )
            return None, "invalid_credentials"
        
        # Check if account is locked
        if cls.is_account_locked(user.id):
            AuditLogService.log_auth_event(
                action="login",
                status="failure",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={"reason": "account_locked"},
                severity="warning"
            )
            return user, "account_locked"
        
        # Check if account is active
        if not user.is_active:
            AuditLogService.log_auth_event(
                action="login",
                status="failure",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={"reason": "account_inactive"},
                severity="warning"
            )
            return user, "account_inactive"
        
        # Verify password
        if not cls.verify_password(password, user.hashed_password):
            # Increment failed login attempts
            attempts = cls.increment_failed_login_attempts(user.id)
            
            AuditLogService.log_auth_event(
                action="login",
                status="failure",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={
                    "reason": "invalid_password",
                    "attempts": attempts,
                    "max_attempts": ACCOUNT_LOCKOUT_ATTEMPTS
                },
                severity="warning"
            )
            
            # Check if account is now locked
            if attempts >= ACCOUNT_LOCKOUT_ATTEMPTS:
                return user, "account_locked"
            
            return user, "invalid_credentials"
        
        # Reset failed login attempts
        cls.reset_failed_login_attempts(user.id)
        
        # Check if MFA is enabled
        if user.mfa_enabled:
            AuditLogService.log_auth_event(
                action="login_first_factor",
                status="success",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={"requires_mfa": True},
                severity="info"
            )
            return user, "requires_mfa"
        
        # Log successful login
        AuditLogService.log_auth_event(
            action="login",
            status="success",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            severity="info"
        )
        
        return user, "success"
    
    @classmethod
    def verify_mfa(cls, db: Session, user_id: int, mfa_code: str, ip_address: Optional[str] = None, remember_device: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Verify a MFA code for a user.
        
        Args:
            db: Database session
            user_id: User ID
            mfa_code: MFA code to verify
            ip_address: IP address of the user
            remember_device: Whether to remember the device
            
        Returns:
            Tuple of (success, device_token) where device_token is provided if remember_device is True
        """
        user = cls.get_user_by_id(db, user_id)
        if not user or not user.mfa_enabled:
            AuditLogService.log_auth_event(
                action="mfa_verify",
                status="failure",
                user_id=user_id,
                ip_address=ip_address,
                details={"reason": "mfa_not_enabled"},
                severity="warning"
            )
            return False, None
        
        # Verify MFA code
        if not cls.verify_totp(user.mfa_secret, mfa_code):
            AuditLogService.log_auth_event(
                action="mfa_verify",
                status="failure",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={"reason": "invalid_code"},
                severity="warning"
            )
            return False, None
        
        # Generate device token if requested
        device_token = None
        if remember_device:
            device_token = cls.generate_mfa_device_token()
            cls.store_mfa_device_token(user.id, device_token)
        
        AuditLogService.log_auth_event(
            action="mfa_verify",
            status="success",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            details={"remember_device": remember_device},
            severity="info"
        )
        
        return True, device_token
    
    @classmethod
    def setup_mfa(cls, db: Session, user_id: int) -> Dict[str, str]:
        """
        Set up MFA for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary containing MFA setup information
        """
        user = cls.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate MFA secret
        secret = cls.generate_totp_secret()
        
        # Generate TOTP URI
        uri = cls.generate_totp_uri(secret, user.username)
        
        # Generate QR code
        qr_code = cls.generate_qr_code(uri)
        
        # Store MFA secret temporarily
        cls.store_mfa_secret(user.id, secret)
        
        AuditLogService.log_auth_event(
            action="mfa_setup_initiated",
            status="success",
            user_id=user.id,
            username=user.username,
            severity="info"
        )
        
        return {
            "secret": secret,
            "uri": uri,
            "qr_code": qr_code
        }
    
    @classmethod
    def confirm_mfa_setup(cls, db: Session, user_id: int, mfa_code: str) -> bool:
        """
        Confirm MFA setup for a user.
        
        Args:
            db: Database session
            user_id: User ID
            mfa_code: MFA code to verify
            
        Returns:
            True if successful, False otherwise
        """
        user = cls.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get MFA secret
        secret = cls.get_mfa_secret(user.id)
        if not secret:
            AuditLogService.log_auth_event(
                action="mfa_setup_confirm",
                status="failure",
                user_id=user.id,
                username=user.username,
                details={"reason": "no_secret_found"},
                severity="warning"
            )
            raise HTTPException(status_code=400, detail="MFA setup not initiated")
        
        # Verify MFA code
        if not cls.verify_totp(secret, mfa_code):
            AuditLogService.log_auth_event(
                action="mfa_setup_confirm",
                status="failure",
                user_id=user.id,
                username=user.username,
                details={"reason": "invalid_code"},
                severity="warning"
            )
            return False
        
        # Update user with MFA secret
        user.mfa_enabled = True
        user.mfa_secret = secret
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Delete temporary MFA secret
        cls.delete_mfa_secret(user.id)
        
        AuditLogService.log_auth_event(
            action="mfa_setup_confirm",
            status="success",
            user_id=user.id,
            username=user.username,
            severity="info"
        )
        
        return True
    
    @classmethod
    def disable_mfa(cls, db: Session, user_id: int, password: str) -> bool:
        """
        Disable MFA for a user.
        
        Args:
            db: Database session
            user_id: User ID
            password: User's password for verification
            
        Returns:
            True if successful, False otherwise
        """
        user = cls.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify password
        if not cls.verify_password(password, user.hashed_password):
            AuditLogService.log_auth_event(
                action="mfa_disable",
                status="failure",
                user_id=user.id,
                username=user.username,
                details={"reason": "invalid_password"},
                severity="warning"
            )
            raise HTTPException(status_code=400, detail="Incorrect password")
        
        # Disable MFA
        user.mfa_enabled = False
        user.mfa_secret = None
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        AuditLogService.log_auth_event(
            action="mfa_disable",
            status="success",
            user_id=user.id,
            username=user.username,
            severity="info"
        )
        
        return True
    
    @classmethod
    def login_with_token(cls, db: Session, token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Tuple[Optional[User], Optional[str], str]:
        """
        Authenticate a user using a JWT token.
        
        Args:
            db: Database session
            token: JWT token
            ip_address: IP address of the user
            user_agent: User agent string
            
        Returns:
            Tuple of (User, session_id, status) where status is one of:
            - "success": Authentication successful
            - "invalid_token": Invalid or expired token
            - "blacklisted_token": Token is blacklisted
            - "account_inactive": Account is inactive
            - "requires_mfa": Authentication requires MFA
        """
        # Check if token is blacklisted
        if cls.is_token_blacklisted(token):
            AuditLogService.log_auth_event(
                action="token_login",
                status="failure",
                ip_address=ip_address,
                details={"reason": "blacklisted_token"},
                severity="warning"
            )
            return None, None, "blacklisted_token"
        
        try:
            # Decode token
            payload = cls.decode_token(token)
            user_id = int(payload.get("sub"))
            
            # Get user
            user = cls.get_user_by_id(db, user_id)
            if not user:
                AuditLogService.log_auth_event(
                    action="token_login",
                    status="failure",
                    ip_address=ip_address,
                    details={"reason": "user_not_found", "user_id": user_id},
                    severity="warning"
                )
                return None, None, "invalid_token"
            
            # Check if account is active
            if not user.is_active:
                AuditLogService.log_auth_event(
                    action="token_login",
                    status="failure",
                    user_id=user.id,
                    username=user.username,
                    ip_address=ip_address,
                    details={"reason": "account_inactive"},
                    severity="warning"
                )
                return user, None, "account_inactive"
            
            # Check if MFA is required
            mfa_verified = payload.get("mfa_verified", False)
            if user.mfa_enabled and not mfa_verified:
                # Check if device is remembered
                device_token = payload.get("device_token")
                if device_token and cls.verify_mfa_device_token(user.id, device_token):
                    # Device is remembered, no MFA required
                    pass
                else:
                    AuditLogService.log_auth_event(
                        action="token_login",
                        status="partial",
                        user_id=user.id,
                        username=user.username,
                        ip_address=ip_address,
                        details={"reason": "requires_mfa"},
                        severity="info"
                    )
                    return user, None, "requires_mfa"
            
            # Create session
            session_id = cls.create_session(user.id, ip_address, user_agent)
            
            AuditLogService.log_auth_event(
                action="token_login",
                status="success",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                details={"session_id": session_id},
                severity="info"
            )
            
            return user, session_id, "success"
            
        except (JWTError, ValidationError):
            AuditLogService.log_auth_event(
                action="token_login",
                status="failure",
                ip_address=ip_address,
                details={"reason": "invalid_token"},
                severity="warning"
            )
            return None, None, "invalid_token"
    
    @classmethod
    def get_user_by_username(cls, db: Session, username: str) -> Optional[User]:
        """Get a user by username."""
        return db.query(User).filter(User.username == username).first()
    
    @classmethod
    def get_user_by_email(cls, db: Session, email: str) -> Optional[User]:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()
    
    @classmethod
    def get_user_by_id(cls, db: Session, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @classmethod
    def create_user(cls, db: Session, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            or_(User.username == user_data.username, User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(status_code=400, detail="Username already registered")
            else:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = cls.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role,
            is_active=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @classmethod
    def update_user(cls, db: Session, user_id: int, user_data: UserUpdate) -> User:
        """Update an existing user."""
        user = cls.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if username is being updated and already exists
        if user_data.username and user_data.username != user.username:
            existing_user = cls.get_user_by_username(db, user_data.username)
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already exists")
        
        # Check if email is being updated and already exists
        if user_data.email and user_data.email != user.email:
            existing_user = cls.get_user_by_email(db, user_data.email)
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already exists")
        
        # Update user fields
        if user_data.username:
            user.username = user_data.username
        if user_data.email:
            user.email = user_data.email
        if user_data.role:
            user.role = user_data.role
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @classmethod
    def change_password(cls, db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        """Change a user's password."""
        user = cls.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify current password
        if not cls.verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")
        
        # Update password
        user.hashed_password = cls.get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return True
    
    @classmethod
    def reset_password(cls, db: Session, email: str, new_password: str) -> bool:
        """Reset a user's password using email."""
        user = cls.get_user_by_email(db, email)
        if not user:
            # Don't reveal that the email doesn't exist
            return False
        
        # Update password
        user.hashed_password = cls.get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return True
    
    @classmethod
    def get_users(cls, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get a list of users."""
        return db.query(User).offset(skip).limit(limit).all()
    
    @classmethod
    def count_users(cls, db: Session) -> int:
        """Count the total number of users."""
        return db.query(User).count()
    
    @classmethod
    def deactivate_user(cls, db: Session, user_id: int) -> User:
        """Deactivate a user."""
        user = cls.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @classmethod
    def activate_user(cls, db: Session, user_id: int) -> User:
        """Activate a user."""
        user = cls.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return user
