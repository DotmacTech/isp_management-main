from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend_core.database import Base

class UserSession(Base):
    """Model for storing user sessions."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    access_token = Column(String(512), nullable=True)
    refresh_token = Column(String(512), nullable=True)
    
    # Device information
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(512), nullable=True)
    device_info = Column(String(255), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    terminated_at = Column(DateTime, nullable=True)
    termination_reason = Column(String(50), nullable=True)
    
    # MFA status for this session
    mfa_verified = Column(Boolean, default=False)
    mfa_verified_at = Column(DateTime, nullable=True)
    remember_device = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, session_id={self.session_id})>"
