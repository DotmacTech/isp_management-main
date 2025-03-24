"""
Alert Management Service for ISP Management Platform.

This module provides services for managing alerts, including:
- Alert configuration management
- Alert evaluation against metrics and logs
- Alert notification delivery
- Alert history tracking
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import re

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, select
from fastapi import HTTPException, Depends

from modules.monitoring.models import (
    AlertConfiguration, 
    AlertHistory, 
    SystemMetric, 
    ServiceLog,
    AlertStatus,
    AlertSeverity,
    MetricType,
    LogLevel
)
from modules.monitoring.schemas import (
    AlertConfigurationCreate,
    AlertConfigurationUpdate,
    AlertConfigurationResponse,
    AlertHistoryCreate,
    AlertHistoryUpdate,
    AlertHistoryResponse,
    AlertSearchParams
)
from modules.monitoring.elasticsearch import ElasticsearchClient
from backend_core.database import get_db
from backend_core.cache import get_redis
from backend_core.config import settings
from modules.monitoring.notification_service import NotificationService

# Configure logging
logger = logging.getLogger(__name__)


class AlertManagementService:
    """Service for managing alerts, alert configurations, and alert history."""
    
    def __init__(self, db: Session = Depends(get_db)):
        """Initialize the alert management service."""
        self.db = db
        self.es_client = ElasticsearchClient()
        self.notification_service = NotificationService(db)
        
    def get_alert_configurations(
        self, 
        service_name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[AlertConfigurationResponse]:
        """
        Get all alert configurations, optionally filtered by service name and active status.
        
        Args:
            service_name: Optional service name to filter by
            is_active: Optional active status to filter by
            
        Returns:
            List of alert configurations
        """
        query = select(AlertConfiguration)
        
        if service_name:
            query = query.where(AlertConfiguration.service_name == service_name)
            
        if is_active is not None:
            query = query.where(AlertConfiguration.is_active == is_active)
            
        result = self.db.execute(query)
        configurations = result.scalars().all()
        
        return [AlertConfigurationResponse.from_orm(config) for config in configurations]
    
    def get_alert_configuration(self, config_id: int) -> AlertConfigurationResponse:
        """
        Get an alert configuration by ID.
        
        Args:
            config_id: Alert configuration ID
            
        Returns:
            Alert configuration
            
        Raises:
            HTTPException: If the configuration is not found
        """
        configuration = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.id == config_id
        ).first()
        
        if not configuration:
            raise HTTPException(status_code=404, detail="Alert configuration not found")
            
        return AlertConfigurationResponse.from_orm(configuration)
    
    def create_alert_configuration(
        self, 
        config_data: AlertConfigurationCreate
    ) -> AlertConfigurationResponse:
        """
        Create a new alert configuration.
        
        Args:
            config_data: Alert configuration data
            
        Returns:
            Created alert configuration
        """
        configuration = AlertConfiguration(**config_data.dict())
        
        self.db.add(configuration)
        self.db.commit()
        self.db.refresh(configuration)
        
        logger.info(f"Created alert configuration: {configuration.name} (ID: {configuration.id})")
        
        return AlertConfigurationResponse.from_orm(configuration)
    
    def update_alert_configuration(
        self, 
        config_id: int, 
        config_data: AlertConfigurationUpdate
    ) -> AlertConfigurationResponse:
        """
        Update an existing alert configuration.
        
        Args:
            config_id: Alert configuration ID
            config_data: Updated alert configuration data
            
        Returns:
            Updated alert configuration
            
        Raises:
            HTTPException: If the configuration is not found
        """
        configuration = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.id == config_id
        ).first()
        
        if not configuration:
            raise HTTPException(status_code=404, detail="Alert configuration not found")
            
        # Update configuration fields
        update_data = config_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(configuration, key, value)
            
        configuration.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(configuration)
        
        logger.info(f"Updated alert configuration: {configuration.name} (ID: {configuration.id})")
        
        return AlertConfigurationResponse.from_orm(configuration)
    
    def delete_alert_configuration(self, config_id: int) -> Dict[str, Any]:
        """
        Delete an alert configuration.
        
        Args:
            config_id: Alert configuration ID
            
        Returns:
            Dictionary with deletion status
            
        Raises:
            HTTPException: If the configuration is not found
        """
        configuration = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.id == config_id
        ).first()
        
        if not configuration:
            raise HTTPException(status_code=404, detail="Alert configuration not found")
            
        self.db.delete(configuration)
        self.db.commit()
        
        logger.info(f"Deleted alert configuration: {configuration.name} (ID: {configuration.id})")
        
        return {"status": "success", "message": "Alert configuration deleted"}
    
    def get_alert_history(
        self, 
        alert_id: Optional[int] = None,
        configuration_id: Optional[int] = None,
        status: Optional[AlertStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AlertHistoryResponse], int]:
        """
        Get alert history, optionally filtered by alert ID, configuration ID, or status.
        
        Args:
            alert_id: Optional alert ID to filter by
            configuration_id: Optional configuration ID to filter by
            status: Optional status to filter by
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of alert history entries, total count)
        """
        query = select(AlertHistory)
        count_query = select(func.count()).select_from(AlertHistory)
        
        if alert_id:
            query = query.where(AlertHistory.id == alert_id)
            count_query = count_query.where(AlertHistory.id == alert_id)
            
        if configuration_id:
            query = query.where(AlertHistory.configuration_id == configuration_id)
            count_query = count_query.where(AlertHistory.configuration_id == configuration_id)
            
        if status:
            query = query.where(AlertHistory.status == status)
            count_query = count_query.where(AlertHistory.status == status)
            
        query = query.order_by(desc(AlertHistory.triggered_at))
        query = query.limit(limit).offset(offset)
        
        result = self.db.execute(query)
        alerts = result.scalars().all()
        
        count_result = self.db.execute(count_query)
        total = count_result.scalar_one()
        
        return [AlertHistoryResponse.from_orm(alert) for alert in alerts], total
    
    def create_alert_history(self, alert_data: AlertHistoryCreate) -> AlertHistoryResponse:
        """
        Create a new alert history entry.
        
        Args:
            alert_data: Alert history data
            
        Returns:
            Created alert history entry
        """
        alert = AlertHistory(**alert_data.dict())
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Created alert history entry: ID {alert.id} for configuration {alert.configuration_id}")
        
        # Get the alert configuration to determine notification channels
        configuration = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.id == alert.configuration_id
        ).first()
        
        if configuration and configuration.notification_channels:
            # Send notification
            self._send_alert_notification(alert, configuration)
        
        return AlertHistoryResponse.from_orm(alert)
    
    def update_alert_status(
        self, 
        alert_id: int, 
        status_update: AlertHistoryUpdate
    ) -> AlertHistoryResponse:
        """
        Update the status of an alert in the history.
        
        Args:
            alert_id: Alert ID
            status_update: Status update data
            
        Returns:
            Updated alert history entry
            
        Raises:
            HTTPException: If the alert is not found
        """
        alert = self.db.query(AlertHistory).filter(
            AlertHistory.id == alert_id
        ).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
            
        # Update status fields
        update_data = status_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(alert, key, value)
            
        # If status is being set to resolved, set resolved_at if not provided
        if status_update.status == AlertStatus.RESOLVED and not status_update.resolved_at:
            alert.resolved_at = datetime.utcnow()
            
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Updated alert status: ID {alert.id} to {alert.status}")
        
        return AlertHistoryResponse.from_orm(alert)
    
    def search_alerts(self, search_params: AlertSearchParams) -> Tuple[List[AlertHistoryResponse], int]:
        """
        Search alerts with filtering options.
        
        Args:
            search_params: Search parameters
            
        Returns:
            Tuple of (list of alert history entries, total count)
        """
        query = select(AlertHistory).join(AlertConfiguration)
        count_query = select(func.count()).select_from(AlertHistory).join(AlertConfiguration)
        
        # Apply filters
        filters = []
        
        if search_params.service_names:
            filters.append(AlertConfiguration.service_name.in_(search_params.service_names))
            
        if search_params.severities:
            filters.append(AlertConfiguration.severity.in_(search_params.severities))
            
        if search_params.statuses:
            filters.append(AlertHistory.status.in_(search_params.statuses))
            
        if search_params.start_time:
            filters.append(AlertHistory.triggered_at >= search_params.start_time)
            
        if search_params.end_time:
            filters.append(AlertHistory.triggered_at <= search_params.end_time)
            
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
            
        # Apply pagination
        query = query.order_by(desc(AlertHistory.triggered_at))
        query = query.limit(search_params.limit).offset(search_params.offset)
        
        result = self.db.execute(query)
        alerts = result.scalars().all()
        
        count_result = self.db.execute(count_query)
        total = count_result.scalar_one()
        
        return [AlertHistoryResponse.from_orm(alert) for alert in alerts], total
    
    def get_active_alerts(
        self, 
        service_name: Optional[str] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[AlertHistoryResponse]:
        """
        Get all active (non-resolved) alerts, optionally filtered by service name and severity.
        
        Args:
            service_name: Optional service name to filter by
            severity: Optional severity to filter by
            
        Returns:
            List of active alerts
        """
        query = select(AlertHistory).join(AlertConfiguration).where(
            AlertHistory.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
        )
        
        if service_name:
            query = query.where(AlertConfiguration.service_name == service_name)
            
        if severity:
            query = query.where(AlertConfiguration.severity == severity)
            
        query = query.order_by(desc(AlertHistory.triggered_at))
        
        result = self.db.execute(query)
        alerts = result.scalars().all()
        
        return [AlertHistoryResponse.from_orm(alert) for alert in alerts]
    
    def evaluate_metric_alert_conditions(self, metric_data: SystemMetric) -> List[AlertHistoryResponse]:
        """
        Evaluate alert conditions against a new metric and trigger alerts if conditions are met.
        
        Args:
            metric_data: System metric data
            
        Returns:
            List of triggered alerts
        """
        # Get active alert configurations for this service and metric type
        configurations = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.service_name == metric_data.service_name,
            AlertConfiguration.metric_type == metric_data.metric_type,
            AlertConfiguration.is_active == True,
            AlertConfiguration.condition_type == 'threshold'
        ).all()
        
        triggered_alerts = []
        
        for config in configurations:
            # Check if the metric value violates the threshold
            if self._check_threshold_violation(metric_data.value, config.threshold_value, config.comparison_operator):
                # Check cooldown period
                if self._is_in_cooldown_period(config.id):
                    logger.debug(f"Alert {config.name} is in cooldown period, skipping")
                    continue
                    
                # Create alert
                alert_data = AlertHistoryCreate(
                    configuration_id=config.id,
                    status=AlertStatus.ACTIVE,
                    message=f"{config.name}: {metric_data.metric_type} value {metric_data.value} {config.comparison_operator} {config.threshold_value}",
                    triggered_value=metric_data.value,
                    source_metric_id=metric_data.id,
                    notification_sent=False,
                    triggered_at=datetime.utcnow()
                )
                
                alert = self.create_alert_history(alert_data)
                triggered_alerts.append(alert)
                
        return triggered_alerts
    
    def evaluate_log_alert_conditions(self, log_data: ServiceLog) -> List[AlertHistoryResponse]:
        """
        Evaluate alert conditions against a new log entry and trigger alerts if conditions are met.
        
        Args:
            log_data: Service log data
            
        Returns:
            List of triggered alerts
        """
        # Get active alert configurations for this service and log level
        configurations = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.service_name == log_data.service_name,
            AlertConfiguration.log_level == log_data.log_level,
            AlertConfiguration.is_active == True,
            AlertConfiguration.condition_type == 'pattern'
        ).all()
        
        triggered_alerts = []
        
        for config in configurations:
            # Check if the log message matches the pattern
            if config.pattern and re.search(config.pattern, log_data.message):
                # Check cooldown period
                if self._is_in_cooldown_period(config.id):
                    logger.debug(f"Alert {config.name} is in cooldown period, skipping")
                    continue
                    
                # Create alert
                alert_data = AlertHistoryCreate(
                    configuration_id=config.id,
                    status=AlertStatus.ACTIVE,
                    message=f"{config.name}: Log message matches pattern '{config.pattern}'",
                    matched_pattern=config.pattern,
                    source_log_id=log_data.id,
                    notification_sent=False,
                    triggered_at=datetime.utcnow()
                )
                
                alert = self.create_alert_history(alert_data)
                triggered_alerts.append(alert)
                
        return triggered_alerts
    
    def _check_threshold_violation(
        self, 
        value: float, 
        threshold: float, 
        operator: str
    ) -> bool:
        """
        Check if a value violates a threshold based on the comparison operator.
        
        Args:
            value: Value to check
            threshold: Threshold value
            operator: Comparison operator (>, <, >=, <=, ==, !=)
            
        Returns:
            True if the threshold is violated, False otherwise
        """
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        else:
            logger.warning(f"Unknown comparison operator: {operator}")
            return False
    
    def _is_in_cooldown_period(self, configuration_id: int) -> bool:
        """
        Check if an alert configuration is in its cooldown period.
        
        Args:
            configuration_id: Alert configuration ID
            
        Returns:
            True if in cooldown period, False otherwise
        """
        # Get the configuration to check cooldown minutes
        config = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.id == configuration_id
        ).first()
        
        if not config or not config.cooldown_minutes:
            return False
            
        # Get the most recent alert for this configuration
        latest_alert = self.db.query(AlertHistory).filter(
            AlertHistory.configuration_id == configuration_id
        ).order_by(desc(AlertHistory.triggered_at)).first()
        
        if not latest_alert:
            return False
            
        # Check if the cooldown period has elapsed
        cooldown_end = latest_alert.triggered_at + timedelta(minutes=config.cooldown_minutes)
        return datetime.utcnow() < cooldown_end
    
    def _send_alert_notification(
        self, 
        alert: AlertHistory, 
        configuration: AlertConfiguration
    ) -> bool:
        """
        Send a notification for an alert.
        
        Args:
            alert: Alert history entry
            configuration: Alert configuration
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not configuration.notification_channels:
            return False
            
        try:
            # Prepare notification data
            notification_data = {
                "alert_id": alert.id,
                "alert_name": configuration.name,
                "service_name": configuration.service_name,
                "severity": configuration.severity.value,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "triggered_value": alert.triggered_value,
                "matched_pattern": alert.matched_pattern,
                "status": alert.status.value
            }
            
            # Send notification to each configured channel
            for channel, config in configuration.notification_channels.items():
                if channel == "email" and config.get("enabled", False):
                    recipients = config.get("recipients", [])
                    if recipients:
                        self.notification_service.send_email_notification(
                            recipients=recipients,
                            subject=f"Alert: {configuration.name} - {configuration.severity.value}",
                            body=self._format_email_notification(notification_data),
                            alert_data=notification_data
                        )
                        
                elif channel == "sms" and config.get("enabled", False):
                    recipients = config.get("recipients", [])
                    if recipients:
                        self.notification_service.send_sms_notification(
                            recipients=recipients,
                            message=self._format_sms_notification(notification_data),
                            alert_data=notification_data
                        )
                        
                elif channel == "webhook" and config.get("enabled", False):
                    webhook_url = config.get("url")
                    if webhook_url:
                        self.notification_service.send_webhook_notification(
                            webhook_url=webhook_url,
                            data=notification_data
                        )
                        
                elif channel == "slack" and config.get("enabled", False):
                    webhook_url = config.get("webhook_url")
                    if webhook_url:
                        self.notification_service.send_slack_notification(
                            webhook_url=webhook_url,
                            message=self._format_slack_notification(notification_data),
                            alert_data=notification_data
                        )
                        
            # Update notification status
            alert.notification_sent = True
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {str(e)}")
            return False
    
    def _format_email_notification(self, alert_data: Dict[str, Any]) -> str:
        """
        Format an alert notification for email.
        
        Args:
            alert_data: Alert data
            
        Returns:
            Formatted email body
        """
        return f"""
        <h2>Alert: {alert_data['alert_name']}</h2>
        <p><strong>Service:</strong> {alert_data['service_name']}</p>
        <p><strong>Severity:</strong> {alert_data['severity']}</p>
        <p><strong>Message:</strong> {alert_data['message']}</p>
        <p><strong>Triggered At:</strong> {alert_data['triggered_at']}</p>
        <p><strong>Status:</strong> {alert_data['status']}</p>
        <p>
        <a href="{settings.BASE_URL}/monitoring/alerts/{alert_data['alert_id']}">
        View Alert Details
        </a>
        </p>
        """
    
    def _format_sms_notification(self, alert_data: Dict[str, Any]) -> str:
        """
        Format an alert notification for SMS.
        
        Args:
            alert_data: Alert data
            
        Returns:
            Formatted SMS message
        """
        return f"Alert: {alert_data['alert_name']} ({alert_data['severity']}) - {alert_data['message']}"
    
    def _format_slack_notification(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format an alert notification for Slack.
        
        Args:
            alert_data: Alert data
            
        Returns:
            Formatted Slack message payload
        """
        # Set color based on severity
        color = "#36a64f"  # Default green
        if alert_data['severity'] == "warning":
            color = "#ffcc00"
        elif alert_data['severity'] == "critical":
            color = "#ff0000"
        elif alert_data['severity'] == "emergency":
            color = "#9b0000"
            
        return {
            "attachments": [
                {
                    "color": color,
                    "title": f"Alert: {alert_data['alert_name']}",
                    "title_link": f"{settings.BASE_URL}/monitoring/alerts/{alert_data['alert_id']}",
                    "fields": [
                        {
                            "title": "Service",
                            "value": alert_data['service_name'],
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert_data['severity'],
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": alert_data['message'],
                            "short": False
                        },
                        {
                            "title": "Triggered At",
                            "value": alert_data['triggered_at'],
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": alert_data['status'],
                            "short": True
                        }
                    ],
                    "footer": "ISP Management Platform",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
