"""
Payment gateway configuration models for the billing module.

This module contains database models for payment gateway configurations.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend_core.database import Base


class PaymentGatewayConfig(Base):
    """Payment gateway configuration database model."""
    
    __tablename__ = "payment_gateway_configs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    gateway_type = Column(String(50), nullable=False)  # stripe, paypal, authorize.net, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Credentials and configuration (encrypted in production)
    credentials = Column(JSON, nullable=True)
    configuration = Column(JSON, nullable=True)
    
    # Environment settings
    environment = Column(String(20), default="sandbox", nullable=False)  # sandbox, production
    webhook_url = Column(String(255), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    
    # Access control
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    is_global = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="payment_gateways")
    
    def __repr__(self):
        return f"<PaymentGatewayConfig(id={self.id}, name='{self.name}', type='{self.gateway_type}')>"
