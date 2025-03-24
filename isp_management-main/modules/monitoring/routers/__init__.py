"""
Routers for the ISP Management Platform Monitoring Module

This module imports all routers for the monitoring module to make them available
through a single import statement.
"""

from fastapi import APIRouter
from modules.monitoring.routers.network_nodes import router as network_nodes_router

# Create a main router for the monitoring module
router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
)

# Include all sub-routers
router.include_router(network_nodes_router)

__all__ = ['router']
