"""
Tax models for the billing module.

This module contains database models for tax rates and exemptions.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Enum, Boolean, JSON, Index
from sqlalchemy.orm import relationship

from backend_core.database import Base


class TaxRate(Base):
    """Tax rate database model for different regions and tax types."""
    
    __tablename__ = "tax_rates"
    __table_args__ = (
        Index('idx_tax_region', 'country_code', 'region_code', 'zip_code'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    country_code = Column(String(2), nullable=False, index=True)
    region_code = Column(String(50), nullable=True, index=True)
    city = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    tax_type = Column(Enum("vat", "sales_tax", "gst", "pst", "hst", "other", name="tax_type"), 
                    nullable=False)
    rate = Column(Numeric(5, 2), nullable=False)  # Percentage (e.g., 20.00 for 20%)
    is_compound = Column(Boolean, nullable=False, default=False)  # Whether this tax is applied on top of other taxes
    status = Column(Enum("active", "inactive", name="tax_status"), nullable=False, default="active")
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    tax_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TaxRate(id={self.id}, name='{self.name}', country_code='{self.country_code}', rate={self.rate})>"


class TaxExemption(Base):
    """Tax exemption database model for users or organizations."""
    
    __tablename__ = "tax_exemptions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    tax_type = Column(Enum("vat", "sales_tax", "gst", "pst", "hst", "all", "other", name="exemption_tax_type"), 
                    nullable=False)
    exemption_certificate = Column(String(100), nullable=True)
    certificate_file_path = Column(String(255), nullable=True)
    verification_status = Column(Enum("pending", "verified", "rejected", name="verification_status"), 
                               nullable=False, default="pending")
    notes = Column(Text, nullable=True)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        entity_id = self.user_id or self.organization_id
        entity_type = "user" if self.user_id else "organization"
        return f"<TaxExemption(id={self.id}, {entity_type}_id={entity_id}, tax_type='{self.tax_type}')>"


class TaxTransaction(Base):
    """Tax transaction record for audit and reporting purposes."""
    
    __tablename__ = "tax_transactions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    tax_rate_id = Column(Integer, ForeignKey("tax_rates.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    taxable_amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255), nullable=True)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    tax_rate = relationship("TaxRate")
    
    def __repr__(self):
        return f"<TaxTransaction(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount})>"
