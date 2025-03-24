from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from fastapi import HTTPException

from backend_core.models import User, TariffPlan
from modules.billing.models import (
    Subscription, SubscriptionStatus, BillingCycle,
    RecurringBillingProfile, UsageRecord, TieredPricing
)
from modules.billing.schemas.subscription import (
    SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse,
    RecurringBillingProfileCreate, UsageRecordCreate
)
from modules.billing.services.invoice_service import InvoiceService
from modules.billing.utils.audit import log_billing_action


class SubscriptionService:
    """Service for managing subscriptions and usage-based billing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.invoice_service = InvoiceService(db)
    
    def create_subscription(self, subscription_data: SubscriptionCreate) -> Subscription:
        """Creates a new subscription for a user."""
        # Verify user exists
        user = self.db.query(User).filter(User.id == subscription_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify plan exists
        plan = self.db.query(TariffPlan).filter(TariffPlan.id == subscription_data.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Tariff plan not found")
        
        # Check if user already has an active subscription for this plan
        existing_subscription = self.db.query(Subscription).filter(
            Subscription.user_id == subscription_data.user_id,
            Subscription.plan_id == subscription_data.plan_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
        
        if existing_subscription:
            raise HTTPException(
                status_code=400, 
                detail="User already has an active subscription for this plan"
            )
        
        # Create subscription
        subscription = Subscription(
            user_id=subscription_data.user_id,
            plan_id=subscription_data.plan_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=subscription_data.start_date or datetime.utcnow()
        )
        
        # Set trial period if specified
        if subscription_data.trial_days:
            subscription.trial_end_date = subscription.start_date + timedelta(days=subscription_data.trial_days)
            subscription.status = SubscriptionStatus.TRIAL
        
        # Set end date if not auto-renewing
        if not subscription_data.auto_renew:
            # Calculate end date based on billing cycle
            if subscription_data.billing_cycle == BillingCycle.MONTHLY:
                subscription.end_date = subscription.start_date + timedelta(days=30)
            elif subscription_data.billing_cycle == BillingCycle.QUARTERLY:
                subscription.end_date = subscription.start_date + timedelta(days=90)
            elif subscription_data.billing_cycle == BillingCycle.SEMI_ANNUAL:
                subscription.end_date = subscription.start_date + timedelta(days=180)
            elif subscription_data.billing_cycle == BillingCycle.ANNUAL:
                subscription.end_date = subscription.start_date + timedelta(days=365)
            else:
                # Default to monthly
                subscription.end_date = subscription.start_date + timedelta(days=30)
        
        # Set current period
        subscription.current_period_start = subscription.start_date
        if subscription.end_date:
            subscription.current_period_end = subscription.end_date
        elif subscription_data.billing_cycle == BillingCycle.MONTHLY:
            subscription.current_period_end = subscription.start_date + timedelta(days=30)
        elif subscription_data.billing_cycle == BillingCycle.QUARTERLY:
            subscription.current_period_end = subscription.start_date + timedelta(days=90)
        elif subscription_data.billing_cycle == BillingCycle.SEMI_ANNUAL:
            subscription.current_period_end = subscription.start_date + timedelta(days=180)
        elif subscription_data.billing_cycle == BillingCycle.ANNUAL:
            subscription.current_period_end = subscription.start_date + timedelta(days=365)
        else:
            # Default to monthly
            subscription.current_period_end = subscription.start_date + timedelta(days=30)
        
        # Create or link to a billing profile
        if subscription_data.billing_profile_id:
            # Verify billing profile exists
            billing_profile = self.db.query(RecurringBillingProfile).filter(
                RecurringBillingProfile.id == subscription_data.billing_profile_id
            ).first()
            
            if not billing_profile:
                raise HTTPException(status_code=404, detail="Billing profile not found")
                
            subscription.billing_profile_id = subscription_data.billing_profile_id
        elif subscription_data.create_billing_profile:
            # Create new billing profile
            billing_profile = RecurringBillingProfile(
                user_id=subscription_data.user_id,
                name=f"{plan.name} Subscription",
                billing_cycle=subscription_data.billing_cycle or BillingCycle.MONTHLY,
                next_billing_date=subscription.current_period_end,
                amount=plan.monthly_fee,
                currency=subscription_data.currency or "USD",
                is_active=True,
                auto_renew=subscription_data.auto_renew or True
            )
            
            self.db.add(billing_profile)
            self.db.flush()
            
            subscription.billing_profile_id = billing_profile.id
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log the action
        log_billing_action(
            self.db, 
            "subscription", 
            subscription.id, 
            "create", 
            subscription_data.user_id, 
            {"plan_id": subscription.plan_id, "status": subscription.status}
        )
        
        return subscription
    
    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """Retrieves a subscription by ID."""
        return self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    def get_user_subscriptions(self, user_id: int, include_inactive: bool = False) -> List[Subscription]:
        """Gets all subscriptions for a specific user."""
        query = self.db.query(Subscription).filter(Subscription.user_id == user_id)
        
        if not include_inactive:
            query = query.filter(Subscription.status.in_([
                SubscriptionStatus.ACTIVE, 
                SubscriptionStatus.TRIAL,
                SubscriptionStatus.PAST_DUE
            ]))
            
        return query.order_by(desc(Subscription.created_at)).all()
    
    def update_subscription(self, subscription_id: int, subscription_data: SubscriptionUpdate) -> Subscription:
        """Updates an existing subscription."""
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Update fields
        for field, value in subscription_data.dict(exclude_unset=True).items():
            if hasattr(subscription, field) and field not in ['id', 'created_at', 'user_id']:
                setattr(subscription, field, value)
        
        subscription.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log the action
        log_billing_action(
            self.db, 
            "subscription", 
            subscription.id, 
            "update", 
            subscription.user_id, 
            {"status": subscription.status}
        )
        
        return subscription
    
    def cancel_subscription(self, subscription_id: int, reason: str = None) -> Subscription:
        """Cancels a subscription."""
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if subscription.status == SubscriptionStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Subscription is already cancelled")
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
        subscription.cancellation_reason = reason
        
        # If there's a billing profile, update it
        if subscription.billing_profile_id:
            billing_profile = self.db.query(RecurringBillingProfile).filter(
                RecurringBillingProfile.id == subscription.billing_profile_id
            ).first()
            
            if billing_profile:
                # Check if this is the only subscription using this billing profile
                other_subs = self.db.query(Subscription).filter(
                    Subscription.billing_profile_id == billing_profile.id,
                    Subscription.id != subscription_id,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                ).count()
                
                if other_subs == 0:
                    billing_profile.is_active = False
                    billing_profile.auto_renew = False
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log the action
        log_billing_action(
            self.db, 
            "subscription", 
            subscription.id, 
            "cancel", 
            subscription.user_id, 
            {"reason": reason}
        )
        
        return subscription
    
    def pause_subscription(self, subscription_id: int, pause_days: int, reason: str = None) -> Subscription:
        """Pauses a subscription for a specified number of days."""
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot pause subscription with status {subscription.status}"
            )
        
        subscription.status = SubscriptionStatus.PAUSED
        subscription.pause_start = datetime.utcnow()
        subscription.pause_end = subscription.pause_start + timedelta(days=pause_days)
        
        # Extend the current period end date
        if subscription.current_period_end:
            subscription.current_period_end += timedelta(days=pause_days)
        
        # If there's a billing profile, update the next billing date
        if subscription.billing_profile_id:
            billing_profile = self.db.query(RecurringBillingProfile).filter(
                RecurringBillingProfile.id == subscription.billing_profile_id
            ).first()
            
            if billing_profile and billing_profile.next_billing_date:
                billing_profile.next_billing_date += timedelta(days=pause_days)
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log the action
        log_billing_action(
            self.db, 
            "subscription", 
            subscription.id, 
            "pause", 
            subscription.user_id, 
            {"pause_days": pause_days, "reason": reason}
        )
        
        return subscription
    
    def resume_subscription(self, subscription_id: int) -> Subscription:
        """Resumes a paused subscription."""
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if subscription.status != SubscriptionStatus.PAUSED:
            raise HTTPException(
                status_code=400, 
                detail="Only paused subscriptions can be resumed"
            )
        
        subscription.status = SubscriptionStatus.ACTIVE
        
        # If the subscription was in trial before pausing, check if trial is still valid
        if subscription.trial_end_date and subscription.trial_end_date > datetime.utcnow():
            subscription.status = SubscriptionStatus.TRIAL
        
        subscription.pause_end = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log the action
        log_billing_action(
            self.db, 
            "subscription", 
            subscription.id, 
            "resume", 
            subscription.user_id, 
            {"status": subscription.status}
        )
        
        return subscription
    
    def change_plan(self, subscription_id: int, new_plan_id: int, prorate: bool = True) -> Subscription:
        """Changes a subscription to a different plan."""
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot change plan for subscription with status {subscription.status}"
            )
        
        # Get the new plan
        new_plan = self.db.query(TariffPlan).filter(TariffPlan.id == new_plan_id).first()
        if not new_plan:
            raise HTTPException(status_code=404, detail="New tariff plan not found")
        
        # Get the old plan
        old_plan = self.db.query(TariffPlan).filter(TariffPlan.id == subscription.plan_id).first()
        if not old_plan:
            raise HTTPException(status_code=404, detail="Current tariff plan not found")
        
        # Handle proration if needed
        if prorate and subscription.current_period_end and old_plan.monthly_fee != new_plan.monthly_fee:
            # Calculate remaining days in current period
            now = datetime.utcnow()
            days_left = (subscription.current_period_end - now).days
            total_days = (subscription.current_period_end - subscription.current_period_start).days
            
            if days_left > 0 and total_days > 0:
                # Calculate prorated credit or charge
                old_daily_rate = old_plan.monthly_fee / total_days
                new_daily_rate = new_plan.monthly_fee / total_days
                
                prorated_amount = (new_daily_rate - old_daily_rate) * days_left
                
                # If positive, create a charge; if negative, create a credit
                if prorated_amount > 0:
                    # Create an invoice for the upgrade charge
                    from modules.billing.schemas.invoice import InvoiceCreate, InvoiceItemCreate
                    
                    invoice_data = InvoiceCreate(
                        user_id=subscription.user_id,
                        due_date=datetime.utcnow() + timedelta(days=7),
                        billing_country="US",  # Should be retrieved from user profile
                        currency="USD",  # Should be retrieved from user profile
                        items=[
                            InvoiceItemCreate(
                                description=f"Plan upgrade: {old_plan.name} to {new_plan.name} (prorated)",
                                quantity=1,
                                unit_price=prorated_amount
                            )
                        ]
                    )
                    
                    self.invoice_service.create_invoice(invoice_data)
                elif prorated_amount < 0:
                    # Create a credit note for the downgrade
                    from modules.billing.schemas.credit import CreditNoteCreate
                    
                    credit_data = CreditNoteCreate(
                        user_id=subscription.user_id,
                        amount=abs(prorated_amount),
                        reason=f"Plan downgrade: {old_plan.name} to {new_plan.name} (prorated)"
                    )
                    
                    # This would be handled by a credit note service
                    # self.credit_service.create_credit_note(credit_data)
        
        # Update the subscription
        old_plan_id = subscription.plan_id
        subscription.plan_id = new_plan_id
        
        # Update billing profile if exists
        if subscription.billing_profile_id:
            billing_profile = self.db.query(RecurringBillingProfile).filter(
                RecurringBillingProfile.id == subscription.billing_profile_id
            ).first()
            
            if billing_profile:
                billing_profile.amount = new_plan.monthly_fee
                billing_profile.name = f"{new_plan.name} Subscription"
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log the action
        log_billing_action(
            self.db, 
            "subscription", 
            subscription.id, 
            "change_plan", 
            subscription.user_id, 
            {"old_plan_id": old_plan_id, "new_plan_id": new_plan_id, "prorate": prorate}
        )
        
        return subscription
    
    def create_billing_profile(self, profile_data: RecurringBillingProfileCreate) -> RecurringBillingProfile:
        """Creates a new recurring billing profile."""
        # Verify user exists
        user = self.db.query(User).filter(User.id == profile_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create billing profile
        billing_profile = RecurringBillingProfile(
            user_id=profile_data.user_id,
            name=profile_data.name,
            billing_cycle=profile_data.billing_cycle,
            next_billing_date=profile_data.next_billing_date,
            amount=profile_data.amount,
            currency=profile_data.currency,
            is_active=profile_data.is_active,
            auto_renew=profile_data.auto_renew,
            grace_period_days=profile_data.grace_period_days
        )
        
        self.db.add(billing_profile)
        self.db.commit()
        self.db.refresh(billing_profile)
        
        return billing_profile
    
    def get_billing_profile(self, profile_id: int) -> Optional[RecurringBillingProfile]:
        """Retrieves a billing profile by ID."""
        return self.db.query(RecurringBillingProfile).filter(
            RecurringBillingProfile.id == profile_id
        ).first()
    
    def get_user_billing_profiles(self, user_id: int) -> List[RecurringBillingProfile]:
        """Gets all billing profiles for a specific user."""
        return self.db.query(RecurringBillingProfile).filter(
            RecurringBillingProfile.user_id == user_id
        ).all()
    
    def update_billing_profile(self, profile_id: int, profile_data: Dict[str, Any]) -> RecurringBillingProfile:
        """Updates a billing profile."""
        profile = self.get_billing_profile(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Billing profile not found")
        
        # Update fields
        for field, value in profile_data.items():
            if hasattr(profile, field) and field not in ['id', 'created_at', 'user_id']:
                setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        
        return profile
    
    def record_usage(self, usage_data: UsageRecordCreate) -> UsageRecord:
        """Records usage for usage-based billing."""
        # Verify subscription exists
        subscription = self.get_subscription(usage_data.subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Create usage record
        usage_record = UsageRecord(
            subscription_id=usage_data.subscription_id,
            quantity=usage_data.quantity,
            unit=usage_data.unit,
            timestamp=usage_data.timestamp or datetime.utcnow(),
            source=usage_data.source
        )
        
        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        return usage_record
    
    def get_subscription_usage(self, subscription_id: int, start_date: datetime = None, end_date: datetime = None) -> List[UsageRecord]:
        """Gets usage records for a subscription in a date range."""
        query = self.db.query(UsageRecord).filter(UsageRecord.subscription_id == subscription_id)
        
        if start_date:
            query = query.filter(UsageRecord.timestamp >= start_date)
            
        if end_date:
            query = query.filter(UsageRecord.timestamp <= end_date)
            
        return query.order_by(desc(UsageRecord.timestamp)).all()
    
    def calculate_usage_charges(self, subscription_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculates charges for usage-based billing."""
        # Get subscription
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Get plan
        plan = self.db.query(TariffPlan).filter(TariffPlan.id == subscription.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Tariff plan not found")
        
        # Get usage records
        usage_records = self.get_subscription_usage(subscription_id, start_date, end_date)
        
        # Get tiered pricing if available
        tiered_pricing = self.db.query(TieredPricing).filter(
            TieredPricing.plan_id == plan.id
        ).order_by(TieredPricing.tier_start).all()
        
        # Calculate total usage
        total_usage = sum(record.quantity for record in usage_records)
        
        # Calculate charges
        charges = Decimal('0.00')
        
        if tiered_pricing:
            # Apply tiered pricing
            remaining_usage = total_usage
            
            for tier in tiered_pricing:
                tier_size = (tier.tier_end - tier.tier_start) if tier.tier_end else float('inf')
                tier_usage = min(remaining_usage, tier_size)
                
                if tier_usage > 0:
                    tier_charge = Decimal(str(tier_usage)) * tier.unit_price
                    charges += tier_charge
                    remaining_usage -= tier_usage
                
                if remaining_usage <= 0:
                    break
        else:
            # Apply flat rate if no tiered pricing
            # This would be based on the plan's overage rate or a default rate
            overage_rate = Decimal('0.01')  # Default rate per unit
            charges = Decimal(str(total_usage)) * overage_rate
        
        return {
            "subscription_id": subscription_id,
            "plan_id": plan.id,
            "plan_name": plan.name,
            "start_date": start_date,
            "end_date": end_date,
            "total_usage": total_usage,
            "charges": charges,
            "usage_records": len(usage_records)
        }
    
    def process_recurring_billing(self) -> List[Dict[str, Any]]:
        """Processes recurring billing for all active subscriptions."""
        now = datetime.utcnow()
        results = []
        
        # Get all active billing profiles due for billing
        due_profiles = self.db.query(RecurringBillingProfile).filter(
            RecurringBillingProfile.is_active == True,
            RecurringBillingProfile.auto_renew == True,
            RecurringBillingProfile.next_billing_date <= now
        ).all()
        
        for profile in due_profiles:
            try:
                # Get all active subscriptions for this profile
                subscriptions = self.db.query(Subscription).filter(
                    Subscription.billing_profile_id == profile.id,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE])
                ).all()
                
                if not subscriptions:
                    continue
                
                # Create invoice for subscription renewal
                from modules.billing.schemas.invoice import InvoiceCreate, InvoiceItemCreate
                
                invoice_items = []
                
                for subscription in subscriptions:
                    # Get plan details
                    plan = self.db.query(TariffPlan).filter(TariffPlan.id == subscription.plan_id).first()
                    if not plan:
                        continue
                    
                    # Add base subscription fee
                    invoice_items.append(
                        InvoiceItemCreate(
                            description=f"{plan.name} Subscription - {profile.billing_cycle}",
                            quantity=1,
                            unit_price=plan.monthly_fee
                        )
                    )
                    
                    # Add usage-based charges if applicable
                    if subscription.current_period_start and subscription.current_period_end:
                        usage_charges = self.calculate_usage_charges(
                            subscription.id,
                            subscription.current_period_start,
                            subscription.current_period_end
                        )
                        
                        if usage_charges["charges"] > 0:
                            invoice_items.append(
                                InvoiceItemCreate(
                                    description=f"Usage charges - {usage_charges['total_usage']} {usage_charges.get('unit', 'units')}",
                                    quantity=1,
                                    unit_price=usage_charges["charges"]
                                )
                            )
                    
                    # Update subscription periods
                    if profile.billing_cycle == BillingCycle.MONTHLY:
                        next_period = timedelta(days=30)
                    elif profile.billing_cycle == BillingCycle.QUARTERLY:
                        next_period = timedelta(days=90)
                    elif profile.billing_cycle == BillingCycle.SEMI_ANNUAL:
                        next_period = timedelta(days=180)
                    elif profile.billing_cycle == BillingCycle.ANNUAL:
                        next_period = timedelta(days=365)
                    else:
                        next_period = timedelta(days=30)
                    
                    subscription.current_period_start = now
                    subscription.current_period_end = now + next_period
                
                # Create the invoice if there are items
                if invoice_items:
                    invoice_data = InvoiceCreate(
                        user_id=profile.user_id,
                        due_date=now + timedelta(days=7),
                        billing_country="US",  # Should be retrieved from user profile
                        currency=profile.currency,
                        items=invoice_items
                    )
                    
                    invoice = self.invoice_service.create_invoice(invoice_data)
                    
                    # Update billing profile next billing date
                    if profile.billing_cycle == BillingCycle.MONTHLY:
                        profile.next_billing_date = now + timedelta(days=30)
                    elif profile.billing_cycle == BillingCycle.QUARTERLY:
                        profile.next_billing_date = now + timedelta(days=90)
                    elif profile.billing_cycle == BillingCycle.SEMI_ANNUAL:
                        profile.next_billing_date = now + timedelta(days=180)
                    elif profile.billing_cycle == BillingCycle.ANNUAL:
                        profile.next_billing_date = now + timedelta(days=365)
                    else:
                        profile.next_billing_date = now + timedelta(days=30)
                    
                    results.append({
                        "profile_id": profile.id,
                        "user_id": profile.user_id,
                        "invoice_id": invoice.id,
                        "amount": str(invoice.amount),
                        "next_billing_date": profile.next_billing_date.isoformat(),
                        "subscriptions": len(subscriptions)
                    })
            except Exception as e:
                # Log error but continue processing other profiles
                results.append({
                    "profile_id": profile.id,
                    "user_id": profile.user_id,
                    "error": str(e),
                    "status": "failed"
                })
        
        self.db.commit()
        return results
    
    def check_trial_expirations(self) -> List[Dict[str, Any]]:
        """Checks for trial subscriptions that have expired and updates their status."""
        now = datetime.utcnow()
        results = []
        
        # Get all trial subscriptions that have expired
        expired_trials = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.TRIAL,
            Subscription.trial_end_date <= now
        ).all()
        
        for subscription in expired_trials:
            try:
                # Convert to active subscription
                subscription.status = SubscriptionStatus.ACTIVE
                
                # Log the action
                log_billing_action(
                    self.db, 
                    "subscription", 
                    subscription.id, 
                    "trial_expired", 
                    subscription.user_id, 
                    {"new_status": subscription.status}
                )
                
                results.append({
                    "subscription_id": subscription.id,
                    "user_id": subscription.user_id,
                    "plan_id": subscription.plan_id,
                    "trial_end_date": subscription.trial_end_date.isoformat(),
                    "new_status": subscription.status
                })
            except Exception as e:
                # Log error but continue processing other subscriptions
                results.append({
                    "subscription_id": subscription.id,
                    "user_id": subscription.user_id,
                    "error": str(e),
                    "status": "failed"
                })
        
        self.db.commit()
        return results
