"""
Authentication dependencies for the ISP Management Platform.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Union
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from redis import Redis
import os
import json
import time
from pydantic import ValidationError

from backend_core.database import get_db
from backend_core.models import User
from backend_core.rbac import RBACService, Permission
from .schemas import TokenData
from .services import AuthService

# Environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "your-refresh-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(self, limit: int, window: int):
        """
        Initialize rate limiter.
        
        Args:
            limit: Maximum number of requests allowed in the window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
    
    def __call__(self, request: Request):
        """
        Check if request is within rate limits.
        
        Args:
            request: FastAPI request object
        
        Raises:
            HTTPException: If rate limit is exceeded
        """
        client_ip = request.client.host
        key = f"ratelimit:{request.url.path}:{client_ip}"
        
        # Get current count
        current = redis_client.get(key)
        
        if current is None:
            # First request, set to 1 with expiry
            redis_client.setex(key, self.window, 1)
        elif int(current) >= self.limit:
            # Rate limit exceeded
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        else:
            # Increment count
            redis_client.incr(key)
        
        return self

class SessionManager:
    """Manage user sessions."""
    
    @staticmethod
    def create_session(user_id: int, token: str) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: ID of the user
            token: JWT token for the session
        
        Returns:
            Session ID
        """
        session_id = AuthService.generate_uuid()
        session_data = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "ip_address": None,
            "user_agent": None
        }
        
        # Store session in Redis
        redis_client.setex(
            f"session:{session_id}", 
            SESSION_TIMEOUT_MINUTES * 60, 
            json.dumps(session_data)
        )
        
        # Add session to user's sessions
        redis_client.sadd(f"user_sessions:{user_id}", session_id)
        
        return session_id
    
    @staticmethod
    def update_session_activity(session_id: str, request: Optional[Request] = None) -> bool:
        """
        Update last activity time for a session.
        
        Args:
            session_id: ID of the session
            request: FastAPI request object
        
        Returns:
            True if session was updated, False otherwise
        """
        # Get session data
        session_data_str = redis_client.get(f"session:{session_id}")
        if not session_data_str:
            return False
        
        try:
            session_data = json.loads(session_data_str)
            
            # Update last activity
            session_data["last_activity"] = datetime.utcnow().isoformat()
            
            # Update IP and user agent if request is provided
            if request:
                session_data["ip_address"] = request.client.host
                session_data["user_agent"] = request.headers.get("user-agent")
            
            # Store updated session
            redis_client.setex(
                f"session:{session_id}", 
                SESSION_TIMEOUT_MINUTES * 60, 
                json.dumps(session_data)
            )
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """
        Get session data.
        
        Args:
            session_id: ID of the session
        
        Returns:
            Session data or None if session doesn't exist
        """
        session_data_str = redis_client.get(f"session:{session_id}")
        if not session_data_str:
            return None
        
        try:
            return json.loads(session_data_str)
        except Exception:
            return None
    
    @staticmethod
    def end_session(session_id: str, user_id: Optional[int] = None) -> bool:
        """
        End a session.
        
        Args:
            session_id: ID of the session
            user_id: ID of the user (optional)
        
        Returns:
            True if session was ended, False otherwise
        """
        # Get session data if user_id is not provided
        if user_id is None:
            session_data = SessionManager.get_session(session_id)
            if not session_data:
                return False
            user_id = session_data.get("user_id")
        
        # Delete session
        redis_client.delete(f"session:{session_id}")
        
        # Remove session from user's sessions
        if user_id:
            redis_client.srem(f"user_sessions:{user_id}", session_id)
        
        return True
    
    @staticmethod
    def end_all_user_sessions(user_id: int, exclude_session_id: Optional[str] = None) -> int:
        """
        End all sessions for a user.
        
        Args:
            user_id: ID of the user
            exclude_session_id: Session ID to exclude from ending
        
        Returns:
            Number of sessions ended
        """
        # Get all session IDs for the user
        session_ids = redis_client.smembers(f"user_sessions:{user_id}")
        
        count = 0
        for session_id in session_ids:
            if exclude_session_id and session_id == exclude_session_id:
                continue
            
            if SessionManager.end_session(session_id, user_id):
                count += 1
        
        return count
    
    @staticmethod
    def get_user_sessions(user_id: int) -> List[dict]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: ID of the user
        
        Returns:
            List of session data
        """
        # Get all session IDs for the user
        session_ids = redis_client.smembers(f"user_sessions:{user_id}")
        
        sessions = []
        for session_id in session_ids:
            session_data = SessionManager.get_session(session_id)
            if session_data:
                session_data["session_id"] = session_id
                sessions.append(session_data)
        
        return sessions

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the JWT token.
    
    This dependency validates the token, checks if it's blacklisted,
    verifies the session is active, and returns the user if all checks pass.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is blacklisted
    if AuthService.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode and validate the token
        payload = AuthService.decode_token(token)
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        session_id: str = payload.get("session_id")
        
        if username is None or user_id is None:
            raise credentials_exception
        
        # Store session_id in request state for later use
        if session_id:
            request.state.session_id = session_id
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        
        # Verify session is active if session_id is present
        if session_id:
            session = db.query(UserSession).filter(
                UserSession.session_id == session_id,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has expired or been terminated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Update session last activity time
            session.last_active_at = datetime.utcnow()
            db.commit()
        
        return user
    except JWTError:
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User object
    
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Get the current admin user.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User object
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_staff_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Get the current staff or admin user.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User object
    
    Raises:
        HTTPException: If user is not staff or admin
    """
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def has_permission(required_permission: Union[str, Permission]):
    """
    Dependency for checking if user has a specific permission.
    
    Args:
        required_permission: Permission to check
    
    Returns:
        Dependency function
    """
    if isinstance(required_permission, Permission):
        required_permission = required_permission.value
    
    async def permission_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if not RBACService.has_permission(current_user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {required_permission}"
            )
        return current_user
    
    return permission_dependency

def has_any_permission(required_permissions: List[Union[str, Permission]]):
    """
    Dependency for checking if user has any of the specified permissions.
    
    Args:
        required_permissions: List of permissions to check
    
    Returns:
        Dependency function
    """
    required_permission_values = [
        p.value if isinstance(p, Permission) else p
        for p in required_permissions
    ]
    
    async def permission_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        user_permissions = RBACService.get_user_permissions(current_user)
        
        for permission in required_permission_values:
            if permission in user_permissions:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Required any of: {', '.join(required_permission_values)}"
        )
    
    return permission_dependency

def has_all_permissions(required_permissions: List[Union[str, Permission]]):
    """
    Dependency for checking if user has all of the specified permissions.
    
    Args:
        required_permissions: List of permissions to check
    
    Returns:
        Dependency function
    """
    required_permission_values = [
        p.value if isinstance(p, Permission) else p
        for p in required_permissions
    ]
    
    async def permission_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        user_permissions = RBACService.get_user_permissions(current_user)
        
        for permission in required_permission_values:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required all of: {', '.join(required_permission_values)}"
                )
        
        return current_user
    
    return permission_dependency
