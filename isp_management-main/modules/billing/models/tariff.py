"""
Tariff plan models for the billing module.

This module defines the database models related to tariff plans and pricing.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend_core.database import Base


class TariffPlan(Base):
    """
    Model representing a service tariff plan.
    
    A tariff plan defines pricing information for ISP services.
    """
    __tablename__ = "billing_tariff_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(10, 2), nullable=False)
    billing_cycle = Column(String(20), nullable=False)  # monthly, quarterly, annual, etc.
    is_active = Column(Boolean, default=True)
    data_cap_gb = Column(Integer, nullable=True)  # Null for unlimited
    bandwidth_mbps = Column(Integer, nullable=False)
    setup_fee = Column(Numeric(10, 2), default=0.00)
    early_termination_fee = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    features = relationship("TariffFeature", back_populates="tariff_plan", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tariff_plan")
    tiered_pricing = relationship("TieredPricing", back_populates="tariff_plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TariffPlan {self.name}>"


class TariffFeature(Base):
    """
    Model representing features included in a tariff plan.
    
    Features are additional services or characteristics of a tariff plan.
    """
    __tablename__ = "billing_tariff_features"
    
    id = Column(Integer, primary_key=True, index=True)
    tariff_plan_id = Column(Integer, ForeignKey("billing_tariff_plans.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_premium = Column(Boolean, default=False)
    additional_cost = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tariff_plan = relationship("TariffPlan", back_populates="features")
    
    def __repr__(self):
        return f"<TariffFeature {self.name}>"


class TariffOverage(Base):
    """
    Model representing overage charges for exceeding tariff plan limits.
    
    Overages are additional fees charged when customers exceed their plan limits.
    """
    __tablename__ = "billing_tariff_overages"
    
    id = Column(Integer, primary_key=True, index=True)
    tariff_plan_id = Column(Integer, ForeignKey("billing_tariff_plans.id"))
    resource_type = Column(String(50), nullable=False)  # data, bandwidth, etc.
    unit = Column(String(20), nullable=False)  # GB, MB, etc.
    cost_per_unit = Column(Numeric(10, 2), nullable=False)
    threshold = Column(Integer, nullable=True)  # When to start applying overage
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tariff_plan = relationship("TariffPlan")
    
    def __repr__(self):
        return f"<TariffOverage {self.resource_type} for Tariff {self.tariff_plan_id}>"


class TieredPricing(Base):
    """
    Model representing tiered pricing for tariff plans.
    
    Tiered pricing allows different rates based on consumption levels
    or user categories. This enables volume-based discounts or premium pricing
    for different usage tiers.
    """
    __tablename__ = "billing_tiered_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    tariff_plan_id = Column(Integer, ForeignKey("billing_tariff_plans.id"))
    tier_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    min_value = Column(Integer, nullable=False)  # Minimum threshold for this tier
    max_value = Column(Integer, nullable=True)   # Maximum threshold for this tier (null for unlimited)
    unit = Column(String(20), nullable=False)    # GB, users, devices, etc.
    price_per_unit = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tariff_plan = relationship("TariffPlan", back_populates="tiered_pricing")
    
    def __repr__(self):
        return f"<TieredPricing {self.tier_name} for Tariff {self.tariff_plan_id}>"
