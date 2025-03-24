from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend_core.models import Invoice, Payment, User, Discount, InvoiceDiscount, CreditNote, CreditNoteApplication, TaxRate, InvoiceTax
from backend_core.cache import (
    get_cached_tax_rate, cache_tax_rate,
    get_cached_active_discounts, cache_active_discounts,
    get_cached_invoice_details, cache_invoice_details, invalidate_invoice_cache,
    get_cached_user_credit_notes, cache_user_credit_notes, invalidate_user_credit_notes_cache,
    get_cached_user_invoices, cache_user_invoices, invalidate_user_invoices_cache,
    get_cached_payment_history, cache_payment_history, invalidate_payment_history_cache,
    get_cached_billing_statistics, cache_billing_statistics, invalidate_billing_statistics_cache
)
from .schemas import InvoiceCreate, PaymentCreate
from .template_service import (
    render_invoice_template, render_invoice_reminder_email, 
    render_monthly_billing_report
)

class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        """Creates a new invoice for a user."""
        user = self.db.query(User).filter(User.id == invoice_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        invoice = Invoice(
            user_id=invoice_data.user_id,
            amount=invoice_data.amount,
            due_date=invoice_data.due_date,
            status="unpaid"
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Retrieves an invoice by ID."""
        # Try to get from cache first
        cached_invoice_details = get_cached_invoice_details(invoice_id)
        if cached_invoice_details is not None:
            # If we have cached details, we can return the invoice from DB
            # without needing to recalculate all the details
            return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            
        # If not in cache, get from database
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def get_user_invoices(self, user_id: int) -> List[Invoice]:
        """Gets all invoices for a specific user."""
        return self.db.query(Invoice).filter(Invoice.user_id == user_id).all()

    def process_payment(self, payment_data: PaymentCreate) -> Payment:
        """Processes a payment for an invoice."""
        invoice = self.get_invoice(payment_data.invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        if invoice.status == "paid":
            raise HTTPException(status_code=400, detail="Invoice is already paid")
            
        payment = Payment(
            invoice_id=payment_data.invoice_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            transaction_id=payment_data.transaction_id
        )
        
        self.db.add(payment)
        
        # Update invoice status
        total_paid = sum(p.amount for p in invoice.payments) + payment.amount
        if total_paid >= invoice.amount:
            invoice.status = "paid"
            invoice.paid_at = datetime.utcnow()
        elif total_paid > 0:
            invoice.status = "partial"
            
        self.db.commit()
        self.db.refresh(payment)
        
        # Invalidate invoice cache
        invalidate_invoice_cache(payment_data.invoice_id)
        
        return payment

    def check_overdue_invoices(self) -> List[Invoice]:
        """Identifies overdue invoices and updates their status."""
        overdue_invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.status.in_(["unpaid", "partial"]),
                Invoice.due_date < datetime.utcnow()
            )
            .all()
        )

        for invoice in overdue_invoices:
            invoice.status = "overdue"
        
        self.db.commit()
        return overdue_invoices

    def calculate_usage_charges(self, user_id: int, usage_mb: float) -> Decimal:
        """Calculates charges based on usage and user's plan."""
        # This would integrate with the Tariff module to get plan details
        # and calculate any overage charges
        pass

    # Discount Management Methods
    def create_discount(self, discount_data):
        """Creates a new discount."""
        discount = Discount(
            name=discount_data.name,
            description=discount_data.description,
            discount_type=discount_data.discount_type,
            value=discount_data.value,
            is_percentage=discount_data.is_percentage,
            is_active=discount_data.is_active,
            valid_from=discount_data.valid_from,
            valid_to=discount_data.valid_to,
            applicable_plans=discount_data.applicable_plans
        )
        
        self.db.add(discount)
        self.db.commit()
        self.db.refresh(discount)
        return discount
    
    def get_discount(self, discount_id: int):
        """Retrieves a discount by ID."""
        return self.db.query(Discount).filter(Discount.id == discount_id).first()
    
    def get_active_discounts(self):
        """Retrieves all active discounts."""
        # Try to get from cache first
        cached_discounts = get_cached_active_discounts()
        if cached_discounts is not None:
            return cached_discounts
            
        # If not in cache, get from database
        current_date = datetime.utcnow()
        discounts = self.db.query(Discount).filter(
            Discount.is_active == True,
            Discount.valid_from <= current_date,
            (Discount.valid_to == None) | (Discount.valid_to >= current_date)
        ).all()
        
        # Cache the results
        cache_active_discounts(discounts)
        
        return discounts
    
    def apply_discount_to_invoice(self, invoice_id: int, discount_id: int):
        """Applies a discount to an invoice."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        discount = self.get_discount(discount_id)
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
            
        # Check if discount is active
        current_date = datetime.utcnow()
        if not discount.is_active or discount.valid_from > current_date or \
           (discount.valid_to and discount.valid_to < current_date):
            raise HTTPException(status_code=400, detail="Discount is not active")
        
        # Calculate discount amount
        discount_amount = Decimal('0.00')
        if discount.is_percentage:
            discount_amount = invoice.amount * (discount.value / Decimal('100.00'))
        else:
            discount_amount = min(discount.value, invoice.amount)
        
        # Create invoice discount record
        invoice_discount = InvoiceDiscount(
            invoice_id=invoice.id,
            discount_id=discount.id,
            amount=discount_amount
        )
        
        self.db.add(invoice_discount)
        self.db.commit()
        
        # Recalculate invoice total
        self._recalculate_invoice_total(invoice)
        
        # Invalidate active discounts cache since usage pattern may have changed
        cache_active_discounts(self.get_active_discounts())
        
        return invoice_discount
    
    # Credit Note Methods
    def create_credit_note(self, credit_note_data):
        """Creates a new credit note."""
        credit_note = CreditNote(
            user_id=credit_note_data.user_id,
            amount=credit_note_data.amount,
            remaining_amount=credit_note_data.amount,  
            reason=credit_note_data.reason,
            reference_invoice_id=credit_note_data.reference_invoice_id,
            status="issued"  
        )
        
        self.db.add(credit_note)
        self.db.commit()
        self.db.refresh(credit_note)
        return credit_note
    
    def get_credit_note(self, credit_note_id: int):
        """Retrieves a credit note by ID."""
        return self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()
    
    def get_user_credit_notes(self, user_id: int):
        """Gets all credit notes for a specific user."""
        # Try to get from cache first
        cached_credit_notes = get_cached_user_credit_notes(user_id)
        if cached_credit_notes is not None:
            return cached_credit_notes
            
        # If not in cache, get from database
        credit_notes = self.db.query(CreditNote).filter(CreditNote.user_id == user_id).all()
        
        # Cache the results
        cache_user_credit_notes(user_id, credit_notes)
        
        return credit_notes
    
    def apply_credit_note_to_invoice(self, credit_note_id: int, invoice_id: int, amount: Optional[Decimal] = None):
        """Applies a credit note to an invoice."""
        credit_note = self.get_credit_note(credit_note_id)
        if not credit_note:
            raise HTTPException(status_code=404, detail="Credit note not found")
            
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        if credit_note.status != "issued" or credit_note.remaining_amount <= 0:
            raise HTTPException(status_code=400, detail="Credit note cannot be applied")
            
        # Determine amount to apply
        apply_amount = amount if amount else min(credit_note.remaining_amount, invoice.amount)
        if apply_amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount to apply")
            
        # Create application record
        application = CreditNoteApplication(
            credit_note_id=credit_note.id,
            invoice_id=invoice.id,
            amount=apply_amount
        )
        
        # Update credit note remaining amount
        credit_note.remaining_amount -= apply_amount
        if credit_note.remaining_amount <= 0:
            credit_note.status = "applied"
            credit_note.applied_at = datetime.utcnow()
            
        self.db.add(application)
        self.db.commit()
        
        # Recalculate invoice total
        self._recalculate_invoice_total(invoice)
        
        # Invalidate caches
        invalidate_invoice_cache(invoice_id)
        invalidate_user_credit_notes_cache(credit_note.user_id)
        
        return application
    
    # Tax Management Methods
    def create_tax_rate(self, tax_rate_data):
        """Creates a new tax rate."""
        # If this is set as default, unset any existing defaults for the same country/region
        if tax_rate_data.is_default:
            existing_defaults = self.db.query(TaxRate).filter(
                TaxRate.country == tax_rate_data.country,
                TaxRate.is_default == True
            )
            if tax_rate_data.region:
                existing_defaults = existing_defaults.filter(TaxRate.region == tax_rate_data.region)
                
            for tax_rate in existing_defaults:
                tax_rate.is_default = False
        
        tax_rate = TaxRate(
            name=tax_rate_data.name,
            description=tax_rate_data.description,
            rate=tax_rate_data.rate,
            country=tax_rate_data.country,
            region=tax_rate_data.region,
            is_default=tax_rate_data.is_default
        )
        
        self.db.add(tax_rate)
        self.db.commit()
        self.db.refresh(tax_rate)
        
        # Cache the tax rate if it's a default
        if tax_rate.is_default:
            cache_tax_rate(tax_rate.country, tax_rate.region, tax_rate)
            
        return tax_rate
    
    def get_tax_rate(self, tax_rate_id: int):
        """Retrieves a tax rate by ID."""
        return self.db.query(TaxRate).filter(TaxRate.id == tax_rate_id).first()
    
    def get_applicable_tax_rate(self, country: str, region: str = None):
        """Gets the applicable tax rate for a country/region."""
        # Try to get from cache first
        cached_tax_rate = get_cached_tax_rate(country, region)
        if cached_tax_rate is not None:
            return cached_tax_rate
            
        # Try to find a specific region match first
        if region:
            tax_rate = self.db.query(TaxRate).filter(
                TaxRate.country == country,
                TaxRate.region == region,
                TaxRate.is_default == True
            ).first()
            
            if tax_rate:
                # Cache the result
                cache_tax_rate(country, region, tax_rate)
                return tax_rate
        
        # Fall back to country-level default
        tax_rate = self.db.query(TaxRate).filter(
            TaxRate.country == country,
            TaxRate.is_default == True,
            TaxRate.region.is_(None)
        ).first()
        
        # Cache the result
        if tax_rate:
            cache_tax_rate(country, None, tax_rate)
            
        return tax_rate
    
    def calculate_invoice_taxes(self, invoice_id: int) -> List[InvoiceTax]:
        """Calculate taxes for an invoice based on applicable tax rates."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")

        # Clear any existing tax records for this invoice
        self.db.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice_id).delete()

        # Get applicable tax rates based on invoice's billing country
        tax_rates = self.db.query(TaxRate).filter(
            TaxRate.country == invoice.billing_country,
            TaxRate.is_default == True
        ).all()

        # Calculate and store tax details
        tax_details = []
        for tax_rate in tax_rates:
            # Calculate tax amount based on invoice amount
            taxable_amount = invoice.amount  # Full amount is taxable
            tax_amount = (taxable_amount * tax_rate.rate) / Decimal("100.00")

            # Create tax record
            tax_detail = InvoiceTax(
                invoice_id=invoice.id,
                tax_rate_id=tax_rate.id,
                taxable_amount=taxable_amount,
                tax_amount=tax_amount,
                created_at=datetime.utcnow()
            )
            self.db.add(tax_detail)
            tax_details.append(tax_detail)

        self.db.commit()
        
        # Invalidate invoice cache since we've modified it
        invalidate_invoice_cache(invoice_id)
        
        return tax_details
    
    def _recalculate_invoice_total(self, invoice):
        """Recalculates the invoice total after applying discounts or taxes."""
        # Get original amount (before discounts and taxes)
        original_amount = invoice.amount
        
        # Calculate total discounts
        total_discounts = sum(
            discount.amount for discount in 
            self.db.query(InvoiceDiscount).filter(InvoiceDiscount.invoice_id == invoice.id).all()
        )
        
        # Calculate total taxes
        total_taxes = sum(
            tax.tax_amount for tax in 
            self.db.query(InvoiceTax).filter(InvoiceTax.invoice_id == invoice.id).all()
        )
        
        # Update invoice amount
        invoice.amount = original_amount - total_discounts + total_taxes
        
        # Calculate total payments and credit notes
        total_paid = sum(
            payment.amount for payment in invoice.payments
        ) + sum(
            application.amount for application in invoice.credit_note_applications
        )
        
        # Update invoice status based on payment status
        if total_paid >= invoice.amount:
            invoice.status = "paid"
            if not invoice.paid_at:
                invoice.paid_at = datetime.utcnow()
        elif total_paid > 0:
            invoice.status = "partial"
        else:
            invoice.status = "unpaid"
            
        self.db.commit()
        
        # Invalidate invoice cache since we've modified it
        invalidate_invoice_cache(invoice.id)
        
        return invoice

    # Template rendering methods
    def generate_invoice_html(self, invoice_id: int) -> str:
        """
        Generate HTML representation of an invoice.
        
        Args:
            invoice_id: ID of the invoice
            
        Returns:
            str: HTML representation of the invoice
        """
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get customer details
        customer = self.db.query(User).filter(User.id == invoice.user_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get invoice items
        invoice_items = []  # This would come from a related table in a real implementation
        
        # Get discounts
        discounts = [
            {
                "name": discount.discount.name,
                "amount": discount.amount
            }
            for discount in self.db.query(InvoiceDiscount).filter(
                InvoiceDiscount.invoice_id == invoice_id
            ).all()
        ]
        
        # Get taxes
        taxes = [
            {
                "name": tax.tax_rate.name,
                "rate": tax.tax_rate.rate,
                "amount": tax.tax_amount
            }
            for tax in self.db.query(InvoiceTax).filter(
                InvoiceTax.invoice_id == invoice_id
            ).join(TaxRate).all()
        ]
        
        # Get payments
        payments = [
            {
                "amount": payment.amount,
                "created_at": payment.created_at,
                "payment_method": payment.payment_method
            }
            for payment in self.db.query(Payment).filter(
                Payment.invoice_id == invoice_id
            ).all()
        ]
        
        # Calculate balance due
        total_paid = sum(payment["amount"] for payment in payments)
        balance_due = invoice.amount - total_paid
        
        # Prepare context for template
        context = {
            "invoice": invoice.to_dict(),
            "customer": customer.to_dict(),
            "invoice_items": invoice_items,
            "discounts": discounts,
            "taxes": taxes,
            "payments": payments,
            "balance_due": balance_due,
            "payment_methods": ["Credit Card", "Bank Transfer", "PayPal"],
            "payment_account_number": "XXXX-XXXX-XXXX-1234",
            "payment_terms": "Net 30"
        }
        
        # Render template
        return render_invoice_template(context)
    
    def generate_invoice_pdf(self, invoice_id: int) -> bytes:
        """
        Generate PDF representation of an invoice.
        
        Args:
            invoice_id: ID of the invoice
            
        Returns:
            bytes: PDF representation of the invoice
        """
        # Get HTML representation
        html = self.generate_invoice_html(invoice_id)
        
        # Convert HTML to PDF
        try:
            import weasyprint
            pdf = weasyprint.HTML(string=html).write_pdf()
            return pdf
        except ImportError:
            # Fallback if weasyprint is not available
            raise HTTPException(
                status_code=500, 
                detail="PDF generation is not available. Please install weasyprint."
            )
    
    def generate_invoice_reminder_email(self, invoice_id: int) -> str:
        """
        Generate an invoice reminder email.
        
        Args:
            invoice_id: ID of the invoice
            
        Returns:
            str: HTML representation of the email
        """
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get customer details
        customer = self.db.query(User).filter(User.id == invoice.user_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Calculate days overdue
        days_overdue = 0
        if invoice.due_date and invoice.due_date < datetime.utcnow():
            days_overdue = (datetime.utcnow() - invoice.due_date).days
        
        # Calculate balance due
        total_paid = sum(payment.amount for payment in invoice.payments)
        balance_due = invoice.amount - total_paid
        
        # Prepare context for template
        context = {
            "invoice": {
                **invoice.to_dict(),
                "balance_due": balance_due
            },
            "customer": customer.to_dict(),
            "days_overdue": days_overdue,
            "payment_link": f"https://billing.example.com/invoices/{invoice_id}/pay"
        }
        
        # Render template
        return render_invoice_reminder_email(context)
    
    def generate_monthly_billing_report(self, year: int, month: int) -> str:
        """
        Generate a monthly billing report.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            str: HTML representation of the report
        """
        # Get start and end dates for the month
        from calendar import monthrange
        import calendar
        
        start_date = datetime(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        # Get all invoices for the month
        invoices = self.db.query(Invoice).filter(
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).all()
        
        # Get all payments for the month
        payments = self.db.query(Payment).filter(
            Payment.created_at >= start_date,
            Payment.created_at <= end_date
        ).all()
        
        # Calculate total revenue
        total_revenue = sum(invoice.amount for invoice in invoices)
        
        # Calculate outstanding amount
        outstanding_amount = sum(
            invoice.amount for invoice in invoices 
            if invoice.status in ["unpaid", "partial", "overdue"]
        )
        
        # Calculate revenue by category (simplified example)
        revenue_categories = [
            {"name": "Internet Services", "amount": total_revenue * Decimal("0.7"), "percentage": 70},
            {"name": "Equipment Rental", "amount": total_revenue * Decimal("0.2"), "percentage": 20},
            {"name": "Installation Fees", "amount": total_revenue * Decimal("0.1"), "percentage": 10}
        ]
        
        # Calculate payment method distribution
        payment_methods = {}
        for payment in payments:
            method = payment.payment_method
            if method not in payment_methods:
                payment_methods[method] = {"amount": Decimal("0"), "count": 0}
            payment_methods[method]["amount"] += payment.amount
            payment_methods[method]["count"] += 1
        
        payment_method_list = []
        for method, data in payment_methods.items():
            percentage = (data["amount"] / sum(p.amount for p in payments)) * 100 if payments else 0
            payment_method_list.append({
                "name": method,
                "amount": data["amount"],
                "percentage": round(percentage, 2),
                "count": data["count"]
            })
        
        # Calculate invoice status distribution
        invoice_statuses = {}
        for invoice in invoices:
            status = invoice.status
            if status not in invoice_statuses:
                invoice_statuses[status] = {"amount": Decimal("0"), "count": 0}
            invoice_statuses[status]["amount"] += invoice.amount
            invoice_statuses[status]["count"] += 1
        
        invoice_status_list = []
        for status, data in invoice_statuses.items():
            percentage = (data["amount"] / total_revenue) * 100 if total_revenue else 0
            invoice_status_list.append({
                "name": status.capitalize(),
                "amount": data["amount"],
                "percentage": round(percentage, 2),
                "count": data["count"]
            })
        
        # Calculate top customers
        customer_revenues = {}
        for invoice in invoices:
            user_id = invoice.user_id
            if user_id not in customer_revenues:
                customer_revenues[user_id] = {"revenue": Decimal("0"), "invoices": []}
            customer_revenues[user_id]["revenue"] += invoice.amount
            customer_revenues[user_id]["invoices"].append(invoice)
        
        top_customers = []
        for user_id, data in sorted(
            customer_revenues.items(), 
            key=lambda x: x[1]["revenue"], 
            reverse=True
        )[:10]:
            customer = self.db.query(User).filter(User.id == user_id).first()
            if customer:
                invoice_count = len(data["invoices"])
                avg_invoice = data["revenue"] / invoice_count if invoice_count else 0
                top_customers.append({
                    "name": f"{customer.first_name} {customer.last_name}",
                    "revenue": data["revenue"],
                    "invoice_count": invoice_count,
                    "average_invoice": avg_invoice
                })
        
        # Prepare context for template
        context = {
            "month_name": calendar.month_name[month],
            "year": year,
            "generation_date": datetime.utcnow(),
            "total_revenue": total_revenue,
            "invoice_count": len(invoices),
            "payment_count": len(payments),
            "outstanding_amount": outstanding_amount,
            "revenue_categories": revenue_categories,
            "payment_methods": payment_method_list,
            "invoice_statuses": invoice_status_list,
            "top_customers": top_customers,
            "revenue_chart_url": f"https://charts.example.com/revenue/{year}/{month}"
        }
        
        # Cache billing statistics
        cache_billing_statistics({
            "year": year,
            "month": month,
            "total_revenue": float(total_revenue),
            "invoice_count": len(invoices),
            "payment_count": len(payments),
            "outstanding_amount": float(outstanding_amount)
        })
        
        # Render template
        return render_monthly_billing_report(context)
