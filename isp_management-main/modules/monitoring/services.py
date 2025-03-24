from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy import func, desc, and_, or_, text
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends
import json
import logging
import uuid
from elasticsearch import Elasticsearch
from redis import Redis

from backend_core.database import get_db
from backend_core.cache import get_redis
from backend_core.config import settings

from .models import (
    ServiceLog, 
    SystemMetric, 
    AlertConfiguration, 
    AlertHistory, 
    LogRetentionPolicy,
    LogArchive,
    DashboardConfiguration,
    DashboardWidget,
    SystemHealthCheck,
    SystemHealthStatus
)

from .schemas import (
    ServiceLogCreate,
    ServiceLogUpdate,
    ServiceLogResponse,
    ServiceLogFilter,
    SystemMetricCreate,
    SystemMetricUpdate,
    SystemMetricResponse,
    SystemMetricFilter,
    AlertConfigurationCreate,
    AlertConfigurationUpdate,
    AlertConfigurationResponse,
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertFilter,
    AlertHistoryCreate,
    AlertHistoryUpdate,
    AlertHistoryResponse,
    LogRetentionPolicyCreate,
    LogRetentionPolicyUpdate,
    LogRetentionPolicyResponse,
    DashboardConfigurationCreate,
    DashboardConfigurationUpdate,
    DashboardConfigurationResponse,
    DashboardWidgetCreate,
    DashboardWidgetUpdate,
    DashboardWidgetResponse,
    SystemHealthCheckCreate,
    SystemHealthCheckUpdate,
    SystemHealthCheckResponse,
    SystemHealthStatusCreate,
    SystemHealthStatusUpdate,
    SystemHealthStatusResponse,
    LogSearchParams,
    MetricSearchParams,
    AlertSearchParams,
    PaginatedResponse,
    MetricType,
    MetricUnit,
    MetricRecord,
    MetricRecordCreate,
    MetricRecordResponse,
    HealthStatusEnum,
    HealthCheckResponse,
    HealthCheckComponentStatus,
    LogLevelEnum
)

# Configure standard logger
logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self, db: Session):
        self.db = db

    async def record_metric(self, metric: MetricRecord) -> Dict[str, Any]:
        """Records a new metric and checks for threshold violations."""
        # Here you would typically:
        # 1. Store the metric in a time-series database (e.g., InfluxDB, Prometheus)
        # 2. Check if any thresholds are violated
        # 3. Create alerts if needed
        
        # For this example, we'll just check some hardcoded thresholds
        # and return the result without actually storing the metric
        
        alert = None
        if metric.metric_type == MetricType.CPU and metric.value > 85:
            alert = self.create_alert(AlertCreate(
                title="High CPU Usage",
                description=f"CPU usage on {metric.host} is {metric.value}%, exceeding 85% threshold",
                severity=AlertSeverity.HIGH,
                metric_type=MetricType.CPU,
                source=metric.host,
                threshold_value=85.0,
                current_value=metric.value
            ))
        elif metric.metric_type == MetricType.MEMORY and metric.value > 90:
            alert = self.create_alert(AlertCreate(
                title="High Memory Usage",
                description=f"Memory usage on {metric.host} is {metric.value}%, exceeding 90% threshold",
                severity=AlertSeverity.HIGH,
                metric_type=MetricType.MEMORY,
                source=metric.host,
                threshold_value=90.0,
                current_value=metric.value
            ))
        elif metric.metric_type == MetricType.RADIUS_AUTH and metric.value > 0:
            # Check if authentication failures are spiking
            # This would typically involve comparing to historical data
            # For simplicity, we'll just create an alert if the value is high
            if metric.value > 100:
                alert = self.create_alert(AlertCreate(
                    title="High RADIUS Authentication Failures",
                    description=f"RADIUS auth failures: {metric.value} in the last 5 minutes",
                    severity=AlertSeverity.MEDIUM,
                    metric_type=MetricType.RADIUS_AUTH,
                    source="radius",
                    threshold_value=100.0,
                    current_value=metric.value
                ))
        
        return {
            "recorded": True,
            "metric_type": metric.metric_type,
            "value": metric.value,
            "timestamp": metric.timestamp,
            "alert_created": alert is not None,
            "alert": alert.dict() if alert else None
        }

    def create_alert(self, alert_data: AlertCreate) -> Any:
        """Creates a new alert in the system."""
        # Here you would typically create an Alert record in the database
        # For now, we'll just return the alert data as if it was created
        
        # Simulating an Alert model with an ID and timestamps
        alert_dict = alert_data.dict()
        alert_dict.update({
            "id": 12345,  # This would normally be assigned by the database
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "resolved_at": None,
            "acknowledged_by": None
        })
        
        # In a real implementation, you would:
        # 1. Create the Alert in the database
        # 2. Possibly send notifications (email, SMS, webhook)
        # 3. Return the created Alert object
        
        return alert_dict

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Gets all active (non-resolved) alerts."""
        # In a real implementation, you would query the database for active alerts
        # For now, we'll return a sample alert
        
        return [{
            "id": 12345,
            "title": "High CPU Usage",
            "description": "CPU usage on server-1 is 92%, exceeding 85% threshold",
            "severity": "high",
            "metric_type": "cpu",
            "source": "server-1",
            "threshold_value": 85.0,
            "current_value": 92.0,
            "status": "active",
            "created_at": datetime.utcnow() - timedelta(minutes=30),
            "updated_at": datetime.utcnow() - timedelta(minutes=30),
            "resolved_at": None,
            "acknowledged_by": None
        }]

    def update_alert(self, alert_id: int, update_data: AlertUpdate) -> Dict[str, Any]:
        """Updates an alert's status (acknowledge or resolve)."""
        # In a real implementation, you would:
        # 1. Find the alert in the database
        # 2. Update its status and other fields
        # 3. Return the updated alert
        
        # For now, we'll just return a sample updated alert
        alert = {
            "id": alert_id,
            "title": "High CPU Usage",
            "description": "CPU usage on server-1 is 92%, exceeding 85% threshold",
            "severity": "high",
            "metric_type": "cpu",
            "source": "server-1",
            "threshold_value": 85.0,
            "current_value": 92.0,
            "status": update_data.status,
            "created_at": datetime.utcnow() - timedelta(minutes=30),
            "updated_at": datetime.utcnow(),
            "resolved_at": datetime.utcnow() if update_data.status == AlertStatus.RESOLVED else None,
            "acknowledged_by": update_data.acknowledged_by
        }
        
        return alert

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Gets key metrics for the dashboard."""
        # In a real implementation, you would:
        # 1. Query various data sources for current metrics
        # 2. Calculate trends and changes
        # 3. Return a structured response
        
        # For now, we'll return sample metrics
        return {
            "system": {
                "cpu": DashboardMetric(
                    name="CPU Usage",
                    value=45.2,
                    unit="%",
                    change_percent=2.3,
                    trend="up"
                ),
                "memory": DashboardMetric(
                    name="Memory Usage",
                    value=62.8,
                    unit="%",
                    change_percent=-1.5,
                    trend="down"
                ),
                "disk": DashboardMetric(
                    name="Disk Usage",
                    value=78.4,
                    unit="%",
                    change_percent=0.2,
                    trend="stable"
                )
            },
            "radius": {
                "active_sessions": DashboardMetric(
                    name="Active Sessions",
                    value=1245,
                    unit="sessions",
                    change_percent=3.8,
                    trend="up"
                ),
                "auth_success_rate": DashboardMetric(
                    name="Auth Success Rate",
                    value=99.2,
                    unit="%",
                    change_percent=0.1,
                    trend="stable"
                )
            },
            "billing": {
                "monthly_revenue": DashboardMetric(
                    name="Monthly Revenue",
                    value=45250,
                    unit="USD",
                    change_percent=5.2,
                    trend="up"
                ),
                "overdue_invoices": DashboardMetric(
                    name="Overdue Invoices",
                    value=23,
                    unit="invoices",
                    change_percent=-2.1,
                    trend="down"
                )
            }
        }

    def check_system_health(self) -> SystemHealthCheck:
        """Performs a health check on all system components."""
        # In a real implementation, you would:
        # 1. Check the status of various services (DB, Redis, etc.)
        # 2. Check for any critical alerts
        # 3. Return an overall health status
        
        # For now, we'll return a sample health check
        components = {
            "database": "healthy",
            "redis": "healthy",
            "elasticsearch": "healthy",
            "radius": "healthy",
            "billing": "healthy",
            "api_gateway": "healthy"
        }
        
        # Overall status is the worst status of any component
        if "unhealthy" in components.values():
            status = "unhealthy"
        elif "degraded" in components.values():
            status = "degraded"
        else:
            status = "healthy"
        
        return SystemHealthCheck(
            status=status,
            components=components,
            last_updated=datetime.utcnow()
        )

class LoggingService:
    """Service for handling centralized logging operations."""
    
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.es_client = self._get_elasticsearch_client()
        
    def _get_elasticsearch_client(self) -> Optional[Elasticsearch]:
        """Get Elasticsearch client if configured."""
        if settings.ELASTICSEARCH_ENABLED:
            try:
                return Elasticsearch(
                    hosts=settings.ELASTICSEARCH_HOSTS.split(','),
                    basic_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD),
                    verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS
                )
            except Exception as e:
                logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
                return None
        return None
    
    async def create_log(self, log_data: ServiceLogCreate) -> ServiceLogResponse:
        """Create a new log entry in both database and Elasticsearch."""
        # Create DB record
        db_log = ServiceLog(**log_data.model_dump())
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        
        # Store in Elasticsearch if available
        if self.es_client:
            try:
                # Add trace ID if not provided
                if not log_data.trace_id:
                    log_data.trace_id = str(uuid.uuid4())
                
                # Format for Elasticsearch
                es_doc = log_data.model_dump()
                es_doc['@timestamp'] = es_doc.pop('timestamp').isoformat()
                
                # Index in Elasticsearch
                self.es_client.index(
                    index=f"logs-{log_data.service_name}-{datetime.utcnow().strftime('%Y.%m.%d')}",
                    document=es_doc
                )
            except Exception as e:
                logger.error(f"Failed to index log in Elasticsearch: {str(e)}")
        
        return ServiceLogResponse.model_validate(db_log)
    
    async def search_logs(self, search_params: LogSearchParams) -> PaginatedResponse:
        """Search logs with filtering options."""
        query = self.db.query(ServiceLog)
        
        # Apply filters
        if search_params.service_names:
            query = query.filter(ServiceLog.service_name.in_(search_params.service_names))
        
        if search_params.log_levels:
            query = query.filter(ServiceLog.log_level.in_(search_params.log_levels))
        
        if search_params.start_time:
            query = query.filter(ServiceLog.timestamp >= search_params.start_time)
        
        if search_params.end_time:
            query = query.filter(ServiceLog.timestamp <= search_params.end_time)
        
        if search_params.trace_id:
            query = query.filter(ServiceLog.trace_id == search_params.trace_id)
        
        if search_params.correlation_id:
            query = query.filter(ServiceLog.correlation_id == search_params.correlation_id)
        
        if search_params.user_id:
            query = query.filter(ServiceLog.user_id == search_params.user_id)
        
        if search_params.message_contains:
            query = query.filter(ServiceLog.message.ilike(f"%{search_params.message_contains}%"))
        
        if search_params.request_path:
            query = query.filter(ServiceLog.request_path.ilike(f"%{search_params.request_path}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(ServiceLog.timestamp))
        query = query.offset(search_params.offset).limit(search_params.limit)
        
        # Execute query
        logs = query.all()
        
        # Convert to response models
        log_responses = [ServiceLogResponse.model_validate(log) for log in logs]
        
        return PaginatedResponse(
            items=log_responses,
            total=total,
            limit=search_params.limit,
            offset=search_params.offset
        )
    
    async def search_logs_elasticsearch(self, search_params: LogSearchParams) -> PaginatedResponse:
        """Search logs in Elasticsearch with advanced filtering and full-text search."""
        if not self.es_client:
            # Fall back to database search if Elasticsearch is not available
            return await self.search_logs(search_params)
        
        # Build Elasticsearch query
        es_query = {"bool": {"must": []}}
        
        # Apply filters
        if search_params.service_names:
            es_query["bool"]["must"].append({"terms": {"service_name": search_params.service_names}})
        
        if search_params.log_levels:
            es_query["bool"]["must"].append({"terms": {"log_level": [level.value for level in search_params.log_levels]}})
        
        if search_params.start_time or search_params.end_time:
            range_query = {"range": {"@timestamp": {}}}
            if search_params.start_time:
                range_query["range"]["@timestamp"]["gte"] = search_params.start_time.isoformat()
            if search_params.end_time:
                range_query["range"]["@timestamp"]["lte"] = search_params.end_time.isoformat()
            es_query["bool"]["must"].append(range_query)
        
        if search_params.trace_id:
            es_query["bool"]["must"].append({"term": {"trace_id": search_params.trace_id}})
        
        if search_params.correlation_id:
            es_query["bool"]["must"].append({"term": {"correlation_id": search_params.correlation_id}})
        
        if search_params.user_id:
            es_query["bool"]["must"].append({"term": {"user_id": search_params.user_id}})
        
        if search_params.message_contains:
            es_query["bool"]["must"].append({"match": {"message": search_params.message_contains}})
        
        if search_params.request_path:
            es_query["bool"]["must"].append({"wildcard": {"request_path": f"*{search_params.request_path}*"}})
        
        try:
            # Execute search
            result = self.es_client.search(
                index="logs-*",
                query=es_query,
                sort=[{"@timestamp": {"order": "desc"}}],
                size=search_params.limit,
                from_=search_params.offset
            )
            
            # Extract hits and total
            hits = result.get("hits", {}).get("hits", [])
            total = result.get("hits", {}).get("total", {}).get("value", 0)
            
            # Convert to response models
            log_responses = []
            for hit in hits:
                source = hit["_source"]
                # Convert timestamp format
                source["timestamp"] = datetime.fromisoformat(source["@timestamp"].replace("Z", "+00:00"))
                log_responses.append(ServiceLogResponse(**source))
            
            return PaginatedResponse(
                items=log_responses,
                total=total,
                limit=search_params.limit,
                offset=search_params.offset
            )
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {str(e)}")
            # Fall back to database search
            return await self.search_logs(search_params)
    
    async def get_log_retention_policies(self) -> List[LogRetentionPolicyResponse]:
        """Get all log retention policies."""
        policies = self.db.query(LogRetentionPolicy).all()
        return [LogRetentionPolicyResponse.model_validate(policy) for policy in policies]
    
    async def create_log_retention_policy(self, policy_data: LogRetentionPolicyCreate) -> LogRetentionPolicyResponse:
        """Create a new log retention policy."""
        db_policy = LogRetentionPolicy(**policy_data.model_dump())
        self.db.add(db_policy)
        self.db.commit()
        self.db.refresh(db_policy)
        return LogRetentionPolicyResponse.model_validate(db_policy)
    
    async def apply_retention_policies(self) -> Dict[str, Any]:
        """Apply retention policies to logs in database and Elasticsearch."""
        policies = self.db.query(LogRetentionPolicy).filter(LogRetentionPolicy.is_active == True).all()
        results = {"database": {}, "elasticsearch": {}}
        
        # Apply to database
        for policy in policies:
            retention_date = datetime.utcnow() - timedelta(days=policy.retention_days)
            
            # Delete logs from database
            deleted_count = self.db.query(ServiceLog).filter(
                ServiceLog.service_name == policy.service_name,
                ServiceLog.log_level == policy.log_level,
                ServiceLog.timestamp < retention_date
            ).delete(synchronize_session=False)
            
            results["database"][f"{policy.service_name}_{policy.log_level.value}"] = deleted_count
        
        self.db.commit()
        
        # Apply to Elasticsearch if available
        if self.es_client:
            try:
                for policy in policies:
                    retention_date = datetime.utcnow() - timedelta(days=policy.retention_days)
                    
                    # Delete logs from Elasticsearch
                    query = {
                        "bool": {
                            "must": [
                                {"term": {"service_name": policy.service_name}},
                                {"term": {"log_level": policy.log_level.value}},
                                {"range": {"@timestamp": {"lt": retention_date.isoformat()}}}
                            ]
                        }
                    }
                    
                    response = self.es_client.delete_by_query(
                        index="logs-*",
                        query=query
                    )
                    
                    results["elasticsearch"][f"{policy.service_name}_{policy.log_level.value}"] = response.get("deleted", 0)
            except Exception as e:
                logger.error(f"Failed to apply retention policies to Elasticsearch: {str(e)}")
                results["elasticsearch"]["error"] = str(e)
        
        return results

class MetricsService:
    """Service for handling system metrics collection and analysis."""
    
    def __init__(self, db: Session = Depends(get_db), redis: Redis = Depends(get_redis)):
        self.db = db
        self.redis = redis
        
    async def create_metric(self, metric_data: SystemMetricCreate) -> SystemMetricResponse:
        """Record a new system metric in the database and cache recent values in Redis."""
        # Create DB record
        db_metric = SystemMetric(**metric_data.model_dump())
        self.db.add(db_metric)
        self.db.commit()
        self.db.refresh(db_metric)
        
        # Cache recent metrics in Redis for real-time dashboards
        if self.redis:
            try:
                # Key format: metrics:{service_name}:{host_name}:{metric_type}
                redis_key = f"metrics:{metric_data.service_name}:{metric_data.host_name}:{metric_data.metric_type.value}"
                
                # Store as a sorted set with timestamp as score for time-based retrieval
                timestamp = metric_data.timestamp.timestamp()
                self.redis.zadd(redis_key, {json.dumps({
                    "value": metric_data.value,
                    "unit": metric_data.unit,
                    "timestamp": metric_data.timestamp.isoformat()
                }): timestamp})
                
                # Set expiration for automatic cleanup (keep last 24 hours)
                self.redis.expire(redis_key, 86400)  # 24 hours in seconds
                
                # Also store latest value for quick access
                latest_key = f"metrics:latest:{metric_data.service_name}:{metric_data.host_name}:{metric_data.metric_type.value}"
                self.redis.set(latest_key, json.dumps({
                    "value": metric_data.value,
                    "unit": metric_data.unit,
                    "timestamp": metric_data.timestamp.isoformat()
                }))
                self.redis.expire(latest_key, 86400)  # 24 hours in seconds
            except Exception as e:
                logger.error(f"Failed to cache metric in Redis: {str(e)}")
        
        return SystemMetricResponse.model_validate(db_metric)
    
    async def search_metrics(self, search_params: MetricSearchParams) -> PaginatedResponse:
        """Search metrics with filtering and optional aggregation."""
        query = self.db.query(SystemMetric)
        
        # Apply filters
        if search_params.service_names:
            query = query.filter(SystemMetric.service_name.in_(search_params.service_names))
        
        if search_params.host_names:
            query = query.filter(SystemMetric.host_name.in_(search_params.host_names))
        
        if search_params.metric_types:
            query = query.filter(SystemMetric.metric_type.in_(search_params.metric_types))
        
        if search_params.start_time:
            query = query.filter(SystemMetric.timestamp >= search_params.start_time)
        
        if search_params.end_time:
            query = query.filter(SystemMetric.timestamp <= search_params.end_time)
        
        # Handle tag filtering (JSON field)
        if search_params.tags:
            for tag_key, tag_value in search_params.tags.items():
                # This is PostgreSQL-specific JSON querying
                query = query.filter(text(f"tags->'{tag_key}' = '{tag_value}'"))
        
        # Handle aggregation if requested
        if search_params.aggregation and search_params.group_by:
            # Build group by columns
            group_columns = []
            for group_field in search_params.group_by:
                if hasattr(SystemMetric, group_field):
                    group_columns.append(getattr(SystemMetric, group_field))
            
            # Build aggregation function
            if search_params.aggregation == "avg":
                agg_func = func.avg(SystemMetric.value)
            elif search_params.aggregation == "sum":
                agg_func = func.sum(SystemMetric.value)
            elif search_params.aggregation == "min":
                agg_func = func.min(SystemMetric.value)
            elif search_params.aggregation == "max":
                agg_func = func.max(SystemMetric.value)
            elif search_params.aggregation == "count":
                agg_func = func.count(SystemMetric.value)
            else:
                agg_func = func.avg(SystemMetric.value)  # Default to average
            
            # Execute aggregation query
            results = query.with_entities(*group_columns, agg_func).group_by(*group_columns).all()
            
            # Format results
            aggregated_metrics = []
            for result in results:
                metric_dict = {}
                for i, group_field in enumerate(search_params.group_by):
                    metric_dict[group_field] = result[i]
                metric_dict["value"] = result[-1]  # Aggregated value is the last item
                metric_dict["unit"] = "aggregated"  # Units may vary in aggregation
                metric_dict["timestamp"] = datetime.utcnow()
                aggregated_metrics.append(SystemMetricResponse(**metric_dict))
            
            return PaginatedResponse(
                items=aggregated_metrics,
                total=len(aggregated_metrics),
                limit=search_params.limit,
                offset=search_params.offset
            )
        else:
            # Regular non-aggregated query
            # Get total count
            total = query.count()
            
            # Apply pagination
            query = query.order_by(desc(SystemMetric.timestamp))
            query = query.offset(search_params.offset).limit(search_params.limit)
            
            # Execute query
            metrics = query.all()
            
            # Convert to response models
            metric_responses = [SystemMetricResponse.model_validate(metric) for metric in metrics]
            
            return PaginatedResponse(
                items=metric_responses,
                total=total,
                limit=search_params.limit,
                offset=search_params.offset
            )
    
    async def get_latest_metrics(self, service_name: Optional[str] = None, 
                               host_name: Optional[str] = None,
                               metric_type: Optional[MetricType] = None) -> List[SystemMetricResponse]:
        """Get the latest metrics, optionally filtered by service, host, or metric type."""
        # Try to get from Redis first for better performance
        if self.redis:
            try:
                # Build Redis key pattern
                service_part = service_name if service_name else "*"
                host_part = host_name if host_name else "*"
                metric_part = metric_type.value if metric_type else "*"
                pattern = f"metrics:latest:{service_part}:{host_part}:{metric_part}"
                
                # Get all matching keys
                keys = self.redis.keys(pattern)
                
                if keys:
                    # Get all values in a single pipeline for efficiency
                    pipe = self.redis.pipeline()
                    for key in keys:
                        pipe.get(key)
                    values = pipe.execute()
                    
                    # Parse results
                    latest_metrics = []
                    for i, key in enumerate(keys):
                        if values[i]:
                            # Parse key to get metadata
                            key_parts = key.decode('utf-8').split(':')
                            if len(key_parts) >= 5:  # metrics:latest:service:host:metric
                                metric_data = json.loads(values[i])
                                latest_metrics.append(SystemMetricResponse(
                                    id=0,  # Not available from Redis
                                    service_name=key_parts[2],
                                    host_name=key_parts[3],
                                    metric_type=key_parts[4],
                                    value=metric_data["value"],
                                    unit=metric_data["unit"],
                                    timestamp=datetime.fromisoformat(metric_data["timestamp"]),
                                    tags=None,
                                    sampling_rate=1.0
                                ))
                    
                    if latest_metrics:
                        return latest_metrics
            except Exception as e:
                logger.error(f"Failed to get latest metrics from Redis: {str(e)}")
        
        # Fall back to database query if Redis failed or returned no results
        query = self.db.query(SystemMetric)
        
        # Apply filters
        if service_name:
            query = query.filter(SystemMetric.service_name == service_name)
        
        if host_name:
            query = query.filter(SystemMetric.host_name == host_name)
        
        if metric_type:
            query = query.filter(SystemMetric.metric_type == metric_type)
        
        # Get latest metrics using a subquery
        subquery = (
            self.db.query(
                SystemMetric.service_name,
                SystemMetric.host_name,
                SystemMetric.metric_type,
                func.max(SystemMetric.timestamp).label("max_timestamp")
            )
            .group_by(
                SystemMetric.service_name,
                SystemMetric.host_name,
                SystemMetric.metric_type
            )
            .subquery()
        )
        
        latest_metrics = (
            self.db.query(SystemMetric)
            .join(
                subquery,
                and_(
                    SystemMetric.service_name == subquery.c.service_name,
                    SystemMetric.host_name == subquery.c.host_name,
                    SystemMetric.metric_type == subquery.c.metric_type,
                    SystemMetric.timestamp == subquery.c.max_timestamp
                )
            )
            .all()
        )
        
        return [SystemMetricResponse.model_validate(metric) for metric in latest_metrics]
    
    async def get_metric_trends(self, service_name: str, host_name: str, 
                              metric_type: MetricType, 
                              hours: int = 24) -> Dict[str, Any]:
        """Get metric trends over time for a specific service, host, and metric type."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get metrics for the specified period
        metrics = (
            self.db.query(SystemMetric)
            .filter(
                SystemMetric.service_name == service_name,
                SystemMetric.host_name == host_name,
                SystemMetric.metric_type == metric_type,
                SystemMetric.timestamp >= start_time
            )
            .order_by(SystemMetric.timestamp)
            .all()
        )
        
        if not metrics:
            return {
                "service_name": service_name,
                "host_name": host_name,
                "metric_type": metric_type.value,
                "data_points": [],
                "min_value": None,
                "max_value": None,
                "avg_value": None,
                "current_value": None,
                "unit": None
            }
        
        # Extract data points
        data_points = [
            {
                "timestamp": metric.timestamp.isoformat(),
                "value": metric.value
            }
            for metric in metrics
        ]
        
        # Calculate statistics
        values = [metric.value for metric in metrics]
        min_value = min(values)
        max_value = max(values)
        avg_value = sum(values) / len(values)
        current_value = values[-1] if values else None
        
        return {
            "service_name": service_name,
            "host_name": host_name,
            "metric_type": metric_type.value,
            "data_points": data_points,
            "min_value": min_value,
            "max_value": max_value,
            "avg_value": avg_value,
            "current_value": current_value,
            "unit": metrics[0].unit if metrics else None
        }

class AlertService:
    """Service for managing alerts, alert configurations, and alert history."""
    
    def __init__(self, db: Session = Depends(get_db), redis: Redis = Depends(get_redis)):
        self.db = db
        self.redis = redis
        
    async def create_alert_configuration(self, alert_config: AlertConfigurationCreate) -> AlertConfigurationResponse:
        """Create a new alert configuration."""
        db_alert_config = AlertConfiguration(**alert_config.model_dump())
        self.db.add(db_alert_config)
        self.db.commit()
        self.db.refresh(db_alert_config)
        return AlertConfigurationResponse.model_validate(db_alert_config)
    
    async def get_alert_configurations(self, service_name: Optional[str] = None) -> List[AlertConfigurationResponse]:
        """Get all alert configurations, optionally filtered by service name."""
        query = self.db.query(AlertConfiguration)
        
        if service_name:
            query = query.filter(AlertConfiguration.service_name == service_name)
            
        alert_configs = query.all()
        return [AlertConfigurationResponse.model_validate(config) for config in alert_configs]
    
    async def update_alert_configuration(self, config_id: int, alert_config: AlertConfigurationCreate) -> AlertConfigurationResponse:
        """Update an existing alert configuration."""
        db_alert_config = self.db.query(AlertConfiguration).filter(AlertConfiguration.id == config_id).first()
        
        if not db_alert_config:
            raise HTTPException(status_code=404, detail="Alert configuration not found")
        
        # Update fields
        for key, value in alert_config.model_dump(exclude_unset=True).items():
            setattr(db_alert_config, key, value)
            
        self.db.commit()
        self.db.refresh(db_alert_config)
        return AlertConfigurationResponse.model_validate(db_alert_config)
    
    async def delete_alert_configuration(self, config_id: int) -> Dict[str, Any]:
        """Delete an alert configuration."""
        db_alert_config = self.db.query(AlertConfiguration).filter(AlertConfiguration.id == config_id).first()
        
        if not db_alert_config:
            raise HTTPException(status_code=404, detail="Alert configuration not found")
            
        self.db.delete(db_alert_config)
        self.db.commit()
        
        return {"success": True, "message": f"Alert configuration {config_id} deleted"}
    
    async def create_alert_history(self, alert_data: AlertHistoryCreate) -> AlertHistoryResponse:
        """Record a new alert in the alert history."""
        db_alert = AlertHistory(**alert_data.model_dump())
        self.db.add(db_alert)
        self.db.commit()
        self.db.refresh(db_alert)
        
        # Publish alert to Redis channel for real-time notifications
        if self.redis:
            try:
                alert_channel = f"alerts:{alert_data.service_name}"
                alert_message = json.dumps({
                    "id": db_alert.id,
                    "alert_config_id": db_alert.alert_config_id,
                    "service_name": db_alert.service_name,
                    "severity": db_alert.severity.value,
                    "message": db_alert.message,
                    "triggered_value": db_alert.triggered_value,
                    "source_metric_id": db_alert.source_metric_id,
                    "status": db_alert.status.value,
                    "timestamp": db_alert.timestamp.isoformat()
                })
                self.redis.publish(alert_channel, alert_message)
                
                # Also store in a sorted set for quick retrieval of recent alerts
                alert_key = "alerts:recent"
                self.redis.zadd(alert_key, {alert_message: db_alert.timestamp.timestamp()})
                self.redis.zremrangebyrank(alert_key, 0, -101)  # Keep only the 100 most recent alerts
            except Exception as e:
                logger.error(f"Failed to publish alert to Redis: {str(e)}")
        
        return AlertHistoryResponse.model_validate(db_alert)
    
    async def update_alert_status(self, alert_id: int, status_update: AlertHistoryUpdate) -> AlertHistoryResponse:
        """Update the status of an alert in the history."""
        db_alert = self.db.query(AlertHistory).filter(AlertHistory.id == alert_id).first()
        
        if not db_alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Update fields
        for key, value in status_update.model_dump(exclude_unset=True).items():
            setattr(db_alert, key, value)
            
        # If we're resolving the alert, set resolved_timestamp
        if status_update.status == AlertStatus.RESOLVED and not db_alert.resolved_timestamp:
            db_alert.resolved_timestamp = datetime.utcnow()
            
        self.db.commit()
        self.db.refresh(db_alert)
        
        # Update in Redis if available
        if self.redis and db_alert.status == AlertStatus.RESOLVED:
            try:
                # Publish resolution to Redis channel
                alert_channel = f"alerts:{db_alert.service_name}"
                resolution_message = json.dumps({
                    "id": db_alert.id,
                    "service_name": db_alert.service_name,
                    "status": db_alert.status.value,
                    "resolved_timestamp": db_alert.resolved_timestamp.isoformat(),
                    "resolved_by": db_alert.resolved_by,
                    "resolution_note": db_alert.resolution_note
                })
                self.redis.publish(alert_channel, resolution_message)
            except Exception as e:
                logger.error(f"Failed to publish alert resolution to Redis: {str(e)}")
        
        return AlertHistoryResponse.model_validate(db_alert)
    
    async def search_alerts(self, search_params: AlertSearchParams) -> PaginatedResponse:
        """Search alerts with filtering options."""
        query = self.db.query(AlertHistory)
        
        # Apply filters
        if search_params.service_names:
            query = query.filter(AlertHistory.service_name.in_(search_params.service_names))
        
        if search_params.severities:
            query = query.filter(AlertHistory.severity.in_(search_params.severities))
        
        if search_params.statuses:
            query = query.filter(AlertHistory.status.in_(search_params.statuses))
        
        if search_params.start_time:
            query = query.filter(AlertHistory.timestamp >= search_params.start_time)
        
        if search_params.end_time:
            query = query.filter(AlertHistory.timestamp <= search_params.end_time)
        
        if search_params.message_contains:
            query = query.filter(AlertHistory.message.ilike(f"%{search_params.message_contains}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(AlertHistory.timestamp))
        query = query.offset(search_params.offset).limit(search_params.limit)
        
        # Execute query
        alerts = query.all()
        
        # Convert to response models
        alert_responses = [AlertHistoryResponse.model_validate(alert) for alert in alerts]
        
        return PaginatedResponse(
            items=alert_responses,
            total=total,
            limit=search_params.limit,
            offset=search_params.offset
        )
    
    async def get_active_alerts(self, service_name: Optional[str] = None) -> List[AlertHistoryResponse]:
        """Get all active (non-resolved) alerts, optionally filtered by service name."""
        query = self.db.query(AlertHistory).filter(AlertHistory.status != AlertStatus.RESOLVED)
        
        if service_name:
            query = query.filter(AlertHistory.service_name == service_name)
            
        query = query.order_by(desc(AlertHistory.timestamp))
        active_alerts = query.all()
        
        return [AlertHistoryResponse.model_validate(alert) for alert in active_alerts]
    
    async def evaluate_alert_conditions(self, metric_data: SystemMetricCreate) -> List[AlertHistoryResponse]:
        """
        Evaluate alert conditions against a new metric and trigger alerts if conditions are met.
        This should be called whenever a new metric is recorded.
        """
        # Get relevant alert configurations for this service and metric type
        alert_configs = (
            self.db.query(AlertConfiguration)
            .filter(
                AlertConfiguration.service_name == metric_data.service_name,
                AlertConfiguration.is_active == True,
                AlertConfiguration.condition_source == "metric",
                AlertConfiguration.condition_metric_type == metric_data.metric_type
            )
            .all()
        )
        
        triggered_alerts = []
        
        for config in alert_configs:
            # Evaluate threshold condition
            if config.condition_type == "threshold":
                threshold_value = float(config.condition_threshold)
                metric_value = float(metric_data.value)
                
                condition_met = False
                if config.condition_operator == "gt" and metric_value > threshold_value:
                    condition_met = True
                elif config.condition_operator == "lt" and metric_value < threshold_value:
                    condition_met = True
                elif config.condition_operator == "gte" and metric_value >= threshold_value:
                    condition_met = True
                elif config.condition_operator == "lte" and metric_value <= threshold_value:
                    condition_met = True
                elif config.condition_operator == "eq" and metric_value == threshold_value:
                    condition_met = True
                elif config.condition_operator == "neq" and metric_value != threshold_value:
                    condition_met = True
                
                if condition_met:
                    # Check if there's already an active alert for this configuration
                    existing_alert = (
                        self.db.query(AlertHistory)
                        .filter(
                            AlertHistory.alert_config_id == config.id,
                            AlertHistory.status != AlertStatus.RESOLVED
                        )
                        .first()
                    )
                    
                    if not existing_alert:
                        # Create new alert
                        alert_data = AlertHistoryCreate(
                            alert_config_id=config.id,
                            service_name=metric_data.service_name,
                            severity=config.severity,
                            message=f"{config.name}: {metric_data.metric_type.value} {config.condition_operator} {threshold_value} {metric_data.unit} (Current value: {metric_value} {metric_data.unit})",
                            triggered_value=str(metric_value),
                            source_metric_id=None,  # We don't have the ID yet as the metric is being created
                            status=AlertStatus.ACTIVE,
                            timestamp=datetime.utcnow()
                        )
                        
                        alert_response = await self.create_alert_history(alert_data)
                        triggered_alerts.append(alert_response)
            
            # Add support for other condition types like anomaly detection, etc.
        
        return triggered_alerts
    
    async def evaluate_log_alert_conditions(self, log_data: ServiceLogCreate) -> List[AlertHistoryResponse]:
        """
        Evaluate alert conditions against a new log entry and trigger alerts if conditions are met.
        This should be called whenever a new log is recorded.
        """
        # Get relevant alert configurations for this service and log level
        alert_configs = (
            self.db.query(AlertConfiguration)
            .filter(
                AlertConfiguration.service_name == log_data.service_name,
                AlertConfiguration.is_active == True,
                AlertConfiguration.condition_source == "log",
                AlertConfiguration.condition_log_level == log_data.log_level
            )
            .all()
        )
        
        triggered_alerts = []
        
        for config in alert_configs:
            # Evaluate pattern condition
            if config.condition_type == "pattern" and config.condition_pattern:
                # Simple pattern matching in log message
                if config.condition_pattern in log_data.message:
                    # Check if there's already an active alert for this configuration
                    existing_alert = (
                        self.db.query(AlertHistory)
                        .filter(
                            AlertHistory.alert_config_id == config.id,
                            AlertHistory.status != AlertStatus.RESOLVED
                        )
                        .first()
                    )
                    
                    if not existing_alert:
                        # Create new alert
                        alert_data = AlertHistoryCreate(
                            alert_config_id=config.id,
                            service_name=log_data.service_name,
                            severity=config.severity,
                            message=f"{config.name}: Pattern '{config.condition_pattern}' found in {log_data.log_level.value} log",
                            triggered_value=log_data.message[:100] + "..." if len(log_data.message) > 100 else log_data.message,
                            source_log_id=None,  # We don't have the ID yet as the log is being created
                            status=AlertStatus.ACTIVE,
                            timestamp=datetime.utcnow()
                        )
                        
                        alert_response = await self.create_alert_history(alert_data)
                        triggered_alerts.append(alert_response)
        
        return triggered_alerts


class DashboardService:
    """Service for managing monitoring dashboards and widgets."""
    
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        
    async def create_dashboard(self, dashboard_data: DashboardConfigurationCreate) -> DashboardConfigurationResponse:
        """Create a new dashboard configuration."""
        db_dashboard = DashboardConfiguration(**dashboard_data.model_dump(exclude={"widgets"}))
        self.db.add(db_dashboard)
        self.db.commit()
        self.db.refresh(db_dashboard)
        
        # Create widgets if provided
        if dashboard_data.widgets:
            for widget_data in dashboard_data.widgets:
                db_widget = DashboardWidget(
                    dashboard_id=db_dashboard.id,
                    **widget_data.model_dump()
                )
                self.db.add(db_widget)
            
            self.db.commit()
            
        # Fetch the complete dashboard with widgets
        db_dashboard = (
            self.db.query(DashboardConfiguration)
            .filter(DashboardConfiguration.id == db_dashboard.id)
            .first()
        )
        
        return DashboardConfigurationResponse.model_validate(db_dashboard)
    
    async def get_dashboards(self, user_id: Optional[int] = None) -> List[DashboardConfigurationResponse]:
        """Get all dashboards, optionally filtered by user ID."""
        query = self.db.query(DashboardConfiguration)
        
        if user_id:
            query = query.filter(
                or_(
                    DashboardConfiguration.user_id == user_id,
                    DashboardConfiguration.is_public == True
                )
            )
            
        dashboards = query.all()
        return [DashboardConfigurationResponse.model_validate(dashboard) for dashboard in dashboards]
    
    async def get_dashboard(self, dashboard_id: int) -> DashboardConfigurationResponse:
        """Get a dashboard by ID with all its widgets."""
        dashboard = (
            self.db.query(DashboardConfiguration)
            .filter(DashboardConfiguration.id == dashboard_id)
            .first()
        )
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")
            
        return DashboardConfigurationResponse.model_validate(dashboard)
    
    async def update_dashboard(self, dashboard_id: int, dashboard_data: DashboardConfigurationCreate) -> DashboardConfigurationResponse:
        """Update an existing dashboard configuration."""
        db_dashboard = self.db.query(DashboardConfiguration).filter(DashboardConfiguration.id == dashboard_id).first()
        
        if not db_dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        
        # Update dashboard fields
        for key, value in dashboard_data.model_dump(exclude={"widgets"}).items():
            setattr(db_dashboard, key, value)
            
        self.db.commit()
        
        # Handle widgets if provided
        if dashboard_data.widgets is not None:
            # Delete existing widgets
            self.db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == dashboard_id).delete()
            
            # Create new widgets
            for widget_data in dashboard_data.widgets:
                db_widget = DashboardWidget(
                    dashboard_id=dashboard_id,
                    **widget_data.model_dump()
                )
                self.db.add(db_widget)
                
            self.db.commit()
        
        # Refresh the dashboard
        self.db.refresh(db_dashboard)
        return DashboardConfigurationResponse.model_validate(db_dashboard)
    
    async def delete_dashboard(self, dashboard_id: int) -> Dict[str, Any]:
        """Delete a dashboard and all its widgets."""
        db_dashboard = self.db.query(DashboardConfiguration).filter(DashboardConfiguration.id == dashboard_id).first()
        
        if not db_dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")
            
        # Delete all widgets first (cascade delete should handle this, but being explicit)
        self.db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == dashboard_id).delete()
        
        # Delete the dashboard
        self.db.delete(db_dashboard)
        self.db.commit()
        
        return {"success": True, "message": f"Dashboard {dashboard_id} deleted"}

class MonitoringService:
    """
    Service for monitoring system health and component status.
    
    This service provides methods for checking the health of system components,
    tracking component status, and generating health reports.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the monitoring service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.logging_service = LoggingService(db)
        self.metrics_service = MetricsService(db)
    
    def check_system_health(self) -> HealthCheckResponse:
        """
        Check the health of all system components.
        
        Returns:
            Health check response
        """
        from .config import settings
        import requests
        import socket
        import psutil
        import time
        from redis import Redis
        from sqlalchemy import text
        
        # Initialize response
        response = HealthCheckResponse(
            timestamp=datetime.utcnow(),
            overall_status="healthy",
            components={}
        )
        
        # Check database
        try:
            # Execute simple query
            start_time = time.time()
            self.db.execute(text("SELECT 1"))
            end_time = time.time()
            
            # Calculate response time
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Add component status
            response.components["database"] = HealthCheckComponentStatus(
                status="healthy",
                response_time=response_time,
                details={
                    "type": "postgresql",
                    "version": self.db.execute(text("SELECT version()")).scalar()
                }
            )
        except Exception as e:
            response.components["database"] = HealthCheckComponentStatus(
                status="unhealthy",
                error=str(e),
                details={"type": "postgresql"}
            )
            response.overall_status = "degraded"
        
        # Check Redis if configured
        try:
            from backend_core.cache import get_redis
            
            # Get Redis connection
            redis = next(get_redis())
            
            # Ping Redis
            start_time = time.time()
            redis.ping()
            end_time = time.time()
            
            # Calculate response time
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Get Redis info
            info = redis.info()
            
            # Add component status
            response.components["redis"] = HealthCheckComponentStatus(
                status="healthy",
                response_time=response_time,
                details={
                    "version": info.get("redis_version"),
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients")
                }
            )
        except Exception as e:
            response.components["redis"] = HealthCheckComponentStatus(
                status="unhealthy",
                error=str(e),
                details={"type": "redis"}
            )
            response.overall_status = "degraded"
        
        # Check Elasticsearch if configured
        if settings.logging.elasticsearch.enabled:
            try:
                from .elasticsearch import elasticsearch_client
                
                # Ping Elasticsearch
                start_time = time.time()
                elasticsearch_client.client.ping()
                end_time = time.time()
                
                # Calculate response time
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                # Get Elasticsearch info
                info = elasticsearch_client.client.info()
                
                # Add component status
                response.components["elasticsearch"] = HealthCheckComponentStatus(
                    status="healthy",
                    response_time=response_time,
                    details={
                        "version": info.get("version", {}).get("number"),
                        "cluster_name": info.get("cluster_name")
                    }
                )
            except Exception as e:
                response.components["elasticsearch"] = HealthCheckComponentStatus(
                    status="unhealthy",
                    error=str(e),
                    details={"type": "elasticsearch"}
                )
                response.overall_status = "degraded"
        
        # Check system resources
        try:
            # Get system information
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Add component status
            response.components["system"] = HealthCheckComponentStatus(
                status="healthy",
                details={
                    "hostname": socket.gethostname(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent
                }
            )
            
            # Check if system resources are critical
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                response.components["system"].status = "warning"
                response.overall_status = "degraded"
        except Exception as e:
            response.components["system"] = HealthCheckComponentStatus(
                status="unhealthy",
                error=str(e),
                details={"type": "system"}
            )
            response.overall_status = "degraded"
        
        # Check configured services
        for service_name, service_url in settings.health_check_services.items():
            if service_name in response.components:
                continue  # Skip already checked components
                
            try:
                # Make request to service health endpoint
                start_time = time.time()
                response_obj = requests.get(service_url, timeout=5)
                end_time = time.time()
                
                # Calculate response time
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                # Check response
                if response_obj.status_code < 400:
                    # Try to parse response as JSON
                    try:
                        response_data = response_obj.json()
                        response.components[service_name] = HealthCheckComponentStatus(
                            status="healthy",
                            response_time=response_time,
                            details=response_data
                        )
                    except Exception:
                        response.components[service_name] = HealthCheckComponentStatus(
                            status="healthy",
                            response_time=response_time,
                            details={"status_code": response_obj.status_code}
                        )
                else:
                    response.components[service_name] = HealthCheckComponentStatus(
                        status="unhealthy",
                        response_time=response_time,
                        error=f"HTTP {response_obj.status_code}",
                        details={"status_code": response_obj.status_code}
                    )
                    response.overall_status = "degraded"
            except Exception as e:
                response.components[service_name] = HealthCheckComponentStatus(
                    status="unhealthy",
                    error=str(e),
                    details={"url": service_url}
                )
                response.overall_status = "degraded"
        
        # Log health check result
        log_level = LogLevel.INFO
        if response.overall_status != "healthy":
            log_level = LogLevel.WARNING
            
        self.logging_service.create_log(ServiceLogCreate(
            service_name="monitoring",
            log_level=log_level,
            message=f"System health check: {response.overall_status}",
            metadata={"health_check": response.dict()}
        ))
        
        return response
    
    def get_component_status(self, component_name: str) -> Optional[HealthCheckComponentStatus]:
        """
        Get the status of a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Component status or None if not found
        """
        # Check system health
        health_check = self.check_system_health()
        
        # Return component status
        return health_check.components.get(component_name)
    
    def get_component_metrics(
        self,
        component_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metric_type: Optional[MetricType] = None,
        limit: int = 100
    ) -> List[SystemMetric]:
        """
        Get metrics for a specific component.
        
        Args:
            component_name: Name of the component
            start_time: Start time for metrics
            end_time: End time for metrics
            metric_type: Type of metrics to retrieve
            limit: Maximum number of metrics to return
            
        Returns:
            List of metrics
        """
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.utcnow()
        
        if not start_time:
            start_time = end_time - timedelta(hours=1)
        
        # Query metrics
        query = self.db.query(SystemMetric).filter(
            SystemMetric.host_name == component_name,
            SystemMetric.timestamp >= start_time,
            SystemMetric.timestamp <= end_time
        )
        
        if metric_type:
            query = query.filter(SystemMetric.metric_type == metric_type)
        
        # Order by timestamp and limit results
        query = query.order_by(SystemMetric.timestamp.desc()).limit(limit)
        
        return query.all()
    
    def get_service_logs(
        self,
        service_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        log_level: Optional[LogLevelEnum] = None,
        limit: int = 100
    ) -> List[ServiceLog]:
        """
        Get logs for a specific service.
        
        Args:
            service_name: Name of the service
            start_time: Start time for logs
            end_time: End time for logs
            log_level: Minimum log level to retrieve
            limit: Maximum number of logs to return
            
        Returns:
            List of logs
        """
        return self.logging_service.search_logs(
            service_name=service_name,
            start_time=start_time,
            end_time=end_time,
            log_level=log_level,
            limit=limit
        )
    
    def get_system_metrics_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of system metrics.
        
        Args:
            start_time: Start time for metrics
            end_time: End time for metrics
            
        Returns:
            Dictionary containing system metrics summary
        """
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.utcnow()
        
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        # Get metrics for different types
        cpu_metrics = self.metrics_service.search_metrics(
            metric_type=MetricType.CPU_USAGE,
            start_time=start_time,
            end_time=end_time
        )
        
        memory_metrics = self.metrics_service.search_metrics(
            metric_type=MetricType.MEMORY_USAGE,
            start_time=start_time,
            end_time=end_time
        )
        
        disk_metrics = self.metrics_service.search_metrics(
            metric_type=MetricType.DISK_USAGE,
            start_time=start_time,
            end_time=end_time
        )
        
        # Calculate statistics
        from .utils import calculate_statistics
        
        cpu_values = [metric.value for metric in cpu_metrics]
        memory_values = [metric.value for metric in memory_metrics]
        disk_values = [metric.value for metric in disk_metrics]
        
        # Return summary
        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "cpu": calculate_statistics(cpu_values),
            "memory": calculate_statistics(memory_values),
            "disk": calculate_statistics(disk_values)
        }
