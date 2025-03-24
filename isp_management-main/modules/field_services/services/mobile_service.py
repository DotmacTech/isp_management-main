"""
Mobile Service for the Field Services Module.

This service handles mobile app integration, including data synchronization,
offline mode support, and mobile-specific functionality for field technicians.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload

from ..models import (
    Job, JobStatusEnum, Technician, TechnicianStatusEnum,
    JobHistory, TechnicianInventory, InventoryTransaction,
    InventoryTransactionTypeEnum
)
from ..schemas import (
    MobileSyncRequest, MobileSyncResponse, MobileJobUpdate,
    MobileLocationUpdate, MobileInventoryUsage
)
from backend_core.utils.hateoas import add_resource_links


class MobileService:
    """Service for handling mobile app integration."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_technician_data(
        self, 
        technician_id: int, 
        sync_request: MobileSyncRequest
    ) -> MobileSyncResponse:
        """
        Synchronize data between mobile app and backend.
        
        This method handles bidirectional synchronization:
        1. Processes updates from the mobile app (jobs, location, inventory)
        2. Sends updated data from the backend to the mobile app
        """
        # Get technician
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            raise ValueError(f"Technician with ID {technician_id} not found")
        
        # Process updates from mobile app
        updated_jobs = []
        if sync_request.job_updates:
            updated_jobs = self._process_job_updates(technician_id, sync_request.job_updates)
        
        # Update technician location if provided
        if sync_request.location_update:
            self._update_technician_location(technician_id, sync_request.location_update)
        
        # Process inventory usage if provided
        if sync_request.inventory_usage:
            self._process_inventory_usage(technician_id, sync_request.inventory_usage)
        
        # Get data to send to mobile app
        jobs_data = self._get_technician_jobs(technician_id, sync_request.last_sync_time)
        notifications_data = self._get_technician_notifications(technician_id, sync_request.last_sync_time)
        inventory_data = self._get_technician_inventory(technician_id, sync_request.last_sync_time)
        
        # Generate sync hash for data verification
        sync_hash = self._generate_sync_hash(jobs_data, notifications_data, inventory_data)
        
        # Create response
        response = MobileSyncResponse(
            technician_id=technician_id,
            sync_time=datetime.utcnow(),
            sync_hash=sync_hash,
            jobs=jobs_data,
            notifications=notifications_data,
            inventory=inventory_data,
            updated_job_ids=[job.id for job in updated_jobs],
            links=[
                {"rel": "self", "href": f"/api/field-services/mobile/sync/{technician_id}"},
                {"rel": "technician", "href": f"/api/field-services/technicians/{technician_id}"}
            ]
        )
        
        return response
    
    def _process_job_updates(self, technician_id: int, job_updates: List[MobileJobUpdate]) -> List[Job]:
        """Process job updates from mobile app."""
        updated_jobs = []
        
        for update in job_updates:
            # Get job
            job = self.db.query(Job).filter(
                Job.id == update.job_id,
                Job.technician_id == technician_id  # Ensure job belongs to this technician
            ).first()
            
            if not job:
                continue
            
            # Store previous status for history tracking
            previous_status = job.status
            
            # Update job status if provided
            if update.status:
                job.status = JobStatusEnum[update.status.upper()]
                
                # Update actual start/end times based on status changes
                if job.status == JobStatusEnum.IN_PROGRESS and not job.actual_start_time:
                    job.actual_start_time = update.timestamp or datetime.utcnow()
                
                if job.status == JobStatusEnum.COMPLETED and not job.actual_end_time:
                    job.actual_end_time = update.timestamp or datetime.utcnow()
            
            # Update notes if provided
            if update.notes:
                if job.notes:
                    job.notes += f"\n\n{update.timestamp.strftime('%Y-%m-%d %H:%M:%S')} (Mobile):\n{update.notes}"
                else:
                    job.notes = f"{update.timestamp.strftime('%Y-%m-%d %H:%M:%S')} (Mobile):\n{update.notes}"
            
            # Update actual start/end times if provided
            if update.actual_start_time:
                job.actual_start_time = update.actual_start_time
            
            if update.actual_end_time:
                job.actual_end_time = update.actual_end_time
            
            # Update job
            job.updated_by = technician_id
            
            # Create job history entry if status changed
            if job.status != previous_status:
                job_history = JobHistory(
                    job_id=job.id,
                    status_from=previous_status,
                    status_to=job.status,
                    notes=f"Status updated from mobile app: {previous_status.value} -> {job.status.value}",
                    changed_by=technician_id
                )
                self.db.add(job_history)
            
            updated_jobs.append(job)
        
        # Commit changes
        if updated_jobs:
            self.db.commit()
            # Refresh jobs to get updated values
            for job in updated_jobs:
                self.db.refresh(job)
        
        return updated_jobs
    
    def _update_technician_location(self, technician_id: int, location_update: MobileLocationUpdate) -> None:
        """Update technician location from mobile app."""
        # Get technician
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            return
        
        # Update location
        technician.current_location_lat = location_update.latitude
        technician.current_location_lon = location_update.longitude
        technician.last_location_update = location_update.timestamp or datetime.utcnow()
        
        # Commit changes
        self.db.commit()
    
    def _process_inventory_usage(self, technician_id: int, inventory_usage: List[MobileInventoryUsage]) -> None:
        """Process inventory usage from mobile app."""
        for usage in inventory_usage:
            # Check if technician has this inventory
            tech_inventory = self.db.query(TechnicianInventory).filter(
                TechnicianInventory.technician_id == technician_id,
                TechnicianInventory.inventory_id == usage.inventory_id
            ).first()
            
            if not tech_inventory or tech_inventory.quantity < usage.quantity:
                continue  # Skip if technician doesn't have enough inventory
            
            # Update technician inventory
            tech_inventory.quantity -= usage.quantity
            
            # Delete record if quantity is zero
            if tech_inventory.quantity <= 0:
                self.db.delete(tech_inventory)
            
            # Create inventory transaction
            transaction = InventoryTransaction(
                inventory_id=usage.inventory_id,
                transaction_type=InventoryTransactionTypeEnum.USAGE,
                quantity=-usage.quantity,
                notes=f"Inventory used by technician ID {technician_id} for job ID {usage.job_id}" if usage.job_id else f"Inventory used by technician ID {technician_id}",
                technician_id=technician_id,
                job_id=usage.job_id,
                created_by=technician_id
            )
            self.db.add(transaction)
        
        # Commit changes
        if inventory_usage:
            self.db.commit()
    
    def _get_technician_jobs(self, technician_id: int, last_sync_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get jobs assigned to a technician for mobile sync."""
        # Base query for technician's jobs
        query = self.db.query(Job).filter(
            Job.technician_id == technician_id
        ).options(
            joinedload(Job.customer)
        )
        
        # Filter by status (only active jobs)
        query = query.filter(
            Job.status.in_([
                JobStatusEnum.ASSIGNED,
                JobStatusEnum.IN_PROGRESS,
                JobStatusEnum.PENDING
            ])
        )
        
        # Filter by last sync time if provided
        if last_sync_time:
            query = query.filter(
                or_(
                    Job.created_at > last_sync_time,
                    Job.updated_at > last_sync_time
                )
            )
        
        # Execute query
        jobs = query.all()
        
        # Convert to dictionary format for mobile app
        jobs_data = []
        for job in jobs:
            # Calculate SLA status
            sla_status = "no_sla"
            if job.sla_deadline:
                now = datetime.utcnow()
                
                if job.status == JobStatusEnum.COMPLETED:
                    if job.actual_end_time <= job.sla_deadline:
                        sla_status = "met"
                    else:
                        sla_status = "breached"
                elif job.status == JobStatusEnum.CANCELLED:
                    sla_status = "cancelled"
                else:
                    # For jobs not completed
                    time_remaining = (job.sla_deadline - now).total_seconds() / 60  # minutes
                    
                    if time_remaining < 0:
                        sla_status = "breached"
                    elif time_remaining < 60:  # Less than 1 hour
                        sla_status = "at_risk"
                    else:
                        sla_status = "on_track"
            
            # Get customer info
            customer_name = job.customer.name if job.customer else None
            customer_phone = job.customer.phone if job.customer else None
            
            # Create job data
            job_data = {
                "id": job.id,
                "title": job.title,
                "description": job.description,
                "customer_id": job.customer_id,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "job_type": job.job_type.value,
                "status": job.status.value,
                "priority": job.priority.value,
                "estimated_duration_minutes": job.estimated_duration_minutes,
                "scheduled_start_time": job.scheduled_start_time,
                "scheduled_end_time": job.scheduled_end_time,
                "actual_start_time": job.actual_start_time,
                "actual_end_time": job.actual_end_time,
                "location_lat": job.location_lat,
                "location_lon": job.location_lon,
                "location_address": job.location_address,
                "required_skills": job.required_skills,
                "required_equipment": job.required_equipment,
                "notes": job.notes,
                "sla_deadline": job.sla_deadline,
                "sla_status": sla_status,
                "created_at": job.created_at,
                "updated_at": job.updated_at
            }
            
            # Add HATEOAS links
            job_data["links"] = [
                {"rel": "self", "href": f"/api/field-services/jobs/{job.id}"},
                {"rel": "customer", "href": f"/api/customers/{job.customer_id}" if job.customer_id else None}
            ]
            
            jobs_data.append(job_data)
        
        return jobs_data
    
    def _get_technician_notifications(self, technician_id: int, last_sync_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get notifications for a technician for mobile sync."""
        # Import here to avoid circular imports
        from .notification_service import NotificationService
        
        notification_service = NotificationService(self.db)
        
        # Get notifications
        notifications, _ = notification_service.get_technician_notifications(
            technician_id=technician_id,
            unread_only=False,
            page=1,
            page_size=100  # Get more notifications for mobile sync
        )
        
        # Filter by last sync time if provided
        if last_sync_time:
            notifications = [n for n in notifications if n.created_at > last_sync_time]
        
        # Convert to dictionary format
        notifications_data = [notification.dict() for notification in notifications]
        
        return notifications_data
    
    def _get_technician_inventory(self, technician_id: int, last_sync_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get inventory assigned to a technician for mobile sync."""
        # Base query for technician's inventory
        query = self.db.query(TechnicianInventory).filter(
            TechnicianInventory.technician_id == technician_id
        ).options(
            joinedload(TechnicianInventory.inventory)
        )
        
        # Filter by last sync time if provided
        if last_sync_time:
            query = query.filter(
                or_(
                    TechnicianInventory.created_at > last_sync_time,
                    TechnicianInventory.updated_at > last_sync_time
                )
            )
        
        # Execute query
        inventory_items = query.all()
        
        # Convert to dictionary format
        inventory_data = []
        for item in inventory_items:
            inventory_name = item.inventory.name if item.inventory else f"Item {item.inventory_id}"
            inventory_type = item.inventory.inventory_type if item.inventory else None
            
            inventory_data.append({
                "technician_id": item.technician_id,
                "inventory_id": item.inventory_id,
                "inventory_name": inventory_name,
                "inventory_type": inventory_type,
                "quantity": item.quantity,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "links": [
                    {"rel": "self", "href": f"/api/field-services/technicians/{item.technician_id}/inventory/{item.inventory_id}"},
                    {"rel": "inventory", "href": f"/api/field-services/inventory/{item.inventory_id}"}
                ]
            })
        
        return inventory_data
    
    def _generate_sync_hash(self, jobs: List[Dict[str, Any]], notifications: List[Dict[str, Any]], inventory: List[Dict[str, Any]]) -> str:
        """Generate a hash for data verification."""
        # Combine all data into a single string
        data_string = json.dumps({
            "jobs": jobs,
            "notifications": notifications,
            "inventory": inventory
        }, default=str)  # Convert datetime objects to strings
        
        # Generate hash
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def get_offline_data_package(self, technician_id: int) -> Dict[str, Any]:
        """
        Get a complete data package for offline use.
        
        This method provides all necessary data for a technician to work offline,
        including jobs, customer information, inventory, and reference data.
        """
        # Get technician
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            raise ValueError(f"Technician with ID {technician_id} not found")
        
        # Get all active jobs for the technician
        jobs_data = self._get_technician_jobs(technician_id)
        
        # Get all inventory for the technician
        inventory_data = self._get_technician_inventory(technician_id)
        
        # Get reference data (job types, statuses, priorities, etc.)
        reference_data = {
            "job_statuses": [status.value for status in JobStatusEnum],
            "job_priorities": [priority.value for priority in JobPriorityEnum],
            "technician_statuses": [status.value for status in TechnicianStatusEnum]
        }
        
        # Generate package hash for data verification
        package_hash = hashlib.sha256(
            json.dumps({
                "jobs": jobs_data,
                "inventory": inventory_data,
                "reference": reference_data
            }, default=str).encode()
        ).hexdigest()
        
        # Create response
        return {
            "technician_id": technician_id,
            "package_time": datetime.utcnow(),
            "package_hash": package_hash,
            "jobs": jobs_data,
            "inventory": inventory_data,
            "reference_data": reference_data,
            "links": [
                {"rel": "self", "href": f"/api/field-services/mobile/offline-package/{technician_id}"},
                {"rel": "technician", "href": f"/api/field-services/technicians/{technician_id}"},
                {"rel": "sync", "href": f"/api/field-services/mobile/sync/{technician_id}"}
            ]
        }
    
    def process_offline_batch(
        self, 
        technician_id: int, 
        job_updates: List[MobileJobUpdate],
        inventory_usage: List[MobileInventoryUsage],
        location_updates: List[MobileLocationUpdate]
    ) -> Dict[str, Any]:
        """
        Process a batch of offline updates from a mobile app.
        
        This method handles processing updates that were collected while
        the technician was working offline.
        """
        # Process job updates
        updated_jobs = self._process_job_updates(technician_id, job_updates)
        
        # Process inventory usage
        self._process_inventory_usage(technician_id, inventory_usage)
        
        # Process location updates - only use the most recent one
        if location_updates:
            # Sort by timestamp descending
            location_updates.sort(key=lambda x: x.timestamp, reverse=True)
            self._update_technician_location(technician_id, location_updates[0])
        
        # Create response
        return {
            "technician_id": technician_id,
            "processed_at": datetime.utcnow(),
            "job_updates_processed": len(updated_jobs),
            "inventory_updates_processed": len(inventory_usage),
            "location_updates_processed": 1 if location_updates else 0,
            "updated_job_ids": [job.id for job in updated_jobs],
            "links": [
                {"rel": "self", "href": f"/api/field-services/mobile/offline-batch/{technician_id}"},
                {"rel": "technician", "href": f"/api/field-services/technicians/{technician_id}"},
                {"rel": "sync", "href": f"/api/field-services/mobile/sync/{technician_id}"}
            ]
        }
