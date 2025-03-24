"""
Mock implementation of the monitoring routes module for testing.
This avoids the dependency on isp_management.backend_core.auth.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock

# Create a mock router
router = APIRouter()

# Mock the endpoints
@router.get("/services/")
def get_services():
    """Mock endpoint for getting services."""
    return {"services": []}

@router.get("/services/{endpoint_id}")
def get_service(endpoint_id: str):
    """Mock endpoint for getting a service."""
    return {"id": endpoint_id, "name": "Mock Service"}

@router.post("/services/")
def create_service():
    """Mock endpoint for creating a service."""
    return {"id": "new-service", "name": "New Service"}

@router.put("/services/{endpoint_id}")
def update_service(endpoint_id: str):
    """Mock endpoint for updating a service."""
    return {"id": endpoint_id, "name": "Updated Service"}

@router.delete("/services/{endpoint_id}")
def delete_service(endpoint_id: str):
    """Mock endpoint for deleting a service."""
    return {"success": True}

@router.get("/services/{endpoint_id}/status")
def get_service_status(endpoint_id: str):
    """Mock endpoint for getting service status."""
    return {"status": "UP", "response_time": 0.1}

@router.get("/services/{endpoint_id}/history")
def get_service_history(endpoint_id: str):
    """Mock endpoint for getting service history."""
    return {"history": []}

@router.get("/outages/")
def get_outages():
    """Mock endpoint for getting outages."""
    return {"outages": []}

@router.get("/maintenance/")
def get_maintenance_windows():
    """Mock endpoint for getting maintenance windows."""
    return {"maintenance_windows": []}

@router.post("/maintenance/")
def create_maintenance_window():
    """Mock endpoint for creating a maintenance window."""
    return {"id": "new-window", "name": "New Maintenance Window"}
