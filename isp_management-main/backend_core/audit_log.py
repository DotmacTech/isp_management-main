"""
Audit logging for the ISP Management Platform.
"""
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union
from elasticsearch import Elasticsearch
from redis import Redis
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audit")

# Environment variables
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
AUDIT_LOG_INDEX = os.getenv("AUDIT_LOG_INDEX", "isp_audit_logs")
ENABLE_ELASTICSEARCH = os.getenv("ENABLE_ELASTICSEARCH", "false").lower() == "true"

# Redis client for buffering logs
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

# Elasticsearch client for persistent storage
es_client = None
if ENABLE_ELASTICSEARCH:
    try:
        es_client = Elasticsearch(ELASTICSEARCH_URL)
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")

class AuditLogService:
    """Service for audit logging."""
    
    @staticmethod
    def log_event(
        event_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> str:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., auth, user, billing)
            user_id: ID of the user performing the action
            username: Username of the user performing the action
            ip_address: IP address of the user
            resource_type: Type of resource being accessed
            resource_id: ID of the resource being accessed
            action: Action being performed
            status: Status of the action (success, failure)
            details: Additional details about the event
            severity: Severity level (info, warning, error)
        
        Returns:
            ID of the logged event
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        event = {
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "status": status,
            "details": details or {},
            "severity": severity
        }
        
        # Log to console
        log_message = (
            f"AUDIT: {event_type} - "
            f"User: {username or user_id or 'Anonymous'} - "
            f"Action: {action or 'N/A'} - "
            f"Status: {status or 'N/A'} - "
            f"Resource: {resource_type or 'N/A'}/{resource_id or 'N/A'}"
        )
        
        if severity == "error":
            logger.error(log_message)
        elif severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Store in Redis for buffering
        redis_client.lpush("audit_log_buffer", json.dumps(event))
        
        # If Elasticsearch is enabled, store directly
        if ENABLE_ELASTICSEARCH and es_client:
            try:
                es_client.index(index=AUDIT_LOG_INDEX, document=event, id=event_id)
            except Exception as e:
                logger.error(f"Failed to store audit log in Elasticsearch: {e}")
        
        return event_id
    
    @staticmethod
    def log_auth_event(
        action: str,
        status: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> str:
        """
        Log an authentication event.
        
        Args:
            action: Authentication action (login, logout, password_reset, etc.)
            status: Status of the action (success, failure)
            user_id: ID of the user
            username: Username of the user
            ip_address: IP address of the user
            details: Additional details about the event
            severity: Severity level (info, warning, error)
        
        Returns:
            ID of the logged event
        """
        return AuditLogService.log_event(
            event_type="auth",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=action,
            status=status,
            details=details,
            severity=severity
        )
    
    @staticmethod
    def log_user_event(
        action: str,
        status: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        target_user_id: Optional[int] = None,
        target_username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> str:
        """
        Log a user management event.
        
        Args:
            action: User management action (create, update, delete, etc.)
            status: Status of the action (success, failure)
            user_id: ID of the user performing the action
            username: Username of the user performing the action
            target_user_id: ID of the target user
            target_username: Username of the target user
            ip_address: IP address of the user
            details: Additional details about the event
            severity: Severity level (info, warning, error)
        
        Returns:
            ID of the logged event
        """
        return AuditLogService.log_event(
            event_type="user",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource_type="user",
            resource_id=str(target_user_id) if target_user_id else None,
            action=action,
            status=status,
            details={
                **(details or {}),
                "target_username": target_username
            },
            severity=severity
        )
    
    @staticmethod
    def log_permission_event(
        action: str,
        status: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        target_user_id: Optional[int] = None,
        target_username: Optional[str] = None,
        role: Optional[str] = None,
        permission: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> str:
        """
        Log a permission/role management event.
        
        Args:
            action: Permission action (grant, revoke, role_change, etc.)
            status: Status of the action (success, failure)
            user_id: ID of the user performing the action
            username: Username of the user performing the action
            target_user_id: ID of the target user
            target_username: Username of the target user
            role: Role being assigned or modified
            permission: Permission being granted or revoked
            ip_address: IP address of the user
            details: Additional details about the event
            severity: Severity level (info, warning, error)
        
        Returns:
            ID of the logged event
        """
        return AuditLogService.log_event(
            event_type="permission",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource_type="role" if role else "permission",
            resource_id=role or permission,
            action=action,
            status=status,
            details={
                **(details or {}),
                "target_user_id": target_user_id,
                "target_username": target_username,
                "role": role,
                "permission": permission
            },
            severity=severity
        )
    
    @staticmethod
    def flush_buffer_to_elasticsearch() -> int:
        """
        Flush buffered audit logs to Elasticsearch.
        
        Returns:
            Number of logs flushed
        """
        if not ENABLE_ELASTICSEARCH or not es_client:
            return 0
        
        count = 0
        while True:
            # Get a log from the buffer
            log_data = redis_client.rpop("audit_log_buffer")
            if not log_data:
                break
            
            try:
                log = json.loads(log_data)
                es_client.index(index=AUDIT_LOG_INDEX, document=log, id=log.get("event_id"))
                count += 1
            except Exception as e:
                logger.error(f"Failed to flush audit log to Elasticsearch: {e}")
                # Push back to the front of the queue
                redis_client.rpush("audit_log_buffer", log_data)
                break
        
        return count
