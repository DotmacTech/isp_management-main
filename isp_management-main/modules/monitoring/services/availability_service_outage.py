"""
Service for monitoring service availability - Outage management.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, ServiceOutage, ServiceAlert, MaintenanceWindow,
    ProtocolType, StatusType, SeverityLevel, NotificationType
)
from modules.monitoring.schemas.service_availability import (
    ServiceOutageCreate, ServiceOutageUpdate, ServiceAlertCreate, 
    MaintenanceWindowCreate, MaintenanceWindowUpdate
)
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)

# Get environment variables
OUTAGE_DETECTION_THRESHOLD = int(os.getenv("OUTAGE_DETECTION_THRESHOLD", "3"))
OUTAGE_VERIFICATION_ENABLED = os.getenv("OUTAGE_VERIFICATION_ENABLED", "true").lower() == "true"


class OutageManagementService:
    """Service for managing service outages."""

    def __init__(self, db: Session):
        """Initialize the service with database session."""
        self.db = db
        self.es_client = ElasticsearchClient()

    # Outage management
    def _handle_potential_outage(self, endpoint: ServiceEndpoint, status: ServiceStatus) -> None:
        """Handle a potential service outage."""
        # Check consecutive failures
        consecutive_failures = (
            self.db.query(ServiceStatus)
            .filter(
                ServiceStatus.endpoint_id == endpoint.id,
                ServiceStatus.status == StatusType.DOWN
            )
            .order_by(desc(ServiceStatus.timestamp))
            .limit(OUTAGE_DETECTION_THRESHOLD)
            .all()
        )
        
        if len(consecutive_failures) >= OUTAGE_DETECTION_THRESHOLD:
            # Verify outage if enabled
            if OUTAGE_VERIFICATION_ENABLED:
                verified = self._verify_outage(endpoint)
                if not verified:
                    logger.info(f"Outage verification failed for {endpoint.id}, not creating outage")
                    return
            
            # Check if there's already an active outage
            active_outage = (
                self.db.query(ServiceOutage)
                .filter(
                    ServiceOutage.endpoint_id == endpoint.id,
                    ServiceOutage.end_time.is_(None)
                )
                .first()
            )
            
            if not active_outage:
                # Create new outage
                self._create_outage(endpoint)

    def _verify_outage(self, endpoint: ServiceEndpoint) -> bool:
        """Verify an outage by performing additional checks."""
        # Implement verification logic, e.g., check from multiple locations
        # For simplicity, we'll just do an additional check
        from modules.monitoring.services.availability_service import AvailabilityService
        
        availability_service = AvailabilityService(self.db)
        status, _ = availability_service._check_by_protocol(endpoint)
        
        return status == StatusType.DOWN

    def _create_outage(self, endpoint: ServiceEndpoint) -> ServiceOutage:
        """Create a new service outage."""
        # Determine severity based on service importance or other factors
        severity = self._determine_outage_severity(endpoint)
        
        # Create outage
        outage_data = ServiceOutageCreate(
            endpoint_id=endpoint.id,
            start_time=datetime.utcnow(),
            severity=severity,
            affected_customers=self._estimate_affected_customers(endpoint)
        )
        
        db_outage = ServiceOutage(**outage_data.model_dump())
        self.db.add(db_outage)
        self.db.commit()
        self.db.refresh(db_outage)
        
        logger.info(f"Created service outage for {endpoint.id} with severity {severity}")
        
        # Index in Elasticsearch
        self._index_outage_to_elasticsearch(db_outage)
        
        # Create alerts
        self._create_outage_alerts(db_outage)
        
        return db_outage

    def _determine_outage_severity(self, endpoint: ServiceEndpoint) -> SeverityLevel:
        """Determine the severity of an outage based on the service."""
        # This is a simple implementation
        # In a real system, you might have a more complex logic based on:
        # - Service importance
        # - Time of day
        # - Number of affected customers
        # - Dependencies on this service
        
        # For this example, we'll use a simple mapping based on protocol
        severity_mapping = {
            ProtocolType.HTTP: SeverityLevel.MEDIUM,
            ProtocolType.HTTPS: SeverityLevel.MEDIUM,
            ProtocolType.TCP: SeverityLevel.MEDIUM,
            ProtocolType.UDP: SeverityLevel.LOW,
            ProtocolType.ICMP: SeverityLevel.LOW,
            ProtocolType.DNS: SeverityLevel.HIGH,
            ProtocolType.RADIUS: SeverityLevel.CRITICAL,
            ProtocolType.SMTP: SeverityLevel.MEDIUM,
            ProtocolType.POP3: SeverityLevel.MEDIUM,
            ProtocolType.IMAP: SeverityLevel.MEDIUM,
            ProtocolType.FTP: SeverityLevel.LOW,
            ProtocolType.SSH: SeverityLevel.MEDIUM,
            ProtocolType.SNMP: SeverityLevel.LOW,
            ProtocolType.CUSTOM: SeverityLevel.MEDIUM
        }
        
        return severity_mapping.get(endpoint.protocol, SeverityLevel.MEDIUM)

    def _estimate_affected_customers(self, endpoint: ServiceEndpoint) -> Optional[int]:
        """Estimate the number of customers affected by an outage."""
        # This would typically involve querying customer data or service usage statistics
        # For this example, we'll return None (unknown)
        return None

    def _check_for_recovery(self, endpoint: ServiceEndpoint) -> None:
        """Check if a service has recovered from an outage."""
        # Check if there's an active outage
        active_outage = (
            self.db.query(ServiceOutage)
            .filter(
                ServiceOutage.endpoint_id == endpoint.id,
                ServiceOutage.end_time.is_(None)
            )
            .first()
        )
        
        if active_outage:
            # Check consecutive successes
            consecutive_successes = (
                self.db.query(ServiceStatus)
                .filter(
                    ServiceStatus.endpoint_id == endpoint.id,
                    ServiceStatus.status == StatusType.UP
                )
                .order_by(desc(ServiceStatus.timestamp))
                .limit(3)  # Require 3 consecutive successful checks
                .all()
            )
            
            if len(consecutive_successes) >= 3:
                self._resolve_outage(active_outage)

    def _resolve_outage(self, outage: ServiceOutage) -> None:
        """Resolve an active outage."""
        now = datetime.utcnow()
        
        # Calculate duration
        duration_seconds = int((now - outage.start_time).total_seconds())
        
        # Update outage
        outage.end_time = now
        outage.duration = duration_seconds
        self.db.commit()
        
        logger.info(f"Resolved service outage {outage.id} after {duration_seconds} seconds")
        
        # Update in Elasticsearch
        self._index_outage_to_elasticsearch(outage)
        
        # Create recovery alert
        self._create_recovery_alert(outage)

    def _index_outage_to_elasticsearch(self, outage: ServiceOutage) -> None:
        """Index service outage in Elasticsearch."""
        try:
            index_name = f"isp-service-outages-{datetime.utcnow().strftime('%Y.%m.%d')}"
            doc = outage.to_dict()
            
            self.es_client.index(index=index_name, body=doc)
            
            # Mark as synced
            outage.elasticsearch_synced = True
            self.db.commit()
        except Exception as e:
            logger.error(f"Error indexing service outage to Elasticsearch: {str(e)}")

    # Outage CRUD operations
    def get_outage(self, outage_id: str) -> Optional[ServiceOutage]:
        """Get an outage by ID."""
        return self.db.query(ServiceOutage).filter(ServiceOutage.id == outage_id).first()

    def get_active_outages(self) -> List[ServiceOutage]:
        """Get all active outages."""
        return (
            self.db.query(ServiceOutage)
            .filter(ServiceOutage.end_time.is_(None))
            .all()
        )

    def get_outages(
        self,
        endpoint_id: Optional[str] = None,
        severity: Optional[SeverityLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_resolved: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ServiceOutage], int]:
        """Get outages with optional filtering."""
        query = self.db.query(ServiceOutage)
        
        if endpoint_id:
            query = query.filter(ServiceOutage.endpoint_id == endpoint_id)
        
        if severity:
            query = query.filter(ServiceOutage.severity == severity)
        
        if start_time:
            query = query.filter(ServiceOutage.start_time >= start_time)
        
        if end_time:
            query = query.filter(ServiceOutage.start_time <= end_time)
        
        if not include_resolved:
            query = query.filter(ServiceOutage.end_time.is_(None))
        
        total = query.count()
        outages = query.order_by(desc(ServiceOutage.start_time)).offset(skip).limit(limit).all()
        
        return outages, total

    def update_outage(self, outage_id: str, outage_update: ServiceOutageUpdate) -> Optional[ServiceOutage]:
        """Update an outage."""
        db_outage = self.get_outage(outage_id)
        if not db_outage:
            return None
        
        update_data = outage_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_outage, key, value)
        
        # If end_time is provided but duration is not, calculate duration
        if 'end_time' in update_data and db_outage.end_time and not db_outage.duration:
            db_outage.duration = int((db_outage.end_time - db_outage.start_time).total_seconds())
        
        self.db.commit()
        self.db.refresh(db_outage)
        
        # Update in Elasticsearch
        self._index_outage_to_elasticsearch(db_outage)
        
        return db_outage

    def resolve_outage(self, outage_id: str, resolution_notes: Optional[str] = None) -> Optional[ServiceOutage]:
        """Resolve an outage manually."""
        db_outage = self.get_outage(outage_id)
        if not db_outage or db_outage.end_time:
            return None
        
        update_data = {
            "end_time": datetime.utcnow(),
            "resolution_notes": resolution_notes
        }
        
        # Calculate duration
        duration_seconds = int((update_data["end_time"] - db_outage.start_time).total_seconds())
        update_data["duration"] = duration_seconds
        
        for key, value in update_data.items():
            setattr(db_outage, key, value)
        
        self.db.commit()
        self.db.refresh(db_outage)
        
        logger.info(f"Manually resolved service outage {outage_id}")
        
        # Update in Elasticsearch
        self._index_outage_to_elasticsearch(db_outage)
        
        # Create recovery alert
        self._create_recovery_alert(db_outage)
        
        return db_outage

    def get_outage_summary(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get a summary of outages."""
        query = self.db.query(ServiceOutage)
        
        if start_time:
            query = query.filter(ServiceOutage.start_time >= start_time)
        
        if end_time:
            query = query.filter(ServiceOutage.start_time <= end_time)
        
        # Total outages
        total_outages = query.count()
        
        # Active outages
        active_outages = query.filter(ServiceOutage.end_time.is_(None)).count()
        
        # Outages by severity
        severity_counts = (
            self.db.query(
                ServiceOutage.severity,
                func.count(ServiceOutage.id).label("count")
            )
            .filter(
                *([ServiceOutage.start_time >= start_time] if start_time else []),
                *([ServiceOutage.start_time <= end_time] if end_time else [])
            )
            .group_by(ServiceOutage.severity)
            .all()
        )
        
        severity_summary = {severity.value: 0 for severity in SeverityLevel}
        for severity, count in severity_counts:
            severity_summary[severity.value] = count
        
        # Average duration of resolved outages
        avg_duration_result = (
            self.db.query(func.avg(ServiceOutage.duration).label("avg_duration"))
            .filter(
                ServiceOutage.end_time.isnot(None),
                *([ServiceOutage.start_time >= start_time] if start_time else []),
                *([ServiceOutage.start_time <= end_time] if end_time else [])
            )
            .first()
        )
        
        avg_duration = avg_duration_result[0] if avg_duration_result and avg_duration_result[0] else 0
        
        return {
            "total_outages": total_outages,
            "active_outages": active_outages,
            "by_severity": severity_summary,
            "avg_duration_seconds": avg_duration
        }

    # Alert management
    def _create_outage_alerts(self, outage: ServiceOutage) -> List[ServiceAlert]:
        """Create alerts for a new outage."""
        alerts = []
        
        # Get notification channels from environment or configuration
        notification_channels = os.getenv("ALERT_NOTIFICATION_CHANNELS", "email").split(",")
        
        for channel in notification_channels:
            try:
                channel_type = NotificationType(channel.strip())
                
                # Create alert message
                message = self._create_alert_message(outage, is_recovery=False)
                
                # Create alert
                alert_data = ServiceAlertCreate(
                    outage_id=outage.id,
                    notification_type=channel_type,
                    message=message
                )
                
                db_alert = ServiceAlert(**alert_data.model_dump())
                self.db.add(db_alert)
                alerts.append(db_alert)
                
                # In a real system, you would send the alert here
                # self._send_alert(db_alert)
                
            except ValueError:
                logger.warning(f"Invalid notification channel: {channel}")
        
        if alerts:
            self.db.commit()
            for alert in alerts:
                self.db.refresh(alert)
            
            logger.info(f"Created {len(alerts)} alerts for outage {outage.id}")
        
        return alerts

    def _create_recovery_alert(self, outage: ServiceOutage) -> List[ServiceAlert]:
        """Create alerts for a resolved outage."""
        alerts = []
        
        # Get notification channels from environment or configuration
        notification_channels = os.getenv("ALERT_NOTIFICATION_CHANNELS", "email").split(",")
        
        for channel in notification_channels:
            try:
                channel_type = NotificationType(channel.strip())
                
                # Create alert message
                message = self._create_alert_message(outage, is_recovery=True)
                
                # Create alert
                alert_data = ServiceAlertCreate(
                    outage_id=outage.id,
                    notification_type=channel_type,
                    message=message
                )
                
                db_alert = ServiceAlert(**alert_data.model_dump())
                self.db.add(db_alert)
                alerts.append(db_alert)
                
                # In a real system, you would send the alert here
                # self._send_alert(db_alert)
                
            except ValueError:
                logger.warning(f"Invalid notification channel: {channel}")
        
        if alerts:
            self.db.commit()
            for alert in alerts:
                self.db.refresh(alert)
            
            logger.info(f"Created {len(alerts)} recovery alerts for outage {outage.id}")
        
        return alerts

    def _create_alert_message(self, outage: ServiceOutage, is_recovery: bool = False) -> str:
        """Create an alert message for an outage."""
        endpoint = outage.endpoint
        
        if is_recovery:
            duration_str = f"{outage.duration} seconds" if outage.duration else "unknown duration"
            return (
                f"SERVICE RECOVERED: {endpoint.name}\n\n"
                f"Service: {endpoint.name} ({endpoint.id})\n"
                f"Status: RECOVERED\n"
                f"Recovery Time: {outage.end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"Outage Duration: {duration_str}\n"
                f"Protocol: {endpoint.protocol.value}\n"
                f"URL: {endpoint.url}" + (f":{endpoint.port}" if endpoint.port else "")
            )
        else:
            return (
                f"SERVICE OUTAGE: {endpoint.name}\n\n"
                f"Service: {endpoint.name} ({endpoint.id})\n"
                f"Status: {outage.severity.value.upper()}\n"
                f"Start Time: {outage.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"Protocol: {endpoint.protocol.value}\n"
                f"URL: {endpoint.url}" + (f":{endpoint.port}" if endpoint.port else "")
            )

    # Maintenance window management
    def is_in_maintenance(self, endpoint_id: str) -> bool:
        """Check if a service endpoint is currently in maintenance."""
        now = datetime.utcnow()
        
        maintenance_windows = (
            self.db.query(MaintenanceWindow)
            .filter(
                MaintenanceWindow.start_time <= now,
                MaintenanceWindow.end_time >= now,
                or_(
                    MaintenanceWindow.affected_services.is_(None),
                    MaintenanceWindow.affected_services == "",
                    MaintenanceWindow.affected_services.like(f"%{endpoint_id}%")
                )
            )
            .all()
        )
        
        return len(maintenance_windows) > 0

    def create_maintenance_window(self, window: MaintenanceWindowCreate) -> MaintenanceWindow:
        """Create a new maintenance window."""
        db_window = MaintenanceWindow(**window.model_dump())
        self.db.add(db_window)
        self.db.commit()
        self.db.refresh(db_window)
        
        logger.info(f"Created maintenance window: {db_window.id} ({db_window.name})")
        return db_window

    def get_maintenance_window(self, window_id: str) -> Optional[MaintenanceWindow]:
        """Get a maintenance window by ID."""
        return self.db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()

    def get_active_maintenance_windows(self) -> List[MaintenanceWindow]:
        """Get all active maintenance windows."""
        now = datetime.utcnow()
        
        return (
            self.db.query(MaintenanceWindow)
            .filter(
                MaintenanceWindow.start_time <= now,
                MaintenanceWindow.end_time >= now
            )
            .all()
        )

    def get_maintenance_windows(
        self,
        include_past: bool = False,
        include_future: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[MaintenanceWindow], int]:
        """Get maintenance windows with optional filtering."""
        query = self.db.query(MaintenanceWindow)
        now = datetime.utcnow()
        
        if not include_past:
            query = query.filter(MaintenanceWindow.end_time >= now)
        
        if not include_future:
            query = query.filter(MaintenanceWindow.start_time <= now)
        
        total = query.count()
        windows = query.order_by(MaintenanceWindow.start_time).offset(skip).limit(limit).all()
        
        return windows, total

    def update_maintenance_window(
        self, 
        window_id: str, 
        window_update: MaintenanceWindowUpdate
    ) -> Optional[MaintenanceWindow]:
        """Update a maintenance window."""
        db_window = self.get_maintenance_window(window_id)
        if not db_window:
            return None
        
        update_data = window_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_window, key, value)
        
        self.db.commit()
        self.db.refresh(db_window)
        
        logger.info(f"Updated maintenance window: {db_window.id}")
        return db_window

    def delete_maintenance_window(self, window_id: str) -> bool:
        """Delete a maintenance window."""
        db_window = self.get_maintenance_window(window_id)
        if not db_window:
            return False
        
        self.db.delete(db_window)
        self.db.commit()
        
        logger.info(f"Deleted maintenance window: {window_id}")
        return True
