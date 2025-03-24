"""
Technician Service for the Field Services Module.

This service handles technician profile management, availability tracking, and skills management.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload

from ..models import Technician, TechnicianStatusEnum, TechnicianAvailability, Job, JobStatusEnum
from ..schemas import TechnicianCreate, TechnicianUpdate, TechnicianResponse
from backend_core.utils.hateoas import add_resource_links


class TechnicianService:
    """Service for managing field service technicians."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_technician(self, technician_data: TechnicianCreate) -> TechnicianResponse:
        """Create a new technician profile."""
        # Create technician object from schema
        technician = Technician(
            user_id=technician_data.user_id,
            name=technician_data.name,
            email=technician_data.email,
            phone=technician_data.phone,
            skills=technician_data.skills,
            certification_level=technician_data.certification_level,
            region=technician_data.region,
            status=TechnicianStatusEnum[technician_data.status.upper()],
            max_jobs_per_day=technician_data.max_jobs_per_day,
            home_location_lat=technician_data.home_location_lat,
            home_location_lon=technician_data.home_location_lon,
            current_location_lat=technician_data.home_location_lat,  # Initialize with home location
            current_location_lon=technician_data.home_location_lon,  # Initialize with home location
            last_location_update=datetime.utcnow()
        )
        
        # Add to database
        self.db.add(technician)
        self.db.commit()
        self.db.refresh(technician)
        
        # Convert to response model
        return self._to_response(technician)
    
    def get_technicians(
        self, 
        status: Optional[str] = None,
        skill: Optional[str] = None,
        region: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TechnicianResponse], int]:
        """Get technicians with optional filtering."""
        query = self.db.query(Technician)
        
        # Apply filters
        if status:
            query = query.filter(Technician.status == TechnicianStatusEnum[status.upper()])
        
        if skill:
            # Filter by skill using JSON contains operator
            query = query.filter(Technician.skills.contains([skill]))
        
        if region:
            query = query.filter(Technician.region == region)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.order_by(Technician.name)
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        technicians = query.all()
        
        # Convert to response models
        technician_responses = [self._to_response(technician) for technician in technicians]
        
        return technician_responses, total
    
    def get_technician_by_id(self, technician_id: int) -> Optional[TechnicianResponse]:
        """Get a technician by ID."""
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            return None
        
        return self._to_response(technician)
    
    def update_technician(self, technician_id: int, technician_data: TechnicianUpdate) -> Optional[TechnicianResponse]:
        """Update a technician profile."""
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            return None
        
        # Update fields if provided
        if technician_data.name is not None:
            technician.name = technician_data.name
        
        if technician_data.email is not None:
            technician.email = technician_data.email
        
        if technician_data.phone is not None:
            technician.phone = technician_data.phone
        
        if technician_data.skills is not None:
            technician.skills = technician_data.skills
        
        if technician_data.certification_level is not None:
            technician.certification_level = technician_data.certification_level
        
        if technician_data.region is not None:
            technician.region = technician_data.region
        
        if technician_data.status is not None:
            technician.status = TechnicianStatusEnum[technician_data.status.upper()]
        
        if technician_data.max_jobs_per_day is not None:
            technician.max_jobs_per_day = technician_data.max_jobs_per_day
        
        if technician_data.home_location_lat is not None:
            technician.home_location_lat = technician_data.home_location_lat
        
        if technician_data.home_location_lon is not None:
            technician.home_location_lon = technician_data.home_location_lon
        
        # Commit changes
        self.db.commit()
        self.db.refresh(technician)
        
        # Convert to response model
        return self._to_response(technician)
    
    def update_technician_location(
        self, 
        technician_id: int, 
        latitude: float, 
        longitude: float
    ) -> Optional[TechnicianResponse]:
        """Update a technician's current location."""
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            return None
        
        # Update location
        technician.current_location_lat = latitude
        technician.current_location_lon = longitude
        technician.last_location_update = datetime.utcnow()
        
        # Commit changes
        self.db.commit()
        self.db.refresh(technician)
        
        # Convert to response model
        return self._to_response(technician)
    
    def get_technician_availability(
        self, 
        technician_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get a technician's availability for a date range."""
        # Get availability records
        availability_records = self.db.query(TechnicianAvailability).filter(
            TechnicianAvailability.technician_id == technician_id,
            TechnicianAvailability.date.between(start_date, end_date)
        ).order_by(TechnicianAvailability.date, TechnicianAvailability.start_time).all()
        
        # Get scheduled jobs
        jobs = self.db.query(Job).filter(
            Job.technician_id == technician_id,
            Job.status.in_([JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS]),
            or_(
                and_(
                    Job.scheduled_start_time >= datetime.combine(start_date, datetime.min.time()),
                    Job.scheduled_start_time <= datetime.combine(end_date, datetime.max.time())
                ),
                and_(
                    Job.scheduled_end_time >= datetime.combine(start_date, datetime.min.time()),
                    Job.scheduled_end_time <= datetime.combine(end_date, datetime.max.time())
                )
            )
        ).order_by(Job.scheduled_start_time).all()
        
        # Combine availability and jobs into a schedule
        schedule = []
        
        # Add availability records
        for record in availability_records:
            schedule.append({
                "date": record.date,
                "start_time": record.start_time,
                "end_time": record.end_time,
                "is_available": record.is_available,
                "reason": record.reason,
                "type": "availability"
            })
        
        # Add jobs
        for job in jobs:
            if job.scheduled_start_time and job.scheduled_end_time:
                schedule.append({
                    "date": job.scheduled_start_time.date(),
                    "start_time": job.scheduled_start_time,
                    "end_time": job.scheduled_end_time,
                    "job_id": job.id,
                    "job_title": job.title,
                    "job_status": job.status.value,
                    "type": "job"
                })
        
        # Sort by date and start time
        schedule.sort(key=lambda x: (x["date"], x["start_time"]))
        
        return schedule
    
    def set_technician_availability(
        self, 
        technician_id: int, 
        date_value: date, 
        start_time: datetime, 
        end_time: datetime, 
        is_available: bool, 
        reason: Optional[str] = None
    ) -> bool:
        """Set a technician's availability for a specific time period."""
        # Check if technician exists
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            return False
        
        # Check for existing availability record
        existing = self.db.query(TechnicianAvailability).filter(
            TechnicianAvailability.technician_id == technician_id,
            TechnicianAvailability.date == date_value,
            TechnicianAvailability.start_time == start_time,
            TechnicianAvailability.end_time == end_time
        ).first()
        
        if existing:
            # Update existing record
            existing.is_available = is_available
            existing.reason = reason
        else:
            # Create new availability record
            availability = TechnicianAvailability(
                technician_id=technician_id,
                date=date_value,
                start_time=start_time,
                end_time=end_time,
                is_available=is_available,
                reason=reason
            )
            self.db.add(availability)
        
        # Commit changes
        self.db.commit()
        
        return True
    
    def get_technician_workload(
        self, 
        technician_id: int, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Get a technician's workload for a date range."""
        # Check if technician exists
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
        
        if not technician:
            return {
                "technician_id": technician_id,
                "error": "Technician not found"
            }
        
        # Get jobs for the date range
        jobs = self.db.query(Job).filter(
            Job.technician_id == technician_id,
            or_(
                and_(
                    Job.scheduled_start_time >= datetime.combine(start_date, datetime.min.time()),
                    Job.scheduled_start_time <= datetime.combine(end_date, datetime.max.time())
                ),
                and_(
                    Job.actual_start_time >= datetime.combine(start_date, datetime.min.time()),
                    Job.actual_start_time <= datetime.combine(end_date, datetime.max.time())
                )
            )
        ).all()
        
        # Calculate workload metrics
        total_jobs = len(jobs)
        completed_jobs = sum(1 for job in jobs if job.status == JobStatusEnum.COMPLETED)
        in_progress_jobs = sum(1 for job in jobs if job.status == JobStatusEnum.IN_PROGRESS)
        pending_jobs = sum(1 for job in jobs if job.status == JobStatusEnum.PENDING or job.status == JobStatusEnum.ASSIGNED)
        
        # Calculate total scheduled time
        total_scheduled_minutes = 0
        for job in jobs:
            if job.scheduled_start_time and job.scheduled_end_time:
                duration = (job.scheduled_end_time - job.scheduled_start_time).total_seconds() / 60
                total_scheduled_minutes += duration
        
        # Calculate total actual time for completed jobs
        total_actual_minutes = 0
        for job in jobs:
            if job.actual_start_time and job.actual_end_time and job.status == JobStatusEnum.COMPLETED:
                duration = (job.actual_end_time - job.actual_start_time).total_seconds() / 60
                total_actual_minutes += duration
        
        # Calculate efficiency (actual vs estimated time)
        efficiency = 0
        efficiency_jobs = 0
        for job in jobs:
            if job.actual_start_time and job.actual_end_time and job.status == JobStatusEnum.COMPLETED:
                actual_duration = (job.actual_end_time - job.actual_start_time).total_seconds() / 60
                estimated_duration = job.estimated_duration_minutes
                if estimated_duration > 0:
                    job_efficiency = estimated_duration / actual_duration
                    efficiency += job_efficiency
                    efficiency_jobs += 1
        
        avg_efficiency = efficiency / efficiency_jobs if efficiency_jobs > 0 else 0
        
        # Group jobs by type
        jobs_by_type = {}
        for job in jobs:
            job_type = job.job_type.value
            if job_type not in jobs_by_type:
                jobs_by_type[job_type] = 0
            jobs_by_type[job_type] += 1
        
        # Return workload metrics
        return {
            "technician_id": technician_id,
            "technician_name": technician.name,
            "period_start": start_date,
            "period_end": end_date,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "in_progress_jobs": in_progress_jobs,
            "pending_jobs": pending_jobs,
            "total_scheduled_minutes": total_scheduled_minutes,
            "total_actual_minutes": total_actual_minutes,
            "average_efficiency": avg_efficiency,
            "jobs_by_type": jobs_by_type,
            "max_jobs_per_day": technician.max_jobs_per_day
        }
    
    def find_available_technicians(
        self, 
        date_value: date, 
        start_time: datetime, 
        end_time: datetime, 
        required_skills: Optional[List[str]] = None,
        region: Optional[str] = None
    ) -> List[TechnicianResponse]:
        """Find technicians available for a specific time period."""
        # Base query for active technicians
        query = self.db.query(Technician).filter(
            Technician.status.in_([
                TechnicianStatusEnum.ACTIVE, 
                TechnicianStatusEnum.AVAILABLE
            ])
        )
        
        # Filter by region if provided
        if region:
            query = query.filter(Technician.region == region)
        
        # Filter by skills if provided
        if required_skills and len(required_skills) > 0:
            for skill in required_skills:
                query = query.filter(Technician.skills.contains([skill]))
        
        # Get all potential technicians
        potential_technicians = query.all()
        
        # Filter out technicians with conflicting jobs
        available_technicians = []
        for technician in potential_technicians:
            # Check for conflicting jobs
            conflicting_jobs = self.db.query(Job).filter(
                Job.technician_id == technician.id,
                Job.status.in_([JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS]),
                or_(
                    and_(
                        Job.scheduled_start_time < end_time,
                        Job.scheduled_end_time > start_time
                    ),
                    and_(
                        Job.actual_start_time < end_time,
                        Job.actual_end_time == None
                    )
                )
            ).count()
            
            if conflicting_jobs == 0:
                # Check for unavailability records
                unavailable = self.db.query(TechnicianAvailability).filter(
                    TechnicianAvailability.technician_id == technician.id,
                    TechnicianAvailability.date == date_value,
                    TechnicianAvailability.is_available == False,
                    TechnicianAvailability.start_time < end_time,
                    TechnicianAvailability.end_time > start_time
                ).count()
                
                if unavailable == 0:
                    # Check workload for the day
                    day_jobs = self.db.query(Job).filter(
                        Job.technician_id == technician.id,
                        Job.status.in_([JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS]),
                        or_(
                            and_(
                                func.date(Job.scheduled_start_time) == date_value,
                                Job.scheduled_start_time != None
                            ),
                            and_(
                                func.date(Job.actual_start_time) == date_value,
                                Job.actual_start_time != None
                            )
                        )
                    ).count()
                    
                    if day_jobs < technician.max_jobs_per_day:
                        available_technicians.append(technician)
        
        # Convert to response models
        return [self._to_response(technician) for technician in available_technicians]
    
    def _to_response(self, technician: Technician) -> TechnicianResponse:
        """Convert Technician model to TechnicianResponse schema."""
        response_dict = {
            "id": technician.id,
            "user_id": technician.user_id,
            "name": technician.name,
            "email": technician.email,
            "phone": technician.phone,
            "skills": technician.skills,
            "certification_level": technician.certification_level,
            "region": technician.region,
            "status": technician.status.value,
            "max_jobs_per_day": technician.max_jobs_per_day,
            "home_location_lat": technician.home_location_lat,
            "home_location_lon": technician.home_location_lon,
            "current_location_lat": technician.current_location_lat,
            "current_location_lon": technician.current_location_lon,
            "last_location_update": technician.last_location_update,
            "created_at": technician.created_at,
            "updated_at": technician.updated_at
        }
        
        # Add HATEOAS links
        add_resource_links(response_dict, "field-services.technicians", technician.id)
        
        return TechnicianResponse(**response_dict)
