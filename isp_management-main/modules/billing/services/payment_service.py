from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from fastapi import HTTPException

from backend_core.models import Invoice, Payment, User
from modules.billing.models import (
    PaymentTransaction, PaymentGatewayConfig, Refund,
    PaymentStatus, InvoiceStatus
)
from modules.billing.schemas.payment import (
    PaymentCreate, PaymentResponse, PaymentGatewayConfigCreate,
    RefundCreate, PaymentMethodStats
)
from modules.billing.utils.audit import log_billing_action


class PaymentService:
    """Service for managing payments and payment gateways"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_payment(self, payment_data: PaymentCreate) -> Payment:
        """Processes a payment for an invoice."""
        # Get the invoice
        invoice = self.db.query(Invoice).filter(Invoice.id == payment_data.invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        if invoice.status == InvoiceStatus.PAID:
            raise HTTPException(status_code=400, detail="Invoice is already paid")
            
        # Create payment record
        payment = Payment(
            invoice_id=payment_data.invoice_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            transaction_id=payment_data.transaction_id,
            status=PaymentStatus.PENDING
        )
        
        self.db.add(payment)
        self.db.flush()  # Get payment ID without committing
        
        # Process payment through gateway if provided
        if payment_data.gateway_id:
            transaction = self._process_through_gateway(payment, payment_data)
            
            # Update payment status based on transaction
            payment.status = transaction.status
            if transaction.status == PaymentStatus.FAILED:
                self.db.commit()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Payment failed: {transaction.error_message}"
                )
        else:
            # Manual payment entry
            payment.status = PaymentStatus.COMPLETED
        
        # Update invoice status
        total_paid = sum(p.amount for p in invoice.payments) + payment.amount
        if total_paid >= invoice.amount:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.utcnow()
        elif total_paid > 0:
            invoice.status = InvoiceStatus.PARTIAL
            
        self.db.commit()
        self.db.refresh(payment)
        
        # Log the action
        log_billing_action(
            self.db, 
            "payment", 
            payment.id, 
            "create", 
            invoice.user_id, 
            {"amount": str(payment.amount), "status": payment.status}
        )
        
        return payment
    
    def _process_through_gateway(
        self, payment: Payment, payment_data: PaymentCreate
    ) -> PaymentTransaction:
        """Processes a payment through the specified payment gateway."""
        # Get the gateway configuration
        gateway = self.db.query(PaymentGatewayConfig).filter(
            PaymentGatewayConfig.id == payment_data.gateway_id
        ).first()
        
        if not gateway or not gateway.is_active:
            raise HTTPException(
                status_code=400, 
                detail="Invalid or inactive payment gateway"
            )
        
        # Initialize transaction record
        transaction = PaymentTransaction(
            payment_id=payment.id,
            gateway_id=gateway.id,
            transaction_id=payment_data.transaction_id or f"txn_{datetime.utcnow().timestamp()}",
            amount=payment_data.amount,
            currency=payment_data.currency or "USD",
            status=PaymentStatus.PENDING
        )
        
        # Process through appropriate gateway
        # This would typically call an external payment gateway API
        # For now, we'll simulate a successful transaction
        try:
            # In a real implementation, this would be replaced with actual gateway API calls
            # based on the gateway type (Stripe, PayPal, etc.)
            if gateway.gateway_type == "stripe":
                # Simulate Stripe API call
                transaction.gateway_response = {
                    "id": transaction.transaction_id,
                    "status": "succeeded",
                    "amount": float(transaction.amount),
                    "currency": transaction.currency,
                    "created": int(datetime.utcnow().timestamp())
                }
                transaction.status = PaymentStatus.COMPLETED
            elif gateway.gateway_type == "paypal":
                # Simulate PayPal API call
                transaction.gateway_response = {
                    "id": transaction.transaction_id,
                    "status": "COMPLETED",
                    "amount": {
                        "value": str(transaction.amount),
                        "currency_code": transaction.currency
                    },
                    "create_time": datetime.utcnow().isoformat()
                }
                transaction.status = PaymentStatus.COMPLETED
            else:
                # Generic success response for other gateways
                transaction.gateway_response = {
                    "id": transaction.transaction_id,
                    "status": "success",
                    "amount": str(transaction.amount),
                    "currency": transaction.currency,
                    "timestamp": datetime.utcnow().isoformat()
                }
                transaction.status = PaymentStatus.COMPLETED
        except Exception as e:
            # Handle payment processing errors
            transaction.status = PaymentStatus.FAILED
            transaction.error_message = str(e)
            transaction.gateway_response = {"error": str(e)}
        
        self.db.add(transaction)
        return transaction
    
    def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Retrieves a payment by ID."""
        return self.db.query(Payment).filter(Payment.id == payment_id).first()
    
    def get_payment_transactions(self, payment_id: int) -> List[PaymentTransaction]:
        """Gets all transactions for a specific payment."""
        return self.db.query(PaymentTransaction).filter(
            PaymentTransaction.payment_id == payment_id
        ).order_by(desc(PaymentTransaction.created_at)).all()
    
    def get_invoice_payments(self, invoice_id: int) -> List[Payment]:
        """Gets all payments for a specific invoice."""
        return self.db.query(Payment).filter(
            Payment.invoice_id == invoice_id
        ).order_by(desc(Payment.created_at)).all()
    
    def get_user_payments(self, user_id: int) -> List[Payment]:
        """Gets all payments for a specific user."""
        return (
            self.db.query(Payment)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .filter(Invoice.user_id == user_id)
            .order_by(desc(Payment.created_at))
            .all()
        )
    
    def create_refund(self, refund_data: RefundCreate) -> Refund:
        """Creates a refund for a payment."""
        # Get the payment
        payment = self.get_payment(refund_data.payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Validate refund amount
        if refund_data.amount > payment.amount:
            raise HTTPException(
                status_code=400, 
                detail="Refund amount cannot exceed payment amount"
            )
        
        # Check if payment has already been refunded
        existing_refunds = self.db.query(func.sum(Refund.amount)).filter(
            Refund.payment_id == payment.id
        ).scalar() or Decimal('0.00')
        
        remaining_refundable = payment.amount - existing_refunds
        if refund_data.amount > remaining_refundable:
            raise HTTPException(
                status_code=400, 
                detail=f"Only {remaining_refundable} is available for refund"
            )
        
        # Create refund record
        refund = Refund(
            payment_id=payment.id,
            transaction_id=payment.transaction_id,
            amount=refund_data.amount,
            reason=refund_data.reason,
            status="pending",
            created_by=refund_data.created_by
        )
        
        self.db.add(refund)
        self.db.flush()
        
        # Process refund through gateway if payment used one
        payment_transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.payment_id == payment.id
        ).first()
        
        if payment_transaction:
            # In a real implementation, this would call the gateway's refund API
            # For now, we'll simulate a successful refund
            refund.status = "completed"
            refund.refund_transaction_id = f"ref_{datetime.utcnow().timestamp()}"
            
            # Update payment status if fully refunded
            if existing_refunds + refund_data.amount >= payment.amount:
                payment.status = PaymentStatus.REFUNDED
            else:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED
        else:
            # Manual refund
            refund.status = "completed"
            
            # Update payment status
            if existing_refunds + refund_data.amount >= payment.amount:
                payment.status = PaymentStatus.REFUNDED
            else:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED
        
        # Update invoice status if needed
        invoice = self.db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
        if invoice and invoice.status == InvoiceStatus.PAID:
            # Recalculate total paid amount
            total_paid = (
                self.db.query(func.sum(Payment.amount))
                .filter(
                    Payment.invoice_id == invoice.id,
                    Payment.status.in_([PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED])
                )
                .scalar() or Decimal('0.00')
            )
            
            total_refunded = (
                self.db.query(func.sum(Refund.amount))
                .join(Payment, Refund.payment_id == Payment.id)
                .filter(Payment.invoice_id == invoice.id, Refund.status == "completed")
                .scalar() or Decimal('0.00')
            )
            
            net_paid = total_paid - total_refunded
            
            if net_paid <= 0:
                invoice.status = InvoiceStatus.ISSUED
                invoice.paid_at = None
            elif net_paid < invoice.amount:
                invoice.status = InvoiceStatus.PARTIAL
        
        self.db.commit()
        self.db.refresh(refund)
        
        # Log the action
        log_billing_action(
            self.db, 
            "refund", 
            refund.id, 
            "create", 
            refund_data.created_by, 
            {"amount": str(refund.amount), "status": refund.status}
        )
        
        return refund
    
    def get_refund(self, refund_id: int) -> Optional[Refund]:
        """Retrieves a refund by ID."""
        return self.db.query(Refund).filter(Refund.id == refund_id).first()
    
    def get_payment_refunds(self, payment_id: int) -> List[Refund]:
        """Gets all refunds for a specific payment."""
        return self.db.query(Refund).filter(
            Refund.payment_id == payment_id
        ).order_by(desc(Refund.created_at)).all()
    
    def create_payment_gateway(self, gateway_data: PaymentGatewayConfigCreate) -> PaymentGatewayConfig:
        """Creates a new payment gateway configuration."""
        # Check if a default gateway exists if this one is marked as default
        if gateway_data.is_default:
            existing_default = self.db.query(PaymentGatewayConfig).filter(
                PaymentGatewayConfig.is_default == True,
                PaymentGatewayConfig.gateway_type == gateway_data.gateway_type
            ).first()
            
            if existing_default:
                existing_default.is_default = False
        
        # Create new gateway config
        gateway = PaymentGatewayConfig(
            name=gateway_data.name,
            gateway_type=gateway_data.gateway_type,
            is_active=gateway_data.is_active,
            is_default=gateway_data.is_default,
            config=gateway_data.config
        )
        
        self.db.add(gateway)
        self.db.commit()
        self.db.refresh(gateway)
        
        return gateway
    
    def get_payment_gateway(self, gateway_id: int) -> Optional[PaymentGatewayConfig]:
        """Retrieves a payment gateway configuration by ID."""
        return self.db.query(PaymentGatewayConfig).filter(
            PaymentGatewayConfig.id == gateway_id
        ).first()
    
    def get_default_gateway(self, gateway_type: str) -> Optional[PaymentGatewayConfig]:
        """Gets the default gateway for a specific type."""
        return self.db.query(PaymentGatewayConfig).filter(
            PaymentGatewayConfig.gateway_type == gateway_type,
            PaymentGatewayConfig.is_default == True,
            PaymentGatewayConfig.is_active == True
        ).first()
    
    def get_all_gateways(self, active_only: bool = True) -> List[PaymentGatewayConfig]:
        """Gets all payment gateway configurations."""
        query = self.db.query(PaymentGatewayConfig)
        
        if active_only:
            query = query.filter(PaymentGatewayConfig.is_active == True)
            
        return query.all()
    
    def update_payment_gateway(
        self, gateway_id: int, gateway_data: Dict[str, Any]
    ) -> PaymentGatewayConfig:
        """Updates a payment gateway configuration."""
        gateway = self.get_payment_gateway(gateway_id)
        if not gateway:
            raise HTTPException(status_code=404, detail="Payment gateway not found")
        
        # Update fields
        for field, value in gateway_data.items():
            if hasattr(gateway, field) and field not in ['id', 'created_at']:
                setattr(gateway, field, value)
        
        # Handle default flag
        if gateway_data.get('is_default', False) and not gateway.is_default:
            # Unset default flag on other gateways of the same type
            self.db.query(PaymentGatewayConfig).filter(
                PaymentGatewayConfig.id != gateway_id,
                PaymentGatewayConfig.gateway_type == gateway.gateway_type,
                PaymentGatewayConfig.is_default == True
            ).update({"is_default": False})
        
        gateway.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(gateway)
        
        return gateway
    
    def delete_payment_gateway(self, gateway_id: int) -> bool:
        """Deletes a payment gateway configuration."""
        gateway = self.get_payment_gateway(gateway_id)
        if not gateway:
            raise HTTPException(status_code=404, detail="Payment gateway not found")
        
        # Check if gateway has been used for transactions
        transaction_count = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.gateway_id == gateway_id
        ).count()
        
        if transaction_count > 0:
            # Don't delete, just deactivate
            gateway.is_active = False
            gateway.is_default = False
            self.db.commit()
            return True
        
        # No transactions, safe to delete
        self.db.delete(gateway)
        self.db.commit()
        return True
    
    def get_payment_method_stats(self, start_date: datetime, end_date: datetime) -> List[PaymentMethodStats]:
        """Gets statistics about payment methods used in a date range."""
        stats = (
            self.db.query(
                Payment.payment_method,
                func.count(Payment.id).label("count"),
                func.sum(Payment.amount).label("total_amount")
            )
            .filter(
                Payment.created_at.between(start_date, end_date),
                Payment.status == PaymentStatus.COMPLETED
            )
            .group_by(Payment.payment_method)
            .all()
        )
        
        # Calculate total amount for percentage
        total_amount = sum(amount for _, _, amount in stats) if stats else Decimal('0.00')
        
        return [
            PaymentMethodStats(
                method=method,
                count=count,
                total_amount=amount,
                percentage=float(amount / total_amount * 100) if total_amount > 0 else 0
            )
            for method, count, amount in stats
        ]
