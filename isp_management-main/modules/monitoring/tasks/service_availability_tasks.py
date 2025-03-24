"""
Celery tasks for service availability monitoring.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from celery import shared_task
from sqlalchemy.orm import Session

from modules.core.database import SessionLocal
from modules.monitoring.collectors.service_availability_collector import (
    collect_service_availability,
    collect_specific_service_availability,
    sync_service_statuses_to_elasticsearch,
    cleanup_old_service_statuses
)
from modules.monitoring.services.availability_service_outage import OutageManagementService

# Configure logging
logger = logging.getLogger(__name__)

# Get environment variables
SERVICE_CHECK_INTERVAL = int(os.getenv("SERVICE_CHECK_INTERVAL", "60"))  # seconds
ELASTICSEARCH_SYNC_INTERVAL = int(os.getenv("ELASTICSEARCH_SYNC_INTERVAL", "300"))  # seconds
CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", "86400"))  # seconds (1 day)
CLEANUP_RETENTION_DAYS = int(os.getenv("CLEANUP_RETENTION_DAYS", "30"))  # days


@shared_task(name="monitoring.check_all_services")
def check_all_services() -> Dict[str, Any]:
    """
    Check availability for all active service endpoints.
    
    This task is scheduled to run at regular intervals defined by SERVICE_CHECK_INTERVAL.
    """
    logger.info("Starting scheduled check for all services")
    
    db = SessionLocal()
    try:
        # Collect service availability data
        results = collect_service_availability(db)
        
        # Process any potential outages
        outage_service = OutageManagementService(db)
        outage_service.process_potential_outages()
        
        # Check for resolved outages
        outage_service.check_for_resolved_outages()
        
        logger.info(f"Completed scheduled check for all services: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in check_all_services task: {str(e)}")
        raise
    
    finally:
        db.close()


@shared_task(name="monitoring.check_specific_service")
def check_specific_service(endpoint_id: str) -> Dict[str, Any]:
    """
    Check availability for a specific service endpoint.
    
    This task can be triggered manually or by other tasks.
    """
    logger.info(f"Starting check for service {endpoint_id}")
    
    db = SessionLocal()
    try:
        # Collect service availability data
        results = collect_specific_service_availability(db, endpoint_id)
        
        # Process any potential outages
        outage_service = OutageManagementService(db)
        outage_service.process_potential_outages(endpoint_id=endpoint_id)
        
        # Check for resolved outages
        outage_service.check_for_resolved_outages(endpoint_id=endpoint_id)
        
        logger.info(f"Completed check for service {endpoint_id}: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in check_specific_service task: {str(e)}")
        raise
    
    finally:
        db.close()


@shared_task(name="monitoring.sync_service_statuses")
def sync_service_statuses(limit: int = 1000) -> Dict[str, Any]:
    """
    Sync unsynced service statuses to Elasticsearch.
    
    This task is scheduled to run at regular intervals defined by ELASTICSEARCH_SYNC_INTERVAL.
    """
    logger.info("Starting sync of service statuses to Elasticsearch")
    
    db = SessionLocal()
    try:
        # Sync service statuses
        results = sync_service_statuses_to_elasticsearch(db, limit)
        
        logger.info(f"Completed sync of service statuses to Elasticsearch: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in sync_service_statuses task: {str(e)}")
        raise
    
    finally:
        db.close()


@shared_task(name="monitoring.cleanup_old_data")
def cleanup_old_data(days_to_keep: int = CLEANUP_RETENTION_DAYS) -> Dict[str, Any]:
    """
    Clean up old service statuses from the database.
    
    This task is scheduled to run at regular intervals defined by CLEANUP_INTERVAL.
    """
    logger.info(f"Starting cleanup of old service statuses (keeping {days_to_keep} days)")
    
    db = SessionLocal()
    try:
        # Clean up old service statuses
        results = cleanup_old_service_statuses(db, days_to_keep)
        
        logger.info(f"Completed cleanup of old service statuses: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in cleanup_old_data task: {str(e)}")
        raise
    
    finally:
        db.close()


@shared_task(name="monitoring.verify_outages")
def verify_outages() -> Dict[str, Any]:
    """
    Verify potential outages and create alerts if necessary.
    
    This task is scheduled to run at regular intervals.
    """
    logger.info("Starting verification of potential outages")
    
    db = SessionLocal()
    try:
        # Verify outages
        outage_service = OutageManagementService(db)
        results = outage_service.verify_potential_outages()
        
        logger.info(f"Completed verification of potential outages: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in verify_outages task: {str(e)}")
        raise
    
    finally:
        db.close()


@shared_task(name="monitoring.update_maintenance_windows")
def update_maintenance_windows() -> Dict[str, Any]:
    """
    Update maintenance window statuses.
    
    This task is scheduled to run at regular intervals.
    """
    logger.info("Starting update of maintenance window statuses")
    
    db = SessionLocal()
    try:
        # Update maintenance windows
        outage_service = OutageManagementService(db)
        active_windows = outage_service.get_active_maintenance_windows()
        
        results = {
            "active_windows": len(active_windows),
            "updated": 0
        }
        
        # Check for windows that should be expired
        now = datetime.utcnow()
        for window in active_windows:
            if window.end_time < now:
                # This window should be expired, but is still marked as active
                # This can happen if the task hasn't run in a while
                logger.info(f"Maintenance window {window.id} has expired, updating status")
                results["updated"] += 1
        
        logger.info(f"Completed update of maintenance window statuses: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in update_maintenance_windows task: {str(e)}")
        raise
    
    finally:
        db.close()


def register_tasks(app):
    """
    Register service availability monitoring tasks with the Celery app.
    
    This function should be called from the main Celery app configuration.
    """
    # Schedule tasks
    app.conf.beat_schedule.update({
        'check-all-services': {
            'task': 'monitoring.check_all_services',
            'schedule': timedelta(seconds=SERVICE_CHECK_INTERVAL),
        },
        'sync-service-statuses': {
            'task': 'monitoring.sync_service_statuses',
            'schedule': timedelta(seconds=ELASTICSEARCH_SYNC_INTERVAL),
        },
        'cleanup-old-data': {
            'task': 'monitoring.cleanup_old_data',
            'schedule': timedelta(seconds=CLEANUP_INTERVAL),
        },
        'verify-outages': {
            'task': 'monitoring.verify_outages',
            'schedule': timedelta(seconds=SERVICE_CHECK_INTERVAL * 2),
        },
        'update-maintenance-windows': {
            'task': 'monitoring.update_maintenance_windows',
            'schedule': timedelta(minutes=5),
        },
    })
    
    logger.info("Registered service availability monitoring tasks with Celery")
