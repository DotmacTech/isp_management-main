"""
Monitoring integration for the Tariff Enforcement Module.

This module provides monitoring capabilities for the Tariff Enforcement Module,
including metrics collection, alerting, and integration with the central monitoring system.
"""

import logging
import time
from functools import wraps
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List, Union

from elasticsearch import Elasticsearch
from prometheus_client import Counter, Histogram, Gauge
from pydantic import BaseModel

from backend_core.config import settings
from backend_core.logging import get_logger

# Configure logger
logger = get_logger(__name__)

# Prometheus metrics
TARIFF_PLAN_ASSIGNMENTS = Counter(
    'tariff_plan_assignments_total',
    'Total number of tariff plan assignments',
    ['plan_name', 'status']
)

TARIFF_PLAN_CHANGES = Counter(
    'tariff_plan_changes_total',
    'Total number of tariff plan changes',
    ['from_plan', 'to_plan', 'change_type']
)

TARIFF_POLICY_ACTIONS = Counter(
    'tariff_policy_actions_total',
    'Total number of tariff policy enforcement actions',
    ['action_type', 'trigger_type', 'plan_name']
)

TARIFF_USAGE_RECORDS = Counter(
    'tariff_usage_records_total',
    'Total number of usage records processed',
    ['source']
)

TARIFF_DATA_USAGE = Histogram(
    'tariff_data_usage_bytes',
    'Data usage in bytes',
    ['direction', 'plan_name'],
    buckets=(
        1024 * 1024,  # 1 MB
        10 * 1024 * 1024,  # 10 MB
        100 * 1024 * 1024,  # 100 MB
        1024 * 1024 * 1024,  # 1 GB
        10 * 1024 * 1024 * 1024,  # 10 GB
        100 * 1024 * 1024 * 1024,  # 100 GB
    )
)

TARIFF_ACTIVE_USERS = Gauge(
    'tariff_active_users',
    'Number of active users per tariff plan',
    ['plan_name']
)

TARIFF_THROTTLED_USERS = Gauge(
    'tariff_throttled_users',
    'Number of throttled users per tariff plan',
    ['plan_name']
)

TARIFF_SERVICE_LATENCY = Histogram(
    'tariff_service_latency_seconds',
    'Latency of tariff service operations',
    ['operation'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)


class TariffAlert(BaseModel):
    """Model for tariff-related alerts."""
    alert_type: str
    severity: str
    user_id: Optional[int] = None
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    message: str
    details: Dict[str, Any] = {}
    timestamp: datetime = datetime.now()


class TariffMonitoring:
    """
    Class for monitoring tariff-related activities and metrics.
    
    This class provides methods for tracking usage, recording metrics,
    generating alerts, and integrating with the central monitoring system.
    """
    
    def __init__(self):
        """Initialize the TariffMonitoring instance."""
        self.es_client = None
        if settings.ELASTICSEARCH_ENABLED:
            try:
                self.es_client = Elasticsearch(
                    hosts=[settings.ELASTICSEARCH_URL],
                    basic_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD),
                    verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS
                )
                logger.info("Connected to Elasticsearch for tariff monitoring")
            except Exception as e:
                logger.error(f"Failed to connect to Elasticsearch: {e}")
    
    def track_plan_assignment(self, plan_name: str, status: str) -> None:
        """
        Track a tariff plan assignment.
        
        Args:
            plan_name: Name of the tariff plan
            status: Status of the assignment (active, pending, etc.)
        """
        TARIFF_PLAN_ASSIGNMENTS.labels(plan_name=plan_name, status=status).inc()
    
    def track_plan_change(self, from_plan: str, to_plan: str, change_type: str) -> None:
        """
        Track a tariff plan change.
        
        Args:
            from_plan: Name of the previous plan
            to_plan: Name of the new plan
            change_type: Type of change (upgrade, downgrade, etc.)
        """
        TARIFF_PLAN_CHANGES.labels(
            from_plan=from_plan, 
            to_plan=to_plan, 
            change_type=change_type
        ).inc()
    
    def track_policy_action(self, action_type: str, trigger_type: str, plan_name: str) -> None:
        """
        Track a tariff policy enforcement action.
        
        Args:
            action_type: Type of action (throttle, notify, etc.)
            trigger_type: Type of trigger (data_cap, fup, etc.)
            plan_name: Name of the tariff plan
        """
        TARIFF_POLICY_ACTIONS.labels(
            action_type=action_type,
            trigger_type=trigger_type,
            plan_name=plan_name
        ).inc()
    
    def track_usage_record(self, source: str, download_bytes: int, upload_bytes: int, plan_name: str) -> None:
        """
        Track a usage record.
        
        Args:
            source: Source of the usage record (radius, netflow, etc.)
            download_bytes: Download bytes
            upload_bytes: Upload bytes
            plan_name: Name of the tariff plan
        """
        TARIFF_USAGE_RECORDS.labels(source=source).inc()
        TARIFF_DATA_USAGE.labels(direction='download', plan_name=plan_name).observe(download_bytes)
        TARIFF_DATA_USAGE.labels(direction='upload', plan_name=plan_name).observe(upload_bytes)
    
    def update_active_users(self, plan_counts: Dict[str, int]) -> None:
        """
        Update the gauge of active users per tariff plan.
        
        Args:
            plan_counts: Dictionary mapping plan names to active user counts
        """
        for plan_name, count in plan_counts.items():
            TARIFF_ACTIVE_USERS.labels(plan_name=plan_name).set(count)
    
    def update_throttled_users(self, plan_counts: Dict[str, int]) -> None:
        """
        Update the gauge of throttled users per tariff plan.
        
        Args:
            plan_counts: Dictionary mapping plan names to throttled user counts
        """
        for plan_name, count in plan_counts.items():
            TARIFF_THROTTLED_USERS.labels(plan_name=plan_name).set(count)
    
    def create_alert(self, alert: TariffAlert) -> None:
        """
        Create an alert for a tariff-related event.
        
        Args:
            alert: The alert to create
        """
        # Log the alert
        log_message = f"TARIFF ALERT [{alert.severity}] {alert.alert_type}: {alert.message}"
        if alert.severity == 'critical':
            logger.critical(log_message)
        elif alert.severity == 'error':
            logger.error(log_message)
        elif alert.severity == 'warning':
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Store in Elasticsearch if available
        if self.es_client:
            try:
                self.es_client.index(
                    index=f"tariff-alerts-{datetime.now().strftime('%Y-%m')}",
                    document=alert.dict()
                )
            except Exception as e:
                logger.error(f"Failed to store alert in Elasticsearch: {e}")
    
    def measure_latency(self, operation: str) -> Callable:
        """
        Decorator to measure the latency of tariff service operations.
        
        Args:
            operation: Name of the operation
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                latency = time.time() - start_time
                TARIFF_SERVICE_LATENCY.labels(operation=operation).observe(latency)
                return result
            return wrapper
        return decorator
    
    def log_usage_summary(self, user_id: int, plan_name: str, current_usage: int, 
                         data_cap: Optional[int], percentage_used: float) -> None:
        """
        Log a summary of a user's data usage.
        
        Args:
            user_id: ID of the user
            plan_name: Name of the tariff plan
            current_usage: Current data usage in bytes
            data_cap: Data cap in bytes, or None if unlimited
            percentage_used: Percentage of data cap used
        """
        if data_cap:
            logger.info(
                f"User {user_id} on plan '{plan_name}' has used {current_usage} bytes "
                f"({percentage_used:.2f}%) of {data_cap} bytes data cap"
            )
        else:
            logger.info(
                f"User {user_id} on plan '{plan_name}' has used {current_usage} bytes "
                f"(unlimited data cap)"
            )
    
    def log_throttling_event(self, user_id: int, plan_name: str, 
                            current_usage: int, data_cap: int) -> None:
        """
        Log a throttling event.
        
        Args:
            user_id: ID of the user
            plan_name: Name of the tariff plan
            current_usage: Current data usage in bytes
            data_cap: Data cap in bytes
        """
        logger.warning(
            f"User {user_id} on plan '{plan_name}' has been throttled after using "
            f"{current_usage} bytes, exceeding the {data_cap} bytes data cap"
        )
        
        # Create an alert for the throttling event
        self.create_alert(
            TariffAlert(
                alert_type="user_throttled",
                severity="warning",
                user_id=user_id,
                plan_name=plan_name,
                message=f"User {user_id} has been throttled due to exceeding data cap",
                details={
                    "current_usage": current_usage,
                    "data_cap": data_cap,
                    "percentage_used": (current_usage / data_cap) * 100 if data_cap else None
                }
            )
        )
    
    def log_fup_threshold_event(self, user_id: int, plan_name: str, 
                               current_usage: int, fup_threshold: int) -> None:
        """
        Log a Fair Usage Policy threshold event.
        
        Args:
            user_id: ID of the user
            plan_name: Name of the tariff plan
            current_usage: Current data usage in bytes
            fup_threshold: FUP threshold in bytes
        """
        logger.warning(
            f"User {user_id} on plan '{plan_name}' has reached the FUP threshold of "
            f"{fup_threshold} bytes with current usage of {current_usage} bytes"
        )
        
        # Create an alert for the FUP threshold event
        self.create_alert(
            TariffAlert(
                alert_type="fup_threshold_reached",
                severity="warning",
                user_id=user_id,
                plan_name=plan_name,
                message=f"User {user_id} has reached the FUP threshold",
                details={
                    "current_usage": current_usage,
                    "fup_threshold": fup_threshold,
                    "percentage_used": (current_usage / fup_threshold) * 100
                }
            )
        )
    
    def log_usage_notification(self, user_id: int, plan_name: str, 
                              current_usage: int, data_cap: int, 
                              percentage_used: float, threshold: float) -> None:
        """
        Log a usage notification event.
        
        Args:
            user_id: ID of the user
            plan_name: Name of the tariff plan
            current_usage: Current data usage in bytes
            data_cap: Data cap in bytes
            percentage_used: Percentage of data cap used
            threshold: Notification threshold percentage
        """
        logger.info(
            f"User {user_id} on plan '{plan_name}' has reached {percentage_used:.2f}% "
            f"of their {data_cap} bytes data cap (threshold: {threshold}%)"
        )
        
        # Create an alert for the usage notification
        self.create_alert(
            TariffAlert(
                alert_type="usage_threshold_reached",
                severity="info",
                user_id=user_id,
                plan_name=plan_name,
                message=f"User {user_id} has reached {percentage_used:.2f}% of their data cap",
                details={
                    "current_usage": current_usage,
                    "data_cap": data_cap,
                    "percentage_used": percentage_used,
                    "threshold": threshold
                }
            )
        )
    
    def log_plan_change(self, user_id: int, from_plan: str, to_plan: str, 
                       change_type: str, effective_date: datetime) -> None:
        """
        Log a plan change event.
        
        Args:
            user_id: ID of the user
            from_plan: Name of the previous plan
            to_plan: Name of the new plan
            change_type: Type of change (upgrade, downgrade, etc.)
            effective_date: Effective date of the change
        """
        logger.info(
            f"User {user_id} plan change from '{from_plan}' to '{to_plan}' "
            f"({change_type}) effective {effective_date.isoformat()}"
        )
        
        # Create an alert for the plan change
        self.create_alert(
            TariffAlert(
                alert_type="plan_change",
                severity="info",
                user_id=user_id,
                message=f"User {user_id} plan changed from '{from_plan}' to '{to_plan}'",
                details={
                    "from_plan": from_plan,
                    "to_plan": to_plan,
                    "change_type": change_type,
                    "effective_date": effective_date.isoformat()
                }
            )
        )


# Create a singleton instance
tariff_monitoring = TariffMonitoring()
