"""
SLA endpoints for the CRM & Ticketing module.

This module provides API endpoints for managing Service Level Agreements (SLAs),
including creation, updates, and SLA metrics tracking.
"""

from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth import get_current_user, require_permissions
from ..services.sla_service import SLAService
from ..schemas.sla import (
    SLA, SLACreate, SLAUpdate, SLAMetric, SLAMetricCreate, SLAMetricUpdate,
    SLAPerformanceReport
)
from ..schemas.common import TicketPriority

router = APIRouter(
    prefix="/sla",
    tags=["SLA Management"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[SLA])
async def list_slas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List all SLAs.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of SLA objects
    """
    require_permissions(current_user, ["crm.view_sla"])
    sla_service = SLAService(db)
    return sla_service.list_slas(skip=skip, limit=limit)


@router.get("/{sla_id}", response_model=SLA)
async def get_sla(
    sla_id: int = Path(..., description="The ID of the SLA to retrieve"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get an SLA by ID.
    
    Args:
        sla_id: The ID of the SLA to retrieve
        
    Returns:
        The SLA object
    """
    require_permissions(current_user, ["crm.view_sla"])
    sla_service = SLAService(db)
    return sla_service.get_sla(sla_id)


@router.post("/", response_model=SLA, status_code=status.HTTP_201_CREATED)
async def create_sla(
    sla_data: SLACreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new SLA.
    
    Args:
        sla_data: Data for the new SLA
        
    Returns:
        The created SLA object
    """
    require_permissions(current_user, ["crm.add_sla"])
    sla_service = SLAService(db)
    return sla_service.create_sla(sla_data, current_user.id)


@router.put("/{sla_id}", response_model=SLA)
async def update_sla(
    sla_data: SLAUpdate,
    sla_id: int = Path(..., description="The ID of the SLA to update"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update an existing SLA.
    
    Args:
        sla_id: The ID of the SLA to update
        sla_data: New data for the SLA
        
    Returns:
        The updated SLA object
    """
    require_permissions(current_user, ["crm.change_sla"])
    sla_service = SLAService(db)
    return sla_service.update_sla(sla_id, sla_data, current_user.id)


@router.delete("/{sla_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sla(
    sla_id: int = Path(..., description="The ID of the SLA to delete"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete an SLA.
    
    Args:
        sla_id: The ID of the SLA to delete
    """
    require_permissions(current_user, ["crm.delete_sla"])
    sla_service = SLAService(db)
    sla_service.delete_sla(sla_id, current_user.id)
    return None


@router.get("/metrics/", response_model=List[SLAMetric])
async def list_sla_metrics(
    sla_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List SLA metrics, optionally filtered by SLA ID.
    
    Args:
        sla_id: Optional SLA ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of SLA metric objects
    """
    require_permissions(current_user, ["crm.view_sla"])
    sla_service = SLAService(db)
    return sla_service.list_sla_metrics(sla_id=sla_id, skip=skip, limit=limit)


@router.get("/metrics/{metric_id}", response_model=SLAMetric)
async def get_sla_metric(
    metric_id: int = Path(..., description="The ID of the SLA metric to retrieve"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get an SLA metric by ID.
    
    Args:
        metric_id: The ID of the SLA metric to retrieve
        
    Returns:
        The SLA metric object
    """
    require_permissions(current_user, ["crm.view_sla"])
    sla_service = SLAService(db)
    return sla_service.get_sla_metric(metric_id)


@router.post("/metrics/", response_model=SLAMetric, status_code=status.HTTP_201_CREATED)
async def create_sla_metric(
    metric_data: SLAMetricCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new SLA metric.
    
    Args:
        metric_data: Data for the new SLA metric
        
    Returns:
        The created SLA metric object
    """
    require_permissions(current_user, ["crm.add_sla"])
    sla_service = SLAService(db)
    return sla_service.create_sla_metric(metric_data, current_user.id)


@router.put("/metrics/{metric_id}", response_model=SLAMetric)
async def update_sla_metric(
    metric_data: SLAMetricUpdate,
    metric_id: int = Path(..., description="The ID of the SLA metric to update"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update an existing SLA metric.
    
    Args:
        metric_id: The ID of the SLA metric to update
        metric_data: New data for the SLA metric
        
    Returns:
        The updated SLA metric object
    """
    require_permissions(current_user, ["crm.change_sla"])
    sla_service = SLAService(db)
    return sla_service.update_sla_metric(metric_id, metric_data, current_user.id)


@router.delete("/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sla_metric(
    metric_id: int = Path(..., description="The ID of the SLA metric to delete"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete an SLA metric.
    
    Args:
        metric_id: The ID of the SLA metric to delete
    """
    require_permissions(current_user, ["crm.delete_sla"])
    sla_service = SLAService(db)
    sla_service.delete_sla_metric(metric_id, current_user.id)
    return None


@router.get("/performance/", response_model=SLAPerformanceReport)
async def get_sla_performance(
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    sla_id: Optional[int] = Query(None, description="Optional SLA ID to filter by"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Calculate SLA performance metrics for a given time period.
    
    Args:
        start_date: The start date for the calculation
        end_date: The end date for the calculation
        sla_id: Optional SLA ID to filter by
        
    Returns:
        A dictionary containing SLA performance metrics
    """
    require_permissions(current_user, ["crm.view_sla"])
    sla_service = SLAService(db)
    
    # Convert dates to datetimes
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    return sla_service.calculate_sla_performance(
        start_date=start_datetime,
        end_date=end_datetime,
        sla_id=sla_id
    )
