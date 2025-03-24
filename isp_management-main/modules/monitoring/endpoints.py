from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user, get_current_user_with_permissions
from backend_core.auth_service.permissions import Permission
from backend_core.utils.hateoas import add_link, generate_collection_links, add_resource_links
from backend_core.schemas import HateoasResponse
from .schemas import (
    MetricRecord,
    AlertCreate,
    AlertResponse,
    AlertUpdate,
    SystemHealthCheck,
    AlertConfigurationCreate,
    AlertConfigurationUpdate,
    AlertConfigurationResponse,
    AlertHistoryCreate,
    AlertHistoryUpdate,
    AlertHistoryResponse,
    AlertSearchParams,
    LogSearchParams,
    MetricSearchParams,
    PaginatedResponse,
    DashboardConfigurationCreate,
    DashboardConfigurationUpdate,
    DashboardConfigurationResponse,
    DashboardWidgetCreate,
    DashboardWidgetUpdate,
    DashboardWidgetResponse,
    ServiceLogCreate,
    SystemMetricCreate
)
from .services import MonitoringService
from .services.alert_management_service import AlertManagementService
from .services.reporting_service import ReportingService
from .services.dashboard_service import DashboardService
from .collectors.system_metrics_collector import collect_system_metrics

router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"]
)

# Protected routes (require authentication)
protected_router = APIRouter(
    dependencies=[Depends(get_current_active_user)]
)

# Admin routes (require admin permissions)
admin_router = APIRouter(
    dependencies=[Depends(get_current_user_with_permissions([Permission.ADMIN]))]
)

@router.get("/health", response_model=SystemHealthCheck)
async def check_system_health(
    db: Session = Depends(get_db)
):
    """Check the health of all system components."""
    monitoring_service = MonitoringService(db)
    health_check = monitoring_service.check_system_health()
    
    # Add HATEOAS links
    add_link(health_check, "self", "/monitoring/health")
    add_link(health_check, "alerts", "/monitoring/alerts")
    add_link(health_check, "metrics", "/monitoring/metrics")
    
    return health_check

@protected_router.post("/metrics", status_code=status.HTTP_201_CREATED)
async def record_metric(
    metric: MetricRecord,
    db: Session = Depends(get_db)
):
    """Record a new metric and check for threshold violations."""
    monitoring_service = MonitoringService(db)
    return await monitoring_service.record_metric(metric)

@protected_router.get("/alerts/active", response_model=List[Dict[str, Any]])
async def get_active_alerts(
    service_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all active (non-resolved) alerts."""
    alert_service = AlertManagementService(db)
    alerts = alert_service.get_active_alerts(service_name)
    
    # Add HATEOAS links to each alert
    for alert in alerts:
        add_resource_links(
            alert, 
            "/monitoring/alerts", 
            alert.id,
            ["history", "configuration"]
        )
        add_link(alert, "acknowledge", f"/monitoring/alerts/{alert.id}/acknowledge", "PUT")
        add_link(alert, "resolve", f"/monitoring/alerts/{alert.id}/resolve", "PUT")
    
    return alerts

@protected_router.patch("/alerts/{alert_id}", response_model=Dict[str, Any])
async def update_alert(
    alert_id: int,
    update_data: AlertHistoryUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert's status (acknowledge or resolve)."""
    alert_service = AlertManagementService(db)
    updated_alert = alert_service.update_alert_status(alert_id, update_data)
    
    # Add HATEOAS links
    add_resource_links(
        updated_alert, 
        "/monitoring/alerts", 
        updated_alert.id
    )
    
    return updated_alert

@protected_router.post("/alerts", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertHistoryCreate,
    db: Session = Depends(get_db)
):
    """Manually create a new alert."""
    alert_service = AlertManagementService(db)
    new_alert = alert_service.create_alert_history(alert_data)
    
    # Add HATEOAS links
    add_resource_links(
        new_alert, 
        "/monitoring/alerts", 
        new_alert.id,
        ["history", "configuration"]
    )
    add_link(new_alert, "acknowledge", f"/monitoring/alerts/{new_alert.id}/acknowledge", "PUT")
    add_link(new_alert, "resolve", f"/monitoring/alerts/{new_alert.id}/resolve", "PUT")
    
    return new_alert

@protected_router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_metrics(
    db: Session = Depends(get_db)
):
    """Get key metrics for the dashboard."""
    monitoring_service = MonitoringService(db)
    return monitoring_service.get_dashboard_metrics()

# New endpoints for system metrics collection
@admin_router.post("/collect/system-metrics", response_model=Dict[str, Any])
async def trigger_system_metrics_collection(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger collection of system metrics.
    
    This endpoint will start a background task to collect system metrics.
    """
    background_tasks.add_task(collect_system_metrics, db)
    return {
        "status": "success",
        "message": "System metrics collection started in the background"
    }

# Alert configuration endpoints
@admin_router.get("/alert-configurations", response_model=Dict[str, Any])
async def get_alert_configurations(
    service_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all alert configurations.
    
    Optionally filter by service name and active status.
    """
    alert_service = AlertManagementService(db)
    configurations = alert_service.get_alert_configurations(service_name, is_active)
    
    # Apply pagination
    total_count = len(configurations)
    paginated_configs = configurations[skip:skip+limit]
    
    # Create response
    response = {
        "items": paginated_configs,
        "total": total_count,
        "skip": skip,
        "limit": limit
    }
    
    # Calculate page number (1-based)
    page = (skip // limit) + 1 if limit > 0 else 1
    
    # Add HATEOAS links
    resource_path = "/api/v1/monitoring/alert-configurations"
    
    # Build filter dictionary for link generation
    filters = {}
    if service_name:
        filters["service_name"] = service_name
    if is_active is not None:
        filters["is_active"] = str(is_active).lower()
    
    # Generate collection links (self, first, last, prev, next)
    collection_links = generate_collection_links(
        resource_path=resource_path,
        page=page,
        limit=limit,
        total=total_count,
        filters=filters
    )
    
    # Add links to response
    response["_links"] = collection_links
    
    # Add create link
    add_link(
        response=response,
        rel="create",
        href=resource_path,
        method="POST",
        title="Create new alert configuration"
    )
    
    # Add item links
    for config in paginated_configs:
        add_resource_links(
            config, 
            "/monitoring/alert-configurations", 
            config.id,
            ["alerts"]
        )
    
    return response

@admin_router.get("/alert-configurations/{config_id}", response_model=Dict[str, Any])
async def get_alert_configuration(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Get an alert configuration by ID."""
    alert_service = AlertManagementService(db)
    config = alert_service.get_alert_configuration(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert configuration with ID {config_id} not found"
        )
    
    # Convert to dict for adding links
    response = config.dict()
    
    # Add HATEOAS links
    resource_path = f"/api/v1/monitoring/alert-configurations/{config_id}"
    
    # Add self link
    add_link(
        response=response,
        rel="self",
        href=resource_path,
        method="GET",
        title="Get this alert configuration"
    )
    
    # Add update link
    add_link(
        response=response,
        rel="update",
        href=resource_path,
        method="PUT",
        title="Update this alert configuration"
    )
    
    # Add delete link
    add_link(
        response=response,
        rel="delete",
        href=resource_path,
        method="DELETE",
        title="Delete this alert configuration"
    )
    
    # Add collection link
    add_link(
        response=response,
        rel="collection",
        href="/api/v1/monitoring/alert-configurations",
        method="GET",
        title="View all alert configurations"
    )
    
    # Add alerts link
    add_link(
        response=response,
        rel="alerts",
        href=f"/api/v1/monitoring/alerts?configuration_id={config_id}",
        method="GET",
        title="View alerts for this configuration"
    )
    
    return response

@admin_router.post("/alert-configurations", response_model=AlertConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_configuration(
    config_data: AlertConfigurationCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert configuration."""
    alert_service = AlertManagementService(db)
    new_config = alert_service.create_alert_configuration(config_data)
    
    # Add HATEOAS links
    add_resource_links(
        new_config, 
        "/monitoring/alert-configurations", 
        new_config.id
    )
    
    return new_config

@admin_router.put("/alert-configurations/{config_id}", response_model=AlertConfigurationResponse)
async def update_alert_configuration(
    config_id: int,
    config_data: AlertConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing alert configuration."""
    alert_service = AlertManagementService(db)
    updated_config = alert_service.update_alert_configuration(config_id, config_data)
    
    # Add HATEOAS links
    add_resource_links(
        updated_config, 
        "/monitoring/alert-configurations", 
        updated_config.id
    )
    
    return updated_config

@admin_router.delete("/alert-configurations/{config_id}", response_model=Dict[str, Any])
async def delete_alert_configuration(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Delete an alert configuration."""
    alert_service = AlertManagementService(db)
    return alert_service.delete_alert_configuration(config_id)

# Alert history endpoints
@protected_router.get("/alert-history", response_model=PaginatedResponse)
async def get_alert_history(
    search_params: AlertSearchParams = Depends(),
    db: Session = Depends(get_db)
):
    """
    Search alert history with filtering options.
    """
    alert_service = AlertManagementService(db)
    alerts, total = alert_service.search_alerts(search_params)
    
    # Create response
    response = {
        "items": alerts,
        "total": total,
        "limit": search_params.limit,
        "offset": search_params.offset
    }
    
    # Calculate page number (1-based)
    page = (search_params.offset // search_params.limit) + 1 if search_params.limit > 0 else 1
    
    # Add HATEOAS links
    resource_path = "/api/v1/monitoring/alert-history"
    
    # Build filter dictionary for link generation
    filters = {}
    if search_params.service_names:
        filters["service_names"] = ",".join(search_params.service_names)
    if search_params.severities:
        filters["severities"] = ",".join([s.value for s in search_params.severities])
    if search_params.statuses:
        filters["statuses"] = ",".join([s.value for s in search_params.statuses])
    if search_params.start_time:
        filters["start_time"] = search_params.start_time.isoformat()
    if search_params.end_time:
        filters["end_time"] = search_params.end_time.isoformat()
    
    # Generate collection links (self, first, last, prev, next)
    collection_links = generate_collection_links(
        resource_path=resource_path,
        page=page,
        limit=search_params.limit,
        total=total,
        filters=filters
    )
    
    # Add links to response
    response["_links"] = collection_links
    
    # Add item links
    for item in alerts:
        add_resource_links(
            item, 
            "/monitoring/alert-history", 
            item.id
        )
        add_link(item, "alert", f"/monitoring/alerts/{item.alert_id}")
    
    return response

# Reporting endpoints
@protected_router.get("/reports/system-performance", response_model=Dict[str, Any])
async def generate_system_performance_report(
    start_time: datetime = Query(..., description="Start time for the report"),
    end_time: datetime = Query(..., description="End time for the report"),
    service_names: Optional[List[str]] = Query(None, description="Optional list of service names to include"),
    metric_types: Optional[List[str]] = Query(None, description="Optional list of metric types to include"),
    report_format: str = Query("json", description="Format of the report (json, csv, pdf)"),
    db: Session = Depends(get_db)
):
    """
    Generate a system performance report.
    """
    reporting_service = ReportingService(db)
    return reporting_service.generate_system_performance_report(
        start_time, end_time, service_names, metric_types, report_format
    )

@protected_router.get("/reports/alerts", response_model=Dict[str, Any])
async def generate_alert_report(
    start_time: datetime = Query(..., description="Start time for the report"),
    end_time: datetime = Query(..., description="End time for the report"),
    service_names: Optional[List[str]] = Query(None, description="Optional list of service names to include"),
    severities: Optional[List[str]] = Query(None, description="Optional list of severities to include"),
    report_format: str = Query("json", description="Format of the report (json, csv, pdf)"),
    db: Session = Depends(get_db)
):
    """
    Generate a report of alerts.
    """
    reporting_service = ReportingService(db)
    return reporting_service.generate_alert_report(
        start_time, end_time, service_names, severities, report_format
    )

@protected_router.get("/reports/service-availability", response_model=Dict[str, Any])
async def generate_service_availability_report(
    start_time: datetime = Query(..., description="Start time for the report"),
    end_time: datetime = Query(..., description="End time for the report"),
    service_names: Optional[List[str]] = Query(None, description="Optional list of service names to include"),
    report_format: str = Query("json", description="Format of the report (json, csv, pdf)"),
    db: Session = Depends(get_db)
):
    """
    Generate a service availability report.
    """
    reporting_service = ReportingService(db)
    return reporting_service.generate_service_availability_report(
        start_time, end_time, service_names, report_format
    )

# Dashboard endpoints
@protected_router.get("/dashboards", response_model=List[DashboardConfigurationResponse])
async def get_dashboards(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get all dashboards, optionally filtered by user ID.
    """
    dashboard_service = DashboardService(db)
    if user_id:
        return dashboard_service.get_user_dashboards(user_id)
    else:
        return dashboard_service.get_public_dashboards()

@protected_router.get("/dashboards/{dashboard_id}", response_model=Dict[str, Any])
async def get_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a dashboard by ID with all its widgets.
    """
    dashboard_service = DashboardService(db)
    dashboard, widgets = dashboard_service.get_dashboard_with_widgets(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return {
        "dashboard": dashboard,
        "widgets": widgets
    }

@protected_router.post("/dashboards", response_model=DashboardConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    dashboard_data: DashboardConfigurationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new dashboard.
    """
    dashboard_service = DashboardService(db)
    return dashboard_service.create_dashboard(dashboard_data.dict())

@protected_router.put("/dashboards/{dashboard_id}", response_model=Dict[str, Any])
async def update_dashboard(
    dashboard_id: int,
    dashboard_data: DashboardConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing dashboard.
    """
    dashboard_service = DashboardService(db)
    success = dashboard_service.update_dashboard(dashboard_id, dashboard_data.dict(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return {"status": "success", "message": "Dashboard updated"}

@protected_router.delete("/dashboards/{dashboard_id}", response_model=Dict[str, Any])
async def delete_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a dashboard.
    """
    dashboard_service = DashboardService(db)
    success = dashboard_service.delete_dashboard(dashboard_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return {"status": "success", "message": "Dashboard deleted"}

@protected_router.post("/dashboards/{dashboard_id}/widgets", response_model=DashboardWidgetResponse, status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: int,
    widget_data: DashboardWidgetCreate,
    db: Session = Depends(get_db)
):
    """
    Add a widget to a dashboard.
    """
    dashboard_service = DashboardService(db)
    widget = dashboard_service.add_widget(dashboard_id, widget_data.dict())
    if not widget:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return widget

# Include the protected and admin routes
router.include_router(protected_router)
router.include_router(admin_router)
