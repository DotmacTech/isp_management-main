"""
Job Service for the Field Services Module.

This service handles job creation, assignment, scheduling, and SLA tracking.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload

from ..models import Job, JobStatusEnum, JobPriorityEnum, JobTypeEnum, SLADefinition, JobHistory
from ..schemas import JobCreate, JobUpdate, JobResponse
from backend_core.utils.hateoas import add_resource_links


class JobService:
    """Service for managing field service jobs."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_job(self, job_data: JobCreate, user_id: int) -> JobResponse:
        """Create a new job."""
        # Create job object from schema
        job = Job(
            title=job_data.title,
            description=job_data.description,
            customer_id=job_data.customer_id,
            technician_id=job_data.technician_id,
            job_type=JobTypeEnum[job_data.job_type.upper()],
            status=JobStatusEnum[job_data.status.upper()],
            priority=JobPriorityEnum[job_data.priority.upper()],
            estimated_duration_minutes=job_data.estimated_duration_minutes,
            scheduled_start_time=job_data.scheduled_start_time,
            scheduled_end_time=job_data.scheduled_end_time,
            location_lat=job_data.location_lat,
            location_lon=job_data.location_lon,
            location_address=job_data.location_address,
            required_skills=job_data.required_skills,
            required_equipment=job_data.required_equipment,
            created_by=user_id,
            sla_deadline=job_data.sla_deadline
        )
        
        # If SLA deadline is not provided, calculate it based on SLA definitions
        if not job.sla_deadline:
            self._calculate_sla_deadline(job)
        
        # Add to database
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Create job history entry
        job_history = JobHistory(
            job_id=job.id,
            status_to=job.status,
            notes="Job created",
            changed_by=user_id
        )
        self.db.add(job_history)
        self.db.commit()
        
        # Convert to response model
        return self._to_response(job)
    
    def get_jobs(
        self, 
        status: Optional[str] = None,
        technician_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[JobResponse], int]:
        """Get jobs with optional filtering."""
        query = self.db.query(Job).options(
            joinedload(Job.technician),
            joinedload(Job.customer)
        )
        
        # Apply filters
        if status:
            query = query.filter(Job.status == JobStatusEnum[status.upper()])
        
        if technician_id:
            query = query.filter(Job.technician_id == technician_id)
        
        if customer_id:
            query = query.filter(Job.customer_id == customer_id)
        
        if priority:
            query = query.filter(Job.priority == JobPriorityEnum[priority.upper()])
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(Job.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        jobs = query.all()
        
        # Convert to response models
        job_responses = [self._to_response(job) for job in jobs]
        
        return job_responses, total
    
    def get_job_by_id(self, job_id: int) -> Optional[JobResponse]:
        """Get a job by ID."""
        job = self.db.query(Job).options(
            joinedload(Job.technician),
            joinedload(Job.customer)
        ).filter(Job.id == job_id).first()
        
        if not job:
            return None
        
        return self._to_response(job)
    
    def update_job(self, job_id: int, job_data: JobUpdate, user_id: int) -> Optional[JobResponse]:
        """Update a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            return None
        
        # Store previous status for history tracking
        previous_status = job.status
        
        # Update fields if provided
        if job_data.title is not None:
            job.title = job_data.title
        
        if job_data.description is not None:
            job.description = job_data.description
        
        if job_data.technician_id is not None:
            job.technician_id = job_data.technician_id
        
        if job_data.status is not None:
            job.status = JobStatusEnum[job_data.status.upper()]
            
            # Update actual start/end times based on status changes
            if job.status == JobStatusEnum.IN_PROGRESS and not job.actual_start_time:
                job.actual_start_time = datetime.utcnow()
            
            if job.status == JobStatusEnum.COMPLETED and not job.actual_end_time:
                job.actual_end_time = datetime.utcnow()
        
        if job_data.priority is not None:
            job.priority = JobPriorityEnum[job_data.priority.upper()]
            # Recalculate SLA if priority changes
            self._calculate_sla_deadline(job)
        
        if job_data.estimated_duration_minutes is not None:
            job.estimated_duration_minutes = job_data.estimated_duration_minutes
        
        if job_data.scheduled_start_time is not None:
            job.scheduled_start_time = job_data.scheduled_start_time
        
        if job_data.scheduled_end_time is not None:
            job.scheduled_end_time = job_data.scheduled_end_time
        
        if job_data.actual_start_time is not None:
            job.actual_start_time = job_data.actual_start_time
        
        if job_data.actual_end_time is not None:
            job.actual_end_time = job_data.actual_end_time
        
        if job_data.location_lat is not None:
            job.location_lat = job_data.location_lat
        
        if job_data.location_lon is not None:
            job.location_lon = job_data.location_lon
        
        if job_data.location_address is not None:
            job.location_address = job_data.location_address
        
        if job_data.required_skills is not None:
            job.required_skills = job_data.required_skills
        
        if job_data.required_equipment is not None:
            job.required_equipment = job_data.required_equipment
        
        if job_data.notes is not None:
            job.notes = job_data.notes
        
        if job_data.sla_deadline is not None:
            job.sla_deadline = job_data.sla_deadline
        
        # Update the updated_by field
        job.updated_by = user_id
        
        # Commit changes
        self.db.commit()
        self.db.refresh(job)
        
        # Create job history entry if status changed
        if job.status != previous_status:
            job_history = JobHistory(
                job_id=job.id,
                status_from=previous_status,
                status_to=job.status,
                notes=f"Status changed from {previous_status.value} to {job.status.value}",
                changed_by=user_id
            )
            self.db.add(job_history)
            self.db.commit()
        
        # Convert to response model
        return self._to_response(job)
    
    def delete_job(self, job_id: int) -> bool:
        """Delete a job."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            return False
        
        # Delete job
        self.db.delete(job)
        self.db.commit()
        
        return True
    
    def assign_job_to_technician(self, job_id: int, technician_id: int, user_id: int) -> Optional[JobResponse]:
        """Assign a job to a technician."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            return None
        
        # Update job
        job.technician_id = technician_id
        job.status = JobStatusEnum.ASSIGNED
        job.updated_by = user_id
        
        # Commit changes
        self.db.commit()
        self.db.refresh(job)
        
        # Create job history entry
        job_history = JobHistory(
            job_id=job.id,
            status_from=JobStatusEnum.PENDING if job.status == JobStatusEnum.ASSIGNED else job.status,
            status_to=job.status,
            notes=f"Job assigned to technician ID {technician_id}",
            changed_by=user_id
        )
        self.db.add(job_history)
        self.db.commit()
        
        # Convert to response model
        return self._to_response(job)
    
    def get_sla_performance(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        technician_id: Optional[int] = None,
        job_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get SLA performance metrics."""
        # Parse dates
        start_datetime = datetime.fromisoformat(start_date) if start_date else datetime.utcnow() - timedelta(days=30)
        end_datetime = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        
        # Base query for completed jobs
        completed_query = self.db.query(Job).filter(
            Job.status == JobStatusEnum.COMPLETED,
            Job.actual_end_time.between(start_datetime, end_datetime)
        )
        
        # Apply additional filters
        if technician_id:
            completed_query = completed_query.filter(Job.technician_id == technician_id)
        
        if job_type:
            completed_query = completed_query.filter(Job.job_type == JobTypeEnum[job_type.upper()])
        
        # Get all completed jobs
        completed_jobs = completed_query.all()
        
        # Count jobs completed on time vs late
        jobs_on_time = 0
        jobs_late = 0
        total_response_time = 0
        total_resolution_time = 0
        
        for job in completed_jobs:
            # Calculate if job was completed on time
            if job.sla_deadline and job.actual_end_time:
                if job.actual_end_time <= job.sla_deadline:
                    jobs_on_time += 1
                else:
                    jobs_late += 1
            
            # Calculate response time (time to start job after creation)
            if job.actual_start_time and job.created_at:
                response_time = (job.actual_start_time - job.created_at).total_seconds() / 60
                total_response_time += response_time
            
            # Calculate resolution time (time to complete job after starting)
            if job.actual_end_time and job.actual_start_time:
                resolution_time = (job.actual_end_time - job.actual_start_time).total_seconds() / 60
                total_resolution_time += resolution_time
        
        # Get in-progress jobs
        in_progress_query = self.db.query(Job).filter(
            Job.status == JobStatusEnum.IN_PROGRESS
        )
        
        # Apply additional filters
        if technician_id:
            in_progress_query = in_progress_query.filter(Job.technician_id == technician_id)
        
        if job_type:
            in_progress_query = in_progress_query.filter(Job.job_type == JobTypeEnum[job_type.upper()])
        
        # Count in-progress jobs
        jobs_in_progress = in_progress_query.count()
        
        # Calculate performance by technician
        performance_by_technician = {}
        if not technician_id:  # Only calculate if not filtering by technician
            technician_query = self.db.query(Job.technician_id, func.count(Job.id).label('total_jobs')).filter(
                Job.status == JobStatusEnum.COMPLETED,
                Job.actual_end_time.between(start_datetime, end_datetime)
            ).group_by(Job.technician_id)
            
            if job_type:
                technician_query = technician_query.filter(Job.job_type == JobTypeEnum[job_type.upper()])
            
            for tech_id, total_jobs in technician_query.all():
                if tech_id:  # Skip if technician_id is None
                    # Count on-time jobs for this technician
                    tech_on_time = self.db.query(Job).filter(
                        Job.technician_id == tech_id,
                        Job.status == JobStatusEnum.COMPLETED,
                        Job.actual_end_time.between(start_datetime, end_datetime),
                        Job.actual_end_time <= Job.sla_deadline
                    ).count()
                    
                    # Get technician name
                    technician = self.db.query(Job.technician).filter(Job.technician_id == tech_id).first()
                    tech_name = technician.name if technician else f"Technician {tech_id}"
                    
                    performance_by_technician[tech_name] = {
                        "total_jobs": total_jobs,
                        "on_time_jobs": tech_on_time,
                        "compliance_percentage": (tech_on_time / total_jobs * 100) if total_jobs > 0 else 0
                    }
        
        # Calculate performance by job type
        performance_by_job_type = {}
        if not job_type:  # Only calculate if not filtering by job type
            job_type_query = self.db.query(Job.job_type, func.count(Job.id).label('total_jobs')).filter(
                Job.status == JobStatusEnum.COMPLETED,
                Job.actual_end_time.between(start_datetime, end_datetime)
            ).group_by(Job.job_type)
            
            if technician_id:
                job_type_query = job_type_query.filter(Job.technician_id == technician_id)
            
            for job_type_enum, total_jobs in job_type_query.all():
                # Count on-time jobs for this job type
                type_on_time = self.db.query(Job).filter(
                    Job.job_type == job_type_enum,
                    Job.status == JobStatusEnum.COMPLETED,
                    Job.actual_end_time.between(start_datetime, end_datetime),
                    Job.actual_end_time <= Job.sla_deadline
                ).count()
                
                performance_by_job_type[job_type_enum.value] = {
                    "total_jobs": total_jobs,
                    "on_time_jobs": type_on_time,
                    "compliance_percentage": (type_on_time / total_jobs * 100) if total_jobs > 0 else 0
                }
        
        # Calculate overall metrics
        total_jobs = len(completed_jobs)
        avg_response_time = total_response_time / total_jobs if total_jobs > 0 else 0
        avg_resolution_time = total_resolution_time / total_jobs if total_jobs > 0 else 0
        sla_compliance = (jobs_on_time / total_jobs * 100) if total_jobs > 0 else 0
        
        # Return metrics
        return {
            "total_jobs": total_jobs,
            "jobs_completed_on_time": jobs_on_time,
            "jobs_completed_late": jobs_late,
            "jobs_in_progress": jobs_in_progress,
            "average_response_time_minutes": avg_response_time,
            "average_resolution_time_minutes": avg_resolution_time,
            "sla_compliance_percentage": sla_compliance,
            "performance_by_technician": performance_by_technician,
            "performance_by_job_type": performance_by_job_type,
            "period_start": start_datetime,
            "period_end": end_datetime
        }
    
    def _calculate_sla_deadline(self, job: Job) -> None:
        """Calculate SLA deadline based on job type and priority."""
        # Get SLA definition for this job type and priority
        sla_def = self.db.query(SLADefinition).filter(
            SLADefinition.job_type == job.job_type,
            SLADefinition.priority == job.priority,
            SLADefinition.is_active == True
        ).first()
        
        if sla_def:
            # Calculate deadline based on SLA definition
            job.sla_deadline = job.created_at + timedelta(minutes=sla_def.resolution_time_minutes)
        else:
            # Default SLA deadlines if no definition exists
            if job.priority == JobPriorityEnum.CRITICAL:
                job.sla_deadline = job.created_at + timedelta(hours=4)
            elif job.priority == JobPriorityEnum.HIGH:
                job.sla_deadline = job.created_at + timedelta(hours=8)
            elif job.priority == JobPriorityEnum.MEDIUM:
                job.sla_deadline = job.created_at + timedelta(hours=24)
            else:  # LOW
                job.sla_deadline = job.created_at + timedelta(hours=48)
    
    def _to_response(self, job: Job) -> JobResponse:
        """Convert Job model to JobResponse schema."""
        # Calculate SLA status
        sla_status = self._calculate_sla_status(job)
        
        # Create response object
        response_dict = {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "customer_id": job.customer_id,
            "technician_id": job.technician_id,
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
            "created_by": job.created_by,
            "updated_by": job.updated_by,
            "sla_deadline": job.sla_deadline,
            "sla_status": sla_status,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
        
        # Add HATEOAS links
        add_resource_links(response_dict, "field-services.jobs", job.id)
        
        return JobResponse(**response_dict)
    
    def _calculate_sla_status(self, job: Job) -> str:
        """Calculate the SLA status of a job."""
        if not job.sla_deadline:
            return "no_sla"
        
        now = datetime.utcnow()
        
        if job.status == JobStatusEnum.COMPLETED:
            if job.actual_end_time <= job.sla_deadline:
                return "met"
            else:
                return "breached"
        
        if job.status == JobStatusEnum.CANCELLED:
            return "cancelled"
        
        # For jobs not completed
        time_remaining = (job.sla_deadline - now).total_seconds() / 60  # minutes
        
        if time_remaining < 0:
            return "breached"
        elif time_remaining < 60:  # Less than 1 hour
            return "at_risk"
        else:
            return "on_track"
