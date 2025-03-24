from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend_core.models import (
    Reseller, 
    ResellerCustomer, 
    ResellerTransaction, 
    ResellerCommissionRule,
    Customer,
    User,
    TariffPlan
)
from .schemas import (
    ResellerCreate,
    ResellerResponse,
    ResellerCustomerCreate,
    ResellerCustomerResponse,
    ResellerTransactionCreate,
    ResellerTransactionResponse,
    ResellerCommissionRuleCreate,
    ResellerCommissionRuleResponse,
    ResellerSearch,
    ResellerStatus,
    ResellerTier,
    ResellerTransactionType
)

class ResellerService:
    def __init__(self, db: Session):
        self.db = db

    # Reseller Management
    def create_reseller(self, reseller_data: ResellerCreate) -> Reseller:
        """Create a new reseller profile."""
        # Check if user exists
        user = self.db.query(User).filter(User.id == reseller_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {reseller_data.user_id} not found"
            )
        
        # Check if reseller already exists for this user
        existing_reseller = self.db.query(Reseller).filter(
            Reseller.user_id == reseller_data.user_id
        ).first()
        
        if existing_reseller:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Reseller profile already exists for user ID {reseller_data.user_id}"
            )
        
        # Create new reseller
        reseller = Reseller(**reseller_data.dict(), current_balance=0.0)
        self.db.add(reseller)
        self.db.commit()
        self.db.refresh(reseller)
        
        # Update user role to reseller if it's not already
        if user.role not in ["admin", "reseller"]:
            user.role = "reseller"
            self.db.commit()
        
        return reseller

    def get_reseller(self, reseller_id: int) -> Reseller:
        """Get a reseller by ID."""
        reseller = self.db.query(Reseller).filter(Reseller.id == reseller_id).first()
        if not reseller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reseller with ID {reseller_id} not found"
            )
        return reseller

    def get_reseller_by_user_id(self, user_id: int) -> Reseller:
        """Get a reseller by user ID."""
        reseller = self.db.query(Reseller).filter(Reseller.user_id == user_id).first()
        if not reseller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reseller profile not found for user ID {user_id}"
            )
        return reseller

    def update_reseller(self, reseller_id: int, reseller_data: Dict[str, Any]) -> Reseller:
        """Update a reseller's information."""
        reseller = self.get_reseller(reseller_id)
        
        for key, value in reseller_data.items():
            setattr(reseller, key, value)
        
        reseller.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(reseller)
        return reseller

    def search_resellers(self, search_params: ResellerSearch) -> List[Reseller]:
        """Search for resellers based on query, status, and tier."""
        query = self.db.query(Reseller)
        
        if search_params.status:
            query = query.filter(Reseller.status == search_params.status)
        
        if search_params.tier:
            query = query.filter(Reseller.tier == search_params.tier)
        
        if search_params.query:
            search_term = f"%{search_params.query}%"
            query = query.filter(
                or_(
                    Reseller.company_name.ilike(search_term),
                    Reseller.contact_person.ilike(search_term),
                    Reseller.email.ilike(search_term),
                    Reseller.phone.ilike(search_term)
                )
            )
        
        return query.offset(search_params.offset).limit(search_params.limit).all()

    def get_reseller_statistics(self, reseller_id: int) -> Dict[str, Any]:
        """Get statistics about a reseller."""
        reseller = self.get_reseller(reseller_id)
        
        # Count customers
        customer_count = self.db.query(func.count(ResellerCustomer.id)).filter(
            ResellerCustomer.reseller_id == reseller_id
        ).scalar()
        
        # Calculate total revenue (sum of all commission transactions)
        total_revenue = self.db.query(func.sum(ResellerTransaction.amount)).filter(
            ResellerTransaction.reseller_id == reseller_id,
            ResellerTransaction.transaction_type == ResellerTransactionType.COMMISSION
        ).scalar() or 0.0
        
        # Get recent transactions
        recent_transactions = self.db.query(ResellerTransaction).filter(
            ResellerTransaction.reseller_id == reseller_id
        ).order_by(desc(ResellerTransaction.created_at)).limit(5).all()
        
        return {
            "reseller_id": reseller_id,
            "company_name": reseller.company_name,
            "status": reseller.status,
            "tier": reseller.tier,
            "current_balance": reseller.current_balance,
            "customer_count": customer_count,
            "total_revenue": total_revenue,
            "recent_transactions": [
                {
                    "id": t.id,
                    "amount": t.amount,
                    "transaction_type": t.transaction_type,
                    "description": t.description,
                    "created_at": t.created_at
                } for t in recent_transactions
            ]
        }

    # Customer Management
    def assign_customer_to_reseller(self, assignment_data: ResellerCustomerCreate) -> ResellerCustomer:
        """Assign a customer to a reseller."""
        # Check if reseller exists
        reseller = self.db.query(Reseller).filter(Reseller.id == assignment_data.reseller_id).first()
        if not reseller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reseller with ID {assignment_data.reseller_id} not found"
            )
        
        # Check if customer exists
        customer = self.db.query(Customer).filter(Customer.id == assignment_data.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {assignment_data.customer_id} not found"
            )
        
        # Check if customer is already assigned to this reseller
        existing_assignment = self.db.query(ResellerCustomer).filter(
            ResellerCustomer.reseller_id == assignment_data.reseller_id,
            ResellerCustomer.customer_id == assignment_data.customer_id
        ).first()
        
        if existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer is already assigned to this reseller"
            )
        
        # Check if customer is already assigned to another reseller
        other_assignment = self.db.query(ResellerCustomer).filter(
            ResellerCustomer.customer_id == assignment_data.customer_id
        ).first()
        
        if other_assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer is already assigned to another reseller (ID: {other_assignment.reseller_id})"
            )
        
        # Create new assignment
        assignment = ResellerCustomer(**assignment_data.dict())
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def get_reseller_customers(self, reseller_id: int) -> List[Dict[str, Any]]:
        """Get all customers assigned to a reseller."""
        # Check if reseller exists
        self.get_reseller(reseller_id)
        
        # Get all customer assignments
        assignments = self.db.query(ResellerCustomer).filter(
            ResellerCustomer.reseller_id == reseller_id
        ).all()
        
        # Get customer details for each assignment
        result = []
        for assignment in assignments:
            customer = self.db.query(Customer).filter(Customer.id == assignment.customer_id).first()
            if customer:
                result.append({
                    "id": assignment.id,
                    "reseller_id": assignment.reseller_id,
                    "customer_id": customer.id,
                    "customer_name": customer.full_name,
                    "customer_email": customer.email,
                    "customer_status": customer.status,
                    "notes": assignment.notes,
                    "created_at": assignment.created_at
                })
        
        return result

    def remove_customer_from_reseller(self, assignment_id: int) -> Dict[str, Any]:
        """Remove a customer from a reseller."""
        assignment = self.db.query(ResellerCustomer).filter(ResellerCustomer.id == assignment_id).first()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer assignment with ID {assignment_id} not found"
            )
        
        customer_id = assignment.customer_id
        reseller_id = assignment.reseller_id
        
        self.db.delete(assignment)
        self.db.commit()
        
        return {
            "message": "Customer removed from reseller successfully",
            "customer_id": customer_id,
            "reseller_id": reseller_id
        }

    # Transaction Management
    def create_transaction(self, transaction_data: ResellerTransactionCreate) -> ResellerTransaction:
        """Create a new transaction for a reseller."""
        # Check if reseller exists
        reseller = self.get_reseller(transaction_data.reseller_id)
        
        # Calculate new balance
        new_balance = reseller.current_balance + transaction_data.amount
        
        # Create transaction
        transaction = ResellerTransaction(
            **transaction_data.dict(),
            balance_after=new_balance
        )
        
        # Update reseller balance
        reseller.current_balance = new_balance
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_reseller_transactions(self, reseller_id: int, limit: int = 50, offset: int = 0) -> List[ResellerTransaction]:
        """Get all transactions for a reseller."""
        # Check if reseller exists
        self.get_reseller(reseller_id)
        
        return self.db.query(ResellerTransaction).filter(
            ResellerTransaction.reseller_id == reseller_id
        ).order_by(desc(ResellerTransaction.created_at)).offset(offset).limit(limit).all()

    # Commission Rules Management
    def create_commission_rule(self, rule_data: ResellerCommissionRuleCreate) -> ResellerCommissionRule:
        """Create a new commission rule for a reseller."""
        # Check if reseller exists
        self.get_reseller(rule_data.reseller_id)
        
        # Check if tariff plan exists
        tariff_plan = self.db.query(TariffPlan).filter(TariffPlan.id == rule_data.tariff_plan_id).first()
        if not tariff_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tariff plan with ID {rule_data.tariff_plan_id} not found"
            )
        
        # Check if rule already exists for this reseller and tariff plan
        existing_rule = self.db.query(ResellerCommissionRule).filter(
            ResellerCommissionRule.reseller_id == rule_data.reseller_id,
            ResellerCommissionRule.tariff_plan_id == rule_data.tariff_plan_id
        ).first()
        
        if existing_rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Commission rule already exists for this reseller and tariff plan"
            )
        
        # Create new rule
        rule = ResellerCommissionRule(**rule_data.dict())
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_reseller_commission_rules(self, reseller_id: int) -> List[Dict[str, Any]]:
        """Get all commission rules for a reseller."""
        # Check if reseller exists
        self.get_reseller(reseller_id)
        
        rules = self.db.query(ResellerCommissionRule).filter(
            ResellerCommissionRule.reseller_id == reseller_id
        ).all()
        
        result = []
        for rule in rules:
            tariff_plan = self.db.query(TariffPlan).filter(TariffPlan.id == rule.tariff_plan_id).first()
            if tariff_plan:
                result.append({
                    "id": rule.id,
                    "reseller_id": rule.reseller_id,
                    "tariff_plan_id": rule.tariff_plan_id,
                    "tariff_plan_name": tariff_plan.name,
                    "commission_type": rule.commission_type,
                    "commission_rate": rule.commission_rate,
                    "min_customers": rule.min_customers,
                    "max_customers": rule.max_customers,
                    "created_at": rule.created_at,
                    "updated_at": rule.updated_at
                })
        
        return result

    def update_commission_rule(self, rule_id: int, rule_data: Dict[str, Any]) -> ResellerCommissionRule:
        """Update a commission rule."""
        rule = self.db.query(ResellerCommissionRule).filter(ResellerCommissionRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Commission rule with ID {rule_id} not found"
            )
        
        for key, value in rule_data.items():
            setattr(rule, key, value)
        
        rule.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_commission_rule(self, rule_id: int) -> Dict[str, Any]:
        """Delete a commission rule."""
        rule = self.db.query(ResellerCommissionRule).filter(ResellerCommissionRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Commission rule with ID {rule_id} not found"
            )
        
        reseller_id = rule.reseller_id
        tariff_plan_id = rule.tariff_plan_id
        
        self.db.delete(rule)
        self.db.commit()
        
        return {
            "message": "Commission rule deleted successfully",
            "reseller_id": reseller_id,
            "tariff_plan_id": tariff_plan_id
        }
