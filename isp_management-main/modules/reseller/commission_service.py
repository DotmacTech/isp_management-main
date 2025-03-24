from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from backend_core.models import (
    Reseller,
    ResellerCustomer,
    ResellerTransaction,
    ResellerCommissionRule,
    ResellerCommissionPayout,
    ResellerPayoutTransaction,
    ResellerTierBenefit,
    Customer,
    Invoice,
    Payment,
    UserTariffPlan,
    TariffPlan
)
from .schemas import (
    CommissionCalculationRequest,
    CommissionCalculationResponse,
    ResellerTransactionType,
    CommissionType,
    CommissionPaymentRequest
)

class CommissionService:
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_commission(self, request: CommissionCalculationRequest) -> CommissionCalculationResponse:
        """
        Calculate commission for a reseller based on customer payments within a date range
        """
        # Get the reseller
        reseller = self.db.query(Reseller).filter(Reseller.id == request.reseller_id).first()
        if not reseller:
            raise ValueError(f"Reseller with ID {request.reseller_id} not found")
        
        # Get tier benefits for commission multiplier
        tier_benefits = self.db.query(ResellerTierBenefit).filter(
            ResellerTierBenefit.tier == reseller.tier,
            ResellerTierBenefit.is_active == True
        ).first()
        
        commission_multiplier = 1.0
        if tier_benefits:
            commission_multiplier = tier_benefits.commission_multiplier
        
        # Get all customers assigned to this reseller
        reseller_customers = self.db.query(ResellerCustomer).filter(
            ResellerCustomer.reseller_id == reseller.id
        ).all()
        
        customer_ids = [rc.customer_id for rc in reseller_customers]
        
        if not customer_ids:
            # No customers assigned to this reseller
            return CommissionCalculationResponse(
                reseller_id=reseller.id,
                period_start=request.start_date,
                period_end=request.end_date,
                total_commission=0.0,
                commission_by_plan={},
                commission_details=[] if request.include_details else None
            )
        
        # Get all paid invoices for these customers within the date range
        invoices = self.db.query(Invoice).join(
            Customer, Customer.user_id == Invoice.user_id
        ).filter(
            Customer.id.in_(customer_ids),
            Invoice.status == "paid",
            Invoice.paid_at >= request.start_date,
            Invoice.paid_at <= request.end_date
        ).all()
        
        # Initialize commission calculation
        total_commission = 0.0
        commission_by_plan = {}
        commission_details = [] if request.include_details else None
        
        # Process each invoice
        for invoice in invoices:
            # Get the customer's tariff plan
            user_tariff_plan = self.db.query(UserTariffPlan).filter(
                UserTariffPlan.user_id == invoice.user_id,
                UserTariffPlan.status == "active"
            ).first()
            
            if not user_tariff_plan:
                continue
            
            tariff_plan = self.db.query(TariffPlan).filter(
                TariffPlan.id == user_tariff_plan.tariff_plan_id
            ).first()
            
            if not tariff_plan:
                continue
            
            # Check if there's a specific commission rule for this tariff plan
            commission_rule = self.db.query(ResellerCommissionRule).filter(
                ResellerCommissionRule.reseller_id == reseller.id,
                ResellerCommissionRule.tariff_plan_id == tariff_plan.id
            ).first()
            
            # Calculate commission based on rule or default reseller commission rate
            commission_amount = 0.0
            
            if commission_rule:
                if commission_rule.commission_type == CommissionType.PERCENTAGE:
                    commission_amount = float(invoice.amount) * (commission_rule.commission_rate / 100.0)
                elif commission_rule.commission_type == CommissionType.FIXED:
                    commission_amount = commission_rule.commission_rate
                elif commission_rule.commission_type == CommissionType.TIERED:
                    # Count customers on this plan for tiered commission
                    customer_count = self.db.query(func.count(UserTariffPlan.id)).filter(
                        UserTariffPlan.tariff_plan_id == tariff_plan.id,
                        UserTariffPlan.status == "active"
                    ).join(
                        Customer, Customer.user_id == UserTariffPlan.user_id
                    ).join(
                        ResellerCustomer, ResellerCustomer.customer_id == Customer.id
                    ).filter(
                        ResellerCustomer.reseller_id == reseller.id
                    ).scalar() or 0
                    
                    # Apply tiered rate if within range
                    if (commission_rule.min_customers is None or customer_count >= commission_rule.min_customers) and \
                       (commission_rule.max_customers is None or customer_count <= commission_rule.max_customers):
                        if commission_rule.commission_type == CommissionType.PERCENTAGE:
                            commission_amount = float(invoice.amount) * (commission_rule.commission_rate / 100.0)
                        else:
                            commission_amount = commission_rule.commission_rate
            else:
                # Use default reseller commission rate
                if reseller.commission_type == CommissionType.PERCENTAGE:
                    commission_amount = float(invoice.amount) * (reseller.commission_rate / 100.0)
                elif reseller.commission_type == CommissionType.FIXED:
                    commission_amount = reseller.commission_rate
            
            # Apply tier multiplier
            commission_amount *= commission_multiplier
            
            # Add to total and by-plan breakdown
            total_commission += commission_amount
            
            plan_name = tariff_plan.name
            if plan_name in commission_by_plan:
                commission_by_plan[plan_name] += commission_amount
            else:
                commission_by_plan[plan_name] = commission_amount
            
            # Add details if requested
            if request.include_details:
                customer = self.db.query(Customer).filter(Customer.user_id == invoice.user_id).first()
                commission_details.append({
                    "invoice_id": invoice.id,
                    "customer_id": customer.id if customer else None,
                    "customer_name": customer.full_name if customer else "Unknown",
                    "invoice_amount": float(invoice.amount),
                    "commission_amount": commission_amount,
                    "tariff_plan": tariff_plan.name,
                    "paid_at": invoice.paid_at.isoformat(),
                    "commission_rate": commission_rule.commission_rate if commission_rule else reseller.commission_rate,
                    "commission_type": commission_rule.commission_type if commission_rule else reseller.commission_type
                })
        
        return CommissionCalculationResponse(
            reseller_id=reseller.id,
            period_start=request.start_date,
            period_end=request.end_date,
            total_commission=total_commission,
            commission_by_plan=commission_by_plan,
            commission_details=commission_details
        )
    
    def process_commission_payment(self, request: CommissionPaymentRequest) -> Dict[str, Any]:
        """
        Process a commission payment for a reseller
        """
        # Get the reseller
        reseller = self.db.query(Reseller).filter(Reseller.id == request.reseller_id).first()
        if not reseller:
            raise ValueError(f"Reseller with ID {request.reseller_id} not found")
        
        # Create a commission payout record
        payout = ResellerCommissionPayout(
            reseller_id=reseller.id,
            amount=request.amount,
            period_start=datetime.utcnow() - timedelta(days=30),  # Default to last 30 days
            period_end=datetime.utcnow(),
            status="completed",
            payment_method=request.payment_method,
            payment_reference=request.payment_reference,
            notes=request.notes,
            processed_at=datetime.utcnow()
        )
        
        self.db.add(payout)
        self.db.flush()
        
        # Create a transaction record
        transaction = ResellerTransaction(
            reseller_id=reseller.id,
            amount=-request.amount,  # Negative amount for payment to reseller
            transaction_type=ResellerTransactionType.PAYMENT,
            description=f"Commission payment: {request.payment_method}",
            reference_id=request.payment_reference,
            balance_after=reseller.current_balance - request.amount
        )
        
        self.db.add(transaction)
        self.db.flush()
        
        # Link the transaction to the payout
        payout_transaction = ResellerPayoutTransaction(
            payout_id=payout.id,
            transaction_id=transaction.id
        )
        
        self.db.add(payout_transaction)
        
        # Update reseller balance
        reseller.current_balance -= request.amount
        
        self.db.commit()
        
        return {
            "payout_id": payout.id,
            "transaction_id": transaction.id,
            "amount": request.amount,
            "new_balance": reseller.current_balance,
            "status": "completed",
            "processed_at": payout.processed_at.isoformat()
        }
    
    def get_commission_history(self, reseller_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get commission payment history for a reseller
        """
        payouts = self.db.query(ResellerCommissionPayout).filter(
            ResellerCommissionPayout.reseller_id == reseller_id
        ).order_by(
            ResellerCommissionPayout.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        result = []
        for payout in payouts:
            result.append({
                "id": payout.id,
                "amount": payout.amount,
                "period_start": payout.period_start.isoformat(),
                "period_end": payout.period_end.isoformat(),
                "status": payout.status,
                "payment_method": payout.payment_method,
                "payment_reference": payout.payment_reference,
                "notes": payout.notes,
                "processed_at": payout.processed_at.isoformat() if payout.processed_at else None,
                "created_at": payout.created_at.isoformat()
            })
        
        return result
    
    def get_tier_benefits(self, tier: str) -> Dict[str, Any]:
        """
        Get benefits for a specific reseller tier
        """
        tier_benefits = self.db.query(ResellerTierBenefit).filter(
            ResellerTierBenefit.tier == tier,
            ResellerTierBenefit.is_active == True
        ).first()
        
        if not tier_benefits:
            return {
                "tier": tier,
                "description": "Standard tier benefits",
                "commission_multiplier": 1.0,
                "features": [],
                "requirements": {}
            }
        
        return {
            "tier": tier_benefits.tier,
            "description": tier_benefits.description,
            "commission_multiplier": tier_benefits.commission_multiplier,
            "features": tier_benefits.features or [],
            "requirements": tier_benefits.requirements or {}
        }
    
    def get_all_tier_benefits(self) -> List[Dict[str, Any]]:
        """
        Get benefits for all reseller tiers
        """
        tier_benefits = self.db.query(ResellerTierBenefit).filter(
            ResellerTierBenefit.is_active == True
        ).all()
        
        result = []
        for benefit in tier_benefits:
            result.append({
                "tier": benefit.tier,
                "description": benefit.description,
                "commission_multiplier": benefit.commission_multiplier,
                "features": benefit.features or [],
                "requirements": benefit.requirements or {}
            })
        
        return result
