"""
Payment models for the billing module.

This module contains database models for payment records.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Enum, JSON
from sqlalchemy.orm import relationship

from backend_core.database import Base


class Payment(Base):
    """Payment database model."""
    
    __tablename__ = "payments"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    payment_reference = Column(String(100), unique=True, index=True, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(Enum("credit_card", "bank_transfer", "cash", "cheque", "paypal", "other", 
                               name="payment_method_type"), nullable=False)
    payment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(Enum("pending", "completed", "failed", "refunded", name="payment_status"), 
                  nullable=False, default="pending")
    transaction_id = Column(String(255), unique=True, nullable=True)
    gateway = Column(String(50), nullable=True)
    gateway_response = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    transactions = relationship("PaymentTransaction", back_populates="payment")
    refunds = relationship("Refund", back_populates="payment")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, payment_reference='{self.payment_reference}', amount={self.amount})>"


class PaymentTransaction(Base):
    """Payment transaction database model for tracking payment activities."""
    
    __tablename__ = "payment_transactions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    transaction_type = Column(Enum("authorization", "capture", "verification", "void", "refund", "chargeback", 
                                  name="transaction_type"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum("pending", "success", "failed", "processing", name="transaction_status"), 
                  nullable=False, default="pending")
    transaction_id = Column(String(255), nullable=True)
    gateway = Column(String(50), nullable=True)
    gateway_response = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processor_response_code = Column(String(50), nullable=True)
    transaction_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payment = relationship("Payment", back_populates="transactions")
    
    def __repr__(self):
        return f"<PaymentTransaction(id={self.id}, payment_id={self.payment_id}, type='{self.transaction_type}', amount={self.amount})>"


class Refund(Base):
    """Refund database model for tracking refund operations."""
    
    __tablename__ = "refunds"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    refund_reference = Column(String(100), unique=True, index=True, nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    credit_note_id = Column(Integer, ForeignKey("credit_notes.id"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    refund_method = Column(Enum("original_payment", "bank_transfer", "credit", "cheque", "other", 
                              name="refund_method_type"), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum("pending", "processing", "completed", "failed", "rejected", 
                       name="refund_status"), nullable=False, default="pending")
    refund_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    transaction_id = Column(String(255), nullable=True)
    gateway = Column(String(50), nullable=True)
    gateway_response = Column(JSON, nullable=True)
    processed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payment = relationship("Payment", back_populates="refunds")
    credit_note = relationship("CreditNote", back_populates="refunds")
    
    def __repr__(self):
        return f"<Refund(id={self.id}, refund_reference='{self.refund_reference}', amount={self.amount})>"


class PaymentRefund(Base):
    """Payment refund database model."""
    
    __tablename__ = "payment_refunds"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    refund_reference = Column(String(100), unique=True, index=True, nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=True)
    refund_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(Enum("pending", "completed", "failed", name="refund_status"), 
                  nullable=False, default="pending")
    transaction_id = Column(String(255), unique=True, nullable=True)
    gateway_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payment = relationship("Payment")
    
    def __repr__(self):
        return f"<PaymentRefund(id={self.id}, refund_reference='{self.refund_reference}', amount={self.amount})>"
