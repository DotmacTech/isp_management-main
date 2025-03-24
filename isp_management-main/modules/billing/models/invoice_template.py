"""
Invoice template models for the billing module.

This module contains database models for invoice templates.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from backend_core.database import Base


class InvoiceTemplate(Base):
    """Model for invoice templates"""
    __tablename__ = "invoice_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    template_html = Column(Text, nullable=False)
    css_styles = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    creator = relationship("User")
    
    def __repr__(self):
        return f"<InvoiceTemplate(id={self.id}, name='{self.name}', is_default={self.is_default})>"
