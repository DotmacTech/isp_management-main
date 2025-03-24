"""
Invoice models for the billing module.

This module contains database models for invoices and invoice items.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from backend_core.database import Base


class Invoice(Base):
    """Invoice database model."""
    
    __tablename__ = "invoices"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    subtotal = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum("paid", "unpaid", "cancelled", name="invoice_status"), nullable=False, default="unpaid")
    due_date = Column(DateTime, nullable=False)
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(Text)
    payment_terms = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', amount={self.amount})>"


class InvoiceItem(Base):
    """Invoice item database model."""
    
    __tablename__ = "invoice_items"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    
    def __repr__(self):
        return f"<InvoiceItem(id={self.id}, description='{self.description}', total_price={self.total_price})>"


class CreditNote(Base):
    """Credit note database model."""
    
    __tablename__ = "credit_notes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    credit_note_number = Column(String(50), unique=True, index=True, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    description = Column(Text)
    reason = Column(String(255))
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice")
    
    def __repr__(self):
        return f"<CreditNote(id={self.id}, credit_note_number='{self.credit_note_number}', amount={self.amount})>"
