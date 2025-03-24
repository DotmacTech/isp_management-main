"""
Subscription models for the billing module.

This module contains database models for subscriptions and related entities.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Enum, JSON, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from backend_core.database import Base


class Subscription(Base):
    """Subscription database model."""
    
    __tablename__ = "subscriptions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("service_plans.id"), nullable=False)
    status = Column(Enum("active", "paused", "cancelled", "expired", name="subscription_status"), 
                  nullable=False, default="active")
    subscription_period = Column(Enum("monthly", "quarterly", "semi_annual", "annual", name="subscription_period"), 
                               nullable=False, default="monthly")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, nullable=False, default=True)
    price = Column(Numeric(12, 2), nullable=False)
    discount_id = Column(Integer, ForeignKey("discounts.id"), nullable=True)
    notes = Column(Text, nullable=True)
    custom_metadata = Column(JSON, nullable=True)  
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    plan = relationship("ServicePlan", foreign_keys=[plan_id])
    discount = relationship("Discount", foreign_keys=[discount_id])
    history = relationship("SubscriptionHistory", back_populates="subscription", order_by="desc(SubscriptionHistory.created_at)")
    usage_records = relationship("UsageRecord", back_populates="subscription")
    recurring_billing_profile = relationship("RecurringBillingProfile", back_populates="subscription", uselist=False)
    
    @hybrid_property
    def is_active(self):
        """Check if subscription is currently active."""
        return self.status == "active" and (self.end_date is None or self.end_date > datetime.utcnow())
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, status='{self.status}')>"


class SubscriptionHistory(Base):
    """Subscription history database model for tracking changes."""
    
    __tablename__ = "subscription_history"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    previous_plan_id = Column(Integer, nullable=True)
    new_plan_id = Column(Integer, nullable=True)
    previous_price = Column(Numeric(12, 2), nullable=True)
    new_price = Column(Numeric(12, 2), nullable=True)
    change_reason = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  
    change_metadata = Column(JSON, nullable=True)  
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="history")
    
    def __repr__(self):
        return f"<SubscriptionHistory(id={self.id}, subscription_id={self.subscription_id}, new_status='{self.new_status}')>"


class RecurringBillingProfile(Base):
    """Recurring billing profile for subscriptions."""
    
    __tablename__ = "recurring_billing_profiles"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), unique=True, nullable=False)
    next_billing_date = Column(DateTime, nullable=False)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    billing_failures = Column(Integer, nullable=False, default=0)
    last_successful_charge = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="recurring_billing_profile")
    
    def __repr__(self):
        return f"<RecurringBillingProfile(id={self.id}, subscription_id={self.subscription_id}, next_billing_date='{self.next_billing_date}')>"


class UsageRecord(Base):
    """Usage record for tracking metered billing on subscriptions."""
    
    __tablename__ = "usage_records"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(50), nullable=False)  
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(String(255), nullable=True)
    source = Column(String(50), nullable=True)  
    usage_metadata = Column(JSON, nullable=True)  
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")
    
    def __repr__(self):
        return f"<UsageRecord(id={self.id}, subscription_id={self.subscription_id}, quantity={self.quantity}, unit='{self.unit}')>"
