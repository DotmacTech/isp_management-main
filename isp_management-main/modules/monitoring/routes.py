from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend_core.database import get_db
from backend_core.cache import get_redis
from backend_core.auth import get_current_user

from .services import (
    LoggingService,
    MetricsService,
    AlertService,
    DashboardService,
    MonitoringService
)

from .models import (
    LogLevel,
    MetricType,
    AlertSeverity,
    AlertStatus
)

from .schemas import (
    # Logging schemas
    ServiceLogCreate,
    ServiceLogResponse,
    LogRetentionPolicyCreate,
    LogRetentionPolicyResponse,
    LogSearchParams,
    
    # Metrics schemas
    SystemMetricCreate,
    SystemMetricResponse,
    MetricSearchParams,
    
    # Alert schemas
    AlertConfigurationCreate,
    AlertConfigurationResponse,
    AlertHistoryCreate,
    AlertHistoryUpdate,
    AlertHistoryResponse,
    AlertSearchParams,
    
    # Dashboard schemas
    DashboardConfigurationCreate,
    DashboardConfigurationResponse,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    
    # Common schemas
    PaginatedResponse,
    HealthCheckResponse,
    HealthCheckComponentStatus,
    ServiceHealthReport
)

# Create router
router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
    responses={404: {"description": "Not found"}},
)

# Health check endpoint
@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """Check the health of all system components."""
    monitoring_service = MonitoringService(db)
    return await monitoring_service.check_system_health()

# Logging endpoints
@router.post("/logs", response_model=ServiceLogResponse)
async def create_log(
    log_data: ServiceLogCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new log entry."""
    logging_service = LoggingService(db)
    alert_service = AlertService(db)
    
    # Add user ID if available and not already set
    if current_user and not log_data.user_id:
        log_data.user_id = current_user.get("id")
    
    # Create log
    log_response = await logging_service.create_log(log_data)
    
    # Check for alert conditions in background
    background_tasks.add_task(alert_service.evaluate_log_alert_conditions, log_data)
    
    return log_response

@router.get("/logs", response_model=PaginatedResponse)
async def search_logs(
    service_names: Optional[List[str]] = Query(None),
    log_levels: Optional[List[LogLevel]] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    trace_id: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    message_contains: Optional[str] = Query(None),
    request_path: Optional[str] = Query(None),
    use_elasticsearch: bool = Query(True),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search logs with filtering options."""
    logging_service = LoggingService(db)
    
    # Create search params
    search_params = LogSearchParams(
        service_names=service_names,
        log_levels=log_levels,
        start_time=start_time,
        end_time=end_time,
        trace_id=trace_id,
        correlation_id=correlation_id,
        user_id=user_id,
        message_contains=message_contains,
        request_path=request_path,
        offset=offset,
        limit=limit
    )
    
    # Use Elasticsearch or database search based on parameter
    if use_elasticsearch:
        return await logging_service.search_logs_elasticsearch(search_params)
    else:
        return await logging_service.search_logs(search_params)

@router.get("/logs/retention-policies", response_model=List[LogRetentionPolicyResponse])
async def get_log_retention_policies(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all log retention policies."""
    logging_service = LoggingService(db)
    return await logging_service.get_log_retention_policies()

@router.post("/logs/retention-policies", response_model=LogRetentionPolicyResponse)
async def create_log_retention_policy(
    policy_data: LogRetentionPolicyCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new log retention policy."""
    logging_service = LoggingService(db)
    return await logging_service.create_log_retention_policy(policy_data)

@router.post("/logs/apply-retention")
async def apply_retention_policies(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Manually apply retention policies to logs."""
    logging_service = LoggingService(db)
    return await logging_service.apply_retention_policies()

# Metrics endpoints
@router.post("/metrics", response_model=SystemMetricResponse)
async def create_metric(
    metric_data: SystemMetricCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Record a new system metric."""
    metrics_service = MetricsService(db, redis)
    alert_service = AlertService(db, redis)
    
    # Create metric
    metric_response = await metrics_service.create_metric(metric_data)
    
    # Check for alert conditions in background
    background_tasks.add_task(alert_service.evaluate_alert_conditions, metric_data)
    
    return metric_response

@router.get("/metrics", response_model=PaginatedResponse[SystemMetricResponse])
async def search_metrics(
    service_names: Optional[List[str]] = Query(None),
    host_names: Optional[List[str]] = Query(None),
    metric_types: Optional[List[MetricType]] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    tags: Optional[List[str]] = Query(None),
    aggregation: Optional[str] = Query(None, regex="^(avg|sum|min|max|count)$"),
    group_by: Optional[List[str]] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search metrics with filtering and optional aggregation."""
    metrics_service = MetricsService(db, redis)
    
    # Create search params
    search_params = MetricSearchParams(
        service_names=service_names,
        host_names=host_names,
        metric_types=metric_types,
        start_time=start_time,
        end_time=end_time,
        tags=tags,
        aggregation=aggregation,
        group_by=group_by,
        offset=offset,
        limit=limit
    )
    
    return await metrics_service.search_metrics(search_params)

@router.get("/metrics/latest", response_model=List[SystemMetricResponse])
async def get_latest_metrics(
    service_name: Optional[str] = Query(None),
    host_name: Optional[str] = Query(None),
    metric_type: Optional[MetricType] = Query(None),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the latest metrics, optionally filtered by service, host, or metric type."""
    metrics_service = MetricsService(db, redis)
    return await metrics_service.get_latest_metrics(service_name, host_name, metric_type)

@router.get("/metrics/trends/{service_name}/{host_name}/{metric_type}")
async def get_metric_trends(
    service_name: str,
    host_name: str,
    metric_type: MetricType,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get metric trends over time for a specific service, host, and metric type."""
    metrics_service = MetricsService(db, redis)
    return await metrics_service.get_metric_trends(service_name, host_name, metric_type, hours)

# Alert endpoints
@router.post("/alerts/configurations", response_model=AlertConfigurationResponse)
async def create_alert_configuration(
    alert_config: AlertConfigurationCreate,
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new alert configuration."""
    alert_service = AlertService(db, redis)
    return await alert_service.create_alert_configuration(alert_config)

@router.get("/alerts/configurations", response_model=List[AlertConfigurationResponse])
async def get_alert_configurations(
    service_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all alert configurations, optionally filtered by service name."""
    alert_service = AlertService(db, redis)
    return await alert_service.get_alert_configurations(service_name)

@router.put("/alerts/configurations/{config_id}", response_model=AlertConfigurationResponse)
async def update_alert_configuration(
    config_id: int,
    alert_config: AlertConfigurationCreate,
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an existing alert configuration."""
    alert_service = AlertService(db, redis)
    return await alert_service.update_alert_configuration(config_id, alert_config)

@router.delete("/alerts/configurations/{config_id}")
async def delete_alert_configuration(
    config_id: int,
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete an alert configuration."""
    alert_service = AlertService(db, redis)
    return await alert_service.delete_alert_configuration(config_id)

@router.post("/alerts/history", response_model=AlertHistoryResponse)
async def create_alert_history(
    alert_data: AlertHistoryCreate,
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Record a new alert in the alert history."""
    alert_service = AlertService(db, redis)
    return await alert_service.create_alert_history(alert_data)

@router.put("/alerts/history/{alert_id}", response_model=AlertHistoryResponse)
async def update_alert_status(
    alert_id: int,
    status_update: AlertHistoryUpdate,
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update the status of an alert in the history."""
    # Add user ID to resolved_by if resolving the alert
    if status_update.status == AlertStatus.RESOLVED and current_user:
        status_update.resolved_by = current_user.get("id")
        
    alert_service = AlertService(db, redis)
    return await alert_service.update_alert_status(alert_id, status_update)

@router.get("/alerts/history", response_model=PaginatedResponse)
async def search_alerts(
    service_names: Optional[List[str]] = Query(None),
    severities: Optional[List[AlertSeverity]] = Query(None),
    statuses: Optional[List[AlertStatus]] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    message_contains: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search alerts with filtering options."""
    alert_service = AlertService(db, redis)
    
    # Create search params
    search_params = AlertSearchParams(
        service_names=service_names,
        severities=severities,
        statuses=statuses,
        start_time=start_time,
        end_time=end_time,
        message_contains=message_contains,
        offset=offset,
        limit=limit
    )
    
    return await alert_service.search_alerts(search_params)

@router.get("/alerts/active", response_model=List[AlertHistoryResponse])
async def get_active_alerts(
    service_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    redis = Depends(get_redis),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all active (non-resolved) alerts, optionally filtered by service name."""
    alert_service = AlertService(db, redis)
    return await alert_service.get_active_alerts(service_name)

# Dashboard endpoints
@router.post("/dashboards", response_model=DashboardConfigurationResponse)
async def create_dashboard(
    dashboard_data: DashboardConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new dashboard configuration."""
    dashboard_service = DashboardService(db)
    
    # Set user ID if not provided
    if not dashboard_data.user_id and current_user:
        dashboard_data.user_id = current_user.get("id")
        
    return await dashboard_service.create_dashboard(dashboard_data)

@router.get("/dashboards", response_model=List[DashboardConfigurationResponse])
async def get_dashboards(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all dashboards accessible to the current user."""
    dashboard_service = DashboardService(db)
    user_id = current_user.get("id") if current_user else None
    return await dashboard_service.get_dashboards(user_id)

@router.get("/dashboards/{dashboard_id}", response_model=DashboardConfigurationResponse)
async def get_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a dashboard by ID with all its widgets."""
    dashboard_service = DashboardService(db)
    dashboard = await dashboard_service.get_dashboard(dashboard_id)
    
    # Check if user has access to this dashboard
    if not dashboard.is_public and current_user and dashboard.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="You don't have access to this dashboard")
        
    return dashboard

@router.put("/dashboards/{dashboard_id}", response_model=DashboardConfigurationResponse)
async def update_dashboard(
    dashboard_id: int,
    dashboard_data: DashboardConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an existing dashboard configuration."""
    dashboard_service = DashboardService(db)
    
    # Check if user owns this dashboard
    dashboard = await dashboard_service.get_dashboard(dashboard_id)
    if current_user and dashboard.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="You don't have permission to update this dashboard")
    
    return await dashboard_service.update_dashboard(dashboard_id, dashboard_data)

@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a dashboard and all its widgets."""
    dashboard_service = DashboardService(db)
    
    # Check if user owns this dashboard
    dashboard = await dashboard_service.get_dashboard(dashboard_id)
    if current_user and dashboard.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this dashboard")
    
    return await dashboard_service.delete_dashboard(dashboard_id)

# Health check routes
@router.get("/health/{component_name}", response_model=HealthCheckComponentStatus, tags=["health"])
async def component_health(component_name: str, db: Session = Depends(get_db)):
    """
    Check the health of a specific component.
    
    This endpoint checks the health of a specific component, such as the database,
    Redis, or Elasticsearch. It returns the component status, including response
    time and any error details.
    """
    monitoring_service = MonitoringService(db)
    component_status = monitoring_service.get_component_status(component_name)
    
    if not component_status:
        raise HTTPException(status_code=404, detail=f"Component {component_name} not found")
    
    return component_status


@router.post("/health/report", response_model=Dict[str, Any], tags=["health"])
async def report_service_health(
    report: ServiceHealthReport,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Report service health to the monitoring system.
    
    This endpoint allows services to report their health status to the monitoring
    system. The report includes service name, health status, and additional details.
    """
    # Check if user has permission to report health
    if not current_user.get("is_admin", False) and not current_user.get("is_service_account", False):
        raise HTTPException(
            status_code=403,
            detail="Only admin users and service accounts can report service health"
        )
    
    # Create log entry for health report
    logging_service = LoggingService(db)
    log_level = LogLevel.INFO
    
    if report.health_info.get("status") != "healthy":
        log_level = LogLevel.WARNING
    
    log = ServiceLogCreate(
        service_name=report.service_name,
        log_level=log_level,
        message=f"Health report from {report.service_name}: {report.health_info.get('status', 'unknown')}",
        metadata={"health_report": report.health_info}
    )
    
    logging_service.create_log(log)
    
    # Create metrics from health report
    metrics_service = MetricsService(db)
    
    # CPU usage metric if available
    cpu_percent = report.health_info.get("cpu", {}).get("percent")
    if cpu_percent is not None:
        metrics_service.create_metric(SystemMetricCreate(
            service_name=report.service_name,
            host_name=report.health_info.get("hostname", "unknown"),
            metric_type=MetricType.CPU_USAGE,
            value=float(cpu_percent),
            unit="percent",
            tags={"source": "health_report"}
        ))
    
    # Memory usage metric if available
    memory_percent = report.health_info.get("memory", {}).get("percent")
    if memory_percent is not None:
        metrics_service.create_metric(SystemMetricCreate(
            service_name=report.service_name,
            host_name=report.health_info.get("hostname", "unknown"),
            metric_type=MetricType.MEMORY_USAGE,
            value=float(memory_percent),
            unit="percent",
            tags={"source": "health_report"}
        ))
    
    # Disk usage metric if available
    disk_percent = report.health_info.get("disk", {}).get("percent")
    if disk_percent is not None:
        metrics_service.create_metric(SystemMetricCreate(
            service_name=report.service_name,
            host_name=report.health_info.get("hostname", "unknown"),
            metric_type=MetricType.DISK_USAGE,
            value=float(disk_percent),
            unit="percent",
            tags={"source": "health_report"}
        ))
    
    return {"status": "success", "message": "Health report received"}


@router.get("/metrics/summary", response_model=Dict[str, Any], tags=["metrics"])
async def get_system_metrics_summary(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a summary of system metrics.
    
    This endpoint returns a summary of system metrics, including CPU, memory,
    and disk usage statistics. The summary includes minimum, maximum, average,
    median, and percentile values for each metric type.
    """
    # Check if user has permission to view metrics
    if not current_user.get("is_admin", False) and not current_user.get("has_permission", {}).get("monitoring:view", False):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view system metrics"
        )
    
    monitoring_service = MonitoringService(db)
    return monitoring_service.get_system_metrics_summary(start_time, end_time)


@router.get("/components/{component_name}/metrics", response_model=List[SystemMetricResponse], tags=["metrics"])
async def get_component_metrics(
    component_name: str,
    metric_type: Optional[MetricType] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get metrics for a specific component.
    
    This endpoint returns metrics for a specific component, such as CPU, memory,
    or disk usage. The metrics can be filtered by metric type and time range.
    """
    # Check if user has permission to view metrics
    if not current_user.get("is_admin", False) and not current_user.get("has_permission", {}).get("monitoring:view", False):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view component metrics"
        )
    
    monitoring_service = MonitoringService(db)
    metrics = monitoring_service.get_component_metrics(
        component_name=component_name,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    return [SystemMetricResponse.from_orm(metric) for metric in metrics]


@router.get("/services/{service_name}/logs", response_model=List[ServiceLogResponse], tags=["logs"])
async def get_service_logs(
    service_name: str,
    log_level: Optional[LogLevel] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get logs for a specific service.
    
    This endpoint returns logs for a specific service. The logs can be filtered
    by log level and time range.
    """
    # Check if user has permission to view logs
    if not current_user.get("is_admin", False) and not current_user.get("has_permission", {}).get("monitoring:view", False):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view service logs"
        )
    
    monitoring_service = MonitoringService(db)
    logs = monitoring_service.get_service_logs(
        service_name=service_name,
        log_level=log_level,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    return [ServiceLogResponse.from_orm(log) for log in logs]


# Network monitoring routes
@router.get("/network/performance", response_model=List[SystemMetricResponse], tags=["network"])
async def get_network_performance(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get network performance metrics.
    
    This endpoint returns network performance metrics, including bandwidth usage,
    latency, and packet loss. The metrics can be filtered by time range.
    """
    # Check if user has permission to view metrics
    if not current_user.get("is_admin", False) and not current_user.get("has_permission", {}).get("monitoring:view", False):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view network performance metrics"
        )
    
    # Set default time range if not provided
    if not end_time:
        end_time = datetime.utcnow()
    
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    # Query network metrics
    metrics_service = MetricsService(db)
    network_metrics = metrics_service.search_metrics(
        metric_type=[
            MetricType.NETWORK_SENT,
            MetricType.NETWORK_RECEIVED,
            MetricType.LATENCY,
            MetricType.PACKET_LOSS
        ],
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    return [SystemMetricResponse.from_orm(metric) for metric in network_metrics]


@router.get("/customer/usage", response_model=List[SystemMetricResponse], tags=["customer"])
async def get_customer_usage(
    customer_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get customer usage metrics.
    
    This endpoint returns customer usage metrics, including bandwidth usage,
    data transfer, and connection statistics. The metrics can be filtered by
    customer ID and time range.
    """
    # Check if user has permission to view metrics
    if not current_user.get("is_admin", False) and not current_user.get("has_permission", {}).get("monitoring:view", False):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view customer usage metrics"
        )
    
    # Set default time range if not provided
    if not end_time:
        end_time = datetime.utcnow()
    
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    # Query customer metrics
    metrics_service = MetricsService(db)
    
    # Build tags filter
    tags = {}
    if customer_id:
        tags["customer_id"] = str(customer_id)
    
    customer_metrics = metrics_service.search_metrics(
        metric_type=[
            MetricType.BANDWIDTH_USAGE,
            MetricType.DATA_TRANSFER,
            MetricType.CONNECTIONS
        ],
        start_time=start_time,
        end_time=end_time,
        tags=tags,
        limit=limit
    )
    
    return [SystemMetricResponse.from_orm(metric) for metric in customer_metrics]


@router.get("/service/availability", response_model=Dict[str, Any], tags=["service"])
async def get_service_availability(
    service_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get service availability metrics.
    
    This endpoint returns service availability metrics, including uptime percentage,
    downtime duration, and response time statistics. The metrics can be filtered by
    service name and time range.
    """
    # Check if user has permission to view metrics
    if not current_user.get("is_admin", False) and not current_user.get("has_permission", {}).get("monitoring:view", False):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view service availability metrics"
        )
    
    # Set default time range if not provided
    if not end_time:
        end_time = datetime.utcnow()
    
    if not start_time:
        start_time = end_time - timedelta(days=7)
    
    # Query service status metrics
    metrics_service = MetricsService(db)
    
    # Build query filters
    filters = {
        "metric_type": MetricType.STATUS,
        "start_time": start_time,
        "end_time": end_time
    }
    
    if service_name:
        filters["service_name"] = service_name
    
    status_metrics = metrics_service.search_metrics(**filters)
    
    # Calculate availability statistics
    from .utils import calculate_statistics
    
    # Group metrics by service
    service_metrics = {}
    for metric in status_metrics:
        if metric.service_name not in service_metrics:
            service_metrics[metric.service_name] = []
        
        service_metrics[metric.service_name].append(metric)
    
    # Calculate availability for each service
    availability_stats = {}
    for service, metrics in service_metrics.items():
        # Extract status values (1.0 = up, 0.0 = down)
        status_values = [metric.value for metric in metrics]
        
        # Calculate uptime percentage
        if status_values:
            uptime_percentage = (sum(status_values) / len(status_values)) * 100
        else:
            uptime_percentage = 0
        
        # Count downtime events
        downtime_events = len([v for v in status_values if v < 1.0])
        
        # Calculate statistics
        stats = calculate_statistics(status_values)
        
        # Add to results
        availability_stats[service] = {
            "uptime_percentage": uptime_percentage,
            "downtime_events": downtime_events,
            "total_checks": len(status_values),
            "statistics": stats
        }
    
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "services": availability_stats
    }
