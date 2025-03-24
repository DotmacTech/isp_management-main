from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid
import os

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
import redis

# Import the shared models
from backend_core.auth_models import Token, TokenData, UserSession, User, MFADeviceToken

# Import the new modules
from backend_core.mfa import MFAManager
from backend_core.user_session import SessionManager

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-stored-in-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
MFA_REMEMBER_DEVICE_DAYS = int(os.getenv("MFA_REMEMBER_DEVICE_DAYS", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Redis client for token blacklist and session management
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class AuthService:
    """Service for handling authentication and authorization operations."""
    
    # Token blacklist (in-memory for now, should be moved to Redis in production)
    _token_blacklist = set()
    
    @classmethod
    def get_password_hash(cls, password: str) -> str:
        """
        Hash a password for storing.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches hash, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @classmethod
    def authenticate_user(cls, db: Session, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user by username/email and password.
        
        Args:
            db: Database session
            username: Username or email
            password: Password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        from backend_core.models import User
        from sqlalchemy import or_
        
        # Find user by username or email
        user = db.query(User).filter(
            or_(User.username == username, User.email == username)
        ).first()
        
        if not user:
            return None
            
        # Check if account is locked
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            return None
            
        # Verify password
        if not cls.verify_password(password, user.hashed_password):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= 5:
                user.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
                
            db.commit()
            return None
            
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        db.commit()
        
        return user
    
    @classmethod
    def create_access_token(cls, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Data to encode in the token
            expires_delta: Token expiration time
            
        Returns:
            JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @classmethod
    def blacklist_token(cls, token: str) -> None:
        """
        Add a token to the blacklist.
        
        Args:
            token: JWT token
        """
        try:
            # Add to Redis with expiration
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            exp = datetime.fromtimestamp(payload["exp"])
            ttl = (exp - datetime.utcnow()).total_seconds()
            if ttl > 0:
                redis_client.set(f"blacklist:{token}", "1", ex=int(ttl))
        except JWTError:
            # If token is invalid, add to in-memory blacklist
            cls._token_blacklist.add(token)
    
    @classmethod
    def is_token_blacklisted(cls, token: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            token: JWT token
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            # Check in Redis
            return bool(redis_client.exists(f"blacklist:{token}"))
        except Exception:
            # Fallback to in-memory if Redis is unavailable
            return token in cls._token_blacklist
    
    # MFA methods delegated to MFAManager
    @classmethod
    def setup_mfa(cls, db: Session, user_id: int) -> Dict[str, str]:
        """
        Set up MFA for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary containing secret and QR code URI
        """
        return MFAManager.setup_mfa(db, user_id)
    
    @classmethod
    def verify_mfa_setup(cls, db: Session, user_id: int, code: str) -> bool:
        """
        Verify MFA setup with a TOTP code.
        
        Args:
            db: Database session
            user_id: User ID
            code: TOTP code
            
        Returns:
            True if verification successful, False otherwise
        """
        return MFAManager.verify_mfa_setup(db, user_id, code)
    
    @classmethod
    def verify_mfa_code(cls, db: Session, user_id: int, code: str) -> bool:
        """
        Verify a TOTP code during login.
        
        Args:
            db: Database session
            user_id: User ID
            code: TOTP code
            
        Returns:
            True if verification successful, False otherwise
        """
        return MFAManager.verify_mfa_code(db, user_id, code)
    
    @classmethod
    def create_mfa_device_token(cls, db: Session, user_id: int) -> str:
        """
        Create a device token for MFA remember device feature.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Device token
        """
        return MFAManager.create_mfa_device_token(db, user_id)
    
    @classmethod
    def verify_mfa_device_token(cls, db: Session, user_id: int, token: str) -> bool:
        """
        Verify a device token for MFA remember device feature.
        
        Args:
            db: Database session
            user_id: User ID
            token: Device token
            
        Returns:
            True if verification successful, False otherwise
        """
        return MFAManager.verify_mfa_device_token(db, user_id, token)
    
    # Session methods delegated to SessionManager
    @classmethod
    def create_user_session(cls, db: Session, user_id: int, request: Request, access_token: str, refresh_token: str = None) -> UserSession:
        """
        Create a new user session.
        
        Args:
            db: Database session
            user_id: User ID
            request: Request object
            access_token: JWT access token
            refresh_token: JWT refresh token (optional)
            
        Returns:
            Created UserSession object
        """
        return SessionManager.create_session(db, user_id, request, access_token, refresh_token)
    
    @classmethod
    def get_user_sessions(cls, db: Session, user_id: int) -> List[UserSession]:
        """
        Get all sessions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of UserSession objects
        """
        return SessionManager.get_user_sessions(db, user_id)
    
    @classmethod
    def terminate_user_session(cls, db: Session, session_id: str, reason: str = "User logout") -> bool:
        """
        Terminate a user session.
        
        Args:
            db: Database session
            session_id: Session ID
            reason: Reason for termination
            
        Returns:
            True if session was terminated, False otherwise
        """
        return SessionManager.terminate_user_session(db, session_id, reason)
    
    @classmethod
    def terminate_all_user_sessions_except(cls, db: Session, user_id: int, current_session_id: Optional[str] = None) -> int:
        """
        Terminate all sessions for a user except the current one.
        
        Args:
            db: Database session
            user_id: User ID
            current_session_id: Current session ID to preserve
            
        Returns:
            Number of terminated sessions
        """
        return SessionManager.terminate_all_user_sessions_except(db, user_id, current_session_id)
    
    @classmethod
    def update_session_activity(cls, db: Session, session_id: str) -> bool:
        """
        Update the last activity timestamp for a session.
        
        Args:
            db: Database session
            session_id: Session ID
            
        Returns:
            True if session was updated, False otherwise
        """
        return SessionManager.update_session_activity(db, session_id)
    
    @classmethod
    def get_session_by_id(cls, db: Session, session_id: str, user_id: Optional[int] = None) -> Optional[UserSession]:
        """
        Get a session by ID.
        
        Args:
            db: Database session
            session_id: Session ID
            user_id: Optional user ID for additional verification
            
        Returns:
            UserSession object if found, None otherwise
        """
        return SessionManager.get_session_by_id(db, session_id, user_id)
    
    @classmethod
    def cleanup_inactive_sessions(cls, db: Session, days: int = 30) -> int:
        """
        Clean up inactive sessions older than the specified number of days.
        
        Args:
            db: Database session
            days: Number of days to keep inactive sessions
            
        Returns:
            Number of sessions deleted
        """
        return SessionManager.cleanup_inactive_sessions(db, days)
    
    @classmethod
    def blacklist_refresh_token(cls, token: str, expires_delta: timedelta) -> bool:
        """
        Add a refresh token to the blacklist.
        
        Args:
            token: Refresh token
            expires_delta: Time until token expiration
            
        Returns:
            True if token was blacklisted, False otherwise
        """
        return SessionManager.blacklist_refresh_token(token, expires_delta)
    
    @classmethod
    def is_refresh_token_blacklisted(cls, token: str) -> bool:
        """
        Check if a refresh token is blacklisted.
        
        Args:
            token: Refresh token
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        return SessionManager.is_refresh_token_blacklisted(token)
    
    @classmethod
    def decode_token(cls, token: str) -> Dict[str, Any]:
        """
        Decode a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Decoded token payload
        """
        try:
            # Check if token is blacklisted
            if token in cls._token_blacklist:
                raise JWTError("Token has been revoked")
                
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @classmethod
    def update_last_login(cls, db: Session, user: User, ip_address: str) -> None:
        """
        Update the last login information for a user.
        
        Args:
            db: Database session
            user: User object
            ip_address: IP address
        """
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.failed_login_attempts = 0  # Reset failed login attempts
        db.commit()
    
    @classmethod
    def verify_email(cls, db: Session, token: str) -> Optional[User]:
        """
        Verify a user's email using the verification token.
        
        Args:
            db: Database session
            token: Email verification token
            
        Returns:
            User object if verification successful, None otherwise
        """
        from backend_core.models import User
        
        user = db.query(User).filter(
            User.email_verification_token == token,
            User.email_verification_token_expires_at > datetime.utcnow()
        ).first()
        
        if not user:
            return None
            
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires_at = None
        db.commit()
        
        return user
    
    @classmethod
    def set_email_verification_token(cls, db: Session, user: User, token: str) -> None:
        """
        Set email verification token for a user.
        
        Args:
            db: Database session
            user: User object
            token: Verification token
        """
        user.email_verification_token = token
        user.email_verification_token_expires_at = datetime.utcnow() + timedelta(days=1)
        db.commit()
        
    @classmethod
    def verify_mfa_code(cls, mfa_secret: str, code: str) -> bool:
        """
        Verify a TOTP MFA code.
        
        Args:
            mfa_secret: MFA secret key
            code: TOTP code to verify
            
        Returns:
            True if code is valid, False otherwise
        """
        import pyotp
        
        if not mfa_secret or not code:
            return False
            
        totp = pyotp.TOTP(mfa_secret)
        return totp.verify(code)
    
    @classmethod
    def generate_mfa_secret(cls) -> str:
        """
        Generate a new MFA secret key.
        
        Returns:
            MFA secret key
        """
        import pyotp
        return pyotp.random_base32()
    
    @classmethod
    def get_mfa_provisioning_uri(cls, username: str, mfa_secret: str, issuer: str = "ISP Management") -> str:
        """
        Get the provisioning URI for MFA setup.
        
        Args:
            username: Username
            mfa_secret: MFA secret key
            issuer: Issuer name
            
        Returns:
            Provisioning URI for QR code generation
        """
        import pyotp
        
        totp = pyotp.TOTP(mfa_secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)
    
    @classmethod
    def enable_mfa(cls, db: Session, user: User, mfa_secret: str) -> None:
        """
        Enable MFA for a user.
        
        Args:
            db: Database session
            user: User object
            mfa_secret: MFA secret key
        """
        user.mfa_enabled = True
        user.mfa_secret = mfa_secret
        db.commit()
    
    @classmethod
    def disable_mfa(cls, db: Session, user: User) -> None:
        """
        Disable MFA for a user.
        
        Args:
            db: Database session
            user: User object
        """
        user.mfa_enabled = False
        user.mfa_secret = None
        
        # Delete all device tokens
        from backend_core.models import MFADeviceToken
        db.query(MFADeviceToken).filter(MFADeviceToken.user_id == user.id).delete()
        
        db.commit()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # Extract id and role from the token payload
        user_id = payload.get("id")
        role = payload.get("role")
        token_data = TokenData(sub=username, id=user_id, role=role)
    except JWTError:
        raise credentials_exception
    # Here you would typically get the user from your database
    # user = get_user(username=token_data.username)
    # if user is None:
    #     raise credentials_exception
    # return user
    return token_data

async def get_current_active_user(current_user = Depends(get_current_user)):
    # Here you would check if the user is active
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_user_role(current_user = Depends(get_current_user)):
    """
    Get the role of the current authenticated user.
    
    This function is used for role-based access control in the application.
    It depends on the get_current_user function to first authenticate the user.
    
    Args:
        current_user: The authenticated user object from get_current_user
        
    Returns:
        str: The role of the current user (e.g., 'admin', 'user', 'reseller')
    """
    # Role information might be stored in the user model or in a separate table
    # For now, we'll extract it directly from the user object
    if hasattr(current_user, 'role'):
        return current_user.role
    
    # Default role if none is specified
    return "user"

class SessionManager:
    @classmethod
    def terminate_all_sessions_except(cls, db: Session, user_id: int, current_session_id: Optional[str] = None) -> int:
        """
        Terminate all sessions for a user except the current one.
        
        Args:
            db: Database session
            user_id: User ID
            current_session_id: Current session ID to preserve
            
        Returns:
            Number of terminated sessions
        """
        query = db.query(UserSession).filter(UserSession.user_id == user_id)
        
        if current_session_id:
            query = query.filter(UserSession.session_id != current_session_id)
            
        # Mark sessions as terminated
        sessions = query.all()
        terminated_count = 0
        
        for session in sessions:
            session.is_active = False
            session.terminated_at = datetime.utcnow()
            session.termination_reason = "user_terminated_all"
            terminated_count += 1
            
        db.commit()
        
        # Add to token blacklist
        for session in sessions:
            if session.access_token:
                AuthService.blacklist_token(session.access_token)
                
        return terminated_count
    
    @classmethod
    def count_active_sessions(cls, db: Session, user_id: int) -> int:
        """
        Count active sessions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of active sessions
        """
        return db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).count()
    
    @classmethod
    def verify_email(cls, db: Session, token: str) -> Optional[User]:
        """
        Verify a user's email using the verification token.
        
        Args:
            db: Database session
            token: Email verification token
            
        Returns:
            User object if verification successful, None otherwise
        """
        user = db.query(User).filter(
            User.email_verification_token == token,
            User.email_verification_token_expires_at > datetime.utcnow()
        ).first()
        
        if not user:
            return None
            
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires_at = None
        db.commit()
        
        return user
    
    @classmethod
    def set_email_verification_token(cls, db: Session, user: User, token: str) -> None:
        """
        Set email verification token for a user.
        
        Args:
            db: Database session
            user: User object
            token: Verification token
        """
        user.email_verification_token = token
        user.email_verification_token_expires_at = datetime.utcnow() + timedelta(days=1)
        db.commit()
        
    @classmethod
    def decode_token(cls, token: str) -> Dict[str, Any]:
        """
        Decode a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Decoded token payload
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
