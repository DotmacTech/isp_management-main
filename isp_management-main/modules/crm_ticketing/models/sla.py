"""
SLA (Service Level Agreement) models for the CRM & Ticketing module.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Enum, Float
from sqlalchemy.orm import relationship

from backend_core.database import Base
from .common import TicketPriority, TicketType


class SLA(Base):
    """
    Service Level Agreement model.
    
    Defines the response and resolution time targets for different types of tickets.
    """
    __tablename__ = "crm_slas"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # SLA targets
    first_response_minutes = Column(JSON, nullable=False)  # Dict mapping priority to minutes
    next_update_minutes = Column(JSON, nullable=False)  # Dict mapping priority to minutes
    resolution_minutes = Column(JSON, nullable=False)  # Dict mapping priority to minutes
    
    # Business hours
    business_hours_only = Column(Boolean, default=True)
    business_hours_start = Column(Integer, default=9)  # 24-hour format
    business_hours_end = Column(Integer, default=17)  # 24-hour format
    business_days = Column(JSON, default=[1, 2, 3, 4, 5])  # 0=Sunday, 6=Saturday
    
    # Applicable ticket types
    applicable_ticket_types = Column(JSON, default=list)  # List of TicketType values
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    metrics = relationship("SLAMetric", back_populates="sla", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SLA(id={self.id}, name={self.name})>"
    
    def get_response_time(self, priority: TicketPriority) -> int:
        """Get the first response time in minutes for a given priority."""
        priority_str = priority.value if isinstance(priority, TicketPriority) else priority
        return self.first_response_minutes.get(priority_str, 
                                              self.first_response_minutes.get(TicketPriority.MEDIUM.value, 480))
    
    def get_update_time(self, priority: TicketPriority) -> int:
        """Get the next update time in minutes for a given priority."""
        priority_str = priority.value if isinstance(priority, TicketPriority) else priority
        return self.next_update_minutes.get(priority_str, 
                                           self.next_update_minutes.get(TicketPriority.MEDIUM.value, 720))
    
    def get_resolution_time(self, priority: TicketPriority) -> int:
        """Get the resolution time in minutes for a given priority."""
        priority_str = priority.value if isinstance(priority, TicketPriority) else priority
        return self.resolution_minutes.get(priority_str, 
                                          self.resolution_minutes.get(TicketPriority.MEDIUM.value, 4320))


class SLAMetric(Base):
    """
    SLA performance metrics.
    
    Tracks the performance of the support team against SLA targets.
    """
    __tablename__ = "crm_sla_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    sla_id = Column(Integer, ForeignKey("crm_slas.id"), nullable=False)
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Performance metrics
    total_tickets = Column(Integer, default=0)
    first_response_breaches = Column(Integer, default=0)
    update_breaches = Column(Integer, default=0)
    resolution_breaches = Column(Integer, default=0)
    
    first_response_compliance = Column(Float, default=100.0)  # Percentage
    update_compliance = Column(Float, default=100.0)  # Percentage
    resolution_compliance = Column(Float, default=100.0)  # Percentage
    overall_compliance = Column(Float, default=100.0)  # Percentage
    
    # Average response times in minutes
    avg_first_response_time = Column(Float, nullable=True)
    avg_resolution_time = Column(Float, nullable=True)
    
    # Breakdown by priority
    metrics_by_priority = Column(JSON, default=dict)  # Dict mapping priority to metrics
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sla = relationship("SLA", back_populates="metrics")
    
    def __repr__(self):
        return f"<SLAMetric(id={self.id}, period={self.period_start} to {self.period_end})>"
