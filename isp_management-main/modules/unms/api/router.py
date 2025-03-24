"""
UNMS API router and endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional

from backend_core.auth import get_current_user
from backend_core.database import get_db
from ..services import UNMSService

router = APIRouter(
    prefix="/unms",
    tags=["unms"],
    responses={404: {"description": "Not found"}}
)


@router.get("/devices")
async def list_devices(
    site_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(get_current_user),
    db = Depends(get_db),
    unms_service = Depends(UNMSService)
):
    """
    Get a list of devices from UNMS.
    
    Args:
        site_id: Filter devices by site ID
        status: Filter devices by status
        limit: Maximum number of results to return
        offset: Result offset for pagination
        
    Returns:
        List of devices
    """
    return await unms_service.get_devices(
        site_id=site_id,
        status=status,
        limit=limit,
        offset=offset
    )


@router.get("/sites")
async def list_sites(
    parent_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(get_current_user),
    db = Depends(get_db),
    unms_service = Depends(UNMSService)
):
    """
    Get a list of sites from UNMS.
    
    Args:
        parent_id: Filter sites by parent site ID
        limit: Maximum number of results to return
        offset: Result offset for pagination
        
    Returns:
        List of sites
    """
    return await unms_service.get_sites(
        parent_id=parent_id,
        limit=limit,
        offset=offset
    )


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint for the UNMS integration.
    """
    return {"status": "ok", "module": "unms"}
