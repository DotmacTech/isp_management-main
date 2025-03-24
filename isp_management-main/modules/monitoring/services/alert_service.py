"""
Service for managing alerts in the monitoring module.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from redis import Redis

from modules.monitoring.models.alert import (
    AlertConfiguration, AlertHistory, AlertSeverity, AlertStatus
)
from modules.monitoring.schemas.alert import (
    AlertConfigurationCreate, AlertConfigurationResponse,
    AlertHistoryCreate, AlertHistoryUpdate, AlertHistoryResponse,
    AlertSummary
)
from modules.monitoring.schemas.dashboard import PaginatedResponse
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing alerts in the monitoring module."""

    def __init__(self, db: Session, redis: Optional[Redis] = None):
        """Initialize the service with database session and Redis client."""
        self.db = db
        self.redis = redis
        self.es_client = ElasticsearchClient()

    def create_alert_configuration(self, alert_config: AlertConfigurationCreate) -> AlertConfiguration:
        """
        Create a new alert configuration.
        
        Args:
            alert_config: Alert configuration data.
            
        Returns:
            Created alert configuration.
        """
        config = AlertConfiguration(**alert_config.model_dump())
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        
        # Cache configuration in Redis if available
        if self.redis:
            cache_key = f"alert_config:{config.id}"
            self.redis.set(cache_key, json.dumps(config.to_dict()), ex=3600)  # 1 hour expiry
        
        return config

    def get_alert_configurations(
        self,
        service_name: Optional[str] = None
    ) -> List[AlertConfigurationResponse]:
        """
        Get all alert configurations, optionally filtered by service name.
        
        Args:
            service_name: Filter by service name.
            
        Returns:
            List of alert configurations.
        """
        query = self.db.query(AlertConfiguration)
        
        if service_name:
            query = query.filter(AlertConfiguration.service_name == service_name)
        
        configs = query.all()
        
        return [AlertConfigurationResponse.model_validate(config) for config in configs]

    def update_alert_configuration(
        self,
        config_id: int,
        alert_config: AlertConfigurationCreate
    ) -> Optional[AlertConfiguration]:
        """
        Update an existing alert configuration.
        
        Args:
            config_id: ID of the configuration to update.
            alert_config: New configuration data.
            
        Returns:
            Updated configuration or None if not found.
        """
        config = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.id == config_id
        ).first()
        
        if not config:
            return None
        
        # Update fields
        for key, value in alert_config.model_dump().items():
            setattr(config, key, value)
        
        self.db.commit()
        self.db.refresh(config)
        
        # Update cache
        if self.redis:
            cache_key = f"alert_config:{config.id}"
            self.redis.set(cache_key, json.dumps(config.to_dict()), ex=3600)  # 1 hour expiry
        
        return config

    def delete_alert_configuration(self, config_id: int) -> bool:
        """
        Delete an alert configuration.
        
        Args:
            config_id: ID of the configuration to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        config = self.db.query(AlertConfiguration).filter(
            AlertConfiguration.id == config_id
        ).first()
        
        if not config:
            return False
        
        self.db.delete(config)
        self.db.commit()
        
        # Remove from cache
        if self.redis:
            cache_key = f"alert_config:{config_id}"
            self.redis.delete(cache_key)
        
        return True

    def create_alert_history(self, alert_data: AlertHistoryCreate) -> AlertHistory:
        """
        Record a new alert in the alert history.
        
        Args:
            alert_data: Alert data to record.
            
        Returns:
            Created alert history entry.
        """
        alert = AlertHistory(**alert_data.model_dump())
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        # Index to Elasticsearch if connected
        if self.es_client.is_connected():
            self.es_client.index(
                index="alert_history",
                id=alert.id,
                document=alert.to_dict()
            )
        
        return alert

    def update_alert_status(
        self,
        alert_id: int,
        status_update: AlertHistoryUpdate
    ) -> Optional[AlertHistory]:
        """
        Update the status of an alert in the history.
        
        Args:
            alert_id: ID of the alert to update.
            status_update: New status data.
            
        Returns:
            Updated alert or None if not found.
        """
        alert = self.db.query(AlertHistory).filter(
            AlertHistory.id == alert_id
        ).first()
        
        if not alert:
            return None
        
        # Update fields
        for key, value in status_update.model_dump(exclude_unset=True).items():
            setattr(alert, key, value)
        
        # Set resolved time if status is RESOLVED
        if alert.status == AlertStatus.RESOLVED and not alert.resolved_time:
            alert.resolved_time = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(alert)
        
        # Update in Elasticsearch if connected
        if self.es_client.is_connected():
            self.es_client.index(
                index="alert_history",
                id=alert.id,
                document=alert.to_dict()
            )
        
        return alert

    def search_alerts(
        self,
        service_names: Optional[List[str]] = None,
        severities: Optional[List[AlertSeverity]] = None,
        statuses: Optional[List[AlertStatus]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        message_contains: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[AlertHistoryResponse]:
        """
        Search alerts with filtering options.
        
        Args:
            service_names: Filter by service names.
            severities: Filter by alert severities.
            statuses: Filter by alert statuses.
            start_time: Filter by start time.
            end_time: Filter by end time.
            message_contains: Filter by message content.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            Paginated response with alerts.
        """
        # Use Elasticsearch if connected
        if self.es_client.is_connected():
            return self._search_alerts_elasticsearch(
                service_names, severities, statuses, start_time, end_time,
                message_contains, offset, limit
            )
        
        # Build query
        query = self.db.query(AlertHistory)
        
        if service_names:
            query = query.filter(AlertHistory.service_name.in_(service_names))
        
        if severities:
            query = query.filter(AlertHistory.severity.in_(severities))
        
        if statuses:
            query = query.filter(AlertHistory.status.in_(statuses))
        
        if start_time:
            query = query.filter(AlertHistory.alert_time >= start_time)
        
        if end_time:
            query = query.filter(AlertHistory.alert_time <= end_time)
        
        if message_contains:
            query = query.filter(AlertHistory.message.ilike(f"%{message_contains}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        alerts = query.order_by(desc(AlertHistory.alert_time)).offset(offset).limit(limit).all()
        
        # Create paginated response
        return PaginatedResponse[AlertHistoryResponse](
            items=[AlertHistoryResponse.model_validate(alert) for alert in alerts],
            total=total,
            page=(offset // limit) + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )

    def _search_alerts_elasticsearch(
        self,
        service_names: Optional[List[str]] = None,
        severities: Optional[List[AlertSeverity]] = None,
        statuses: Optional[List[AlertStatus]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        message_contains: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[AlertHistoryResponse]:
        """
        Search alerts using Elasticsearch.
        
        Args:
            service_names: Filter by service names.
            severities: Filter by alert severities.
            statuses: Filter by alert statuses.
            start_time: Filter by start time.
            end_time: Filter by end time.
            message_contains: Filter by message content.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            Paginated response with alerts.
        """
        # Build Elasticsearch query
        query = {"bool": {"must": []}}
        
        if service_names:
            query["bool"]["must"].append({"terms": {"service_name.keyword": service_names}})
        
        if severities:
            query["bool"]["must"].append({"terms": {"severity.keyword": [s.value for s in severities]}})
        
        if statuses:
            query["bool"]["must"].append({"terms": {"status.keyword": [s.value for s in statuses]}})
        
        if start_time or end_time:
            range_query = {"range": {"alert_time": {}}}
            if start_time:
                range_query["range"]["alert_time"]["gte"] = start_time.isoformat()
            if end_time:
                range_query["range"]["alert_time"]["lte"] = end_time.isoformat()
            query["bool"]["must"].append(range_query)
        
        if message_contains:
            query["bool"]["must"].append({"match": {"message": message_contains}})
        
        # Execute search
        result = self.es_client.search(
            index="alert_history",
            query=query,
            sort=[{"alert_time": {"order": "desc"}}],
            from_=offset,
            size=limit
        )
        
        # Process results
        alerts = []
        for hit in result.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            alerts.append(AlertHistoryResponse.model_validate(source))
        
        total = result.get("hits", {}).get("total", {}).get("value", 0)
        
        return PaginatedResponse[AlertHistoryResponse](
            items=alerts,
            total=total,
            page=(offset // limit) + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )

    def get_active_alerts(
        self,
        service_name: Optional[str] = None
    ) -> List[AlertHistoryResponse]:
        """
        Get all active (non-resolved) alerts, optionally filtered by service name.
        
        Args:
            service_name: Filter by service name.
            
        Returns:
            List of active alerts.
        """
        query = self.db.query(AlertHistory).filter(
            AlertHistory.status != AlertStatus.RESOLVED
        )
        
        if service_name:
            query = query.filter(AlertHistory.service_name == service_name)
        
        alerts = query.order_by(desc(AlertHistory.alert_time)).all()
        
        return [AlertHistoryResponse.model_validate(alert) for alert in alerts]

    def get_alert_summary(
        self,
        days: int = 7
    ) -> AlertSummary:
        """
        Get a summary of alerts for the specified number of days.
        
        Args:
            days: Number of days to include in the summary.
            
        Returns:
            Alert summary.
        """
        # Calculate start time
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get total count
        total_count = self.db.query(func.count(AlertHistory.id)).filter(
            AlertHistory.alert_time >= start_time
        ).scalar() or 0
        
        # Get counts by severity
        severity_counts = {}
        for severity in AlertSeverity:
            count = self.db.query(func.count(AlertHistory.id)).filter(
                AlertHistory.alert_time >= start_time,
                AlertHistory.severity == severity
            ).scalar() or 0
            severity_counts[severity.value] = count
        
        # Get counts by status
        status_counts = {}
        for status in AlertStatus:
            count = self.db.query(func.count(AlertHistory.id)).filter(
                AlertHistory.alert_time >= start_time,
                AlertHistory.status == status
            ).scalar() or 0
            status_counts[status.value] = count
        
        # Get average resolution time
        avg_resolution_time = self.db.query(
            func.avg(AlertHistory.resolved_time - AlertHistory.alert_time)
        ).filter(
            AlertHistory.alert_time >= start_time,
            AlertHistory.status == AlertStatus.RESOLVED,
            AlertHistory.resolved_time.isnot(None)
        ).scalar()
        
        # Convert to seconds if not None
        avg_resolution_seconds = None
        if avg_resolution_time is not None:
            avg_resolution_seconds = avg_resolution_time.total_seconds()
        
        return AlertSummary(
            total_count=total_count,
            severity_counts=severity_counts,
            status_counts=status_counts,
            avg_resolution_time_seconds=avg_resolution_seconds,
            period_days=days
        )
