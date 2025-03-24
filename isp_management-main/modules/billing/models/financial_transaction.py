"""
Financial transaction models for the billing module.

This module defines the database models related to financial transactions and accounting.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from backend_core.database import Base


class FinancialTransaction(Base):
    """
    Model for financial transactions (for accounting purposes).
    
    This model tracks all financial transactions across the system for accounting
    and financial reporting purposes.
    """
    __tablename__ = "financial_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String(50), nullable=False)  # invoice, payment, refund, credit_note, etc.
    reference_id = Column(Integer, nullable=False)  # ID of the related entity
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    description = Column(Text, nullable=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    accounting_code = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<FinancialTransaction {self.id}: {self.transaction_type} - {self.amount}>"


class AccountingIntegration(Base):
    """
    Model for accounting software integrations.
    
    This model manages connections to external accounting systems like
    QuickBooks, Xero, etc.
    """
    __tablename__ = "accounting_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    integration_type = Column(String(50), nullable=False)  # quickbooks, xero, etc.
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AccountingIntegration {self.name}: {self.integration_type}>"
