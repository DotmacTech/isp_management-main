"""
Discount models for the billing module.

This module contains database models for discounts and discount usage.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Enum, Boolean, JSON
from sqlalchemy.orm import relationship

from backend_core.database import Base


class Discount(Base):
    """Discount database model."""
    
    __tablename__ = "discounts"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    discount_type = Column(Enum("percentage", "fixed_amount", "free_item", name="discount_type"), 
                         nullable=False)
    value = Column(Numeric(12, 2), nullable=False)  # Either percentage or fixed amount
    is_limited_use = Column(Boolean, nullable=False, default=False)
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, nullable=False, default=0)
    min_order_amount = Column(Numeric(12, 2), nullable=True)
    max_discount_amount = Column(Numeric(12, 2), nullable=True)
    applies_to_plan_ids = Column(JSON, nullable=True)  # List of plan IDs this discount applies to
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    is_first_time_only = Column(Boolean, nullable=False, default=False)  # Only for new customers
    status = Column(Enum("active", "inactive", "expired", name="discount_status"), 
                  nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    usages = relationship("DiscountUsage", back_populates="discount")
    
    def __repr__(self):
        return f"<Discount(id={self.id}, name='{self.name}', code='{self.code}', type='{self.discount_type}', value={self.value})>"


class DiscountUsage(Base):
    """Discount usage record."""
    
    __tablename__ = "discount_usages"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    discount_id = Column(Integer, ForeignKey("discounts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    amount_applied = Column(Numeric(12, 2), nullable=False)  # Actual discount amount applied
    applied_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    discount = relationship("Discount", back_populates="usages")
    
    def __repr__(self):
        return f"<DiscountUsage(id={self.id}, discount_id={self.discount_id}, user_id={self.user_id}, amount_applied={self.amount_applied})>"
