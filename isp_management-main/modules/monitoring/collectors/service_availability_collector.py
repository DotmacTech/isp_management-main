"""
Collector for service availability monitoring.
"""

import os
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from modules.monitoring.models.service_availability import (
    ServiceEndpoint, ServiceStatus, StatusType
)
from modules.monitoring.services.availability_service import AvailabilityService
from modules.monitoring.services.availability_service_outage import OutageManagementService
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)

# Get environment variables
SERVICE_CHECK_INTERVAL = int(os.getenv("SERVICE_CHECK_INTERVAL", "60"))  # seconds


class ServiceAvailabilityCollector:
    """Collector for service availability monitoring."""

    def __init__(self, db: Session):
        """Initialize the collector with database session."""
        self.db = db
        self.availability_service = AvailabilityService(db)
        self.outage_service = OutageManagementService(db)
        self.es_client = ElasticsearchClient()

    def collect_all_services(self) -> Dict[str, Any]:
        """Collect availability data for all active services."""
        logger.info("Starting service availability collection for all services")
        start_time = time.time()
        
        # Get all active service endpoints
        endpoints, _ = self.availability_service.get_all_endpoints(is_active=True)
        
        results = {
            "total": len(endpoints),
            "successful": 0,
            "failed": 0,
            "in_maintenance": 0,
            "by_status": {status.value: 0 for status in StatusType}
        }
        
        # Check each service
        for endpoint in endpoints:
            try:
                # Check if service is in maintenance
                if self.outage_service.is_in_maintenance(endpoint.id):
                    logger.info(f"Service {endpoint.id} is in maintenance, skipping check")
                    results["in_maintenance"] += 1
                    continue
                
                # Check service
                status = self.availability_service.check_service(endpoint.id)
                
                # Update results
                results["successful"] += 1
                results["by_status"][status.status.value] += 1
                
                logger.info(f"Checked service {endpoint.id}: {status.status.value}")
                
            except Exception as e:
                logger.error(f"Error checking service {endpoint.id}: {str(e)}")
                results["failed"] += 1
        
        # Calculate execution time
        execution_time = time.time() - start_time
        results["execution_time"] = execution_time
        
        logger.info(f"Completed service availability collection in {execution_time:.2f} seconds")
        logger.info(f"Results: {results}")
        
        return results

    def collect_service(self, endpoint_id: str) -> Dict[str, Any]:
        """Collect availability data for a specific service."""
        logger.info(f"Starting service availability collection for service {endpoint_id}")
        start_time = time.time()
        
        results = {
            "endpoint_id": endpoint_id,
            "status": None,
            "response_time": None,
            "execution_time": None,
            "success": False,
            "error": None
        }
        
        try:
            # Check service
            status = self.availability_service.check_service(endpoint_id)
            
            # Update results
            results["status"] = status.status.value
            results["response_time"] = status.response_time
            results["success"] = True
            
            logger.info(f"Checked service {endpoint_id}: {status.status.value}")
            
        except Exception as e:
            logger.error(f"Error checking service {endpoint_id}: {str(e)}")
            results["error"] = str(e)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        results["execution_time"] = execution_time
        
        return results

    def sync_unsynced_statuses(self, limit: int = 100) -> Dict[str, Any]:
        """Sync unsynced service statuses to Elasticsearch."""
        logger.info("Syncing unsynced service statuses to Elasticsearch")
        
        # Get unsynced statuses
        unsynced_statuses = (
            self.db.query(ServiceStatus)
            .filter(ServiceStatus.elasticsearch_synced == False)
            .limit(limit)
            .all()
        )
        
        results = {
            "total": len(unsynced_statuses),
            "successful": 0,
            "failed": 0
        }
        
        if not unsynced_statuses:
            logger.info("No unsynced service statuses found")
            return results
        
        logger.info(f"Found {len(unsynced_statuses)} unsynced service statuses")
        
        # Sync each status
        for status in unsynced_statuses:
            try:
                # Get index name
                index_name = f"isp-service-status-{status.timestamp.strftime('%Y.%m.%d')}"
                
                # Convert to dict
                doc = status.to_dict()
                
                # Index in Elasticsearch
                self.es_client.index(index=index_name, body=doc)
                
                # Mark as synced
                status.elasticsearch_synced = True
                
                results["successful"] += 1
                
            except Exception as e:
                logger.error(f"Error syncing service status {status.id} to Elasticsearch: {str(e)}")
                results["failed"] += 1
        
        # Commit changes
        self.db.commit()
        
        logger.info(f"Synced {results['successful']} service statuses to Elasticsearch")
        
        return results

    def cleanup_old_statuses(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Clean up old service statuses from the database."""
        logger.info(f"Cleaning up service statuses older than {days_to_keep} days")
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count statuses to delete
        count_to_delete = (
            self.db.query(ServiceStatus)
            .filter(ServiceStatus.timestamp < cutoff_date)
            .count()
        )
        
        if count_to_delete == 0:
            logger.info("No old service statuses to clean up")
            return {"deleted": 0}
        
        logger.info(f"Found {count_to_delete} service statuses to clean up")
        
        # Delete old statuses
        self.db.query(ServiceStatus).filter(
            ServiceStatus.timestamp < cutoff_date
        ).delete(synchronize_session=False)
        
        # Commit changes
        self.db.commit()
        
        logger.info(f"Cleaned up {count_to_delete} old service statuses")
        
        return {"deleted": count_to_delete}


def collect_service_availability(db: Session) -> Dict[str, Any]:
    """Collect service availability data for all services."""
    collector = ServiceAvailabilityCollector(db)
    return collector.collect_all_services()


def collect_specific_service_availability(db: Session, endpoint_id: str) -> Dict[str, Any]:
    """Collect service availability data for a specific service."""
    collector = ServiceAvailabilityCollector(db)
    return collector.collect_service(endpoint_id)


def sync_service_statuses_to_elasticsearch(db: Session, limit: int = 100) -> Dict[str, Any]:
    """Sync unsynced service statuses to Elasticsearch."""
    collector = ServiceAvailabilityCollector(db)
    return collector.sync_unsynced_statuses(limit)


def cleanup_old_service_statuses(db: Session, days_to_keep: int = 30) -> Dict[str, Any]:
    """Clean up old service statuses from the database."""
    collector = ServiceAvailabilityCollector(db)
    return collector.cleanup_old_statuses(days_to_keep)
