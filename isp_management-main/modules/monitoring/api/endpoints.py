from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user
from backend_core.auth import require_permissions
from backend_core.rbac import Permission
from backend_core.utils.hateoas import add_resource_links, generate_collection_links, add_link
from backend_core.schemas import HateoasResponse

from ..schemas import (
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
from ..services.monitoring_service import MonitoringService
from ..services.alert_management_service import AlertManagementService
from ..services.reporting_service import ReportingService
from ..services.dashboard_service import DashboardService
from ..collectors.system_metrics_collector import collect_system_metrics

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
    dependencies=[Depends(require_permissions([Permission.CONFIGURE_ALERTS, Permission.VIEW_SYSTEM_METRICS, Permission.CONFIGURE_LOGGING]))]
)

@router.get("/health", response_model=SystemHealthCheck)
async def check_system_health(
    db: Session = Depends(get_db)
):
    """Check the health of all system components."""
    health_data = await MonitoringService.check_system_health(db)
    
    # Add HATEOAS links
    response = health_data
    add_link(
        response=response,
        rel="self",
        href="/api/v1/monitoring/health",
        method="GET",
        title="Get system health"
    )
    
    add_link(
        response=response,
        rel="alerts",
        href="/api/v1/monitoring/alerts",
        method="GET",
        title="Get active alerts"
    )
    
    return response

@protected_router.post("/metrics", response_model=Dict[str, Any])
async def record_metric(
    metric: MetricRecord,
    db: Session = Depends(get_db)
):
    """Record a new metric and check for threshold violations."""
    result = await MonitoringService.record_metric(db, metric)
    
    # Add HATEOAS links
    response = result
    add_link(
        response=response,
        rel="metrics",
        href="/api/v1/monitoring/metrics",
        method="GET",
        title="Get metrics"
    )
    
    return response

@protected_router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts(
    service_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all active (non-resolved) alerts."""
    alerts = await AlertManagementService.get_active_alerts(db, service_name)
    
    # Convert to response models and add HATEOAS links
    alert_responses = []
    for alert in alerts:
        alert_response = AlertResponse.model_validate(alert)
        
        # Add resource links
        add_resource_links(
            response=alert_response,
            resource_path="/api/v1/monitoring/alerts",
            resource_id=alert.id
        )
        
        # Add specific action links
        add_link(
            response=alert_response,
            rel="acknowledge",
            href=f"/api/v1/monitoring/alerts/{alert.id}",
            method="PUT",
            title="Acknowledge alert"
        )
        
        add_link(
            response=alert_response,
            rel="resolve",
            href=f"/api/v1/monitoring/alerts/{alert.id}",
            method="PUT",
            title="Resolve alert"
        )
        
        alert_responses.append(alert_response)
    
    return alert_responses

@protected_router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    update_data: AlertHistoryUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert's status (acknowledge or resolve)."""
    updated_alert = await AlertManagementService.update_alert(db, alert_id, update_data)
    
    # Convert to response model
    response = AlertResponse.model_validate(updated_alert)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/alerts",
        resource_id=alert_id
    )
    
    return response

@protected_router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertHistoryCreate,
    db: Session = Depends(get_db)
):
    """Manually create a new alert."""
    new_alert = await AlertManagementService.create_alert(db, alert_data)
    
    # Convert to response model
    response = AlertResponse.model_validate(new_alert)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/alerts",
        resource_id=new_alert.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="acknowledge",
        href=f"/api/v1/monitoring/alerts/{new_alert.id}",
        method="PUT",
        title="Acknowledge alert"
    )
    
    add_link(
        response=response,
        rel="resolve",
        href=f"/api/v1/monitoring/alerts/{new_alert.id}",
        method="PUT",
        title="Resolve alert"
    )
    
    return response

@protected_router.get("/dashboard/metrics", response_model=Dict[str, Any])
async def get_dashboard_metrics(
    db: Session = Depends(get_db)
):
    """Get key metrics for the dashboard."""
    metrics = await MonitoringService.get_dashboard_metrics(db)
    
    # Add HATEOAS links
    response = metrics
    add_link(
        response=response,
        rel="self",
        href="/api/v1/monitoring/dashboard/metrics",
        method="GET",
        title="Get dashboard metrics"
    )
    
    return response

# New endpoints for system metrics collection
@admin_router.post("/system-metrics/collect", response_model=Dict[str, str])
async def trigger_system_metrics_collection(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger collection of system metrics.
    
    This endpoint will start a background task to collect system metrics.
    """
    # Add the collection task to background tasks
    background_tasks.add_task(collect_system_metrics, db)
    
    # Create a response with HATEOAS links
    response = HateoasResponse()
    
    # Add links
    add_link(
        response=response,
        rel="metrics",
        href="/api/v1/monitoring/metrics",
        method="GET",
        title="View metrics"
    )
    
    return {"status": "System metrics collection started"}

# Alert configuration endpoints
@protected_router.get("/alert-configurations", response_model=List[AlertConfigurationResponse])
async def get_alert_configurations(
    service_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get all alert configurations.
    
    Optionally filter by service name and active status.
    """
    configs = await AlertManagementService.get_alert_configurations(db, service_name, is_active)
    
    # Convert to response models and add HATEOAS links
    config_responses = []
    for config in configs:
        config_response = AlertConfigurationResponse.model_validate(config)
        
        # Add resource links
        add_resource_links(
            response=config_response,
            resource_path="/api/v1/monitoring/alert-configurations",
            resource_id=config.id
        )
        
        # Add specific action links
        add_link(
            response=config_response,
            rel="update",
            href=f"/api/v1/monitoring/alert-configurations/{config.id}",
            method="PUT",
            title="Update configuration"
        )
        
        add_link(
            response=config_response,
            rel="delete",
            href=f"/api/v1/monitoring/alert-configurations/{config.id}",
            method="DELETE",
            title="Delete configuration"
        )
        
        config_responses.append(config_response)
    
    return config_responses

@protected_router.get("/alert-configurations/{config_id}", response_model=AlertConfigurationResponse)
async def get_alert_configuration(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Get an alert configuration by ID."""
    config = await AlertManagementService.get_alert_configuration(db, config_id)
    
    # Convert to response model
    response = AlertConfigurationResponse.model_validate(config)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/alert-configurations",
        resource_id=config_id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/monitoring/alert-configurations/{config_id}",
        method="PUT",
        title="Update configuration"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/monitoring/alert-configurations/{config_id}",
        method="DELETE",
        title="Delete configuration"
    )
    
    return response

@admin_router.post("/alert-configurations", response_model=AlertConfigurationResponse)
async def create_alert_configuration(
    config_data: AlertConfigurationCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert configuration."""
    new_config = await AlertManagementService.create_alert_configuration(db, config_data)
    
    # Convert to response model
    response = AlertConfigurationResponse.model_validate(new_config)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/alert-configurations",
        resource_id=new_config.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/monitoring/alert-configurations/{new_config.id}",
        method="PUT",
        title="Update configuration"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/monitoring/alert-configurations/{new_config.id}",
        method="DELETE",
        title="Delete configuration"
    )
    
    return response

@admin_router.put("/alert-configurations/{config_id}", response_model=AlertConfigurationResponse)
async def update_alert_configuration(
    config_id: int,
    config_data: AlertConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing alert configuration."""
    updated_config = await AlertManagementService.update_alert_configuration(db, config_id, config_data)
    
    # Convert to response model
    response = AlertConfigurationResponse.model_validate(updated_config)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/alert-configurations",
        resource_id=config_id
    )
    
    return response

@admin_router.delete("/alert-configurations/{config_id}", response_model=Dict[str, str])
async def delete_alert_configuration(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Delete an alert configuration."""
    await AlertManagementService.delete_alert_configuration(db, config_id)
    
    # Create a response with HATEOAS links
    response = HateoasResponse()
    
    # Add link to configurations collection
    add_link(
        response=response,
        rel="configurations",
        href="/api/v1/monitoring/alert-configurations",
        method="GET",
        title="View all configurations"
    )
    
    return {"status": "Alert configuration deleted"}

# Alert history endpoints
@protected_router.get("/alert-history", response_model=PaginatedResponse)
async def get_alert_history(
    search_params: AlertSearchParams = Depends(),
    db: Session = Depends(get_db)
):
    """
    Search alert history with filtering options.
    """
    alerts, total = await AlertManagementService.search_alert_history(db, search_params)
    
    # Convert to response models
    alert_responses = [AlertHistoryResponse.model_validate(alert) for alert in alerts]
    
    # Create paginated response
    response = PaginatedResponse(
        items=alert_responses,
        total=total,
        skip=search_params.skip,
        limit=search_params.limit
    )
    
    # Calculate pagination
    page = search_params.skip // search_params.limit + 1 if search_params.limit > 0 else 1
    
    # Add collection links
    collection_links = generate_collection_links(
        resource_path="/api/v1/monitoring/alert-history",
        page=page,
        limit=search_params.limit,
        total=total
    )
    
    for rel, link in collection_links.items():
        response.links[rel] = link
    
    # Add links to each alert
    for alert_response in alert_responses:
        add_resource_links(
            response=alert_response,
            resource_path="/api/v1/monitoring/alerts",
            resource_id=alert_response.id
        )
    
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
    report = await ReportingService.generate_system_performance_report(
        db, start_time, end_time, service_names, metric_types, report_format
    )
    
    # Add HATEOAS links
    response = report
    add_link(
        response=response,
        rel="self",
        href="/api/v1/monitoring/reports/system-performance",
        method="GET",
        title="Generate system performance report"
    )
    
    return response

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
    report = await ReportingService.generate_alert_report(
        db, start_time, end_time, service_names, severities, report_format
    )
    
    # Add HATEOAS links
    response = report
    add_link(
        response=response,
        rel="self",
        href="/api/v1/monitoring/reports/alerts",
        method="GET",
        title="Generate alert report"
    )
    
    return response

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
    report = await ReportingService.generate_service_availability_report(
        db, start_time, end_time, service_names, report_format
    )
    
    # Add HATEOAS links
    response = report
    add_link(
        response=response,
        rel="self",
        href="/api/v1/monitoring/reports/service-availability",
        method="GET",
        title="Generate service availability report"
    )
    
    return response

# Dashboard endpoints
@protected_router.get("/dashboards", response_model=List[DashboardConfigurationResponse])
async def get_dashboards(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get all dashboards, optionally filtered by user ID.
    """
    dashboards = await DashboardService.get_dashboards(db, user_id)
    
    # Convert to response models and add HATEOAS links
    dashboard_responses = []
    for dashboard in dashboards:
        dashboard_response = DashboardConfigurationResponse.model_validate(dashboard)
        
        # Add resource links
        add_resource_links(
            response=dashboard_response,
            resource_path="/api/v1/monitoring/dashboards",
            resource_id=dashboard.id
        )
        
        # Add specific action links
        add_link(
            response=dashboard_response,
            rel="update",
            href=f"/api/v1/monitoring/dashboards/{dashboard.id}",
            method="PUT",
            title="Update dashboard"
        )
        
        add_link(
            response=dashboard_response,
            rel="delete",
            href=f"/api/v1/monitoring/dashboards/{dashboard.id}",
            method="DELETE",
            title="Delete dashboard"
        )
        
        add_link(
            response=dashboard_response,
            rel="widgets",
            href=f"/api/v1/monitoring/dashboards/{dashboard.id}/widgets",
            method="GET",
            title="Get dashboard widgets"
        )
        
        dashboard_responses.append(dashboard_response)
    
    return dashboard_responses

@protected_router.get("/dashboards/{dashboard_id}", response_model=DashboardConfigurationResponse)
async def get_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a dashboard by ID with all its widgets.
    """
    dashboard = await DashboardService.get_dashboard(db, dashboard_id)
    
    # Convert to response model
    response = DashboardConfigurationResponse.model_validate(dashboard)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/dashboards",
        resource_id=dashboard_id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}",
        method="PUT",
        title="Update dashboard"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}",
        method="DELETE",
        title="Delete dashboard"
    )
    
    add_link(
        response=response,
        rel="add_widget",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets",
        method="POST",
        title="Add widget to dashboard"
    )
    
    # Add links to each widget
    if hasattr(response, 'widgets') and response.widgets:
        for widget in response.widgets:
            add_resource_links(
                response=widget,
                resource_path=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets",
                resource_id=widget.id
            )
            
            add_link(
                response=widget,
                rel="update",
                href=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets/{widget.id}",
                method="PUT",
                title="Update widget"
            )
            
            add_link(
                response=widget,
                rel="delete",
                href=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets/{widget.id}",
                method="DELETE",
                title="Delete widget"
            )
    
    return response

@protected_router.post("/dashboards", response_model=DashboardConfigurationResponse)
async def create_dashboard(
    dashboard_data: DashboardConfigurationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new dashboard.
    """
    new_dashboard = await DashboardService.create_dashboard(db, dashboard_data)
    
    # Convert to response model
    response = DashboardConfigurationResponse.model_validate(new_dashboard)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/dashboards",
        resource_id=new_dashboard.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/monitoring/dashboards/{new_dashboard.id}",
        method="PUT",
        title="Update dashboard"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/monitoring/dashboards/{new_dashboard.id}",
        method="DELETE",
        title="Delete dashboard"
    )
    
    add_link(
        response=response,
        rel="add_widget",
        href=f"/api/v1/monitoring/dashboards/{new_dashboard.id}/widgets",
        method="POST",
        title="Add widget to dashboard"
    )
    
    return response

@protected_router.put("/dashboards/{dashboard_id}", response_model=DashboardConfigurationResponse)
async def update_dashboard(
    dashboard_id: int,
    dashboard_data: DashboardConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing dashboard.
    """
    updated_dashboard = await DashboardService.update_dashboard(db, dashboard_id, dashboard_data)
    
    # Convert to response model
    response = DashboardConfigurationResponse.model_validate(updated_dashboard)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path="/api/v1/monitoring/dashboards",
        resource_id=dashboard_id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}",
        method="DELETE",
        title="Delete dashboard"
    )
    
    add_link(
        response=response,
        rel="add_widget",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets",
        method="POST",
        title="Add widget to dashboard"
    )
    
    return response

@protected_router.delete("/dashboards/{dashboard_id}", response_model=Dict[str, str])
async def delete_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a dashboard.
    """
    await DashboardService.delete_dashboard(db, dashboard_id)
    
    # Create a response with HATEOAS links
    response = HateoasResponse()
    
    # Add link to dashboards collection
    add_link(
        response=response,
        rel="dashboards",
        href="/api/v1/monitoring/dashboards",
        method="GET",
        title="View all dashboards"
    )
    
    return {"status": "Dashboard deleted"}

@protected_router.post("/dashboards/{dashboard_id}/widgets", response_model=DashboardWidgetResponse)
async def add_widget(
    dashboard_id: int,
    widget_data: DashboardWidgetCreate,
    db: Session = Depends(get_db)
):
    """
    Add a widget to a dashboard.
    """
    new_widget = await DashboardService.add_widget(db, dashboard_id, widget_data)
    
    # Convert to response model
    response = DashboardWidgetResponse.model_validate(new_widget)
    
    # Add HATEOAS links
    add_resource_links(
        response=response,
        resource_path=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets",
        resource_id=new_widget.id
    )
    
    # Add specific action links
    add_link(
        response=response,
        rel="update",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets/{new_widget.id}",
        method="PUT",
        title="Update widget"
    )
    
    add_link(
        response=response,
        rel="delete",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}/widgets/{new_widget.id}",
        method="DELETE",
        title="Delete widget"
    )
    
    add_link(
        response=response,
        rel="dashboard",
        href=f"/api/v1/monitoring/dashboards/{dashboard_id}",
        method="GET",
        title="View parent dashboard"
    )
    
    return response

# Include the protected and admin routes
router.include_router(protected_router)
router.include_router(admin_router)
