from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from backend_core.database import Base

logger = logging.getLogger(__name__)

class AuditLog(Base):
    """Model for storing audit logs of user activities."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)
    username = Column(String(100), index=True, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(20), nullable=False)
    details = Column(Text, nullable=True)
    severity = Column(String(20), default="info")
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)


class AuditLogService:
    """Service for handling audit logging operations."""

    @classmethod
    def log_event(cls, 
                  event_type: str, 
                  status: str, 
                  user_id: Optional[int] = None,
                  username: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  severity: str = "info",
                  resource_type: Optional[str] = None,
                  resource_id: Optional[str] = None,
                  db: Optional[Session] = None) -> None:
        """
        Log an audit event to the database and optionally to Elasticsearch.
        
        Args:
            event_type: Type of event (e.g., login, logout, data_access)
            status: Status of the event (e.g., success, failed, pending)
            user_id: ID of the user who performed the action
            username: Username of the user who performed the action
            ip_address: IP address from which the action was performed
            details: Additional details about the event
            severity: Severity level (info, warning, error, critical)
            resource_type: Type of resource being accessed/modified
            resource_id: ID of the resource being accessed/modified
            db: Database session (if None, logs to console only)
        """
        # Create log entry
        log_entry = {
            "event_type": event_type,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "details": json.dumps(details) if details else None,
            "severity": severity,
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        
        # Log to console for debugging
        log_message = (f"AUDIT: {event_type} by {username or 'anonymous'} "
                      f"(ID: {user_id or 'N/A'}) from {ip_address or 'unknown'} - {status}")
        
        if severity == "error" or severity == "critical":
            logger.error(log_message)
        elif severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
            
        # Store in database if session provided
        if db:
            try:
                audit_log = AuditLog(
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    ip_address=ip_address,
                    status=status,
                    details=json.dumps(details) if details else None,
                    severity=severity,
                    resource_type=resource_type,
                    resource_id=resource_id
                )
                db.add(audit_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to store audit log in database: {str(e)}")
                db.rollback()
                
        # TODO: Add Elasticsearch logging integration here
        # This would send the log_entry to Elasticsearch for advanced search and analytics
        
    @classmethod
    def get_logs(cls,
                user_id: Optional[int] = None,
                event_type: Optional[str] = None,
                start_date: Optional[datetime] = None,
                end_date: Optional[datetime] = None,
                severity: Optional[str] = None,
                resource_type: Optional[str] = None,
                resource_id: Optional[str] = None,
                skip: int = 0,
                limit: int = 50,
                db: Session = None) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve audit logs with optional filtering.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Filter by start date
            end_date: Filter by end date
            severity: Filter by severity level
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            db: Database session
            
        Returns:
            Tuple of (list of log entries, total count)
        """
        if not db:
            logger.error("Database session is required to retrieve audit logs")
            return [], 0
            
        query = db.query(AuditLog)
        
        # Apply filters
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        if severity:
            query = query.filter(AuditLog.severity == severity)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
            
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        query = query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit)
        
        # Convert to list of dictionaries
        logs = []
        for log in query.all():
            log_dict = {
                "id": log.id,
                "event_type": log.event_type,
                "user_id": log.user_id,
                "username": log.username,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat(),
                "status": log.status,
                "details": json.loads(log.details) if log.details else None,
                "severity": log.severity,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id
            }
            logs.append(log_dict)
            
        return logs, total
