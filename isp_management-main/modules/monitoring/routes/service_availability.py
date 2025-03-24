"""
API routes for service availability monitoring.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.orm import Session

from modules.core.database import get_db
from modules.core.auth import get_current_active_user, require_permissions
from modules.core.models import User
from modules.monitoring.models.service_availability import (
    ProtocolType, StatusType, SeverityLevel, NotificationType
)
from modules.monitoring.schemas.service_availability import (
    ServiceEndpointCreate, ServiceEndpointUpdate, ServiceEndpointInDB, ServiceEndpointResponse,
    ServiceStatusInDB, ServiceStatusResponse,
    ServiceOutageCreate, ServiceOutageUpdate, ServiceOutageInDB, ServiceOutageResponse,
    MaintenanceWindowCreate, MaintenanceWindowUpdate, MaintenanceWindowInDB, MaintenanceWindowResponse,
    ServiceEndpointListResponse, ServiceStatusListResponse, ServiceOutageListResponse, MaintenanceWindowListResponse
)
from modules.monitoring.services.availability_service import AvailabilityService
from modules.monitoring.services.availability_service_outage import OutageManagementService
from modules.monitoring.collectors.service_availability_collector import collect_specific_service_availability

router = APIRouter(
    prefix="/services",
    tags=["service-availability"],
    responses={404: {"description": "Not found"}},
)


# Service Endpoint routes
@router.post(
    "/",
    response_model=ServiceEndpointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service endpoint",
    dependencies=[Depends(require_permissions(["monitoring:write"]))],
)
async def create_service_endpoint(
    endpoint: ServiceEndpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new service endpoint to monitor.
    
    Requires monitoring:write permission.
    """
    service = AvailabilityService(db)
    
    # Check if endpoint with this ID already exists
    existing_endpoint = service.get_endpoint(endpoint.id)
    if existing_endpoint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service endpoint with ID {endpoint.id} already exists"
        )
    
    # Create endpoint
    db_endpoint = service.create_endpoint(endpoint)
    
    # Get current status (will be None for new endpoint)
    current_status = service.get_latest_status(db_endpoint.id)
    
    # Create response
    response = ServiceEndpointResponse.from_orm(db_endpoint)
    if current_status:
        response.current_status = {
            "status": current_status.status.value,
            "response_time": current_status.response_time,
            "timestamp": current_status.timestamp
        }
    
    return response


@router.get(
    "/",
    response_model=ServiceEndpointListResponse,
    summary="Get all service endpoints",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_endpoints(
    protocol: Optional[ProtocolType] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all service endpoints with optional filtering.
    
    Requires monitoring:read permission.
    """
    service = AvailabilityService(db)
    
    # Get endpoints
    endpoints, total = service.get_all_endpoints(
        protocol=protocol.value if protocol else None,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    
    # Create response items with current status
    items = []
    for endpoint in endpoints:
        # Get current status
        current_status = service.get_latest_status(endpoint.id)
        
        # Create response
        response = ServiceEndpointResponse.from_orm(endpoint)
        if current_status:
            response.current_status = {
                "status": current_status.status.value,
                "response_time": current_status.response_time,
                "timestamp": current_status.timestamp
            }
        
        items.append(response)
    
    return ServiceEndpointListResponse(
        items=items,
        total=total
    )


@router.get(
    "/{endpoint_id}",
    response_model=ServiceEndpointResponse,
    summary="Get a service endpoint",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_endpoint(
    endpoint_id: str = Path(..., description="The ID of the service endpoint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a service endpoint by ID.
    
    Requires monitoring:read permission.
    """
    service = AvailabilityService(db)
    
    # Get endpoint
    endpoint = service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service endpoint with ID {endpoint_id} not found"
        )
    
    # Get current status
    current_status = service.get_latest_status(endpoint.id)
    
    # Create response
    response = ServiceEndpointResponse.from_orm(endpoint)
    if current_status:
        response.current_status = {
            "status": current_status.status.value,
            "response_time": current_status.response_time,
            "timestamp": current_status.timestamp
        }
    
    return response


@router.put(
    "/{endpoint_id}",
    response_model=ServiceEndpointResponse,
    summary="Update a service endpoint",
    dependencies=[Depends(require_permissions(["monitoring:write"]))],
)
async def update_service_endpoint(
    endpoint_update: ServiceEndpointUpdate,
    endpoint_id: str = Path(..., description="The ID of the service endpoint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a service endpoint.
    
    Requires monitoring:write permission.
    """
    service = AvailabilityService(db)
    
    # Update endpoint
    updated_endpoint = service.update_endpoint(endpoint_id, endpoint_update)
    if not updated_endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service endpoint with ID {endpoint_id} not found"
        )
    
    # Get current status
    current_status = service.get_latest_status(updated_endpoint.id)
    
    # Create response
    response = ServiceEndpointResponse.from_orm(updated_endpoint)
    if current_status:
        response.current_status = {
            "status": current_status.status.value,
            "response_time": current_status.response_time,
            "timestamp": current_status.timestamp
        }
    
    return response


@router.delete(
    "/{endpoint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a service endpoint",
    dependencies=[Depends(require_permissions(["monitoring:write"]))],
)
async def delete_service_endpoint(
    endpoint_id: str = Path(..., description="The ID of the service endpoint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a service endpoint.
    
    Requires monitoring:write permission.
    """
    service = AvailabilityService(db)
    
    # Delete endpoint
    deleted = service.delete_endpoint(endpoint_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service endpoint with ID {endpoint_id} not found"
        )
    
    return None


@router.post(
    "/{endpoint_id}/check",
    summary="Check a service endpoint",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def check_service_endpoint(
    endpoint_id: str = Path(..., description="The ID of the service endpoint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Manually check a service endpoint.
    
    Requires monitoring:read permission.
    """
    service = AvailabilityService(db)
    
    # Check if endpoint exists
    endpoint = service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service endpoint with ID {endpoint_id} not found"
        )
    
    # Check service
    result = collect_specific_service_availability(db, endpoint_id)
    
    return result


# Service Status routes
@router.get(
    "/{endpoint_id}/status",
    response_model=ServiceStatusResponse,
    summary="Get current status of a service endpoint",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_status(
    endpoint_id: str = Path(..., description="The ID of the service endpoint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the current status of a service endpoint.
    
    Requires monitoring:read permission.
    """
    service = AvailabilityService(db)
    
    # Check if endpoint exists
    endpoint = service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service endpoint with ID {endpoint_id} not found"
        )
    
    # Get current status
    current_status = service.get_latest_status(endpoint_id)
    if not current_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No status found for service endpoint with ID {endpoint_id}"
        )
    
    # Create response
    response = ServiceStatusResponse.from_orm(current_status)
    response.endpoint = ServiceEndpointInDB.from_orm(endpoint)
    
    return response


@router.get(
    "/{endpoint_id}/history",
    response_model=ServiceStatusListResponse,
    summary="Get status history of a service endpoint",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_status_history(
    endpoint_id: str = Path(..., description="The ID of the service endpoint"),
    start_time: Optional[datetime] = Query(None, description="Start time for history"),
    end_time: Optional[datetime] = Query(None, description="End time for history"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the status history of a service endpoint.
    
    Requires monitoring:read permission.
    """
    service = AvailabilityService(db)
    
    # Check if endpoint exists
    endpoint = service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service endpoint with ID {endpoint_id} not found"
        )
    
    # Get status history
    status_history = service.get_service_status(
        endpoint_id=endpoint_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    # Create response items
    items = []
    for status in status_history:
        response = ServiceStatusResponse.from_orm(status)
        response.endpoint = ServiceEndpointInDB.from_orm(endpoint)
        items.append(response)
    
    return ServiceStatusListResponse(
        items=items,
        total=len(items)
    )


@router.get(
    "/status/summary",
    summary="Get summary of service statuses",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_status_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a summary of service statuses.
    
    Requires monitoring:read permission.
    """
    service = AvailabilityService(db)
    
    # Get status summary
    summary = service.get_status_summary()
    
    return summary


# Outage routes
outage_router = APIRouter(
    prefix="/outages",
    tags=["service-outages"],
    responses={404: {"description": "Not found"}},
)


@outage_router.get(
    "/",
    response_model=ServiceOutageListResponse,
    summary="Get all service outages",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_outages(
    endpoint_id: Optional[str] = Query(None, description="Filter by endpoint ID"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    include_resolved: bool = Query(True, description="Include resolved outages"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all service outages with optional filtering.
    
    Requires monitoring:read permission.
    """
    service = OutageManagementService(db)
    
    # Get outages
    outages, total = service.get_outages(
        endpoint_id=endpoint_id,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
        include_resolved=include_resolved,
        skip=skip,
        limit=limit
    )
    
    # Create response items
    items = []
    for outage in outages:
        response = ServiceOutageResponse.from_orm(outage)
        response.endpoint = ServiceEndpointInDB.from_orm(outage.endpoint)
        items.append(response)
    
    return ServiceOutageListResponse(
        items=items,
        total=total
    )


@outage_router.get(
    "/active",
    response_model=ServiceOutageListResponse,
    summary="Get active service outages",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_active_service_outages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all active (unresolved) service outages.
    
    Requires monitoring:read permission.
    """
    service = OutageManagementService(db)
    
    # Get active outages
    outages = service.get_active_outages()
    
    # Create response items
    items = []
    for outage in outages:
        response = ServiceOutageResponse.from_orm(outage)
        response.endpoint = ServiceEndpointInDB.from_orm(outage.endpoint)
        items.append(response)
    
    return ServiceOutageListResponse(
        items=items,
        total=len(items)
    )


@outage_router.get(
    "/{outage_id}",
    response_model=ServiceOutageResponse,
    summary="Get a service outage",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_outage(
    outage_id: str = Path(..., description="The ID of the service outage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a service outage by ID.
    
    Requires monitoring:read permission.
    """
    service = OutageManagementService(db)
    
    # Get outage
    outage = service.get_outage(outage_id)
    if not outage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service outage with ID {outage_id} not found"
        )
    
    # Create response
    response = ServiceOutageResponse.from_orm(outage)
    response.endpoint = ServiceEndpointInDB.from_orm(outage.endpoint)
    
    return response


@outage_router.post(
    "/{outage_id}/resolve",
    response_model=ServiceOutageResponse,
    summary="Resolve a service outage",
    dependencies=[Depends(require_permissions(["monitoring:write"]))],
)
async def resolve_service_outage(
    resolution_notes: Optional[str] = Body(None, description="Notes about the resolution"),
    outage_id: str = Path(..., description="The ID of the service outage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Manually resolve a service outage.
    
    Requires monitoring:write permission.
    """
    service = OutageManagementService(db)
    
    # Resolve outage
    resolved_outage = service.resolve_outage(outage_id, resolution_notes)
    if not resolved_outage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service outage with ID {outage_id} not found or already resolved"
        )
    
    # Create response
    response = ServiceOutageResponse.from_orm(resolved_outage)
    response.endpoint = ServiceEndpointInDB.from_orm(resolved_outage.endpoint)
    
    return response


@outage_router.get(
    "/summary",
    summary="Get summary of service outages",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_service_outage_summary(
    start_time: Optional[datetime] = Query(None, description="Start time for summary"),
    end_time: Optional[datetime] = Query(None, description="End time for summary"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a summary of service outages.
    
    Requires monitoring:read permission.
    """
    service = OutageManagementService(db)
    
    # Get outage summary
    summary = service.get_outage_summary(
        start_time=start_time,
        end_time=end_time
    )
    
    return summary


# Maintenance window routes
maintenance_router = APIRouter(
    prefix="/maintenance",
    tags=["service-maintenance"],
    responses={404: {"description": "Not found"}},
)


@maintenance_router.post(
    "/",
    response_model=MaintenanceWindowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new maintenance window",
    dependencies=[Depends(require_permissions(["monitoring:write"]))],
)
async def create_maintenance_window(
    window: MaintenanceWindowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new maintenance window.
    
    Requires monitoring:write permission.
    """
    service = OutageManagementService(db)
    
    # Create maintenance window
    db_window = service.create_maintenance_window(window)
    
    # Create response
    response = MaintenanceWindowResponse.from_orm(db_window)
    response.is_active = db_window.is_active()
    
    return response


@maintenance_router.get(
    "/",
    response_model=MaintenanceWindowListResponse,
    summary="Get all maintenance windows",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_maintenance_windows(
    include_past: bool = Query(False, description="Include past maintenance windows"),
    include_future: bool = Query(True, description="Include future maintenance windows"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all maintenance windows with optional filtering.
    
    Requires monitoring:read permission.
    """
    service = OutageManagementService(db)
    
    # Get maintenance windows
    windows, total = service.get_maintenance_windows(
        include_past=include_past,
        include_future=include_future,
        skip=skip,
        limit=limit
    )
    
    # Create response items
    items = []
    for window in windows:
        response = MaintenanceWindowResponse.from_orm(window)
        response.is_active = window.is_active()
        items.append(response)
    
    return MaintenanceWindowListResponse(
        items=items,
        total=total
    )


@maintenance_router.get(
    "/active",
    response_model=MaintenanceWindowListResponse,
    summary="Get active maintenance windows",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_active_maintenance_windows(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all active maintenance windows.
    
    Requires monitoring:read permission.
    """
    service = OutageManagementService(db)
    
    # Get active maintenance windows
    windows = service.get_active_maintenance_windows()
    
    # Create response items
    items = []
    for window in windows:
        response = MaintenanceWindowResponse.from_orm(window)
        response.is_active = True  # By definition, these are active
        items.append(response)
    
    return MaintenanceWindowListResponse(
        items=items,
        total=len(items)
    )


@maintenance_router.get(
    "/{window_id}",
    response_model=MaintenanceWindowResponse,
    summary="Get a maintenance window",
    dependencies=[Depends(require_permissions(["monitoring:read"]))],
)
async def get_maintenance_window(
    window_id: str = Path(..., description="The ID of the maintenance window"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a maintenance window by ID.
    
    Requires monitoring:read permission.
    """
    service = OutageManagementService(db)
    
    # Get maintenance window
    window = service.get_maintenance_window(window_id)
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance window with ID {window_id} not found"
        )
    
    # Create response
    response = MaintenanceWindowResponse.from_orm(window)
    response.is_active = window.is_active()
    
    return response


@maintenance_router.put(
    "/{window_id}",
    response_model=MaintenanceWindowResponse,
    summary="Update a maintenance window",
    dependencies=[Depends(require_permissions(["monitoring:write"]))],
)
async def update_maintenance_window(
    window_update: MaintenanceWindowUpdate,
    window_id: str = Path(..., description="The ID of the maintenance window"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a maintenance window.
    
    Requires monitoring:write permission.
    """
    service = OutageManagementService(db)
    
    # Update maintenance window
    updated_window = service.update_maintenance_window(window_id, window_update)
    if not updated_window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance window with ID {window_id} not found"
        )
    
    # Create response
    response = MaintenanceWindowResponse.from_orm(updated_window)
    response.is_active = updated_window.is_active()
    
    return response


@maintenance_router.delete(
    "/{window_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a maintenance window",
    dependencies=[Depends(require_permissions(["monitoring:write"]))],
)
async def delete_maintenance_window(
    window_id: str = Path(..., description="The ID of the maintenance window"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a maintenance window.
    
    Requires monitoring:write permission.
    """
    service = OutageManagementService(db)
    
    # Delete maintenance window
    deleted = service.delete_maintenance_window(window_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance window with ID {window_id} not found"
        )
    
    return None
