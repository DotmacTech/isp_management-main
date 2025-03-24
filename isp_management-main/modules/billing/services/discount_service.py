from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from fastapi import HTTPException
import uuid

from backend_core.models import User
from modules.billing.models import (
    Discount, DiscountType, DiscountStatus,
    DiscountUsage, TariffPlan
)
from modules.billing.schemas.discount import (
    DiscountCreate, DiscountUpdate, DiscountUsageCreate
)
from modules.billing.utils.audit import log_billing_action


class DiscountService:
    """Service for managing discounts, promotions, and coupon codes"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_discount(self, discount_data: DiscountCreate) -> Discount:
        """Creates a new discount."""
        # Generate code if not provided
        if not discount_data.code and discount_data.discount_type == DiscountType.COUPON:
            discount_data.code = self._generate_unique_code()
        
        # Create discount
        discount = Discount(
            name=discount_data.name,
            description=discount_data.description,
            discount_type=discount_data.discount_type,
            amount=discount_data.amount,
            is_percentage=discount_data.is_percentage,
            code=discount_data.code,
            valid_from=discount_data.valid_from or datetime.utcnow(),
            valid_to=discount_data.valid_to,
            max_uses=discount_data.max_uses,
            max_uses_per_user=discount_data.max_uses_per_user,
            min_order_amount=discount_data.min_order_amount,
            status=DiscountStatus.ACTIVE,
            applicable_plans=discount_data.applicable_plans
        )
        
        self.db.add(discount)
        self.db.commit()
        self.db.refresh(discount)
        
        # Log the action
        log_billing_action(
            self.db, 
            "discount", 
            discount.id, 
            "create", 
            None,  # Admin action, no user ID
            {"name": discount.name, "amount": str(discount.amount)}
        )
        
        return discount
    
    def _generate_unique_code(self, length: int = 8) -> str:
        """Generates a unique discount code."""
        code = str(uuid.uuid4()).upper()[:length]
        
        # Check if code already exists
        while self.db.query(Discount).filter(Discount.code == code).first():
            code = str(uuid.uuid4()).upper()[:length]
        
        return code
    
    def get_discount(self, discount_id: int) -> Optional[Discount]:
        """Retrieves a discount by ID."""
        return self.db.query(Discount).filter(Discount.id == discount_id).first()
    
    def get_discount_by_code(self, code: str) -> Optional[Discount]:
        """Retrieves a discount by code."""
        return self.db.query(Discount).filter(
            func.upper(Discount.code) == code.upper(),
            Discount.status == DiscountStatus.ACTIVE
        ).first()
    
    def get_active_discounts(self, discount_type: Optional[DiscountType] = None) -> List[Discount]:
        """Gets all active discounts, optionally filtered by type."""
        now = datetime.utcnow()
        
        query = self.db.query(Discount).filter(
            Discount.status == DiscountStatus.ACTIVE,
            or_(
                Discount.valid_from.is_(None),
                Discount.valid_from <= now
            ),
            or_(
                Discount.valid_to.is_(None),
                Discount.valid_to > now
            )
        )
        
        if discount_type:
            query = query.filter(Discount.discount_type == discount_type)
            
        return query.order_by(desc(Discount.created_at)).all()
    
    def update_discount(self, discount_id: int, discount_data: DiscountUpdate) -> Discount:
        """Updates an existing discount."""
        discount = self.get_discount(discount_id)
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        
        # Update fields
        for field, value in discount_data.dict(exclude_unset=True).items():
            if hasattr(discount, field) and field not in ['id', 'created_at']:
                setattr(discount, field, value)
        
        discount.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(discount)
        
        # Log the action
        log_billing_action(
            self.db, 
            "discount", 
            discount.id, 
            "update", 
            None,  # Admin action, no user ID
            {"name": discount.name, "status": discount.status}
        )
        
        return discount
    
    def deactivate_discount(self, discount_id: int) -> Discount:
        """Deactivates a discount."""
        discount = self.get_discount(discount_id)
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        
        discount.status = DiscountStatus.INACTIVE
        discount.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(discount)
        
        # Log the action
        log_billing_action(
            self.db, 
            "discount", 
            discount.id, 
            "deactivate", 
            None,  # Admin action, no user ID
            {"name": discount.name}
        )
        
        return discount
    
    def record_discount_usage(self, usage_data: DiscountUsageCreate) -> DiscountUsage:
        """Records usage of a discount."""
        # Verify discount exists
        discount = self.get_discount(usage_data.discount_id)
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        
        # Verify user exists if provided
        if usage_data.user_id:
            user = self.db.query(User).filter(User.id == usage_data.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
        
        # Create usage record
        usage = DiscountUsage(
            discount_id=usage_data.discount_id,
            user_id=usage_data.user_id,
            invoice_id=usage_data.invoice_id,
            amount=usage_data.amount
        )
        
        self.db.add(usage)
        
        # Update discount usage count
        discount.times_used = (discount.times_used or 0) + 1
        
        self.db.commit()
        self.db.refresh(usage)
        
        return usage
    
    def get_discount_usage(self, discount_id: int) -> List[DiscountUsage]:
        """Gets usage records for a discount."""
        return self.db.query(DiscountUsage).filter(
            DiscountUsage.discount_id == discount_id
        ).order_by(desc(DiscountUsage.created_at)).all()
    
    def get_user_discount_usage(self, discount_id: int, user_id: int) -> List[DiscountUsage]:
        """Gets usage records for a discount by a specific user."""
        return self.db.query(DiscountUsage).filter(
            DiscountUsage.discount_id == discount_id,
            DiscountUsage.user_id == user_id
        ).order_by(desc(DiscountUsage.created_at)).all()
    
    def validate_discount(self, discount_id: int, user_id: Optional[int] = None, amount: Optional[Decimal] = None, plan_id: Optional[int] = None) -> Dict[str, Any]:
        """Validates if a discount can be applied."""
        discount = self.get_discount(discount_id)
        if not discount:
            return {"valid": False, "reason": "Discount not found"}
        
        now = datetime.utcnow()
        
        # Check if discount is active
        if discount.status != DiscountStatus.ACTIVE:
            return {"valid": False, "reason": "Discount is not active"}
        
        # Check validity period
        if discount.valid_from and discount.valid_from > now:
            return {"valid": False, "reason": "Discount is not yet valid"}
        
        if discount.valid_to and discount.valid_to <= now:
            return {"valid": False, "reason": "Discount has expired"}
        
        # Check max uses
        if discount.max_uses and discount.times_used and discount.times_used >= discount.max_uses:
            return {"valid": False, "reason": "Discount has reached maximum uses"}
        
        # Check min order amount
        if amount and discount.min_order_amount and amount < discount.min_order_amount:
            return {
                "valid": False, 
                "reason": f"Order amount must be at least {discount.min_order_amount}"
            }
        
        # Check applicable plans
        if plan_id and discount.applicable_plans:
            applicable_plans = [int(plan_id) for plan_id in discount.applicable_plans.split(',')]
            if plan_id not in applicable_plans:
                return {"valid": False, "reason": "Discount not applicable to this plan"}
        
        # Check user-specific limits
        if user_id and discount.max_uses_per_user:
            user_usage_count = self.db.query(DiscountUsage).filter(
                DiscountUsage.discount_id == discount_id,
                DiscountUsage.user_id == user_id
            ).count()
            
            if user_usage_count >= discount.max_uses_per_user:
                return {
                    "valid": False, 
                    "reason": f"You have already used this discount {user_usage_count} times"
                }
        
        return {"valid": True}
    
    def validate_discount_code(self, code: str, user_id: Optional[int] = None, amount: Optional[Decimal] = None, plan_id: Optional[int] = None) -> Dict[str, Any]:
        """Validates if a discount code can be applied."""
        discount = self.get_discount_by_code(code)
        if not discount:
            return {"valid": False, "reason": "Invalid discount code"}
        
        return self.validate_discount(discount.id, user_id, amount, plan_id)
    
    def calculate_discount_amount(self, discount_id: int, base_amount: Decimal) -> Dict[str, Any]:
        """Calculates the discount amount for a given base amount."""
        discount = self.get_discount(discount_id)
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        
        if discount.is_percentage:
            # Calculate percentage discount
            discount_amount = (base_amount * discount.amount) / Decimal('100.00')
        else:
            # Fixed amount discount
            discount_amount = min(discount.amount, base_amount)
        
        # Round to 2 decimal places
        discount_amount = discount_amount.quantize(Decimal('0.01'))
        
        return {
            "discount_id": discount.id,
            "discount_name": discount.name,
            "discount_code": discount.code,
            "base_amount": base_amount,
            "discount_amount": discount_amount,
            "final_amount": base_amount - discount_amount,
            "is_percentage": discount.is_percentage,
            "percentage_or_amount": discount.amount
        }
    
    def get_applicable_discounts_for_plan(self, plan_id: int) -> List[Discount]:
        """Gets all active discounts applicable to a specific plan."""
        now = datetime.utcnow()
        
        # Get plan-specific discounts
        plan_specific = self.db.query(Discount).filter(
            Discount.status == DiscountStatus.ACTIVE,
            or_(
                Discount.valid_from.is_(None),
                Discount.valid_from <= now
            ),
            or_(
                Discount.valid_to.is_(None),
                Discount.valid_to > now
            ),
            Discount.applicable_plans.contains(str(plan_id))
        ).all()
        
        # Get global discounts (applicable to all plans)
        global_discounts = self.db.query(Discount).filter(
            Discount.status == DiscountStatus.ACTIVE,
            or_(
                Discount.valid_from.is_(None),
                Discount.valid_from <= now
            ),
            or_(
                Discount.valid_to.is_(None),
                Discount.valid_to > now
            ),
            or_(
                Discount.applicable_plans.is_(None),
                Discount.applicable_plans == ""
            )
        ).all()
        
        # Combine and return unique discounts
        all_discounts = plan_specific + global_discounts
        unique_discounts = {discount.id: discount for discount in all_discounts}
        
        return list(unique_discounts.values())
    
    def create_referral_discount(self, referrer_id: int, discount_percentage: Decimal = Decimal('10.00'), valid_days: int = 30) -> Discount:
        """Creates a referral discount for a new user."""
        # Get referrer user
        referrer = self.db.query(User).filter(User.id == referrer_id).first()
        if not referrer:
            raise HTTPException(status_code=404, detail="Referrer user not found")
        
        # Create a unique referral code
        referral_code = f"REF-{referrer_id}-{self._generate_unique_code(6)}"
        
        # Create the discount
        discount_data = DiscountCreate(
            name=f"Referral from {referrer.username or referrer.email}",
            description="Discount for signing up through a referral",
            discount_type=DiscountType.REFERRAL,
            amount=discount_percentage,
            is_percentage=True,
            code=referral_code,
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=valid_days),
            max_uses=1,  # One-time use
            max_uses_per_user=1,
            status=DiscountStatus.ACTIVE
        )
        
        return self.create_discount(discount_data)
    
    def create_loyalty_discount(self, user_id: int, months_active: int) -> Optional[Discount]:
        """Creates a loyalty discount based on user's subscription duration."""
        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Determine discount percentage based on loyalty
        if months_active >= 36:  # 3+ years
            discount_percentage = Decimal('20.00')
            discount_name = "Gold Loyalty Discount"
        elif months_active >= 24:  # 2+ years
            discount_percentage = Decimal('15.00')
            discount_name = "Silver Loyalty Discount"
        elif months_active >= 12:  # 1+ year
            discount_percentage = Decimal('10.00')
            discount_name = "Bronze Loyalty Discount"
        else:
            # No loyalty discount for less than a year
            return None
        
        # Create a unique loyalty code
        loyalty_code = f"LOYAL-{user_id}-{self._generate_unique_code(4)}"
        
        # Create the discount
        discount_data = DiscountCreate(
            name=discount_name,
            description=f"Loyalty discount for {months_active} months of service",
            discount_type=DiscountType.LOYALTY,
            amount=discount_percentage,
            is_percentage=True,
            code=loyalty_code,
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=30),  # Valid for 30 days
            max_uses=1,  # One-time use
            max_uses_per_user=1,
            status=DiscountStatus.ACTIVE
        )
        
        return self.create_discount(discount_data)
    
    def create_seasonal_promotion(self, name: str, description: str, discount_percentage: Decimal, valid_days: int, applicable_plan_ids: List[int] = None) -> Discount:
        """Creates a seasonal promotion discount."""
        # Generate a promotional code
        promo_code = f"PROMO-{self._generate_unique_code(6)}"
        
        # Format applicable plans
        applicable_plans = None
        if applicable_plan_ids:
            applicable_plans = ",".join(str(plan_id) for plan_id in applicable_plan_ids)
        
        # Create the discount
        discount_data = DiscountCreate(
            name=name,
            description=description,
            discount_type=DiscountType.PROMOTION,
            amount=discount_percentage,
            is_percentage=True,
            code=promo_code,
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=valid_days),
            status=DiscountStatus.ACTIVE,
            applicable_plans=applicable_plans
        )
        
        return self.create_discount(discount_data)
