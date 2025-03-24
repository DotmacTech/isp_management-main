"""
Initialization module for the central logging and monitoring services.

This module provides functions to initialize and configure the logging and monitoring
services for the ISP Management Platform.
"""

import os
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from isp_management.backend_core.config import settings
from isp_management.backend_core.logging_service import get_logger, LoggingMiddleware
from isp_management.backend_core.monitoring_service import (
    get_monitoring_service, 
    setup_database_monitoring,
    email_alert_callback,
    slack_alert_callback
)
from isp_management.backend_core.dashboard_service import dashboard_router


def init_logging_and_monitoring(
    app: Optional[FastAPI] = None,
    db_engine: Optional[Engine] = None
) -> None:
    """
    Initialize logging and monitoring services.
    
    Args:
        app: FastAPI application instance
        db_engine: SQLAlchemy engine instance
    """
    logger = get_logger()
    monitoring_service = get_monitoring_service()
    
    # Log initialization
    logger.info("Initializing central logging and monitoring services", "system")
    
    # Register alert callbacks
    if os.getenv("ENABLE_EMAIL_ALERTS", "false").lower() == "true":
        monitoring_service.register_alert_callback(email_alert_callback)
        logger.info("Email alert callback registered", "monitoring")
    
    if os.getenv("ENABLE_SLACK_ALERTS", "false").lower() == "true":
        monitoring_service.register_alert_callback(slack_alert_callback)
        logger.info("Slack alert callback registered", "monitoring")
    
    # Set up database monitoring if engine is provided
    if db_engine:
        setup_database_monitoring(db_engine)
        logger.info("Database monitoring initialized", "monitoring")
    
    # Register FastAPI middleware and routes if app is provided
    if app:
        # Add logging middleware
        app.add_middleware(LoggingMiddleware)
        logger.info("Logging middleware registered with FastAPI", "monitoring")
        
        # Include dashboard router
        app.include_router(dashboard_router, prefix="/api")
        logger.info("Dashboard router registered with FastAPI", "monitoring")
    
    # Start monitoring service
    monitoring_service.start(app)
    logger.info("Monitoring service started", "monitoring")
    
    logger.info("Logging and monitoring services initialized successfully", "system")


def shutdown_logging_and_monitoring() -> None:
    """Shutdown logging and monitoring services."""
    monitoring_service = get_monitoring_service()
    logger = get_logger()
    
    # Stop monitoring service
    monitoring_service.stop()
    logger.info("Monitoring service stopped", "monitoring")
    
    logger.info("Logging and monitoring services shutdown successfully", "system")
