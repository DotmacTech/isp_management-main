"""
Celery tasks for the Tariff Enforcement Module.

This module contains scheduled tasks for:
1. Processing scheduled tariff plan changes
2. Resetting usage cycles at billing period boundaries
3. Sending usage notifications to users
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from celery import shared_task
from sqlalchemy.orm import Session

from backend_core.database import get_db_session
from .services import TariffService
from .models import UserTariffPlan, TariffPlan, TariffPolicyAction

logger = logging.getLogger(__name__)


@shared_task(name="tariff.process_scheduled_plan_changes")
def process_scheduled_plan_changes() -> Dict[str, Any]:
    """
    Process all scheduled tariff plan changes that are due.
    
    This task is typically scheduled to run daily.
    """
    logger.info("Starting scheduled task: process_scheduled_plan_changes")
    
    try:
        db = get_db_session()
        tariff_service = TariffService(db)
        results = tariff_service.process_scheduled_plan_changes()
        
        logger.info(
            f"Processed {results['processed']} of {results['total']} scheduled changes. "
            f"Failed: {results['failed']}"
        )
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing scheduled plan changes: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "total": 0,
            "processed": 0,
            "failed": 0,
            "errors": [str(e)]
        }
    finally:
        if 'db' in locals():
            db.close()


@shared_task(name="tariff.reset_billing_cycles")
def reset_billing_cycles() -> Dict[str, Any]:
    """
    Reset billing cycles for users whose current cycle has ended.
    
    This task is typically scheduled to run daily.
    """
    logger.info("Starting scheduled task: reset_billing_cycles")
    results = {
        "total": 0,
        "processed": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        db = get_db_session()
        tariff_service = TariffService(db)
        
        # Find all user tariff plans where the current cycle has ended
        now = datetime.utcnow()
        expired_cycles = (
            db.query(UserTariffPlan)
            .filter(
                UserTariffPlan.status == "active",
                UserTariffPlan.current_cycle_end <= now
            )
            .all()
        )
        
        results["total"] = len(expired_cycles)
        
        for user_plan in expired_cycles:
            try:
                # Reset the usage cycle
                tariff_service.reset_usage_cycle(user_plan.user_id)
                results["processed"] += 1
                logger.info(f"Reset billing cycle for user {user_plan.user_id}")
            
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Error resetting cycle for user {user_plan.user_id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in reset_billing_cycles task: {str(e)}")
        results["errors"].append(str(e))
        return results
    
    finally:
        if 'db' in locals():
            db.close()


@shared_task(name="tariff.send_usage_notifications")
def send_usage_notifications() -> Dict[str, Any]:
    """
    Send notifications to users based on their usage thresholds.
    
    This task is typically scheduled to run daily.
    """
    logger.info("Starting scheduled task: send_usage_notifications")
    results = {
        "total": 0,
        "sent": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        db = get_db_session()
        
        # Get all active user tariff plans
        active_plans = (
            db.query(UserTariffPlan)
            .filter(UserTariffPlan.status == "active")
            .all()
        )
        
        results["total"] = len(active_plans)
        
        for user_plan in active_plans:
            try:
                # Get the tariff plan
                plan = db.query(TariffPlan).filter(TariffPlan.id == user_plan.tariff_plan_id).first()
                
                if not plan or not plan.data_cap:
                    continue  # Skip plans with no data cap
                
                # Calculate usage percentage
                usage_percentage = (user_plan.data_used / plan.data_cap) * 100
                
                # Get notification thresholds from policy actions
                notification_actions = (
                    db.query(TariffPolicyAction)
                    .filter(
                        TariffPolicyAction.tariff_plan_id == plan.id,
                        TariffPolicyAction.action_type == "notify",
                        TariffPolicyAction.is_active == True
                    )
                    .all()
                )
                
                for action in notification_actions:
                    # Check if threshold is defined and exceeded
                    if action.threshold_value:
                        threshold_percentage = (action.threshold_value / plan.data_cap) * 100
                        
                        if usage_percentage >= threshold_percentage:
                            # Send notification
                            tariff_service = TariffService(db)
                            tariff_service._send_notification(action, user_plan)
                            results["sent"] += 1
                            logger.info(
                                f"Sent usage notification to user {user_plan.user_id}. "
                                f"Usage: {usage_percentage:.1f}%, Threshold: {threshold_percentage:.1f}%"
                            )
            
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Error sending notification for user {user_plan.user_id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in send_usage_notifications task: {str(e)}")
        results["errors"].append(str(e))
        return results
    
    finally:
        if 'db' in locals():
            db.close()


@shared_task(name="tariff.cleanup_expired_plans")
def cleanup_expired_plans() -> Dict[str, Any]:
    """
    Clean up expired tariff plans and handle renewals.
    
    This task is typically scheduled to run daily.
    """
    logger.info("Starting scheduled task: cleanup_expired_plans")
    results = {
        "total": 0,
        "processed": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        db = get_db_session()
        tariff_service = TariffService(db)
        
        # Find all expired user tariff plans
        now = datetime.utcnow()
        expired_plans = (
            db.query(UserTariffPlan)
            .filter(
                UserTariffPlan.status == "active",
                UserTariffPlan.end_date.isnot(None),
                UserTariffPlan.end_date <= now
            )
            .all()
        )
        
        results["total"] = len(expired_plans)
        
        for user_plan in expired_plans:
            try:
                # Cancel the expired plan
                tariff_service.cancel_user_tariff_plan(user_plan.user_id)
                results["processed"] += 1
                logger.info(f"Cancelled expired plan for user {user_plan.user_id}")
            
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Error cancelling plan for user {user_plan.user_id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in cleanup_expired_plans task: {str(e)}")
        results["errors"].append(str(e))
        return results
    
    finally:
        if 'db' in locals():
            db.close()


@shared_task(name="tariff.sync_radius_policies")
def sync_radius_policies() -> Dict[str, Any]:
    """
    Synchronize RADIUS policies with tariff plans.
    
    This task is typically scheduled to run weekly.
    """
    logger.info("Starting scheduled task: sync_radius_policies")
    results = {
        "total": 0,
        "synced": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        db = get_db_session()
        tariff_service = TariffService(db)
        
        # Get all active tariff plans
        active_plans = (
            db.query(TariffPlan)
            .filter(TariffPlan.is_active == True)
            .all()
        )
        
        results["total"] = len(active_plans)
        
        for plan in active_plans:
            try:
                # Sync RADIUS policy
                tariff_service._sync_radius_policy(plan)
                results["synced"] += 1
                logger.info(f"Synchronized RADIUS policy for plan {plan.id}")
            
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Error syncing RADIUS policy for plan {plan.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in sync_radius_policies task: {str(e)}")
        results["errors"].append(str(e))
        return results
    
    finally:
        if 'db' in locals():
            db.close()
