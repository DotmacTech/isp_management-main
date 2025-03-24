"""
API endpoints for the Field Services Module.

This module provides endpoints for job scheduling, technician management,
and field service operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth import get_current_user
from backend_core.utils.hateoas import add_resource_links, add_collection_links

from .schemas import (
    JobCreate, JobUpdate, JobResponse, JobList,
    TechnicianCreate, TechnicianUpdate, TechnicianResponse, TechnicianList,
    RouteOptimizationRequest, RouteOptimizationResponse,
    InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse, InventoryItemList
)
from .services.job_service import JobService
from .services.technician_service import TechnicianService
from .services.route_service import RouteService
from .services.inventory_service import InventoryService

router = APIRouter()

# Job endpoints
@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new job assignment."""
    job_service = JobService(db)
    job = job_service.create_job(job_data, current_user.id)
    
    response = job.dict()
    add_resource_links(response, "field-services.jobs", job.id)
    
    return response

@router.get("/jobs", response_model=JobList)
def list_jobs(
    status: Optional[str] = Query(None, description="Filter jobs by status"),
    technician_id: Optional[int] = Query(None, description="Filter jobs by technician"),
    customer_id: Optional[int] = Query(None, description="Filter jobs by customer"),
    priority: Optional[str] = Query(None, description="Filter jobs by priority"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all jobs with optional filtering."""
    job_service = JobService(db)
    jobs, total = job_service.get_jobs(
        status=status,
        technician_id=technician_id,
        customer_id=customer_id,
        priority=priority,
        page=page,
        page_size=page_size
    )
    
    response = {
        "items": jobs,
        "total": total,
        "page": page,
        "page_size": page_size
    }
    
    add_collection_links(
        response, 
        "field-services.jobs", 
        page=page, 
        page_size=page_size, 
        total=total
    )
    
    return response

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific job by ID."""
    job_service = JobService(db)
    job = job_service.get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    response = job.dict()
    add_resource_links(response, "field-services.jobs", job_id)
    
    return response

@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an existing job."""
    job_service = JobService(db)
    job = job_service.update_job(job_id, job_data, current_user.id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    response = job.dict()
    add_resource_links(response, "field-services.jobs", job_id)
    
    return response

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a job."""
    job_service = JobService(db)
    success = job_service.delete_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return None

# Technician endpoints
@router.post("/technicians", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED)
def create_technician(
    technician_data: TechnicianCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new technician profile."""
    technician_service = TechnicianService(db)
    technician = technician_service.create_technician(technician_data)
    
    response = technician.dict()
    add_resource_links(response, "field-services.technicians", technician.id)
    
    return response

@router.get("/technicians", response_model=TechnicianList)
def list_technicians(
    status: Optional[str] = Query(None, description="Filter technicians by status"),
    skill: Optional[str] = Query(None, description="Filter technicians by skill"),
    region: Optional[str] = Query(None, description="Filter technicians by region"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all technicians with optional filtering."""
    technician_service = TechnicianService(db)
    technicians, total = technician_service.get_technicians(
        status=status,
        skill=skill,
        region=region,
        page=page,
        page_size=page_size
    )
    
    response = {
        "items": technicians,
        "total": total,
        "page": page,
        "page_size": page_size
    }
    
    add_collection_links(
        response, 
        "field-services.technicians", 
        page=page, 
        page_size=page_size, 
        total=total
    )
    
    return response

@router.get("/technicians/{technician_id}", response_model=TechnicianResponse)
def get_technician(
    technician_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific technician by ID."""
    technician_service = TechnicianService(db)
    technician = technician_service.get_technician_by_id(technician_id)
    
    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found"
        )
    
    response = technician.dict()
    add_resource_links(response, "field-services.technicians", technician_id)
    
    return response

@router.put("/technicians/{technician_id}", response_model=TechnicianResponse)
def update_technician(
    technician_id: int,
    technician_data: TechnicianUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an existing technician profile."""
    technician_service = TechnicianService(db)
    technician = technician_service.update_technician(technician_id, technician_data)
    
    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found"
        )
    
    response = technician.dict()
    add_resource_links(response, "field-services.technicians", technician_id)
    
    return response

# Route optimization endpoints
@router.post("/routes/optimize", response_model=RouteOptimizationResponse)
def optimize_routes(
    optimization_request: RouteOptimizationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Optimize routes for technicians based on job locations and priorities."""
    route_service = RouteService(db)
    optimization_result = route_service.optimize_routes(optimization_request)
    
    return optimization_result

# Inventory management endpoints
@router.post("/inventory", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    item_data: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new inventory item."""
    inventory_service = InventoryService(db)
    item = inventory_service.create_inventory_item(item_data)
    
    response = item.dict()
    add_resource_links(response, "field-services.inventory", item.id)
    
    return response

@router.get("/inventory", response_model=InventoryItemList)
def list_inventory_items(
    category: Optional[str] = Query(None, description="Filter items by category"),
    location: Optional[str] = Query(None, description="Filter items by location"),
    status: Optional[str] = Query(None, description="Filter items by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all inventory items with optional filtering."""
    inventory_service = InventoryService(db)
    items, total = inventory_service.get_inventory_items(
        category=category,
        location=location,
        status=status,
        page=page,
        page_size=page_size
    )
    
    response = {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }
    
    add_collection_links(
        response, 
        "field-services.inventory", 
        page=page, 
        page_size=page_size, 
        total=total
    )
    
    return response

@router.get("/inventory/{item_id}", response_model=InventoryItemResponse)
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific inventory item by ID."""
    inventory_service = InventoryService(db)
    item = inventory_service.get_inventory_item_by_id(item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    response = item.dict()
    add_resource_links(response, "field-services.inventory", item_id)
    
    return response

@router.put("/inventory/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(
    item_id: int,
    item_data: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an existing inventory item."""
    inventory_service = InventoryService(db)
    item = inventory_service.update_inventory_item(item_id, item_data)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    response = item.dict()
    add_resource_links(response, "field-services.inventory", item_id)
    
    return response

@router.delete("/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete an inventory item."""
    inventory_service = InventoryService(db)
    success = inventory_service.delete_inventory_item(item_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    return None

# SLA management endpoints
@router.get("/sla/performance")
def get_sla_performance(
    start_date: Optional[str] = Query(None, description="Start date for SLA report"),
    end_date: Optional[str] = Query(None, description="End date for SLA report"),
    technician_id: Optional[int] = Query(None, description="Filter by technician"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get SLA performance metrics for field services."""
    job_service = JobService(db)
    sla_metrics = job_service.get_sla_performance(
        start_date=start_date,
        end_date=end_date,
        technician_id=technician_id,
        job_type=job_type
    )
    
    return sla_metrics
