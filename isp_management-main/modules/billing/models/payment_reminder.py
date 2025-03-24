"""
Payment reminder models for the billing module.

This module contains database models for payment reminders.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend_core.database import Base


class PaymentReminder(Base):
    """Model for payment reminders"""
    __tablename__ = "payment_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    reminder_type = Column(String(20))
    days_offset = Column(Integer)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="reminders")
    
    def __repr__(self):
        return f"<PaymentReminder(id={self.id}, invoice_id={self.invoice_id}, type='{self.reminder_type}')>"
