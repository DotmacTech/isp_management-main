"""
Database models for the AI Chatbot Integration Module.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship

from core.database import Base
from core.models import TimestampMixin


class ChatbotQuery(Base, TimestampMixin):
    """Model for storing chatbot queries and responses."""
    
    __tablename__ = "chatbot_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    context_data = Column(JSON, nullable=True)
    intent = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=True)
    entities = Column(JSON, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    ai_service_name = Column(String(50), nullable=True)
    ai_model_version = Column(String(50), nullable=True)
    is_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="chatbot_queries")
    tenant = relationship("Tenant", back_populates="chatbot_queries")
    feedback = relationship("ChatbotFeedback", back_populates="query", cascade="all, delete-orphan")
    actions = relationship("ChatbotAction", back_populates="query", cascade="all, delete-orphan")


class ChatbotFeedback(Base, TimestampMixin):
    """Model for storing feedback on chatbot responses."""
    
    __tablename__ = "chatbot_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("chatbot_queries.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comments = Column(Text, nullable=True)
    is_helpful = Column(Boolean, nullable=True)
    
    # Relationships
    query = relationship("ChatbotQuery", back_populates="feedback")
    user = relationship("User", back_populates="chatbot_feedback")


class ChatbotAction(Base, TimestampMixin):
    """Model for storing actions performed by the chatbot."""
    
    __tablename__ = "chatbot_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("chatbot_queries.id"), nullable=False)
    action_type = Column(String(50), nullable=False)
    module_name = Column(String(50), nullable=False)
    endpoint = Column(String(255), nullable=True)
    parameters = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    is_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    query = relationship("ChatbotQuery", back_populates="actions")


class AIServiceConfig(Base, TimestampMixin):
    """Model for storing AI service configurations."""
    
    __tablename__ = "ai_service_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    service_name = Column(String(50), nullable=False)
    service_url = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=False)
    model_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    config_params = Column(JSON, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="ai_service_configs")
