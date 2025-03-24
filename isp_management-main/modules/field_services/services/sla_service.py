"""
SLA Service for the Field Services Module.

This service handles SLA definition, tracking, and reporting for field service jobs.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, case
from sqlalchemy.orm import Session, joinedload

from ..models import SLADefinition, Job, JobStatusEnum, JobPriorityEnum, JobTypeEnum, JobHistory
from ..schemas import SLADefinitionCreate, SLADefinitionUpdate, SLADefinitionResponse
from backend_core.utils.hateoas import add_resource_links


class SLAService:
    """Service for managing SLA definitions and compliance."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_sla_definition(self, sla_data: SLADefinitionCreate, user_id: int) -> SLADefinitionResponse:
        """Create a new SLA definition."""
        # Check if an active SLA definition already exists for this job type and priority
        existing = self.db.query(SLADefinition).filter(
            SLADefinition.job_type == JobTypeEnum[sla_data.job_type.upper()],
            SLADefinition.priority == JobPriorityEnum[sla_data.priority.upper()],
            SLADefinition.is_active == True
        ).first()
        
        if existing:
            # Deactivate existing SLA definition
            existing.is_active = False
            existing.updated_by = user_id
        
        # Create SLA object from schema
        sla = SLADefinition(
            job_type=JobTypeEnum[sla_data.job_type.upper()],
            priority=JobPriorityEnum[sla_data.priority.upper()],
            response_time_minutes=sla_data.response_time_minutes,
            resolution_time_minutes=sla_data.resolution_time_minutes,
            description=sla_data.description,
            is_active=True,
            created_by=user_id
        )
        
        # Add to database
        self.db.add(sla)
        self.db.commit()
        self.db.refresh(sla)
        
        # Convert to response model
        return self._to_response(sla)
    
    def get_sla_definitions(
        self, 
        job_type: Optional[str] = None,
        priority: Optional[str] = None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[SLADefinitionResponse], int]:
        """Get SLA definitions with optional filtering."""
        query = self.db.query(SLADefinition)
        
        # Apply filters
        if job_type:
            query = query.filter(SLADefinition.job_type == JobTypeEnum[job_type.upper()])
        
        if priority:
            query = query.filter(SLADefinition.priority == JobPriorityEnum[priority.upper()])
        
        if active_only:
            query = query.filter(SLADefinition.is_active == True)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.order_by(SLADefinition.job_type, SLADefinition.priority)
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        sla_definitions = query.all()
        
        # Convert to response models
        sla_responses = [self._to_response(sla) for sla in sla_definitions]
        
        return sla_responses, total
    
    def get_sla_definition_by_id(self, sla_id: int) -> Optional[SLADefinitionResponse]:
        """Get an SLA definition by ID."""
        sla = self.db.query(SLADefinition).filter(SLADefinition.id == sla_id).first()
        
        if not sla:
            return None
        
        return self._to_response(sla)
    
    def update_sla_definition(self, sla_id: int, sla_data: SLADefinitionUpdate, user_id: int) -> Optional[SLADefinitionResponse]:
        """Update an SLA definition."""
        sla = self.db.query(SLADefinition).filter(SLADefinition.id == sla_id).first()
        
        if not sla:
            return None
        
        # Update fields if provided
        if sla_data.response_time_minutes is not None:
            sla.response_time_minutes = sla_data.response_time_minutes
        
        if sla_data.resolution_time_minutes is not None:
            sla.resolution_time_minutes = sla_data.resolution_time_minutes
        
        if sla_data.description is not None:
            sla.description = sla_data.description
        
        if sla_data.is_active is not None:
            # If activating this SLA, deactivate any other active SLAs for the same job type and priority
            if sla_data.is_active and not sla.is_active:
                existing = self.db.query(SLADefinition).filter(
                    SLADefinition.job_type == sla.job_type,
                    SLADefinition.priority == sla.priority,
                    SLADefinition.is_active == True,
                    SLADefinition.id != sla_id
                ).all()
                
                for existing_sla in existing:
                    existing_sla.is_active = False
                    existing_sla.updated_by = user_id
            
            sla.is_active = sla_data.is_active
        
        # Update the updated_by field
        sla.updated_by = user_id
        
        # Commit changes
        self.db.commit()
        self.db.refresh(sla)
        
        # Convert to response model
        return self._to_response(sla)
    
    def delete_sla_definition(self, sla_id: int) -> bool:
        """Delete an SLA definition."""
        sla = self.db.query(SLADefinition).filter(SLADefinition.id == sla_id).first()
        
        if not sla:
            return False
        
        # Delete SLA definition
        self.db.delete(sla)
        self.db.commit()
        
        return True
    
    def get_sla_compliance_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        job_type: Optional[str] = None,
        priority: Optional[str] = None,
        technician_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an SLA compliance report for completed jobs.
        
        This report provides detailed metrics on SLA compliance, including:
        - Overall compliance rate
        - Compliance by job type
        - Compliance by priority
        - Compliance by technician
        - Average response and resolution times
        """
        # Parse dates
        start_datetime = datetime.fromisoformat(start_date) if start_date else datetime.utcnow() - timedelta(days=30)
        end_datetime = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        
        # Base query for completed jobs
        query = self.db.query(Job).filter(
            Job.status == JobStatusEnum.COMPLETED,
            Job.actual_end_time.between(start_datetime, end_datetime)
        )
        
        # Apply additional filters
        if job_type:
            query = query.filter(Job.job_type == JobTypeEnum[job_type.upper()])
        
        if priority:
            query = query.filter(Job.priority == JobPriorityEnum[priority.upper()])
        
        if technician_id:
            query = query.filter(Job.technician_id == technician_id)
        
        # Get all completed jobs
        completed_jobs = query.all()
        
        # Calculate SLA compliance metrics
        total_jobs = len(completed_jobs)
        jobs_within_sla = 0
        jobs_breached_sla = 0
        total_response_time = 0
        total_resolution_time = 0
        response_time_count = 0
        resolution_time_count = 0
        
        # Track metrics by job type, priority, and technician
        metrics_by_job_type = {}
        metrics_by_priority = {}
        metrics_by_technician = {}
        
        for job in completed_jobs:
            # Check SLA compliance
            is_compliant = False
            if job.sla_deadline and job.actual_end_time:
                is_compliant = job.actual_end_time <= job.sla_deadline
                if is_compliant:
                    jobs_within_sla += 1
                else:
                    jobs_breached_sla += 1
            
            # Calculate response time (time to start job after creation)
            if job.actual_start_time and job.created_at:
                response_time = (job.actual_start_time - job.created_at).total_seconds() / 60
                total_response_time += response_time
                response_time_count += 1
            
            # Calculate resolution time (time to complete job after starting)
            if job.actual_end_time and job.actual_start_time:
                resolution_time = (job.actual_end_time - job.actual_start_time).total_seconds() / 60
                total_resolution_time += resolution_time
                resolution_time_count += 1
            
            # Track metrics by job type
            job_type_value = job.job_type.value
            if job_type_value not in metrics_by_job_type:
                metrics_by_job_type[job_type_value] = {
                    'total': 0,
                    'compliant': 0,
                    'breached': 0,
                    'total_response_time': 0,
                    'total_resolution_time': 0,
                    'response_time_count': 0,
                    'resolution_time_count': 0
                }
            
            metrics_by_job_type[job_type_value]['total'] += 1
            if job.sla_deadline and job.actual_end_time:
                if is_compliant:
                    metrics_by_job_type[job_type_value]['compliant'] += 1
                else:
                    metrics_by_job_type[job_type_value]['breached'] += 1
            
            if job.actual_start_time and job.created_at:
                response_time = (job.actual_start_time - job.created_at).total_seconds() / 60
                metrics_by_job_type[job_type_value]['total_response_time'] += response_time
                metrics_by_job_type[job_type_value]['response_time_count'] += 1
            
            if job.actual_end_time and job.actual_start_time:
                resolution_time = (job.actual_end_time - job.actual_start_time).total_seconds() / 60
                metrics_by_job_type[job_type_value]['total_resolution_time'] += resolution_time
                metrics_by_job_type[job_type_value]['resolution_time_count'] += 1
            
            # Track metrics by priority
            priority_value = job.priority.value
            if priority_value not in metrics_by_priority:
                metrics_by_priority[priority_value] = {
                    'total': 0,
                    'compliant': 0,
                    'breached': 0,
                    'total_response_time': 0,
                    'total_resolution_time': 0,
                    'response_time_count': 0,
                    'resolution_time_count': 0
                }
            
            metrics_by_priority[priority_value]['total'] += 1
            if job.sla_deadline and job.actual_end_time:
                if is_compliant:
                    metrics_by_priority[priority_value]['compliant'] += 1
                else:
                    metrics_by_priority[priority_value]['breached'] += 1
            
            if job.actual_start_time and job.created_at:
                response_time = (job.actual_start_time - job.created_at).total_seconds() / 60
                metrics_by_priority[priority_value]['total_response_time'] += response_time
                metrics_by_priority[priority_value]['response_time_count'] += 1
            
            if job.actual_end_time and job.actual_start_time:
                resolution_time = (job.actual_end_time - job.actual_start_time).total_seconds() / 60
                metrics_by_priority[priority_value]['total_resolution_time'] += resolution_time
                metrics_by_priority[priority_value]['resolution_time_count'] += 1
            
            # Track metrics by technician
            if job.technician_id:
                tech_id = job.technician_id
                if tech_id not in metrics_by_technician:
                    # Get technician name
                    technician = self.db.query(Job.technician).filter(Job.technician_id == tech_id).first()
                    tech_name = technician.name if technician else f"Technician {tech_id}"
                    
                    metrics_by_technician[tech_id] = {
                        'name': tech_name,
                        'total': 0,
                        'compliant': 0,
                        'breached': 0,
                        'total_response_time': 0,
                        'total_resolution_time': 0,
                        'response_time_count': 0,
                        'resolution_time_count': 0
                    }
                
                metrics_by_technician[tech_id]['total'] += 1
                if job.sla_deadline and job.actual_end_time:
                    if is_compliant:
                        metrics_by_technician[tech_id]['compliant'] += 1
                    else:
                        metrics_by_technician[tech_id]['breached'] += 1
                
                if job.actual_start_time and job.created_at:
                    response_time = (job.actual_start_time - job.created_at).total_seconds() / 60
                    metrics_by_technician[tech_id]['total_response_time'] += response_time
                    metrics_by_technician[tech_id]['response_time_count'] += 1
                
                if job.actual_end_time and job.actual_start_time:
                    resolution_time = (job.actual_end_time - job.actual_start_time).total_seconds() / 60
                    metrics_by_technician[tech_id]['total_resolution_time'] += resolution_time
                    metrics_by_technician[tech_id]['resolution_time_count'] += 1
        
        # Calculate averages and percentages for job types
        for job_type, metrics in metrics_by_job_type.items():
            metrics['compliance_percentage'] = (metrics['compliant'] / metrics['total'] * 100) if metrics['total'] > 0 else 0
            metrics['avg_response_time'] = (metrics['total_response_time'] / metrics['response_time_count']) if metrics['response_time_count'] > 0 else 0
            metrics['avg_resolution_time'] = (metrics['total_resolution_time'] / metrics['resolution_time_count']) if metrics['resolution_time_count'] > 0 else 0
        
        # Calculate averages and percentages for priorities
        for priority, metrics in metrics_by_priority.items():
            metrics['compliance_percentage'] = (metrics['compliant'] / metrics['total'] * 100) if metrics['total'] > 0 else 0
            metrics['avg_response_time'] = (metrics['total_response_time'] / metrics['response_time_count']) if metrics['response_time_count'] > 0 else 0
            metrics['avg_resolution_time'] = (metrics['total_resolution_time'] / metrics['resolution_time_count']) if metrics['resolution_time_count'] > 0 else 0
        
        # Calculate averages and percentages for technicians
        for tech_id, metrics in metrics_by_technician.items():
            metrics['compliance_percentage'] = (metrics['compliant'] / metrics['total'] * 100) if metrics['total'] > 0 else 0
            metrics['avg_response_time'] = (metrics['total_response_time'] / metrics['response_time_count']) if metrics['response_time_count'] > 0 else 0
            metrics['avg_resolution_time'] = (metrics['total_resolution_time'] / metrics['resolution_time_count']) if metrics['resolution_time_count'] > 0 else 0
        
        # Calculate overall averages
        avg_response_time = (total_response_time / response_time_count) if response_time_count > 0 else 0
        avg_resolution_time = (total_resolution_time / resolution_time_count) if resolution_time_count > 0 else 0
        compliance_percentage = (jobs_within_sla / total_jobs * 100) if total_jobs > 0 else 0
        
        # Get jobs at risk of breaching SLA
        at_risk_jobs = self.db.query(Job).filter(
            Job.status.in_([JobStatusEnum.PENDING, JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS]),
            Job.sla_deadline.between(datetime.utcnow(), datetime.utcnow() + timedelta(hours=24))
        ).count()
        
        # Get jobs that have already breached SLA but are not completed
        breached_jobs = self.db.query(Job).filter(
            Job.status.in_([JobStatusEnum.PENDING, JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS]),
            Job.sla_deadline < datetime.utcnow()
        ).count()
        
        # Return metrics
        return {
            "period_start": start_datetime,
            "period_end": end_datetime,
            "total_jobs": total_jobs,
            "jobs_within_sla": jobs_within_sla,
            "jobs_breached_sla": jobs_breached_sla,
            "compliance_percentage": compliance_percentage,
            "average_response_time_minutes": avg_response_time,
            "average_resolution_time_minutes": avg_resolution_time,
            "metrics_by_job_type": metrics_by_job_type,
            "metrics_by_priority": metrics_by_priority,
            "metrics_by_technician": metrics_by_technician,
            "jobs_at_risk": at_risk_jobs,
            "jobs_already_breached": breached_jobs
        }
    
    def get_sla_trend_report(
        self,
        period: str = "monthly",  # "daily", "weekly", "monthly"
        months: int = 6,
        job_type: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an SLA compliance trend report over time.
        
        This report shows how SLA compliance has changed over time, allowing
        for trend analysis and identification of improvement or degradation.
        """
        # Calculate date range based on period and months
        end_date = datetime.utcnow()
        if period == "daily":
            start_date = end_date - timedelta(days=30)  # Last 30 days
            date_format = "%Y-%m-%d"
            date_trunc = func.date_trunc('day', Job.actual_end_time)
        elif period == "weekly":
            start_date = end_date - timedelta(weeks=12)  # Last 12 weeks
            date_format = "%Y-W%W"
            date_trunc = func.date_trunc('week', Job.actual_end_time)
        else:  # monthly
            start_date = end_date - timedelta(days=30 * months)  # Last X months
            date_format = "%Y-%m"
            date_trunc = func.date_trunc('month', Job.actual_end_time)
        
        # Base query filters
        filters = [
            Job.status == JobStatusEnum.COMPLETED,
            Job.actual_end_time.between(start_date, end_date)
        ]
        
        if job_type:
            filters.append(Job.job_type == JobTypeEnum[job_type.upper()])
        
        if priority:
            filters.append(Job.priority == JobPriorityEnum[priority.upper()])
        
        # Query for SLA compliance by period
        compliance_query = self.db.query(
            date_trunc.label('period'),
            func.count(Job.id).label('total_jobs'),
            func.sum(case(
                [(Job.actual_end_time <= Job.sla_deadline, 1)],
                else_=0
            )).label('compliant_jobs')
        ).filter(*filters).group_by('period').order_by('period').all()
        
        # Query for average response and resolution times by period
        time_query = self.db.query(
            date_trunc.label('period'),
            func.avg(func.extract('epoch', Job.actual_start_time - Job.created_at) / 60).label('avg_response_time'),
            func.avg(func.extract('epoch', Job.actual_end_time - Job.actual_start_time) / 60).label('avg_resolution_time')
        ).filter(*filters).group_by('period').order_by('period').all()
        
        # Combine results
        trend_data = {}
        
        for item in compliance_query:
            period_str = item.period.strftime(date_format)
            compliance_percentage = (item.compliant_jobs / item.total_jobs * 100) if item.total_jobs > 0 else 0
            
            trend_data[period_str] = {
                'period': period_str,
                'total_jobs': item.total_jobs,
                'compliant_jobs': item.compliant_jobs,
                'compliance_percentage': compliance_percentage,
                'avg_response_time': 0,
                'avg_resolution_time': 0
            }
        
        for item in time_query:
            period_str = item.period.strftime(date_format)
            if period_str in trend_data:
                trend_data[period_str]['avg_response_time'] = item.avg_response_time or 0
                trend_data[period_str]['avg_resolution_time'] = item.avg_resolution_time or 0
        
        # Convert to list and sort by period
        trend_list = list(trend_data.values())
        trend_list.sort(key=lambda x: x['period'])
        
        # Calculate overall trend
        if len(trend_list) >= 2:
            first_compliance = trend_list[0]['compliance_percentage']
            last_compliance = trend_list[-1]['compliance_percentage']
            compliance_trend = last_compliance - first_compliance
            
            first_response = trend_list[0]['avg_response_time']
            last_response = trend_list[-1]['avg_response_time']
            response_trend = first_response - last_response  # Positive means improving (faster)
            
            first_resolution = trend_list[0]['avg_resolution_time']
            last_resolution = trend_list[-1]['avg_resolution_time']
            resolution_trend = first_resolution - last_resolution  # Positive means improving (faster)
        else:
            compliance_trend = 0
            response_trend = 0
            resolution_trend = 0
        
        # Return trend report
        return {
            "period_type": period,
            "start_date": start_date,
            "end_date": end_date,
            "trend_data": trend_list,
            "compliance_trend": compliance_trend,
            "response_time_trend": response_trend,
            "resolution_time_trend": resolution_trend
        }
    
    def recalculate_job_sla_deadlines(self, job_type: Optional[str] = None, priority: Optional[str] = None) -> int:
        """
        Recalculate SLA deadlines for jobs based on current SLA definitions.
        
        This is useful when SLA definitions change and you want to update existing jobs.
        Returns the number of jobs updated.
        """
        # Base query for jobs that need SLA recalculation
        query = self.db.query(Job).filter(
            Job.status.in_([JobStatusEnum.PENDING, JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS])
        )
        
        # Apply filters if provided
        if job_type:
            query = query.filter(Job.job_type == JobTypeEnum[job_type.upper()])
        
        if priority:
            query = query.filter(Job.priority == JobPriorityEnum[priority.upper()])
        
        # Get jobs to update
        jobs = query.all()
        updated_count = 0
        
        for job in jobs:
            # Get SLA definition for this job type and priority
            sla_def = self.db.query(SLADefinition).filter(
                SLADefinition.job_type == job.job_type,
                SLADefinition.priority == job.priority,
                SLADefinition.is_active == True
            ).first()
            
            if sla_def:
                # Calculate new deadline based on SLA definition
                new_deadline = job.created_at + timedelta(minutes=sla_def.resolution_time_minutes)
                
                # Update job if deadline has changed
                if job.sla_deadline != new_deadline:
                    job.sla_deadline = new_deadline
                    updated_count += 1
            else:
                # Use default SLA deadlines if no definition exists
                if job.priority == JobPriorityEnum.CRITICAL:
                    new_deadline = job.created_at + timedelta(hours=4)
                elif job.priority == JobPriorityEnum.HIGH:
                    new_deadline = job.created_at + timedelta(hours=8)
                elif job.priority == JobPriorityEnum.MEDIUM:
                    new_deadline = job.created_at + timedelta(hours=24)
                else:  # LOW
                    new_deadline = job.created_at + timedelta(hours=48)
                
                # Update job if deadline has changed
                if job.sla_deadline != new_deadline:
                    job.sla_deadline = new_deadline
                    updated_count += 1
        
        # Commit changes if any jobs were updated
        if updated_count > 0:
            self.db.commit()
        
        return updated_count
    
    def _to_response(self, sla: SLADefinition) -> SLADefinitionResponse:
        """Convert SLADefinition model to SLADefinitionResponse schema."""
        response_dict = {
            "id": sla.id,
            "job_type": sla.job_type.value,
            "priority": sla.priority.value,
            "response_time_minutes": sla.response_time_minutes,
            "resolution_time_minutes": sla.resolution_time_minutes,
            "description": sla.description,
            "is_active": sla.is_active,
            "created_by": sla.created_by,
            "updated_by": sla.updated_by,
            "created_at": sla.created_at,
            "updated_at": sla.updated_at
        }
        
        # Add HATEOAS links
        add_resource_links(response_dict, "field-services.sla-definitions", sla.id)
        
        return SLADefinitionResponse(**response_dict)
