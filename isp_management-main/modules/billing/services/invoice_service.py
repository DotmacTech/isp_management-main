from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from fastapi import HTTPException

from backend_core.models import (
    Invoice, Payment, User, Discount, InvoiceDiscount, 
    CreditNote, CreditNoteApplication, TaxRate, InvoiceTax
)
from modules.billing.models import (
    InvoiceItem, InvoiceTemplate, PaymentReminder, 
    InvoiceStatus, BillingCycle
)
from modules.billing.schemas.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceDetailsResponse,
    InvoiceFilterParams, ProformaInvoiceCreate
)
from modules.billing.services.tax_service import TaxService
from modules.billing.services.discount_service import DiscountService
from modules.billing.services.credit_service import CreditService
from modules.billing.utils.currency import format_currency, convert_currency
from modules.billing.utils.audit import log_billing_action


class InvoiceService:
    """Service for managing invoices"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tax_service = TaxService(db)
        self.discount_service = DiscountService(db)
        self.credit_service = CreditService(db)
    
    def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        """Creates a new invoice for a user with detailed line items."""
        user = self.db.query(User).filter(User.id == invoice_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create the invoice
        invoice = Invoice(
            user_id=invoice_data.user_id,
            amount=Decimal('0.00'),  # Will be calculated from items
            due_date=invoice_data.due_date,
            status=InvoiceStatus.DRAFT,
            billing_country=invoice_data.billing_country,
            currency=invoice_data.currency
        )
        
        if hasattr(invoice_data, 'subscription_id') and invoice_data.subscription_id:
            invoice.subscription_id = invoice_data.subscription_id
            
        self.db.add(invoice)
        self.db.flush()  # Get the invoice ID without committing
        
        # Add invoice items
        subtotal = Decimal('0.00')
        for item_data in invoice_data.items:
            item_amount = item_data.unit_price * Decimal(str(item_data.quantity))
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data.description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                amount=item_amount,
                tax_rate=Decimal('0.00'),  # Will be calculated later
                discount_amount=Decimal('0.00')  # Will be calculated later
            )
            self.db.add(item)
            subtotal += item_amount
        
        # Apply discounts if provided
        discount_total = Decimal('0.00')
        if hasattr(invoice_data, 'discount_ids') and invoice_data.discount_ids:
            discount_total = self._apply_discounts(invoice, invoice_data.discount_ids, subtotal)
        
        # Calculate taxes
        tax_total = Decimal('0.00')
        if not invoice_data.tax_exempt:
            tax_total = self._calculate_taxes(invoice, subtotal - discount_total)
        
        # Update invoice total amount
        invoice.subtotal = subtotal
        invoice.discount_amount = discount_total
        invoice.tax_amount = tax_total
        invoice.amount = subtotal - discount_total + tax_total
        
        # Apply credit notes if provided
        if hasattr(invoice_data, 'apply_credit') and invoice_data.apply_credit:
            self._apply_available_credits(invoice)
        
        # If the invoice is fully covered by credits, mark it as paid
        if invoice.amount <= Decimal('0.00'):
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.utcnow()
        else:
            invoice.status = InvoiceStatus.ISSUED
        
        # Create payment reminders
        self._create_payment_reminders(invoice)
        
        self.db.commit()
        self.db.refresh(invoice)
        
        # Log the action
        log_billing_action(
            self.db, 
            "invoice", 
            invoice.id, 
            "create", 
            invoice_data.user_id, 
            {"amount": str(invoice.amount), "status": invoice.status}
        )
        
        return invoice
    
    def create_proforma_invoice(self, invoice_data: ProformaInvoiceCreate) -> Invoice:
        """Creates a proforma invoice that doesn't affect the accounting system."""
        # Similar to create_invoice but with proforma flag
        invoice = self.create_invoice(invoice_data)
        invoice.is_proforma = True
        invoice.status = "proforma"
        self.db.commit()
        
        log_billing_action(
            self.db, 
            "invoice", 
            invoice.id, 
            "create_proforma", 
            invoice_data.user_id, 
            {"amount": str(invoice.amount)}
        )
        
        return invoice
    
    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Retrieves an invoice by ID with all related details."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return None
        
        # Eager load relationships for detailed view
        self.db.refresh(invoice)
        return invoice
    
    def get_invoice_details(self, invoice_id: int) -> InvoiceDetailsResponse:
        """Gets detailed invoice information including items, taxes, discounts, etc."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get all the related data
        items = self.db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
        discounts = self.db.query(InvoiceDiscount).filter(InvoiceDiscount.invoice_id == invoice_id).all()
        taxes = self.db.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice_id).all()
        credits = self.db.query(CreditNoteApplication).filter(CreditNoteApplication.invoice_id == invoice_id).all()
        
        # Format the response
        discount_details = [
            {
                "id": d.discount_id,
                "name": d.discount.name,
                "amount": d.amount
            } for d in discounts
        ]
        
        tax_details = [
            {
                "id": t.tax_rate_id,
                "name": t.tax_rate.name,
                "rate": t.tax_rate.rate,
                "amount": t.tax_amount
            } for t in taxes
        ]
        
        credit_details = [
            {
                "id": c.credit_note_id,
                "amount": c.amount,
                "applied_at": c.applied_at
            } for c in credits
        ]
        
        item_details = [
            {
                "id": item.id,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.amount,
                "tax_rate": item.tax_rate,
                "discount_amount": item.discount_amount
            } for item in items
        ]
        
        # Calculate totals
        total_discount = sum(d.amount for d in discounts)
        total_tax = sum(t.tax_amount for t in taxes)
        total_credit = sum(c.amount for c in credits)
        
        return InvoiceDetailsResponse(
            id=invoice.id,
            user_id=invoice.user_id,
            status=invoice.status,
            subtotal=invoice.subtotal,
            discounts=discount_details,
            total_discount=total_discount,
            taxes=tax_details,
            total_tax=total_tax,
            credit_notes=credit_details,
            total_credit=total_credit,
            total=invoice.amount,
            due_date=invoice.due_date,
            created_at=invoice.created_at,
            paid_at=invoice.paid_at,
            items=item_details,
            currency=invoice.currency
        )
    
    def update_invoice(self, invoice_id: int, invoice_data: InvoiceUpdate) -> Invoice:
        """Updates an existing invoice."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Only allow updates to draft invoices
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=400, 
                detail="Only draft invoices can be updated"
            )
        
        # Update basic invoice fields
        for field, value in invoice_data.dict(exclude_unset=True).items():
            if hasattr(invoice, field) and field not in ['id', 'created_at', 'paid_at']:
                setattr(invoice, field, value)
        
        # Handle items update if provided
        if hasattr(invoice_data, 'items') and invoice_data.items:
            # Remove existing items
            self.db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
            
            # Add new items
            subtotal = Decimal('0.00')
            for item_data in invoice_data.items:
                item_amount = item_data.unit_price * Decimal(str(item_data.quantity))
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data.description,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    amount=item_amount
                )
                self.db.add(item)
                subtotal += item_amount
            
            # Update invoice subtotal
            invoice.subtotal = subtotal
            
            # Recalculate discounts and taxes
            self.db.query(InvoiceDiscount).filter(InvoiceDiscount.invoice_id == invoice_id).delete()
            self.db.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice_id).delete()
            
            discount_total = Decimal('0.00')
            if hasattr(invoice_data, 'discount_ids') and invoice_data.discount_ids:
                discount_total = self._apply_discounts(invoice, invoice_data.discount_ids, subtotal)
            
            tax_total = Decimal('0.00')
            if not invoice_data.tax_exempt:
                tax_total = self._calculate_taxes(invoice, subtotal - discount_total)
            
            # Update invoice total amount
            invoice.discount_amount = discount_total
            invoice.tax_amount = tax_total
            invoice.amount = subtotal - discount_total + tax_total
        
        self.db.commit()
        self.db.refresh(invoice)
        
        # Log the action
        log_billing_action(
            self.db, 
            "invoice", 
            invoice.id, 
            "update", 
            invoice_data.user_id, 
            {"amount": str(invoice.amount), "status": invoice.status}
        )
        
        return invoice
    
    def delete_invoice(self, invoice_id: int, user_id: int) -> bool:
        """Deletes a draft invoice."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Only allow deletion of draft invoices
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=400, 
                detail="Only draft invoices can be deleted"
            )
        
        # Delete related records
        self.db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
        self.db.query(InvoiceDiscount).filter(InvoiceDiscount.invoice_id == invoice_id).delete()
        self.db.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice_id).delete()
        self.db.query(PaymentReminder).filter(PaymentReminder.invoice_id == invoice_id).delete()
        
        # Delete the invoice
        self.db.delete(invoice)
        self.db.commit()
        
        # Log the action
        log_billing_action(
            self.db, 
            "invoice", 
            invoice_id, 
            "delete", 
            user_id, 
            {"status": "deleted"}
        )
        
        return True
    
    def get_user_invoices(self, user_id: int, filters: Optional[InvoiceFilterParams] = None) -> List[Invoice]:
        """Gets all invoices for a specific user with optional filtering."""
        query = self.db.query(Invoice).filter(Invoice.user_id == user_id)
        
        if filters:
            if filters.status:
                query = query.filter(Invoice.status == filters.status)
            
            if filters.start_date:
                query = query.filter(Invoice.created_at >= filters.start_date)
                
            if filters.end_date:
                query = query.filter(Invoice.created_at <= filters.end_date)
                
            if filters.min_amount:
                query = query.filter(Invoice.amount >= filters.min_amount)
                
            if filters.max_amount:
                query = query.filter(Invoice.amount <= filters.max_amount)
        
        # Order by created_at desc
        query = query.order_by(desc(Invoice.created_at))
        
        return query.all()
    
    def get_overdue_invoices(self) -> List[Invoice]:
        """Gets all overdue invoices across all users."""
        now = datetime.utcnow()
        
        return (
            self.db.query(Invoice)
            .filter(
                Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIAL]),
                Invoice.due_date < now
            )
            .order_by(Invoice.due_date)
            .all()
        )
    
    def mark_invoice_as_sent(self, invoice_id: int, user_id: int) -> Invoice:
        """Marks an invoice as sent to the customer."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice.status not in [InvoiceStatus.DRAFT, InvoiceStatus.ISSUED]:
            raise HTTPException(
                status_code=400, 
                detail="Only draft or issued invoices can be marked as sent"
            )
        
        invoice.status = InvoiceStatus.SENT
        invoice.sent_at = datetime.utcnow()
        self.db.commit()
        
        # Log the action
        log_billing_action(
            self.db, 
            "invoice", 
            invoice.id, 
            "mark_sent", 
            user_id, 
            {"status": invoice.status}
        )
        
        return invoice
    
    def void_invoice(self, invoice_id: int, user_id: int, reason: str) -> Invoice:
        """Voids an invoice, making it inactive in the system."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice.status == InvoiceStatus.PAID:
            raise HTTPException(
                status_code=400, 
                detail="Paid invoices cannot be voided. Create a credit note instead."
            )
        
        invoice.status = InvoiceStatus.VOID
        invoice.void_reason = reason
        invoice.voided_at = datetime.utcnow()
        self.db.commit()
        
        # Log the action
        log_billing_action(
            self.db, 
            "invoice", 
            invoice.id, 
            "void", 
            user_id, 
            {"reason": reason}
        )
        
        return invoice
    
    def _apply_discounts(self, invoice: Invoice, discount_ids: List[int], subtotal: Decimal) -> Decimal:
        """Applies discounts to an invoice and returns the total discount amount."""
        total_discount = Decimal('0.00')
        
        for discount_id in discount_ids:
            discount = self.discount_service.get_discount(discount_id)
            if not discount or not discount.is_active:
                continue
            
            # Check if discount is valid for this date
            now = datetime.utcnow()
            if discount.valid_from > now or (discount.valid_to and discount.valid_to < now):
                continue
            
            # Calculate discount amount
            discount_amount = Decimal('0.00')
            if discount.is_percentage:
                discount_amount = (subtotal * discount.value) / Decimal('100.00')
            else:
                discount_amount = min(discount.value, subtotal)
            
            # Create invoice discount record
            invoice_discount = InvoiceDiscount(
                invoice_id=invoice.id,
                discount_id=discount.id,
                amount=discount_amount
            )
            self.db.add(invoice_discount)
            
            total_discount += discount_amount
        
        return total_discount
    
    def _calculate_taxes(self, invoice: Invoice, taxable_amount: Decimal) -> Decimal:
        """Calculates taxes for an invoice and returns the total tax amount."""
        total_tax = Decimal('0.00')
        
        # Get applicable tax rates for the user's country
        tax_rates = self.tax_service.get_applicable_tax_rates(invoice.billing_country)
        
        for tax_rate in tax_rates:
            # Check if user is exempt from this tax
            if self.tax_service.is_user_exempt(invoice.user_id, tax_rate.id):
                continue
            
            # Calculate tax amount
            tax_amount = (taxable_amount * tax_rate.rate) / Decimal('100.00')
            
            # Create invoice tax record
            invoice_tax = InvoiceTax(
                invoice_id=invoice.id,
                tax_rate_id=tax_rate.id,
                taxable_amount=taxable_amount,
                tax_amount=tax_amount
            )
            self.db.add(invoice_tax)
            
            total_tax += tax_amount
        
        return total_tax
    
    def _apply_available_credits(self, invoice: Invoice) -> Decimal:
        """Applies available credit notes to an invoice and returns the amount applied."""
        # Get available credit notes for the user
        available_credits = self.credit_service.get_available_credit_notes(invoice.user_id)
        
        total_applied = Decimal('0.00')
        remaining_amount = invoice.amount
        
        for credit in available_credits:
            if remaining_amount <= 0:
                break
                
            # Calculate amount to apply
            apply_amount = min(credit.remaining_amount, remaining_amount)
            
            # Create credit note application
            application = CreditNoteApplication(
                credit_note_id=credit.id,
                invoice_id=invoice.id,
                amount=apply_amount,
                applied_at=datetime.utcnow()
            )
            self.db.add(application)
            
            # Update credit note remaining amount
            credit.remaining_amount -= apply_amount
            if credit.remaining_amount <= 0:
                credit.status = "used"
                credit.applied_at = datetime.utcnow()
            
            # Update remaining invoice amount
            remaining_amount -= apply_amount
            total_applied += apply_amount
        
        return total_applied
    
    def _create_payment_reminders(self, invoice: Invoice) -> None:
        """Creates payment reminders for an invoice."""
        # Create reminder for 3 days before due date
        before_reminder = PaymentReminder(
            invoice_id=invoice.id,
            reminder_type="upcoming",
            days_offset=-3  # 3 days before
        )
        self.db.add(before_reminder)
        
        # Create reminder for due date
        due_reminder = PaymentReminder(
            invoice_id=invoice.id,
            reminder_type="due",
            days_offset=0  # On due date
        )
        self.db.add(due_reminder)
        
        # Create reminder for 3 days after due date
        after_reminder = PaymentReminder(
            invoice_id=invoice.id,
            reminder_type="overdue",
            days_offset=3  # 3 days after
        )
        self.db.add(after_reminder)
        
        # Create reminder for 7 days after due date
        late_reminder = PaymentReminder(
            invoice_id=invoice.id,
            reminder_type="late",
            days_offset=7  # 7 days after
        )
        self.db.add(late_reminder)
    
    def get_billing_statistics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Gets billing statistics for a specific period."""
        # Total revenue
        revenue_query = (
            self.db.query(func.sum(Invoice.amount))
            .filter(
                Invoice.status == InvoiceStatus.PAID,
                Invoice.paid_at.between(start_date, end_date)
            )
        )
        total_revenue = revenue_query.scalar() or Decimal('0.00')
        
        # Outstanding amount
        outstanding_query = (
            self.db.query(func.sum(Invoice.amount))
            .filter(
                Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.SENT, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]),
                Invoice.created_at <= end_date
            )
        )
        outstanding_amount = outstanding_query.scalar() or Decimal('0.00')
        
        # Invoice count by status
        status_counts = {}
        for status in InvoiceStatus:
            count = (
                self.db.query(func.count(Invoice.id))
                .filter(
                    Invoice.status == status,
                    Invoice.created_at.between(start_date, end_date)
                )
                .scalar() or 0
            )
            status_counts[status] = count
        
        # Payment method distribution
        payment_methods = (
            self.db.query(
                Payment.payment_method,
                func.sum(Payment.amount).label("total_amount"),
                func.count(Payment.id).label("count")
            )
            .filter(Payment.created_at.between(start_date, end_date))
            .group_by(Payment.payment_method)
            .all()
        )
        
        payment_distribution = {
            method: {
                "amount": amount,
                "count": count,
                "percentage": (amount / total_revenue * 100) if total_revenue > 0 else 0
            }
            for method, amount, count in payment_methods
        }
        
        return {
            "total_revenue": total_revenue,
            "outstanding_amount": outstanding_amount,
            "invoice_count": sum(status_counts.values()),
            "status_distribution": status_counts,
            "payment_distribution": payment_distribution,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
