"""
Audit utilities for the billing module.

This module provides functions for logging and auditing billing activities.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def log_billing_action(
    action_type: str, 
    user_id: int, 
    resource_type: str, 
    resource_id: Optional[int] = None, 
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None
) -> None:
    """
    Log a billing-related action for audit purposes.
    
    Args:
        action_type: Type of action (create, update, delete, etc.)
        user_id: ID of the user performing the action
        resource_type: Type of resource being modified (invoice, payment, etc.)
        resource_id: ID of the resource being modified
        previous_state: Previous state of the resource before modification
        new_state: New state of the resource after modification
        notes: Additional notes about the action
    """
    # Create audit log entry
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action_type": action_type,
        "user_id": user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "notes": notes
    }
    
    # Log the entry (in a production system, this might write to a database or external service)
    logger.info(f"BILLING AUDIT: {log_entry}")
    
    return None


def audit_invoice_creation(user_id: int, invoice_id: int, invoice_data: Dict[str, Any]) -> None:
    """
    Audit the creation of a new invoice.
    
    Args:
        user_id: ID of the user creating the invoice
        invoice_id: ID of the newly created invoice
        invoice_data: Data used to create the invoice
    """
    return log_billing_action(
        action_type="create",
        user_id=user_id,
        resource_type="invoice",
        resource_id=invoice_id,
        new_state=invoice_data,
        notes=f"Invoice {invoice_id} created for user {user_id}"
    )


def audit_payment_processing(user_id: int, payment_id: int, payment_data: Dict[str, Any]) -> None:
    """
    Audit the processing of a payment.
    
    Args:
        user_id: ID of the user making the payment
        payment_id: ID of the payment
        payment_data: Data about the payment
    """
    return log_billing_action(
        action_type="process",
        user_id=user_id,
        resource_type="payment",
        resource_id=payment_id,
        new_state=payment_data,
        notes=f"Payment {payment_id} processed for user {user_id}"
    )


def audit_subscription_change(
    user_id: int, 
    subscription_id: int, 
    previous_data: Dict[str, Any],
    new_data: Dict[str, Any]
) -> None:
    """
    Audit changes to a subscription.
    
    Args:
        user_id: ID of the user whose subscription is being modified
        subscription_id: ID of the subscription
        previous_data: Previous subscription data
        new_data: New subscription data
    """
    return log_billing_action(
        action_type="update",
        user_id=user_id,
        resource_type="subscription",
        resource_id=subscription_id,
        previous_state=previous_data,
        new_state=new_data,
        notes=f"Subscription {subscription_id} updated for user {user_id}"
    )
