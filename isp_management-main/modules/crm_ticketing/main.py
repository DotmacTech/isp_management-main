"""
Main module for the CRM & Ticketing module.

This module initializes the CRM & Ticketing module and registers its API endpoints
with the main FastAPI application.
"""

from fastapi import FastAPI
from .endpoints import router as crm_router

def init_app(app: FastAPI) -> None:
    """
    Initialize the CRM & Ticketing module and register its API endpoints.
    
    Args:
        app: The FastAPI application instance
    """
    # Include the CRM & Ticketing router in the main app
    app.include_router(crm_router)
