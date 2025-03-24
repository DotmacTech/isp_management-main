"""
Service for managing logs in the monitoring module.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from modules.monitoring.models.service_log import ServiceLog
from modules.monitoring.models.log_retention import LogRetentionPolicy
from modules.monitoring.models.monitoring_models import (
    ServiceLogCreate, ServiceLogResponse, LogSearchParams, LogSearchResult, LogLevel
)
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)


class LoggingService:
    """Service for managing logs in the monitoring module."""

    def __init__(self, db: Session):
        """Initialize the service with database session."""
        self.db = db
        self.es_client = ElasticsearchClient()

    def create_log(self, log_data: ServiceLogCreate) -> ServiceLog:
        """
        Create a new log entry.
        
        Args:
            log_data: Log data to create.
            
        Returns:
            Created log entry.
        """
        log = ServiceLog(**log_data.model_dump())
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def search_logs(
        self,
        service_names: Optional[List[str]] = None,
        log_levels: Optional[List[LogLevel]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        message_contains: Optional[str] = None,
        request_path: Optional[str] = None,
        use_elasticsearch: bool = True,
        offset: int = 0,
        limit: int = 50
    ) -> LogSearchResult:
        """
        Search logs with filtering options.
        
        Args:
            service_names: Filter by service names.
            log_levels: Filter by log levels.
            start_time: Filter by start time.
            end_time: Filter by end time.
            trace_id: Filter by trace ID.
            correlation_id: Filter by correlation ID.
            user_id: Filter by user ID.
            message_contains: Filter by message content.
            request_path: Filter by request path.
            use_elasticsearch: Whether to use Elasticsearch for search.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            Search result with logs and total count.
        """
        if use_elasticsearch and self.es_client.is_connected():
            # Use Elasticsearch for search
            return self._search_logs_elasticsearch(
                service_names, log_levels, start_time, end_time,
                trace_id, correlation_id, user_id, message_contains,
                request_path, offset, limit
            )
        else:
            # Use database for search
            return self._search_logs_database(
                service_names, log_levels, start_time, end_time,
                trace_id, correlation_id, user_id, message_contains,
                request_path, offset, limit
            )

    def _search_logs_elasticsearch(
        self,
        service_names: Optional[List[str]] = None,
        log_levels: Optional[List[LogLevel]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        message_contains: Optional[str] = None,
        request_path: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> LogSearchResult:
        """
        Search logs using Elasticsearch.
        
        Args:
            service_names: Filter by service names.
            log_levels: Filter by log levels.
            start_time: Filter by start time.
            end_time: Filter by end time.
            trace_id: Filter by trace ID.
            correlation_id: Filter by correlation ID.
            user_id: Filter by user ID.
            message_contains: Filter by message content.
            request_path: Filter by request path.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            Search result with logs and total count.
        """
        # Build Elasticsearch query
        query = {"bool": {"must": []}}
        
        if service_names:
            query["bool"]["must"].append({"terms": {"service_name.keyword": service_names}})
        
        if log_levels:
            query["bool"]["must"].append({"terms": {"log_level.keyword": [level.value for level in log_levels]}})
        
        if start_time or end_time:
            range_query = {"range": {"timestamp": {}}}
            if start_time:
                range_query["range"]["timestamp"]["gte"] = start_time.isoformat()
            if end_time:
                range_query["range"]["timestamp"]["lte"] = end_time.isoformat()
            query["bool"]["must"].append(range_query)
        
        if trace_id:
            query["bool"]["must"].append({"term": {"trace_id.keyword": trace_id}})
        
        if correlation_id:
            query["bool"]["must"].append({"term": {"correlation_id.keyword": correlation_id}})
        
        if user_id:
            query["bool"]["must"].append({"term": {"user_id": user_id}})
        
        if message_contains:
            query["bool"]["must"].append({"match": {"message": message_contains}})
        
        if request_path:
            query["bool"]["must"].append({"term": {"request_path.keyword": request_path}})
        
        # Execute search
        result = self.es_client.search(
            index="service_logs",
            query=query,
            sort=[{"timestamp": {"order": "desc"}}],
            from_=offset,
            size=limit
        )
        
        # Process results
        logs = []
        for hit in result.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            logs.append(ServiceLogResponse.model_validate(source))
        
        total = result.get("hits", {}).get("total", {}).get("value", 0)
        
        return LogSearchResult(logs=logs, total=total)

    def _search_logs_database(
        self,
        service_names: Optional[List[str]] = None,
        log_levels: Optional[List[LogLevel]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        message_contains: Optional[str] = None,
        request_path: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> LogSearchResult:
        """
        Search logs using the database.
        
        Args:
            service_names: Filter by service names.
            log_levels: Filter by log levels.
            start_time: Filter by start time.
            end_time: Filter by end time.
            trace_id: Filter by trace ID.
            correlation_id: Filter by correlation ID.
            user_id: Filter by user ID.
            message_contains: Filter by message content.
            request_path: Filter by request path.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            Search result with logs and total count.
        """
        # Build query
        query = self.db.query(ServiceLog)
        
        # Apply filters
        if service_names:
            query = query.filter(ServiceLog.service_name.in_(service_names))
        
        if log_levels:
            query = query.filter(ServiceLog.log_level.in_([level.value for level in log_levels]))
        
        if start_time:
            query = query.filter(ServiceLog.timestamp >= start_time)
        
        if end_time:
            query = query.filter(ServiceLog.timestamp <= end_time)
        
        if trace_id:
            query = query.filter(ServiceLog.trace_id == trace_id)
        
        if correlation_id:
            query = query.filter(ServiceLog.correlation_id == correlation_id)
        
        if user_id:
            query = query.filter(ServiceLog.user_id == user_id)
        
        if message_contains:
            query = query.filter(ServiceLog.message.ilike(f"%{message_contains}%"))
        
        if request_path:
            query = query.filter(ServiceLog.request_path == request_path)
        
        # Count total results
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(ServiceLog.timestamp)).offset(offset).limit(limit)
        
        # Execute query
        logs = query.all()
        
        # Convert to response objects
        log_responses = [ServiceLogResponse.model_validate(log) for log in logs]
        
        return LogSearchResult(logs=log_responses, total=total)
    
    def get_log_by_id(self, log_id: str) -> Optional[ServiceLog]:
        """
        Get a log by ID.
        
        Args:
            log_id: ID of the log to retrieve.
            
        Returns:
            Log if found, None otherwise.
        """
        return self.db.query(ServiceLog).filter_by(id=log_id).first()
    
    def update_log(self, log_id: str, log_data: dict) -> Optional[ServiceLog]:
        """
        Update a log.
        
        Args:
            log_id: ID of the log to update.
            log_data: Data to update.
            
        Returns:
            Updated log if found, None otherwise.
        """
        log = self.get_log_by_id(log_id)
        if not log:
            return None
        
        for key, value in log_data.items():
            setattr(log, key, value)
        
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def delete_log(self, log_id: str) -> bool:
        """
        Delete a log.
        
        Args:
            log_id: ID of the log to delete.
            
        Returns:
            True if deleted, False otherwise.
        """
        log = self.get_log_by_id(log_id)
        if not log:
            return False
        
        self.db.delete(log)
        self.db.commit()
        return True
    
    def apply_retention_policy(self) -> int:
        """
        Apply log retention policy and delete old logs.
        
        Returns:
            Number of logs deleted.
        """
        # Get retention policy
        policy = self.db.query(LogRetentionPolicy).first()
        if not policy:
            logger.warning("No log retention policy found, skipping cleanup")
            return 0
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
        
        # Delete old logs
        result = self.db.query(ServiceLog).filter(
            ServiceLog.timestamp < cutoff_date
        ).delete(synchronize_session=False)
        
        self.db.commit()
        
        logger.info(f"Deleted {result} logs older than {policy.retention_days} days")
        return result
    
    def sync_logs_to_elasticsearch(self, batch_size: int = 100) -> int:
        """
        Sync logs to Elasticsearch.
        
        Args:
            batch_size: Number of logs to sync in each batch.
            
        Returns:
            Number of logs synced.
        """
        if not self.es_client.is_connected():
            logger.warning("Elasticsearch client not connected, skipping sync")
            return 0
        
        # Get logs that haven't been synced
        logs = self.db.query(ServiceLog).filter_by(
            elasticsearch_synced=False
        ).limit(batch_size).all()
        
        if not logs:
            return 0
        
        # Prepare batch
        batch = []
        log_ids = []
        
        for log in logs:
            batch.append({
                "index": {
                    "_index": "service_logs",
                    "_id": log.id
                }
            })
            
            # Convert log to dict
            log_dict = {
                "id": log.id,
                "service_name": log.service_name,
                "log_level": log.log_level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat(),
                "trace_id": log.trace_id,
                "correlation_id": log.correlation_id,
                "user_id": log.user_id,
                "request_path": log.request_path,
                "request_method": log.request_method,
                "response_status": log.response_status,
                "response_time": log.response_time,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "additional_data": log.additional_data
            }
            
            batch.append(log_dict)
            log_ids.append(log.id)
        
        # Send batch to Elasticsearch
        try:
            self.es_client.bulk(batch)
            
            # Mark logs as synced
            self.db.query(ServiceLog).filter(
                ServiceLog.id.in_(log_ids)
            ).update(
                {"elasticsearch_synced": True},
                synchronize_session=False
            )
            
            self.db.commit()
            
            logger.info(f"Synced {len(logs)} logs to Elasticsearch")
            return len(logs)
            
        except Exception as e:
            logger.error(f"Error syncing logs to Elasticsearch: {str(e)}")
            return 0
