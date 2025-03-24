import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from celery import Celery, Task
from celery.schedules import crontab
from sqlalchemy.orm import Session
import json

from backend_core.database import get_db
from backend_core.config import settings
from backend_core.cache import get_redis

from .services import (
    LoggingService,
    MetricsService,
    AlertService,
    MonitoringService
)

from .services.alert_management_service import AlertManagementService
from .services.reporting_service import ReportingService
from .collectors.system_metrics_collector import collect_system_metrics as collect_metrics

from .models import (
    ServiceLog,
    SystemMetric,
    AlertConfiguration,
    AlertHistory,
    LogLevel,
    MetricType,
    AlertStatus
)

from .schemas import (
    ServiceLogCreate,
    SystemMetricCreate,
    AlertHistoryCreate
)

# Configure logger
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "monitoring_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    "apply-log-retention-daily": {
        "task": "modules.monitoring.tasks.apply_log_retention",
        "schedule": crontab(hour=2, minute=0),  # Run at 2 AM every day
        "args": (),
    },
    "check-system-health-every-5-minutes": {
        "task": "modules.monitoring.tasks.check_system_health",
        "schedule": crontab(minute="*/5"),  # Run every 5 minutes
        "args": (),
    },
    "collect-system-metrics-every-minute": {
        "task": "modules.monitoring.tasks.collect_system_metrics",
        "schedule": crontab(minute="*"),  # Run every minute
        "args": (),
    },
    "evaluate-alert-conditions-every-minute": {
        "task": "modules.monitoring.tasks.evaluate_alert_conditions",
        "schedule": crontab(minute="*"),  # Run every minute
        "args": (),
    },
    "cleanup-old-metrics-weekly": {
        "task": "modules.monitoring.tasks.cleanup_old_metrics",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Run at 3 AM every Monday
        "args": (),
    },
    "health-check-every-minute": {
        "task": "monitoring.health_check",
        "schedule": crontab(minute="*"),  # Run every minute
        "args": (),
    },
    "collect-system-metrics-every-minute": {
        "task": "monitoring.collect_system_metrics",
        "schedule": crontab(minute="*"),  # Run every minute
        "args": (),
    },
    "check-service-availability-every-minute": {
        "task": "monitoring.check_service_availability",
        "schedule": crontab(minute="*"),  # Run every minute
        "args": (),
    },
    "sync-logs-to-elasticsearch-every-minute": {
        "task": "monitoring.sync_logs_to_elasticsearch",
        "schedule": crontab(minute="*"),  # Run every minute
        "args": (),
    },
    "sync-metrics-to-elasticsearch-every-minute": {
        "task": "monitoring.sync_metrics_to_elasticsearch",
        "schedule": crontab(minute="*"),  # Run every minute
        "args": (),
    },
    "generate-daily-reports": {
        "task": "modules.monitoring.tasks.generate_daily_reports",
        "schedule": crontab(hour=1, minute=0),  # Run at 1 AM every day
        "args": (),
    },
}

class DatabaseTask(Task):
    """Base task that provides database session management."""
    
    _db = None
    
    def after_return(self, *args, **kwargs):
        """Close database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None
    
    @property
    def db(self) -> Session:
        """Get database session."""
        if self._db is None:
            self._db = next(get_db())
        return self._db


@celery_app.task(base=DatabaseTask, name="modules.monitoring.tasks.apply_log_retention")
def apply_log_retention() -> Dict[str, Any]:
    """
    Apply log retention policies to remove old logs.
    This task runs daily to clean up logs based on configured retention policies.
    """
    try:
        # Get database session from task
        db = apply_log_retention.db
        
        # Create logging service
        logging_service = LoggingService(db)
        
        # Apply retention policies
        result = logging_service.apply_retention_policies()
        
        # Log the result
        log_data = ServiceLogCreate(
            service_name="monitoring",
            log_level=LogLevel.INFO,
            message=f"Applied log retention policies: {len(result['database'])} policies applied to database",
            trace_id=None,
            correlation_id=None,
            source_ip=None,
            user_id=None,
            request_path=None,
            request_method=None,
            response_status=None,
            execution_time=None,
            metadata={"retention_result": result}
        )
        logging_service.create_log(log_data)
        
        return result
    except Exception as e:
        logger.error(f"Error applying log retention: {str(e)}")
        
        # Log the error
        try:
            log_data = ServiceLogCreate(
                service_name="monitoring",
                log_level=LogLevel.ERROR,
                message=f"Error applying log retention: {str(e)}",
                trace_id=None,
                correlation_id=None,
                source_ip=None,
                user_id=None,
                request_path=None,
                request_method=None,
                response_status=None,
                execution_time=None,
                metadata={"error": str(e)}
            )
            logging_service = LoggingService(apply_log_retention.db)
            logging_service.create_log(log_data)
        except Exception:
            pass
        
        raise


@celery_app.task(base=DatabaseTask, name="modules.monitoring.tasks.check_system_health")
def check_system_health() -> Dict[str, Any]:
    """
    Check the health of all system components.
    This task runs every 5 minutes to monitor the health of all services.
    """
    try:
        # Get database session from task
        db = check_system_health.db
        
        # Create monitoring service
        monitoring_service = MonitoringService(db)
        
        # Check system health
        health_check = monitoring_service.check_system_health()
        
        # Create metrics for each component
        metrics_service = MetricsService(db)
        alert_service = AlertService(db)
        
        for component_name, component in health_check.components.items():
            # Create metric for component status
            metric_data = SystemMetricCreate(
                service_name="system_health",
                host_name=component_name,
                metric_type=MetricType.STATUS,
                value=1.0 if component.status == "healthy" else 0.0,
                unit="status",
                timestamp=datetime.utcnow(),
                tags={"component": component_name},
                sampling_rate=1.0
            )
            
            # Record metric and evaluate alerts
            metric = metrics_service.create_metric(metric_data)
            alert_service.evaluate_alert_conditions(metric_data)
            
            # Create metric for component response time if available
            if component.response_time is not None:
                response_time_metric = SystemMetricCreate(
                    service_name="system_health",
                    host_name=component_name,
                    metric_type=MetricType.RESPONSE_TIME,
                    value=float(component.response_time),
                    unit="ms",
                    timestamp=datetime.utcnow(),
                    tags={"component": component_name},
                    sampling_rate=1.0
                )
                
                # Record metric and evaluate alerts
                metrics_service.create_metric(response_time_metric)
                alert_service.evaluate_alert_conditions(response_time_metric)
        
        # Log the health check result
        log_data = ServiceLogCreate(
            service_name="monitoring",
            log_level=LogLevel.INFO,
            message=f"System health check completed: {health_check.overall_status}",
            trace_id=None,
            correlation_id=None,
            source_ip=None,
            user_id=None,
            request_path=None,
            request_method=None,
            response_status=None,
            execution_time=None,
            metadata={"health_check": health_check.dict()}
        )
        logging_service = LoggingService(db)
        logging_service.create_log(log_data)
        
        return health_check.dict()
    except Exception as e:
        logger.error(f"Error checking system health: {str(e)}")
        
        # Log the error
        try:
            log_data = ServiceLogCreate(
                service_name="monitoring",
                log_level=LogLevel.ERROR,
                message=f"Error checking system health: {str(e)}",
                trace_id=None,
                correlation_id=None,
                source_ip=None,
                user_id=None,
                request_path=None,
                request_method=None,
                response_status=None,
                execution_time=None,
                metadata={"error": str(e)}
            )
            logging_service = LoggingService(check_system_health.db)
            logging_service.create_log(log_data)
        except Exception:
            pass
        
        raise


@celery_app.task(base=DatabaseTask, name="modules.monitoring.tasks.collect_system_metrics")
def collect_system_metrics() -> Dict[str, Any]:
    """
    Collect system performance metrics from all services.
    This task runs every minute to gather metrics about CPU, memory, disk, and network usage.
    """
    try:
        # Get database session from task
        db = collect_system_metrics.db
        
        # Collect metrics using the collector
        metrics = collect_metrics(db)
        
        # Log the result
        log_data = ServiceLogCreate(
            service_name="monitoring",
            log_level=LogLevel.INFO,
            message=f"Collected {len(metrics)} system metrics",
            trace_id=None,
            correlation_id=None,
            source_ip=None,
            user_id=None,
            request_path=None,
            request_method=None,
            response_status=None,
            execution_time=None,
            metadata={"metrics_count": len(metrics)}
        )
        logging_service = LoggingService(db)
        logging_service.create_log(log_data)
        
        return {"status": "success", "metrics_collected": len(metrics)}
    except Exception as e:
        logger.error(f"Error collecting system metrics: {str(e)}")
        
        # Log the error
        try:
            log_data = ServiceLogCreate(
                service_name="monitoring",
                log_level=LogLevel.ERROR,
                message=f"Error collecting system metrics: {str(e)}",
                trace_id=None,
                correlation_id=None,
                source_ip=None,
                user_id=None,
                request_path=None,
                request_method=None,
                response_status=None,
                execution_time=None,
                metadata={"error": str(e)}
            )
            logging_service = LoggingService(collect_system_metrics.db)
            logging_service.create_log(log_data)
        except Exception:
            pass
        
        raise


@celery_app.task(base=DatabaseTask, name="modules.monitoring.tasks.evaluate_alert_conditions")
def evaluate_alert_conditions() -> Dict[str, Any]:
    """
    Evaluate alert conditions against the latest metrics.
    This task runs every minute to check for any alert conditions that should be triggered.
    """
    try:
        # Get database session from task
        db = evaluate_alert_conditions.db
        
        # Create alert management service
        alert_service = AlertManagementService(db)
        
        # Evaluate alert conditions
        results = alert_service.evaluate_all_alert_conditions()
        
        # Log the result
        log_data = ServiceLogCreate(
            service_name="monitoring",
            log_level=LogLevel.INFO,
            message=f"Evaluated alert conditions: {results['evaluated']} conditions evaluated, {results['triggered']} alerts triggered",
            trace_id=None,
            correlation_id=None,
            source_ip=None,
            user_id=None,
            request_path=None,
            request_method=None,
            response_status=None,
            execution_time=None,
            metadata=results
        )
        logging_service = LoggingService(db)
        logging_service.create_log(log_data)
        
        return results
    except Exception as e:
        logger.error(f"Error evaluating alert conditions: {str(e)}")
        
        # Log the error
        try:
            log_data = ServiceLogCreate(
                service_name="monitoring",
                log_level=LogLevel.ERROR,
                message=f"Error evaluating alert conditions: {str(e)}",
                trace_id=None,
                correlation_id=None,
                source_ip=None,
                user_id=None,
                request_path=None,
                request_method=None,
                response_status=None,
                execution_time=None,
                metadata={"error": str(e)}
            )
            logging_service = LoggingService(evaluate_alert_conditions.db)
            logging_service.create_log(log_data)
        except Exception:
            pass
        
        raise


@celery_app.task(base=DatabaseTask, name="modules.monitoring.tasks.cleanup_old_metrics")
def cleanup_old_metrics(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old metrics data to prevent database bloat.
    This task runs weekly to remove metrics older than the specified number of days.
    
    Args:
        days: Number of days to keep metrics for (default: 30)
    """
    try:
        # Get database session from task
        db = cleanup_old_metrics.db
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Delete old metrics
        deleted_count = db.query(SystemMetric).filter(
            SystemMetric.timestamp < cutoff_date
        ).delete(synchronize_session=False)
        
        db.commit()
        
        # Log the result
        log_data = ServiceLogCreate(
            service_name="monitoring",
            log_level=LogLevel.INFO,
            message=f"Cleaned up old metrics: {deleted_count} metrics older than {days} days removed",
            trace_id=None,
            correlation_id=None,
            source_ip=None,
            user_id=None,
            request_path=None,
            request_method=None,
            response_status=None,
            execution_time=None,
            metadata={"deleted_count": deleted_count, "retention_days": days}
        )
        logging_service = LoggingService(db)
        logging_service.create_log(log_data)
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "retention_days": days
        }
    except Exception as e:
        logger.error(f"Error cleaning up old metrics: {str(e)}")
        
        # Log the error
        try:
            log_data = ServiceLogCreate(
                service_name="monitoring",
                log_level=LogLevel.ERROR,
                message=f"Error cleaning up old metrics: {str(e)}",
                trace_id=None,
                correlation_id=None,
                source_ip=None,
                user_id=None,
                request_path=None,
                request_method=None,
                response_status=None,
                execution_time=None,
                metadata={"error": str(e)}
            )
            logging_service = LoggingService(cleanup_old_metrics.db)
            logging_service.create_log(log_data)
        except Exception:
            pass
        
        raise


@celery_app.task(base=DatabaseTask, name="modules.monitoring.tasks.generate_daily_reports")
def generate_daily_reports() -> Dict[str, Any]:
    """
    Generate daily performance reports.
    
    This task runs daily to generate performance reports for the previous day.
    Reports include system metrics, alerts, and service availability.
    """
    try:
        # Get database session from task
        db = generate_daily_reports.db
        
        # Create reporting service
        reporting_service = ReportingService(db)
        
        # Calculate time range for the previous day
        end_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=1)
        
        # Generate system performance report
        performance_report = reporting_service.generate_system_performance_report(
            start_time=start_time,
            end_time=end_time,
            report_format="json"
        )
        
        # Generate alert report
        alert_report = reporting_service.generate_alert_report(
            start_time=start_time,
            end_time=end_time,
            report_format="json"
        )
        
        # Generate service availability report
        availability_report = reporting_service.generate_service_availability_report(
            start_time=start_time,
            end_time=end_time,
            report_format="json"
        )
        
        # Store reports in Redis for quick access
        redis_client = get_redis()
        redis_key_prefix = f"monitoring:reports:{start_time.strftime('%Y-%m-%d')}"
        
        redis_client.set(
            f"{redis_key_prefix}:performance",
            json.dumps(performance_report),
            ex=60*60*24*7  # Expire after 7 days
        )
        
        redis_client.set(
            f"{redis_key_prefix}:alerts",
            json.dumps(alert_report),
            ex=60*60*24*7  # Expire after 7 days
        )
        
        redis_client.set(
            f"{redis_key_prefix}:availability",
            json.dumps(availability_report),
            ex=60*60*24*7  # Expire after 7 days
        )
        
        # Log the result
        log_data = ServiceLogCreate(
            service_name="monitoring",
            log_level=LogLevel.INFO,
            message=f"Generated daily reports for {start_time.strftime('%Y-%m-%d')}",
            trace_id=None,
            correlation_id=None,
            source_ip=None,
            user_id=None,
            request_path=None,
            request_method=None,
            response_status=None,
            execution_time=None,
            metadata={
                "performance_metrics_count": performance_report.get("metrics_count", 0),
                "alerts_count": alert_report.get("alerts_count", 0)
            }
        )
        logging_service = LoggingService(db)
        logging_service.create_log(log_data)
        
        return {
            "status": "success",
            "date": start_time.strftime("%Y-%m-%d"),
            "reports_generated": [
                "system_performance",
                "alerts",
                "service_availability"
            ]
        }
    except Exception as e:
        logger.error(f"Error generating daily reports: {str(e)}")
        
        # Log the error
        try:
            log_data = ServiceLogCreate(
                service_name="monitoring",
                log_level=LogLevel.ERROR,
                message=f"Error generating daily reports: {str(e)}",
                trace_id=None,
                correlation_id=None,
                source_ip=None,
                user_id=None,
                request_path=None,
                request_method=None,
                response_status=None,
                execution_time=None,
                metadata={"error": str(e)}
            )
            logging_service = LoggingService(generate_daily_reports.db)
            logging_service.create_log(log_data)
        except Exception:
            pass
        
        raise


@celery_app.task(name="monitoring.health_check")
def health_check_task():
    """
    Perform a health check on all system components.
    
    This task checks the health of all system components and stores the results
    in Elasticsearch for historical analysis and alerting.
    """
    from .services import MonitoringService
    from sqlalchemy.orm import Session
    from backend_core.database import SessionLocal
    from .elasticsearch import elasticsearch_client
    from .config import settings
    import json
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Perform health check
        monitoring_service = MonitoringService(db)
        health_check = monitoring_service.check_system_health()
        
        # Store health check in Elasticsearch if enabled
        if settings.logging.elasticsearch.enabled:
            # Convert health check to dictionary
            health_check_dict = health_check.dict()
            
            # Add document type
            health_check_dict["document_type"] = "health_check"
            
            # Index health check
            elasticsearch_client.index_document(
                index=f"{settings.logging.elasticsearch.metric_index_prefix}-health",
                document=health_check_dict
            )
        
        # Check for unhealthy components and trigger alerts
        for component_name, component_status in health_check.components.items():
            if component_status.status == "unhealthy":
                # Create alert
                from .models import AlertSeverity, AlertStatus
                from .schemas import AlertCreate
                
                alert = AlertCreate(
                    name=f"{component_name} is unhealthy",
                    description=f"Component {component_name} is reporting unhealthy status",
                    service_name="monitoring",
                    condition_type="status",
                    severity=AlertSeverity.CRITICAL,
                    metric_type="health",
                    threshold=None,
                    pattern=None,
                    message=f"Component {component_name} is unhealthy: {component_status.error}",
                    triggered_value=json.dumps(component_status.dict()),
                    status=AlertStatus.ACTIVE
                )
                
                # Save alert
                from .services import AlertService
                alert_service = AlertService(db)
                alert_service.create_alert(alert)
        
        return {"status": "success", "health_check": health_check.dict()}
    
    finally:
        # Close database session
        db.close()


@celery_app.task(name="monitoring.collect_system_metrics")
def collect_system_metrics_task():
    """
    Collect system metrics and store them in the database and Elasticsearch.
    
    This task collects system metrics such as CPU, memory, and disk usage
    and stores them in the database and Elasticsearch for historical analysis.
    """
    from sqlalchemy.orm import Session
    from backend_core.database import SessionLocal
    from .schemas import SystemMetricCreate
    from .models import MetricType
    from .services import MetricsService
    from .elasticsearch import elasticsearch_client
    from .config import settings
    import psutil
    import socket
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Get hostname
        hostname = socket.gethostname()
        
        # Create metrics service
        metrics_service = MetricsService(db)
        
        # Create CPU usage metric
        cpu_metric = SystemMetricCreate(
            service_name="system",
            host_name=hostname,
            metric_type=MetricType.CPU_USAGE,
            value=float(cpu_percent),
            unit="percent",
            tags={"source": "system"}
        )
        cpu_db_metric = metrics_service.create_metric(cpu_metric)
        
        # Create memory usage metric
        memory_metric = SystemMetricCreate(
            service_name="system",
            host_name=hostname,
            metric_type=MetricType.MEMORY_USAGE,
            value=float(memory.percent),
            unit="percent",
            tags={"source": "system", "total": str(memory.total), "available": str(memory.available)}
        )
        memory_db_metric = metrics_service.create_metric(memory_metric)
        
        # Create disk usage metric
        disk_metric = SystemMetricCreate(
            service_name="system",
            host_name=hostname,
            metric_type=MetricType.DISK_USAGE,
            value=float(disk.percent),
            unit="percent",
            tags={"source": "system", "total": str(disk.total), "used": str(disk.used), "free": str(disk.free)}
        )
        disk_db_metric = metrics_service.create_metric(disk_metric)
        
        # Create network sent metric
        network_sent_metric = SystemMetricCreate(
            service_name="system",
            host_name=hostname,
            metric_type=MetricType.NETWORK_SENT,
            value=float(network.bytes_sent),
            unit="bytes",
            tags={"source": "system"}
        )
        network_sent_db_metric = metrics_service.create_metric(network_sent_metric)
        
        # Create network received metric
        network_recv_metric = SystemMetricCreate(
            service_name="system",
            host_name=hostname,
            metric_type=MetricType.NETWORK_RECEIVED,
            value=float(network.bytes_recv),
            unit="bytes",
            tags={"source": "system"}
        )
        network_recv_db_metric = metrics_service.create_metric(network_recv_metric)
        
        # Store metrics in Elasticsearch if enabled
        if settings.logging.elasticsearch.enabled:
            # Create bulk metrics list
            metrics = [
                {
                    "document_type": "metric",
                    "metric_type": cpu_db_metric.metric_type.value,
                    "service_name": cpu_db_metric.service_name,
                    "host_name": cpu_db_metric.host_name,
                    "value": cpu_db_metric.value,
                    "unit": cpu_db_metric.unit,
                    "tags": cpu_db_metric.tags,
                    "timestamp": cpu_db_metric.timestamp.isoformat()
                },
                {
                    "document_type": "metric",
                    "metric_type": memory_db_metric.metric_type.value,
                    "service_name": memory_db_metric.service_name,
                    "host_name": memory_db_metric.host_name,
                    "value": memory_db_metric.value,
                    "unit": memory_db_metric.unit,
                    "tags": memory_db_metric.tags,
                    "timestamp": memory_db_metric.timestamp.isoformat()
                },
                {
                    "document_type": "metric",
                    "metric_type": disk_db_metric.metric_type.value,
                    "service_name": disk_db_metric.service_name,
                    "host_name": disk_db_metric.host_name,
                    "value": disk_db_metric.value,
                    "unit": disk_db_metric.unit,
                    "tags": disk_db_metric.tags,
                    "timestamp": disk_db_metric.timestamp.isoformat()
                },
                {
                    "document_type": "metric",
                    "metric_type": network_sent_db_metric.metric_type.value,
                    "service_name": network_sent_db_metric.service_name,
                    "host_name": network_sent_db_metric.host_name,
                    "value": network_sent_db_metric.value,
                    "unit": network_sent_db_metric.unit,
                    "tags": network_sent_db_metric.tags,
                    "timestamp": network_sent_db_metric.timestamp.isoformat()
                },
                {
                    "document_type": "metric",
                    "metric_type": network_recv_db_metric.metric_type.value,
                    "service_name": network_recv_db_metric.service_name,
                    "host_name": network_recv_db_metric.host_name,
                    "value": network_recv_db_metric.value,
                    "unit": network_recv_db_metric.unit,
                    "tags": network_recv_db_metric.tags,
                    "timestamp": network_recv_db_metric.timestamp.isoformat()
                }
            ]
            
            # Bulk index metrics
            elasticsearch_client.bulk_index_documents(
                index=settings.logging.elasticsearch.metric_index_prefix,
                documents=metrics
            )
        
        return {
            "status": "success",
            "metrics": {
                "cpu": cpu_percent,
                "memory": memory.percent,
                "disk": disk.percent,
                "network_sent": network.bytes_sent,
                "network_recv": network.bytes_recv
            }
        }
    
    finally:
        # Close database session
        db.close()


@celery_app.task(name="monitoring.check_service_availability")
def check_service_availability_task():
    """
    Check the availability of configured services.
    
    This task checks the availability of services configured in the settings
    and stores the results in the database and Elasticsearch for historical analysis.
    """
    from sqlalchemy.orm import Session
    from backend_core.database import SessionLocal
    from .schemas import SystemMetricCreate
    from .models import MetricType
    from .services import MetricsService
    from .elasticsearch import elasticsearch_client
    from .config import settings
    import requests
    import socket
    import time
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get hostname
        hostname = socket.gethostname()
        
        # Create metrics service
        metrics_service = MetricsService(db)
        
        # Check configured services
        metrics = []
        
        for service_name, service_url in settings.health_check_services.items():
            try:
                # Make request to service health endpoint
                start_time = time.time()
                response = requests.get(service_url, timeout=5)
                end_time = time.time()
                
                # Calculate response time
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                # Check if service is healthy
                is_healthy = response.status_code < 400
                
                # Create status metric
                status_metric = SystemMetricCreate(
                    service_name=service_name,
                    host_name=hostname,
                    metric_type=MetricType.STATUS,
                    value=1.0 if is_healthy else 0.0,
                    unit="boolean",
                    tags={"source": "availability_check", "status_code": str(response.status_code)}
                )
                status_db_metric = metrics_service.create_metric(status_metric)
                
                # Create latency metric
                latency_metric = SystemMetricCreate(
                    service_name=service_name,
                    host_name=hostname,
                    metric_type=MetricType.LATENCY,
                    value=float(response_time),
                    unit="milliseconds",
                    tags={"source": "availability_check"}
                )
                latency_db_metric = metrics_service.create_metric(latency_metric)
                
                # Add metrics to list for Elasticsearch
                if settings.logging.elasticsearch.enabled:
                    metrics.extend([
                        {
                            "document_type": "metric",
                            "metric_type": status_db_metric.metric_type.value,
                            "service_name": status_db_metric.service_name,
                            "host_name": status_db_metric.host_name,
                            "value": status_db_metric.value,
                            "unit": status_db_metric.unit,
                            "tags": status_db_metric.tags,
                            "timestamp": status_db_metric.timestamp.isoformat()
                        },
                        {
                            "document_type": "metric",
                            "metric_type": latency_db_metric.metric_type.value,
                            "service_name": latency_db_metric.service_name,
                            "host_name": latency_db_metric.host_name,
                            "value": latency_db_metric.value,
                            "unit": latency_db_metric.unit,
                            "tags": latency_db_metric.tags,
                            "timestamp": latency_db_metric.timestamp.isoformat()
                        }
                    ])
                
                # Check if service is unhealthy and create alert
                if not is_healthy:
                    from .models import AlertSeverity, AlertStatus
                    from .schemas import AlertCreate
                    from .services import AlertService
                    
                    alert = AlertCreate(
                        name=f"{service_name} is down",
                        description=f"Service {service_name} is reporting unhealthy status",
                        service_name="monitoring",
                        condition_type="status",
                        severity=AlertSeverity.CRITICAL,
                        metric_type="availability",
                        threshold=None,
                        pattern=None,
                        message=f"Service {service_name} returned status code {response.status_code}",
                        triggered_value=str(response.status_code),
                        status=AlertStatus.ACTIVE
                    )
                    
                    # Save alert
                    alert_service = AlertService(db)
                    alert_service.create_alert(alert)
            
            except Exception as e:
                # Service is unreachable
                # Create status metric
                status_metric = SystemMetricCreate(
                    service_name=service_name,
                    host_name=hostname,
                    metric_type=MetricType.STATUS,
                    value=0.0,
                    unit="boolean",
                    tags={"source": "availability_check", "error": str(e)}
                )
                status_db_metric = metrics_service.create_metric(status_metric)
                
                # Add metric to list for Elasticsearch
                if settings.logging.elasticsearch.enabled:
                    metrics.append({
                        "document_type": "metric",
                        "metric_type": status_db_metric.metric_type.value,
                        "service_name": status_db_metric.service_name,
                        "host_name": status_db_metric.host_name,
                        "value": status_db_metric.value,
                        "unit": status_db_metric.unit,
                        "tags": status_db_metric.tags,
                        "timestamp": status_db_metric.timestamp.isoformat()
                    })
                
                # Create alert
                from .models import AlertSeverity, AlertStatus
                from .schemas import AlertCreate
                from .services import AlertService
                
                alert = AlertCreate(
                    name=f"{service_name} is unreachable",
                    description=f"Service {service_name} is unreachable",
                    service_name="monitoring",
                    condition_type="status",
                    severity=AlertSeverity.CRITICAL,
                    metric_type="availability",
                    threshold=None,
                    pattern=None,
                    message=f"Service {service_name} is unreachable: {str(e)}",
                    triggered_value="unreachable",
                    status=AlertStatus.ACTIVE
                )
                
                # Save alert
                alert_service = AlertService(db)
                alert_service.create_alert(alert)
        
        # Bulk index metrics in Elasticsearch if enabled
        if settings.logging.elasticsearch.enabled and metrics:
            elasticsearch_client.bulk_index_documents(
                index=settings.logging.elasticsearch.metric_index_prefix,
                documents=metrics
            )
        
        return {"status": "success", "services_checked": len(settings.health_check_services)}
    
    finally:
        # Close database session
        db.close()


@celery_app.task(name="monitoring.sync_logs_to_elasticsearch")
def sync_logs_to_elasticsearch_task():
    """
    Sync logs from the database to Elasticsearch.
    
    This task will retrieve logs that haven't been synced to Elasticsearch
    and send them in batches. It will mark logs as synced after successful
    indexing.
    """
    if not settings.logging.elasticsearch.enabled:
        logger.info("Elasticsearch integration is disabled. Skipping log sync.")
        return {"status": "skipped", "reason": "elasticsearch_disabled"}
    
    try:
        logger.info("Starting log sync to Elasticsearch")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Sync logs to Elasticsearch
            success_count, error_count = elasticsearch_client.sync_logs_to_elasticsearch(db)
            
            logger.info(f"Log sync completed: {success_count} logs synced, {error_count} errors")
            
            return {
                "status": "success",
                "synced_count": success_count,
                "error_count": error_count
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error syncing logs to Elasticsearch: {str(e)}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="monitoring.sync_metrics_to_elasticsearch")
def sync_metrics_to_elasticsearch_task():
    """
    Sync metrics from the database to Elasticsearch.
    
    This task will retrieve metrics that haven't been synced to Elasticsearch
    and send them in batches. It will mark metrics as synced after successful
    indexing.
    """
    if not settings.logging.elasticsearch.enabled:
        logger.info("Elasticsearch integration is disabled. Skipping metric sync.")
        return {"status": "skipped", "reason": "elasticsearch_disabled"}
    
    try:
        logger.info("Starting metric sync to Elasticsearch")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Sync metrics to Elasticsearch
            success_count, error_count = elasticsearch_client.sync_metrics_to_elasticsearch(db)
            
            logger.info(f"Metric sync completed: {success_count} metrics synced, {error_count} errors")
            
            return {
                "status": "success",
                "synced_count": success_count,
                "error_count": error_count
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error syncing metrics to Elasticsearch: {str(e)}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def collect_network_performance_metrics_task():
    """
    Celery task to collect network performance metrics and send them to Elasticsearch.
    
    This task collects various network metrics including:
    - Latency
    - Packet loss
    - Bandwidth utilization
    - Connection counts
    - Service availability
    - Customer usage statistics
    
    The collected metrics are saved to the database and sent to Elasticsearch
    for visualization in Kibana dashboards and alerting.
    """
    try:
        logger.info("Starting network performance metrics collection task")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Create collector and run once
            from modules.monitoring.collectors.network_performance_collector import NetworkPerformanceCollector
            collector = NetworkPerformanceCollector(db)
            
            # Collect metrics
            collector.collect_all_metrics()
            
            # Save to database
            collector.save_to_database()
            
            # Send to Elasticsearch
            collector.send_to_elasticsearch()
            
            logger.info("Network performance metrics collection completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error in network performance metrics collection task: {str(e)}")
            return False
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to execute network performance metrics collection task: {str(e)}")
        return False
