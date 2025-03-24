"""
Credit service for the billing module.

This service handles credit operations such as credit notes, refunds, and account credits.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from backend_core.database import get_db
from modules.billing.models import Invoice, CreditNote, Payment
from modules.billing.schemas.invoice import CreditNoteCreate, CreditNoteUpdate, CreditNoteResponse


class CreditService:
    """
    Service for managing customer credits and credit notes.
    """
    
    def __init__(self, db: Session = None):
        """Initialize the credit service with optional database session."""
        self.db = db or next(get_db())
    
    def create_credit_note(self, credit_data: CreditNoteCreate) -> CreditNoteResponse:
        """
        Create a new credit note for an invoice.
        
        Args:
            credit_data: Credit note information
            
        Returns:
            The created credit note
        """
        # Check if invoice exists
        invoice = self.db.query(Invoice).filter(Invoice.id == credit_data.invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice with ID {credit_data.invoice_id} not found")
        
        # Create credit note
        credit_note = CreditNote(
            invoice_id=credit_data.invoice_id,
            amount=credit_data.amount,
            reason=credit_data.reason,
            issued_date=datetime.utcnow(),
            status="active",  # Default status for new credit notes
            notes=credit_data.notes,
            created_by=credit_data.created_by
        )
        
        self.db.add(credit_note)
        self.db.commit()
        self.db.refresh(credit_note)
        
        # Return the response model
        return CreditNoteResponse.from_orm(credit_note)
    
    def get_credit_note(self, credit_note_id: int) -> Optional[CreditNoteResponse]:
        """
        Get credit note by ID.
        
        Args:
            credit_note_id: ID of the credit note
            
        Returns:
            The credit note if found, None otherwise
        """
        credit_note = self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()
        if not credit_note:
            return None
        
        return CreditNoteResponse.from_orm(credit_note)
    
    def get_credit_notes_by_invoice(self, invoice_id: int) -> List[CreditNoteResponse]:
        """
        Get all credit notes for an invoice.
        
        Args:
            invoice_id: ID of the invoice
            
        Returns:
            List of credit notes
        """
        credit_notes = self.db.query(CreditNote).filter(CreditNote.invoice_id == invoice_id).all()
        return [CreditNoteResponse.from_orm(cn) for cn in credit_notes]
    
    def update_credit_note(self, credit_note_id: int, update_data: CreditNoteUpdate) -> Optional[CreditNoteResponse]:
        """
        Update a credit note.
        
        Args:
            credit_note_id: ID of the credit note to update
            update_data: Data to update
            
        Returns:
            Updated credit note or None if not found
        """
        credit_note = self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()
        if not credit_note:
            return None
        
        # Update fields if provided
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(credit_note, field, value)
        
        self.db.commit()
        self.db.refresh(credit_note)
        
        return CreditNoteResponse.from_orm(credit_note)
    
    def void_credit_note(self, credit_note_id: int, reason: str) -> Optional[CreditNoteResponse]:
        """
        Void a credit note.
        
        Args:
            credit_note_id: ID of the credit note to void
            reason: Reason for voiding
            
        Returns:
            Voided credit note or None if not found
        """
        credit_note = self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()
        if not credit_note:
            return None
        
        # Can only void active credit notes
        if credit_note.status != "active":
            raise ValueError(f"Cannot void credit note with status '{credit_note.status}'")
        
        # Update status and add voiding reason
        credit_note.status = "voided"
        credit_note.notes = f"{credit_note.notes or ''}\nVOIDED: {reason}"
        credit_note.voided_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(credit_note)
        
        return CreditNoteResponse.from_orm(credit_note)
    
    def apply_credit_to_invoice(self, credit_note_id: int, invoice_id: int, amount: Decimal) -> Dict[str, Any]:
        """
        Apply a credit note to an invoice.
        
        Args:
            credit_note_id: ID of the credit note to apply
            invoice_id: ID of the invoice to apply the credit to
            amount: Amount of credit to apply
            
        Returns:
            Dict with status and details of the operation
        """
        credit_note = self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()
        if not credit_note:
            raise ValueError(f"Credit note with ID {credit_note_id} not found")
        
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Check if credit note is active
        if credit_note.status != "active":
            raise ValueError(f"Cannot apply credit note with status '{credit_note.status}'")
        
        # Check if amount is valid
        if amount > credit_note.amount:
            raise ValueError(f"Credit amount {amount} exceeds available credit {credit_note.amount}")
        
        # Apply credit to invoice
        if amount >= invoice.remaining_amount:
            # Credit covers the entire remaining amount
            applied_amount = invoice.remaining_amount
            invoice.status = "paid"
        else:
            # Partial payment
            applied_amount = amount
            invoice.status = "partial"
        
        # Update invoice
        invoice.remaining_amount -= applied_amount
        invoice.updated_at = datetime.utcnow()
        
        # Update credit note
        credit_note.amount -= applied_amount
        if credit_note.amount == 0:
            credit_note.status = "used"
        
        # Create a virtual payment to track the credit application
        payment = Payment(
            invoice_id=invoice_id,
            amount=applied_amount,
            payment_method="credit_note",
            payment_date=datetime.utcnow(),
            status="completed",
            reference=f"Credit Note #{credit_note_id}",
            notes=f"Applied from Credit Note #{credit_note_id}"
        )
        
        # Save changes
        self.db.add(payment)
        self.db.commit()
        
        return {
            "status": "success",
            "applied_amount": applied_amount,
            "invoice_status": invoice.status,
            "remaining_credit": credit_note.amount,
            "credit_note_status": credit_note.status,
            "payment_id": payment.id
        }
