from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union, Tuple
from decimal import Decimal
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, BackgroundTasks

from backend_core.models import (
    TariffPlan, User, RadiusProfile, UserTariffPlan, UserUsageRecord,
    TariffPolicyAction, TariffPlanChange, NotificationTemplate,
    RadiusBandwidthPolicy, RadiusAccounting, RadiusCoALog
)
from modules.radius.services import RadiusService
from .schemas import (
    TariffPlanCreate, TariffPlanUpdate,
    UserTariffPlanCreate, UserTariffPlanUpdate,
    UserUsageRecordCreate,
    TariffPolicyActionCreate, TariffPolicyActionUpdate,
    TariffPlanChangeCreate, TariffPlanChangeUpdate,
    NotificationTemplateCreate, NotificationTemplateUpdate,
    UsageCheckRequest, UsageCheckResponse,
    BandwidthPolicyResponse, TariffAssignmentCreate,
    FUPThresholdCheck, FUPThresholdResponse
)

from modules.tariff.radius_integration import radius_integration
from modules.tariff.billing_integration import billing_integration

logger = logging.getLogger(__name__)

class TariffService:
    def __init__(self, db: Session):
        self.db = db
        self.radius_service = RadiusService(db)

    def create_tariff_plan(self, plan_data: TariffPlanCreate) -> TariffPlan:
        """Creates a new tariff plan."""
        # Check if a plan with the same name already exists
        existing_plan = (
            self.db.query(TariffPlan)
            .filter(TariffPlan.name == plan_data.name)
            .first()
        )
        if existing_plan:
            raise HTTPException(status_code=400, detail="A plan with this name already exists")
        
        # Create new plan
        plan_dict = plan_data.dict()
        plan = TariffPlan(**plan_dict)
        
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_tariff_plan(self, plan_id: int) -> Optional[TariffPlan]:
        """Retrieves a tariff plan by ID."""
        plan = self.db.query(TariffPlan).filter(TariffPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Tariff plan not found")
        return plan

    def get_all_active_plans(self) -> List[TariffPlan]:
        """Gets all active tariff plans."""
        return self.db.query(TariffPlan).filter(TariffPlan.is_active == True).all()

    def update_tariff_plan(self, plan_id: int, plan_data: TariffPlanUpdate) -> TariffPlan:
        """Updates an existing tariff plan."""
        plan = self.get_tariff_plan(plan_id)
        
        # Check if name is being updated and if it already exists
        if plan_data.name and plan_data.name != plan.name:
            existing_plan = (
                self.db.query(TariffPlan)
                .filter(TariffPlan.name == plan_data.name)
                .first()
            )
            if existing_plan:
                raise HTTPException(status_code=400, detail="A plan with this name already exists")
        
        # Update plan attributes
        update_data = plan_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plan, key, value)
        
        # Update timestamp
        plan.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(plan)
        
        # If the plan has associated radius policies, update them
        if plan.radius_policy_id:
            self._sync_radius_policy(plan)
        
        return plan

    def delete_tariff_plan(self, plan_id: int) -> bool:
        """Deletes a tariff plan if it's not assigned to any users."""
        plan = self.get_tariff_plan(plan_id)
        
        # Check if plan is assigned to any users
        assigned_users = (
            self.db.query(UserTariffPlan)
            .filter(
                UserTariffPlan.tariff_plan_id == plan_id,
                UserTariffPlan.status == "active"
            )
            .first()
        )
        
        if assigned_users:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete plan that is assigned to active users"
            )
        
        # Mark as inactive instead of deleting
        plan.is_active = False
        plan.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True

    def _sync_radius_policy(self, plan: TariffPlan) -> None:
        """Synchronizes the tariff plan with its associated RADIUS policy."""
        if not plan.radius_policy_id:
            return
        
        try:
            radius_policy = (
                self.db.query(RadiusBandwidthPolicy)
                .filter(RadiusBandwidthPolicy.id == plan.radius_policy_id)
                .first()
            )
            
            if radius_policy:
                # Update RADIUS policy to match tariff plan
                radius_policy.download_rate = plan.download_speed
                radius_policy.upload_rate = plan.upload_speed
                
                # Update throttled policy if it exists
                if plan.throttled_radius_policy_id:
                    throttled_policy = (
                        self.db.query(RadiusBandwidthPolicy)
                        .filter(RadiusBandwidthPolicy.id == plan.throttled_radius_policy_id)
                        .first()
                    )
                    
                    if throttled_policy:
                        throttled_policy.download_rate = plan.throttle_speed_download or plan.download_speed // 2
                        throttled_policy.upload_rate = plan.throttle_speed_upload or plan.upload_speed // 2
                        
                self.db.commit()
                logger.info(f"Synchronized RADIUS policy for tariff plan {plan.id}")
        except Exception as e:
            logger.error(f"Error synchronizing RADIUS policy: {str(e)}")

    def assign_plan_to_user(self, assignment_data: UserTariffPlanCreate) -> UserTariffPlan:
        """Assigns a tariff plan to a user."""
        # Check if user exists
        user = self.db.query(User).filter(User.id == assignment_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if plan exists and is active
        plan = self.get_tariff_plan(assignment_data.tariff_plan_id)
        if not plan.is_active:
            raise HTTPException(status_code=400, detail="Cannot assign inactive tariff plan")
        
        # Check if user already has an active plan
        existing_plan = (
            self.db.query(UserTariffPlan)
            .filter(
                UserTariffPlan.user_id == assignment_data.user_id,
                UserTariffPlan.status == "active"
            )
            .first()
        )
        
        if existing_plan:
            # Create a plan change record instead of direct assignment
            return self._handle_plan_change(existing_plan, plan, assignment_data)
        
        # Calculate billing cycle end date
        cycle_end = self._calculate_cycle_end(assignment_data.start_date, plan.billing_cycle)
        
        # Create new user tariff plan
        user_plan = UserTariffPlan(
            user_id=assignment_data.user_id,
            tariff_plan_id=assignment_data.tariff_plan_id,
            status=assignment_data.status,
            start_date=assignment_data.start_date,
            end_date=assignment_data.end_date,
            current_cycle_start=assignment_data.start_date,
            current_cycle_end=cycle_end,
            data_used=0,
            is_throttled=False
        )
        
        self.db.add(user_plan)
        self.db.commit()
        self.db.refresh(user_plan)
        
        # Apply RADIUS policy if applicable
        self._apply_radius_policy(user.id, plan)
        
        # Handle billing for the plan assignment
        try:
            billing_integration.handle_plan_assignment(
                user_id=user.id,
                plan_name=plan.name,
                price=str(plan.price),
                start_date=assignment_data.start_date,
                end_date=assignment_data.end_date
            )
        except Exception as e:
            logger.error(f"Failed to handle billing for plan assignment: {str(e)}")
        
        return user_plan

    def _handle_plan_change(self, existing_plan: UserTariffPlan, new_plan: TariffPlan, 
                           assignment_data: UserTariffPlanCreate) -> UserTariffPlan:
        """Handles changing a user from one plan to another."""
        # Determine change type
        if existing_plan.tariff_plan.price < new_plan.price:
            change_type = "upgrade"
        elif existing_plan.tariff_plan.price > new_plan.price:
            change_type = "downgrade"
        else:
            change_type = "switch"  # Same price, different plan
        
        # Create plan change record
        plan_change = TariffPlanChange(
            user_id=existing_plan.user_id,
            previous_plan_id=existing_plan.tariff_plan_id,
            new_plan_id=new_plan.id,
            change_type=change_type,
            requested_at=datetime.utcnow(),
            effective_date=assignment_data.start_date,
            status="pending",
            reason=assignment_data.get("reason", "User requested plan change")
        )
        
        self.db.add(plan_change)
        
        # If immediate effect, process the change now
        if assignment_data.start_date <= datetime.utcnow():
            # Update existing plan
            existing_plan.status = "cancelled"
            existing_plan.end_date = datetime.utcnow()
            
            # Create new plan assignment
            cycle_end = self._calculate_cycle_end(assignment_data.start_date, new_plan.billing_cycle)
            
            user_plan = UserTariffPlan(
                user_id=existing_plan.user_id,
                tariff_plan_id=new_plan.id,
                status="active",
                start_date=assignment_data.start_date,
                end_date=assignment_data.end_date,
                current_cycle_start=assignment_data.start_date,
                current_cycle_end=cycle_end,
                data_used=0,
                is_throttled=False
            )
            
            self.db.add(user_plan)
            
            # Update plan change record
            plan_change.status = "processed"
            plan_change.processed_at = datetime.utcnow()
            
            # Calculate prorated amounts if needed
            if change_type in ["upgrade", "downgrade"]:
                self._calculate_prorated_amounts(plan_change, existing_plan, new_plan)
            
            # Apply new RADIUS policy
            self._apply_radius_policy(existing_plan.user_id, new_plan)
            
            # Handle billing for the plan change
            try:
                billing_integration.handle_plan_change(
                    user_id=existing_plan.user_id,
                    previous_plan={
                        "id": existing_plan.tariff_plan_id,
                        "name": existing_plan.tariff_plan.name,
                        "price": str(existing_plan.tariff_plan.price)
                    },
                    new_plan={
                        "id": new_plan.id,
                        "name": new_plan.name,
                        "price": str(new_plan.price)
                    },
                    effective_date=assignment_data.start_date,
                    current_cycle_start=existing_plan.current_cycle_start,
                    current_cycle_end=existing_plan.current_cycle_end
                )
            except Exception as e:
                logger.error(f"Failed to handle billing for plan change: {str(e)}")
            
            self.db.commit()
            self.db.refresh(user_plan)
            return user_plan
        else:
            # Schedule the change for later
            self.db.commit()
            # Return the existing plan since the change will happen later
            return existing_plan

    def _calculate_cycle_end(self, start_date: datetime, billing_cycle: str) -> datetime:
        """Calculates the end date of a billing cycle."""
        if billing_cycle == "monthly":
            # Add one month (approximately)
            if start_date.month == 12:
                return start_date.replace(year=start_date.year + 1, month=1)
            else:
                return start_date.replace(month=start_date.month + 1)
        elif billing_cycle == "quarterly":
            # Add three months
            month = start_date.month + 3
            year = start_date.year
            if month > 12:
                month -= 12
                year += 1
            return start_date.replace(year=year, month=month)
        elif billing_cycle == "yearly":
            # Add one year
            return start_date.replace(year=start_date.year + 1)
        else:
            # Default to monthly
            if start_date.month == 12:
                return start_date.replace(year=start_date.year + 1, month=1)
            else:
                return start_date.replace(month=start_date.month + 1)

    def _calculate_prorated_amounts(self, plan_change: TariffPlanChange, 
                                   old_plan: UserTariffPlan, new_plan: TariffPlan) -> None:
        """Calculates prorated credits and charges for plan changes."""
        # Get the old plan details
        old_plan_obj = self.get_tariff_plan(old_plan.tariff_plan_id)
        
        # Calculate days left in current cycle
        now = datetime.utcnow()
        cycle_end = old_plan.current_cycle_end
        total_days_in_cycle = (cycle_end - old_plan.current_cycle_start).days
        days_left_in_cycle = (cycle_end - now).days
        
        if days_left_in_cycle <= 0 or total_days_in_cycle <= 0:
            # No proration needed
            plan_change.prorated_credit = Decimal('0.00')
            plan_change.prorated_charge = Decimal('0.00')
            return
        
        # Calculate prorated credit for old plan
        daily_rate_old = old_plan_obj.price / Decimal(total_days_in_cycle)
        prorated_credit = daily_rate_old * Decimal(days_left_in_cycle)
        
        # Calculate prorated charge for new plan
        daily_rate_new = new_plan.price / Decimal(total_days_in_cycle)
        prorated_charge = daily_rate_new * Decimal(days_left_in_cycle)
        
        # Update plan change record
        plan_change.prorated_credit = prorated_credit.quantize(Decimal('0.01'))
        plan_change.prorated_charge = prorated_charge.quantize(Decimal('0.01'))

    def _apply_radius_policy(self, user_id: int, plan: TariffPlan) -> None:
        """Applies the RADIUS policy associated with a tariff plan to a user."""
        if not plan.radius_policy_id:
            logger.warning(f"No RADIUS policy associated with plan {plan.id}")
            return
        
        try:
            # Get user's RADIUS profile
            radius_profile = (
                self.db.query(RadiusProfile)
                .filter(RadiusProfile.user_id == user_id)
                .first()
            )
            
            if not radius_profile:
                logger.warning(f"User {user_id} has no RADIUS profile")
                return
            
            # Update RADIUS profile with policy ID
            radius_profile.bandwidth_policy_id = plan.radius_policy_id
            self.db.commit()
            
            # If user has active sessions, send CoA to apply new policy
            active_sessions = (
                self.db.query(RadiusAccounting)
                .filter(
                    RadiusAccounting.profile_id == radius_profile.id,
                    RadiusAccounting.acct_status_type != "Stop",
                    RadiusAccounting.stop_time.is_(None)
                )
                .all()
            )
            
            for session in active_sessions:
                try:
                    # Send CoA request to update session
                    self.radius_service.send_coa_request({
                        "profile_id": radius_profile.id,
                        "nas_id": session.nas_id,
                        "session_id": session.session_id,
                        "coa_type": "update",
                        "attributes": {
                            "Bandwidth-Policy-Id": plan.radius_policy_id
                        }
                    })
                    logger.info(f"Applied RADIUS policy for user {user_id}, session {session.session_id}")
                except Exception as e:
                    logger.error(f"Error applying RADIUS policy for session {session.session_id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error applying RADIUS policy: {str(e)}")

    def get_user_tariff_plan(self, user_id: int) -> Optional[UserTariffPlan]:
        """Gets the active tariff plan for a user."""
        return (
            self.db.query(UserTariffPlan)
            .filter(
                UserTariffPlan.user_id == user_id,
                UserTariffPlan.status == "active"
            )
            .first()
        )

    def update_user_tariff_plan(self, user_plan_id: int, 
                               update_data: UserTariffPlanUpdate) -> UserTariffPlan:
        """Updates a user's tariff plan."""
        user_plan = (
            self.db.query(UserTariffPlan)
            .filter(UserTariffPlan.id == user_plan_id)
            .first()
        )
        
        if not user_plan:
            raise HTTPException(status_code=404, detail="User tariff plan not found")
        
        # Update attributes
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(user_plan, key, value)
        
        user_plan.updated_at = datetime.utcnow()
        
        # If status changed to suspended, apply throttling
        if update_data.status == "suspended" and user_plan.status != "suspended":
            plan = self.get_tariff_plan(user_plan.tariff_plan_id)
            if plan.throttled_radius_policy_id:
                self._apply_throttling(user_plan.user_id, plan)
        
        # If status changed from suspended to active, remove throttling
        if user_plan.status == "suspended" and update_data.status == "active":
            plan = self.get_tariff_plan(user_plan.tariff_plan_id)
            self._remove_throttling(user_plan.user_id, plan)
        
        self.db.commit()
        self.db.refresh(user_plan)
        return user_plan

    def cancel_user_tariff_plan(self, user_id: int) -> bool:
        """Cancels a user's active tariff plan."""
        user_plan = self.get_user_tariff_plan(user_id)
        
        if not user_plan:
            raise HTTPException(status_code=404, detail="No active tariff plan found for user")
        
        user_plan.status = "cancelled"
        user_plan.end_date = datetime.utcnow()
        user_plan.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Disconnect user's active sessions
        try:
            self.radius_service.disconnect_user(user_id)
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {str(e)}")
        
        # Handle billing for the plan cancellation
        try:
            billing_integration.handle_plan_cancellation(
                user_id=user_id,
                plan_name=user_plan.tariff_plan.name,
                cancellation_date=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Failed to handle billing for plan cancellation: {str(e)}")
        
        return True

    def check_fup_threshold(self, check_data: FUPThresholdCheck) -> FUPThresholdResponse:
        """Checks if a user has crossed the FUP threshold and should be throttled."""
        # Get the plan
        plan = self.get_tariff_plan(check_data.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Tariff plan not found")
        
        # If plan has no FUP threshold or data cap, no throttling needed
        if plan.fup_threshold == 0 or plan.data_cap == 0:
            return FUPThresholdResponse(
                user_id=check_data.user_id,
                plan_id=check_data.plan_id,
                threshold_reached=False,
                current_usage_mb=check_data.current_usage_mb,
                threshold_mb=0
            )
        
        # Check if user has crossed the threshold
        threshold_reached = check_data.current_usage_mb >= plan.fup_threshold
        
        # If threshold reached, calculate new speed (e.g., 50% of original)
        new_speed_limit = None
        if threshold_reached:
            new_speed_limit = int(plan.speed_limit * 0.5)  # Reduce to 50%
            
            # Update RADIUS profile with new speed limit
            radius_profile = (
                self.db.query(RadiusProfile)
                .filter(RadiusProfile.user_id == check_data.user_id)
                .first()
            )
            
            if radius_profile:
                radius_profile.speed_limit = new_speed_limit
                self.db.commit()
        
        return FUPThresholdResponse(
            user_id=check_data.user_id,
            plan_id=check_data.plan_id,
            threshold_reached=threshold_reached,
            current_usage_mb=check_data.current_usage_mb,
            threshold_mb=plan.fup_threshold,
            new_speed_limit=new_speed_limit
        )

    def calculate_overage_fee(self, user_id: int, usage_mb: int) -> float:
        """Calculates any overage fees based on usage and plan."""
        user_plan = self.get_user_tariff_plan(user_id)
        
        if not user_plan:
            raise HTTPException(status_code=404, detail="No active tariff plan found for user")
        
        plan = self.get_tariff_plan(user_plan.tariff_plan_id)
        
        # If plan has no data cap, no overage fee
        if not plan.data_cap:
            return 0.0
        
        # Convert MB to bytes for comparison
        usage_bytes = usage_mb * 1024 * 1024
        
        # If usage is under cap, no fee
        if usage_bytes <= plan.data_cap:
            return 0.0
        
        # Calculate overage
        overage_bytes = usage_bytes - plan.data_cap
        overage_gb = overage_bytes / (1024 * 1024 * 1024)
        
        # Get rate from plan features or use default
        rate = 0.0
        if plan.features and "overage_rate" in plan.features:
            rate = float(plan.features["overage_rate"])
        else:
            # Default rate of $10 per GB
            rate = 10.0
        
        return rate * overage_gb

    def record_usage(self, usage_data: UserUsageRecordCreate) -> UserUsageRecord:
        """Records usage data for a user's tariff plan."""
        # Get the user tariff plan
        user_tariff_plan = (
            self.db.query(UserTariffPlan)
            .filter(UserTariffPlan.id == usage_data.user_tariff_plan_id)
            .first()
        )
        
        if not user_tariff_plan:
            raise HTTPException(status_code=404, detail="User tariff plan not found")
        
        # Create usage record
        usage_record = UserUsageRecord(
            user_tariff_plan_id=usage_data.user_tariff_plan_id,
            download_bytes=usage_data.download_bytes,
            upload_bytes=usage_data.upload_bytes,
            total_bytes=usage_data.download_bytes + usage_data.upload_bytes,
            source=usage_data.source,
            session_id=usage_data.session_id,
            timestamp=usage_data.timestamp
        )
        
        self.db.add(usage_record)
        
        # Update total usage on user tariff plan
        user_tariff_plan.data_used += usage_record.total_bytes
        user_tariff_plan.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(usage_record)
        
        # Check if any policy actions need to be triggered
        self._check_policy_triggers(user_tariff_plan)
        
        # Handle billing for the usage record
        try:
            billing_integration.handle_usage_record(
                user_id=user_tariff_plan.user_id,
                plan_name=user_tariff_plan.tariff_plan.name,
                usage_bytes=usage_record.total_bytes,
                timestamp=usage_record.timestamp
            )
        except Exception as e:
            logger.error(f"Failed to handle billing for usage record: {str(e)}")
        
        return usage_record

    def _check_policy_triggers(self, user_tariff_plan: UserTariffPlan) -> None:
        """Checks if any policy actions need to be triggered based on usage."""
        plan = self.get_tariff_plan(user_tariff_plan.tariff_plan_id)
        
        # Get all policy actions for this plan
        policy_actions = (
            self.db.query(TariffPolicyAction)
            .filter(
                TariffPolicyAction.tariff_plan_id == plan.id,
                TariffPolicyAction.is_active == True
            )
            .all()
        )
        
        for action in policy_actions:
            # Check if trigger condition is met
            if action.trigger_type == "data_cap" and plan.data_cap:
                if user_tariff_plan.data_used >= plan.data_cap and action.threshold_value is None:
                    self._execute_policy_action(action, user_tariff_plan)
                elif action.threshold_value and user_tariff_plan.data_used >= action.threshold_value:
                    self._execute_policy_action(action, user_tariff_plan)
            
            elif action.trigger_type == "fup" and plan.fup_threshold:
                if user_tariff_plan.data_used >= plan.fup_threshold and action.threshold_value is None:
                    self._execute_policy_action(action, user_tariff_plan)
                elif action.threshold_value and user_tariff_plan.data_used >= action.threshold_value:
                    self._execute_policy_action(action, user_tariff_plan)
            
            elif action.trigger_type == "time_restriction" and plan.time_restrictions:
                # Time-based restrictions would be checked here
                # This is a placeholder for future implementation
                pass

    def _execute_policy_action(self, action: TariffPolicyAction, user_tariff_plan: UserTariffPlan) -> None:
        """Executes a policy action based on the action type."""
        try:
            if action.action_type == "notify":
                self._send_notification(action, user_tariff_plan)
            
            elif action.action_type == "throttle" and not user_tariff_plan.is_throttled:
                self._apply_throttling(user_tariff_plan.user_id, self.get_tariff_plan(user_tariff_plan.tariff_plan_id))
                user_tariff_plan.is_throttled = True
                user_tariff_plan.throttled_at = datetime.utcnow()
                self.db.commit()
            
            elif action.action_type == "block":
                self._block_user(user_tariff_plan.user_id)
            
            elif action.action_type == "charge":
                self._apply_overage_charge(user_tariff_plan, action.action_params)
            
            logger.info(f"Executed policy action {action.id} for user tariff plan {user_tariff_plan.id}")
        
        except Exception as e:
            logger.error(f"Error executing policy action: {str(e)}")

    def _send_notification(self, action: TariffPolicyAction, user_tariff_plan: UserTariffPlan) -> None:
        """Sends a notification based on the policy action."""
        if not action.notification_template_id:
            logger.warning(f"No notification template specified for action {action.id}")
            return
        
        template = (
            self.db.query(NotificationTemplate)
            .filter(NotificationTemplate.id == action.notification_template_id)
            .first()
        )
        
        if not template:
            logger.warning(f"Notification template {action.notification_template_id} not found")
            return
        
        # Get user and plan details
        user = self.db.query(User).filter(User.id == user_tariff_plan.user_id).first()
        plan = self.get_tariff_plan(user_tariff_plan.tariff_plan_id)
        
        if not user:
            logger.warning(f"User {user_tariff_plan.user_id} not found")
            return
        
        # Prepare notification context
        context = {
            "user_name": user.username,
            "plan_name": plan.name,
            "data_used": self._format_bytes(user_tariff_plan.data_used),
            "data_cap": self._format_bytes(plan.data_cap) if plan.data_cap else "Unlimited",
            "percentage_used": self._calculate_percentage_used(user_tariff_plan.data_used, plan.data_cap),
            "cycle_end": user_tariff_plan.current_cycle_end.strftime("%Y-%m-%d")
        }
        
        # TODO: Integrate with actual notification system
        # For now, just log the notification
        logger.info(f"Notification to user {user.id}: {template.subject}")
        logger.info(f"Notification body would contain: {context}")

    def _apply_throttling(self, user_id: int, plan: TariffPlan) -> None:
        """Applies throttling to a user's connection."""
        if not plan.throttled_radius_policy_id:
            logger.warning(f"No throttled RADIUS policy defined for plan {plan.id}")
            return
        
        try:
            # Get user's RADIUS profile
            radius_profile = (
                self.db.query(RadiusProfile)
                .filter(RadiusProfile.user_id == user_id)
                .first()
            )
            
            if not radius_profile:
                logger.warning(f"User {user_id} has no RADIUS profile")
                return
            
            # Store original policy ID if not already throttled
            if not hasattr(radius_profile, 'original_bandwidth_policy_id') or not radius_profile.original_bandwidth_policy_id:
                radius_profile.original_bandwidth_policy_id = radius_profile.bandwidth_policy_id
            
            # Apply throttled policy
            radius_profile.bandwidth_policy_id = plan.throttled_radius_policy_id
            self.db.commit()
            
            # Send CoA to active sessions
            active_sessions = (
                self.db.query(RadiusAccounting)
                .filter(
                    RadiusAccounting.profile_id == radius_profile.id,
                    RadiusAccounting.acct_status_type != "Stop",
                    RadiusAccounting.stop_time.is_(None)
                )
                .all()
            )
            
            for session in active_sessions:
                try:
                    # Send CoA request to update session
                    self.radius_service.send_coa_request({
                        "profile_id": radius_profile.id,
                        "nas_id": session.nas_id,
                        "session_id": session.session_id,
                        "coa_type": "update",
                        "attributes": {
                            "Bandwidth-Policy-Id": plan.throttled_radius_policy_id
                        }
                    })
                    logger.info(f"Applied throttling for user {user_id}, session {session.session_id}")
                except Exception as e:
                    logger.error(f"Error applying throttling for session {session.session_id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error applying throttling: {str(e)}")

    def _remove_throttling(self, user_id: int, plan: TariffPlan) -> None:
        """Removes throttling from a user's connection."""
        try:
            # Get user's RADIUS profile
            radius_profile = (
                self.db.query(RadiusProfile)
                .filter(RadiusProfile.user_id == user_id)
                .first()
            )
            
            if not radius_profile:
                logger.warning(f"User {user_id} has no RADIUS profile")
                return
            
            # Restore original policy if available, otherwise use plan's default
            if hasattr(radius_profile, 'original_bandwidth_policy_id') and radius_profile.original_bandwidth_policy_id:
                radius_profile.bandwidth_policy_id = radius_profile.original_bandwidth_policy_id
                radius_profile.original_bandwidth_policy_id = None
            else:
                radius_profile.bandwidth_policy_id = plan.radius_policy_id
            
            self.db.commit()
            
            # Send CoA to active sessions
            active_sessions = (
                self.db.query(RadiusAccounting)
                .filter(
                    RadiusAccounting.profile_id == radius_profile.id,
                    RadiusAccounting.acct_status_type != "Stop",
                    RadiusAccounting.stop_time.is_(None)
                )
                .all()
            )
            
            for session in active_sessions:
                try:
                    # Send CoA request to update session
                    self.radius_service.send_coa_request({
                        "profile_id": radius_profile.id,
                        "nas_id": session.nas_id,
                        "session_id": session.session_id,
                        "coa_type": "update",
                        "attributes": {
                            "Bandwidth-Policy-Id": radius_profile.bandwidth_policy_id
                        }
                    })
                    logger.info(f"Removed throttling for user {user_id}, session {session.session_id}")
                except Exception as e:
                    logger.error(f"Error removing throttling for session {session.session_id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error removing throttling: {str(e)}")

    def _block_user(self, user_id: int) -> None:
        """Blocks a user's connection by disconnecting all sessions."""
        try:
            # Disconnect all user sessions
            self.radius_service.disconnect_user(user_id)
            
            # Update user's RADIUS profile to prevent reconnection
            radius_profile = (
                self.db.query(RadiusProfile)
                .filter(RadiusProfile.user_id == user_id)
                .first()
            )
            
            if radius_profile:
                radius_profile.is_active = False
                self.db.commit()
                logger.info(f"Blocked user {user_id}")
        
        except Exception as e:
            logger.error(f"Error blocking user {user_id}: {str(e)}")

    def _apply_overage_charge(self, user_tariff_plan: UserTariffPlan, action_params: Dict[str, Any]) -> None:
        """Applies an overage charge to a user's account."""
        # This would typically integrate with the billing module
        # For now, just log the charge
        if not action_params or "rate" not in action_params:
            logger.warning("No rate specified for overage charge")
            return
        
        plan = self.get_tariff_plan(user_tariff_plan.tariff_plan_id)
        
        # Calculate overage
        overage_bytes = 0
        if plan.data_cap and user_tariff_plan.data_used > plan.data_cap:
            overage_bytes = user_tariff_plan.data_used - plan.data_cap
        
        # Convert to GB for billing (bytes to GB)
        overage_gb = overage_bytes / (1024 * 1024 * 1024)
        
        # Calculate charge
        rate = Decimal(str(action_params.get("rate", 0)))
        charge = rate * Decimal(overage_gb)
        
        logger.info(f"Applied overage charge of {charge} for user {user_tariff_plan.user_id}")
        
        # TODO: Integrate with billing module to actually apply the charge

    def check_usage(self, check_data: UsageCheckRequest) -> UsageCheckResponse:
        """Checks a user's usage against their plan limits and returns status."""
        # Get user's active tariff plan
        user_plan = self.get_user_tariff_plan(check_data.user_id)
        
        if not user_plan:
            raise HTTPException(status_code=404, detail="No active tariff plan found for user")
        
        plan = self.get_tariff_plan(user_plan.tariff_plan_id)
        
        # Record usage if provided
        if check_data.download_bytes > 0 or check_data.upload_bytes > 0:
            usage_data = UserUsageRecordCreate(
                user_tariff_plan_id=user_plan.id,
                download_bytes=check_data.download_bytes,
                upload_bytes=check_data.upload_bytes,
                source="api",
                session_id=check_data.session_id
            )
            self.record_usage(usage_data)
            
            # Refresh user plan to get updated usage
            self.db.refresh(user_plan)
        
        # Determine status
        status = "ok"
        if user_plan.status == "suspended":
            status = "suspended"
        elif user_plan.is_throttled:
            status = "throttled"
        
        # Calculate percentage used
        percentage_used = self._calculate_percentage_used(user_plan.data_used, plan.data_cap)
        
        # Get triggered actions
        actions_triggered = []
        if user_plan.is_throttled:
            actions_triggered.append({
                "type": "throttle",
                "triggered_at": user_plan.throttled_at.isoformat() if user_plan.throttled_at else None,
                "download_speed": plan.throttle_speed_download,
                "upload_speed": plan.throttle_speed_upload
            })
        
        # Prepare response message
        message = None
        if status == "ok":
            if plan.data_cap:
                message = f"Using {self._format_bytes(user_plan.data_used)} of {self._format_bytes(plan.data_cap)} ({percentage_used:.1f}%)"
            else:
                message = f"Using {self._format_bytes(user_plan.data_used)} (Unlimited plan)"
        elif status == "throttled":
            message = f"Connection throttled due to exceeding {self._format_bytes(plan.fup_threshold)} FUP threshold"
        elif status == "suspended":
            message = "Account suspended"
        
        return UsageCheckResponse(
            user_id=check_data.user_id,
            tariff_plan_id=plan.id,
            plan_name=plan.name,
            status=status,
            current_usage=user_plan.data_used,
            data_cap=plan.data_cap,
            percentage_used=percentage_used,
            actions_triggered=actions_triggered,
            message=message
        )

    def get_bandwidth_policy(self, user_id: int) -> BandwidthPolicyResponse:
        """Gets the bandwidth policy for a user based on their tariff plan."""
        # Get user's active tariff plan
        user_plan = self.get_user_tariff_plan(user_id)
        
        if not user_plan:
            raise HTTPException(status_code=404, detail="No active tariff plan found for user")
        
        plan = self.get_tariff_plan(user_plan.tariff_plan_id)
        
        # Determine which speeds to use based on throttling status
        download_speed = plan.throttle_speed_download if user_plan.is_throttled else plan.download_speed
        upload_speed = plan.throttle_speed_upload if user_plan.is_throttled else plan.upload_speed
        
        # Additional attributes (time restrictions, etc.)
        additional_attributes = {}
        if plan.time_restrictions:
            additional_attributes["time_restrictions"] = plan.time_restrictions
        
        return BandwidthPolicyResponse(
            user_id=user_id,
            download_speed=download_speed,
            upload_speed=upload_speed,
            is_throttled=user_plan.is_throttled,
            session_timeout=None,  # Could be set based on plan settings
            additional_attributes=additional_attributes
        )

    def reset_usage_cycle(self, user_id: int) -> bool:
        """Resets the usage cycle for a user's tariff plan."""
        user_plan = self.get_user_tariff_plan(user_id)
        
        if not user_plan:
            raise HTTPException(status_code=404, detail="No active tariff plan found for user")
        
        # Reset usage
        user_plan.data_used = 0
        
        # If throttled, remove throttling
        if user_plan.is_throttled:
            plan = self.get_tariff_plan(user_plan.tariff_plan_id)
            self._remove_throttling(user_id, plan)
            user_plan.is_throttled = False
            user_plan.throttled_at = None
        
        # Set new cycle dates
        now = datetime.utcnow()
        user_plan.current_cycle_start = now
        user_plan.current_cycle_end = self._calculate_cycle_end(
            now, 
            self.get_tariff_plan(user_plan.tariff_plan_id).billing_cycle
        )
        
        self.db.commit()
        
        # Handle billing for the cycle reset
        try:
            billing_integration.handle_cycle_reset(
                user_id=user_id,
                plan_name=user_plan.tariff_plan.name,
                cycle_start=user_plan.current_cycle_start,
                cycle_end=user_plan.current_cycle_end
            )
        except Exception as e:
            logger.error(f"Failed to handle billing for cycle reset: {str(e)}")
        
        return True

    def process_scheduled_plan_changes(self) -> Dict[str, Any]:
        """Processes scheduled plan changes that are due."""
        now = datetime.utcnow()
        
        # Find pending plan changes that are due
        pending_changes = (
            self.db.query(TariffPlanChange)
            .filter(
                TariffPlanChange.status == "pending",
                TariffPlanChange.effective_date <= now
            )
            .all()
        )
        
        results = {
            "total": len(pending_changes),
            "processed": 0,
            "failed": 0,
            "errors": []
        }
        
        for change in pending_changes:
            try:
                # Get current active plan
                current_plan = (
                    self.db.query(UserTariffPlan)
                    .filter(
                        UserTariffPlan.user_id == change.user_id,
                        UserTariffPlan.status == "active"
                    )
                    .first()
                )
                
                if not current_plan:
                    # User has no active plan, create a new one
                    new_plan = self.get_tariff_plan(change.new_plan_id)
                    cycle_end = self._calculate_cycle_end(now, new_plan.billing_cycle)
                    
                    user_plan = UserTariffPlan(
                        user_id=change.user_id,
                        tariff_plan_id=change.new_plan_id,
                        status="active",
                        start_date=now,
                        current_cycle_start=now,
                        current_cycle_end=cycle_end,
                        data_used=0,
                        is_throttled=False
                    )
                    
                    self.db.add(user_plan)
                else:
                    # Cancel current plan
                    current_plan.status = "cancelled"
                    current_plan.end_date = now
                    
                    # Create new plan
                    new_plan = self.get_tariff_plan(change.new_plan_id)
                    cycle_end = self._calculate_cycle_end(now, new_plan.billing_cycle)
                    
                    user_plan = UserTariffPlan(
                        user_id=change.user_id,
                        tariff_plan_id=change.new_plan_id,
                        status="active",
                        start_date=now,
                        current_cycle_start=now,
                        current_cycle_end=cycle_end,
                        data_used=0,
                        is_throttled=False
                    )
                    
                    self.db.add(user_plan)
                    
                    # Calculate prorated amounts
                    self._calculate_prorated_amounts(change, current_plan, new_plan)
                
                # Apply RADIUS policy
                self._apply_radius_policy(change.user_id, new_plan)
                
                # Update change record
                change.status = "processed"
                change.processed_at = now
                
                # Handle billing for the plan change
                try:
                    billing_integration.handle_plan_change(
                        user_id=change.user_id,
                        previous_plan={
                            "id": current_plan.tariff_plan_id,
                            "name": current_plan.tariff_plan.name,
                            "price": str(current_plan.tariff_plan.price)
                        },
                        new_plan={
                            "id": new_plan.id,
                            "name": new_plan.name,
                            "price": str(new_plan.price)
                        },
                        effective_date=now,
                        current_cycle_start=current_plan.current_cycle_start,
                        current_cycle_end=current_plan.current_cycle_end
                    )
                except Exception as e:
                    logger.error(f"Failed to handle billing for plan change: {str(e)}")
                
                self.db.commit()
                results["processed"] += 1
            
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error processing change {change.id}: {str(e)}")
                logger.error(f"Error processing plan change {change.id}: {str(e)}")
        
        return results

    def _calculate_percentage_used(self, used: int, cap: Optional[int]) -> float:
        """Calculates the percentage of data cap used."""
        if not cap or cap == 0:
            return 0.0
        return (used / cap) * 100.0

    def _format_bytes(self, bytes_value: Optional[int]) -> str:
        """Formats bytes into a human-readable string."""
        if bytes_value is None:
            return "Unlimited"
        
        if bytes_value == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
        i = 0
        while bytes_value >= 1024 and i < len(size_names) - 1:
            bytes_value /= 1024
            i += 1
        
        return f"{bytes_value:.2f} {size_names[i]}"
