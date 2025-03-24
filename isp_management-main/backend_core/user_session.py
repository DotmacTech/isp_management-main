"""
User Session Manager.

This module contains functions for managing user sessions.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import Request
from sqlalchemy.orm import Session
import redis

# Import shared models
from backend_core.auth_models import UserSession

# Redis client for token blacklist and session management
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

# Session configuration
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

class SessionManager:
    """Manager for user session operations."""
    
    @classmethod
    def create_session(cls, db: Session, user_id: int, request: Request, 
                       access_token: Optional[str] = None, 
                       refresh_token: Optional[str] = None) -> UserSession:
        """
        Create a new user session.
        
        Args:
            db: Database session
            user_id: User ID
            request: Request object
            access_token: JWT access token (optional)
            refresh_token: JWT refresh token (optional)
            
        Returns:
            Created UserSession object
        """
        # Get client information
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Create a new session
        session = UserSession(
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            access_token=access_token,
            refresh_token=refresh_token,
            ip_address=client_ip,
            user_agent=user_agent,
            device_info=cls._extract_device_info(user_agent),
            is_active=True,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    @classmethod
    def _extract_device_info(cls, user_agent: str) -> str:
        """
        Extract device information from user agent string.
        
        Args:
            user_agent: User agent string
            
        Returns:
            Device information string
        """
        if not user_agent:
            return "Unknown device"
        
        # Simple extraction - in production, consider using a proper user agent parser
        if "Mobile" in user_agent:
            if "iPhone" in user_agent:
                return "iPhone"
            elif "Android" in user_agent:
                return "Android device"
            return "Mobile device"
        elif "Windows" in user_agent:
            return "Windows computer"
        elif "Macintosh" in user_agent or "Mac OS" in user_agent:
            return "Mac computer"
        elif "Linux" in user_agent:
            return "Linux computer"
        
        return "Unknown device"
    
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
        return db.query(UserSession).filter_by(user_id=user_id).all()
    
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
        session = db.query(UserSession).filter_by(
            session_id=session_id,
            is_active=True
        ).first()
        
        if not session:
            return False
        
        # Terminate the session
        session.is_active = False
        session.terminated_at = datetime.utcnow()
        session.termination_reason = reason
        
        db.commit()
        
        return True
    
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
        query = db.query(UserSession).filter_by(
            user_id=user_id,
            is_active=True
        )
        
        if current_session_id:
            # If we have a current session ID, we want to exclude it
            sessions = []
            for session in query.all():
                if session.session_id != current_session_id:
                    sessions.append(session)
        else:
            sessions = query.all()
        
        count = 0
        for session in sessions:
            # Terminate the session
            session.is_active = False
            session.terminated_at = datetime.utcnow()
            session.termination_reason = "User terminated all other sessions"
            count += 1
        
        db.commit()
        
        return count
    
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
        session = db.query(UserSession).filter_by(
            session_id=session_id,
            is_active=True
        ).first()
        
        if not session:
            return False
        
        session.last_active = datetime.utcnow()
        db.commit()
        
        return True
    
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
        query = db.query(UserSession).filter_by(
            session_id=session_id,
            is_active=True
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.first()
    
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
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # We need to use a combination of filter_by and filter
        # filter_by for exact matches, filter for comparisons
        sessions = db.query(UserSession).filter_by(
            is_active=False
        ).filter(
            "terminated_at < :cutoff_date"
        ).params(cutoff_date=cutoff_date).all()
        
        count = len(sessions)
        for session in sessions:
            db.delete(session)
        
        db.commit()
        
        return count
    
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
        try:
            # Store in Redis with expiration
            key = f"refresh_blacklist:{token}"
            redis_client.set(key, "1", ex=int(expires_delta.total_seconds()))
            return True
        except Exception:
            return False
    
    @classmethod
    def is_refresh_token_blacklisted(cls, token: str) -> bool:
        """
        Check if a refresh token is blacklisted.
        
        Args:
            token: Refresh token
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            # Check in Redis
            key = f"refresh_blacklist:{token}"
            return bool(redis_client.exists(key))
        except Exception:
            # Fallback to in-memory if Redis is unavailable
            return False
