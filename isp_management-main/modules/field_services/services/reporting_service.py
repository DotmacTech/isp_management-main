"""
Reporting Service for the Field Services Module.

This service handles analytics and reporting for field services operations,
including job performance metrics, technician efficiency, SLA compliance,
and inventory usage reports.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import calendar
from sqlalchemy import func, and_, or_, desc, cast, Float, Integer
from sqlalchemy.orm import Session, joinedload

from ..models import (
    Job, JobStatusEnum, JobPriorityEnum, Technician, TechnicianStatusEnum,
    JobHistory, TechnicianInventory, InventoryTransaction,
    InventoryTransactionTypeEnum
)
from backend_core.utils.hateoas import add_resource_links


class ReportingService:
    """Service for generating field services reports and analytics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_job_performance_report(
        self, 
        start_date: datetime,
        end_date: datetime,
        job_type: Optional[str] = None,
        technician_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate job performance report for the specified period.
        
        Includes metrics like completion rate, average resolution time,
        SLA compliance, and job distribution by type and priority.
        """
        # Base query for jobs within date range
        query = self.db.query(Job).filter(
            Job.created_at.between(start_date, end_date)
        )
        
        # Apply filters if provided
        if job_type:
            query = query.filter(Job.job_type == job_type)
        
        if technician_id:
            query = query.filter(Job.technician_id == technician_id)
        
        # Execute query
        jobs = query.all()
        
        # Calculate metrics
        total_jobs = len(jobs)
        completed_jobs = sum(1 for job in jobs if job.status == JobStatusEnum.COMPLETED)
        cancelled_jobs = sum(1 for job in jobs if job.status == JobStatusEnum.CANCELLED)
        
        # Completion rate
        completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # Average resolution time (for completed jobs)
        resolution_times = []
        for job in jobs:
            if job.status == JobStatusEnum.COMPLETED and job.actual_start_time and job.actual_end_time:
                resolution_time = (job.actual_end_time - job.actual_start_time).total_seconds() / 60  # minutes
                resolution_times.append(resolution_time)
        
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # SLA compliance
        jobs_with_sla = [job for job in jobs if job.sla_deadline is not None]
        sla_met = sum(1 for job in jobs_with_sla 
                     if job.status == JobStatusEnum.COMPLETED 
                     and job.actual_end_time <= job.sla_deadline)
        
        sla_compliance_rate = (sla_met / len(jobs_with_sla) * 100) if jobs_with_sla else 0
        
        # Job distribution by type
        job_types = {}
        for job in jobs:
            job_type = job.job_type.value
            job_types[job_type] = job_types.get(job_type, 0) + 1
        
        # Job distribution by priority
        job_priorities = {}
        for job in jobs:
            priority = job.priority.value
            job_priorities[priority] = job_priorities.get(priority, 0) + 1
        
        # Job distribution by status
        job_statuses = {}
        for job in jobs:
            status = job.status.value
            job_statuses[status] = job_statuses.get(status, 0) + 1
        
        # Create report
        report = {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "filters": {
                "job_type": job_type,
                "technician_id": technician_id
            },
            "summary": {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "cancelled_jobs": cancelled_jobs,
                "completion_rate": round(completion_rate, 2),
                "avg_resolution_time_minutes": round(avg_resolution_time, 2),
                "sla_compliance_rate": round(sla_compliance_rate, 2)
            },
            "distributions": {
                "by_type": job_types,
                "by_priority": job_priorities,
                "by_status": job_statuses
            }
        }
        
        # Add HATEOAS links
        links = [
            {"rel": "self", "href": f"/api/field-services/reports/job-performance"}
        ]
        
        if technician_id:
            links.append({"rel": "technician", "href": f"/api/field-services/technicians/{technician_id}"})
        
        report["links"] = links
        
        return report
    
    def get_technician_efficiency_report(
        self, 
        start_date: datetime,
        end_date: datetime,
        technician_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate technician efficiency report for the specified period.
        
        Includes metrics like jobs completed per day, average job duration,
        travel time, and SLA compliance rate per technician.
        """
        # Base query for technicians
        technician_query = self.db.query(Technician)
        
        # Filter by technician ID if provided
        if technician_id:
            technician_query = technician_query.filter(Technician.id == technician_id)
        
        # Execute query
        technicians = technician_query.all()
        
        # Calculate number of working days in period
        working_days = self._calculate_working_days(start_date, end_date)
        
        # Calculate metrics for each technician
        technician_metrics = []
        for technician in technicians:
            # Get jobs assigned to this technician in the period
            jobs = self.db.query(Job).filter(
                Job.technician_id == technician.id,
                Job.created_at.between(start_date, end_date)
            ).all()
            
            # Calculate metrics
            total_jobs = len(jobs)
            completed_jobs = sum(1 for job in jobs if job.status == JobStatusEnum.COMPLETED)
            
            # Jobs per day
            jobs_per_day = completed_jobs / working_days if working_days > 0 else 0
            
            # Average job duration
            job_durations = []
            for job in jobs:
                if job.status == JobStatusEnum.COMPLETED and job.actual_start_time and job.actual_end_time:
                    duration = (job.actual_end_time - job.actual_start_time).total_seconds() / 60  # minutes
                    job_durations.append(duration)
            
            avg_job_duration = sum(job_durations) / len(job_durations) if job_durations else 0
            
            # SLA compliance
            jobs_with_sla = [job for job in jobs if job.sla_deadline is not None]
            sla_met = sum(1 for job in jobs_with_sla 
                         if job.status == JobStatusEnum.COMPLETED 
                         and job.actual_end_time <= job.sla_deadline)
            
            sla_compliance_rate = (sla_met / len(jobs_with_sla) * 100) if jobs_with_sla else 0
            
            # Add to metrics list
            technician_metrics.append({
                "technician_id": technician.id,
                "technician_name": f"{technician.first_name} {technician.last_name}",
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "jobs_per_day": round(jobs_per_day, 2),
                "avg_job_duration_minutes": round(avg_job_duration, 2),
                "sla_compliance_rate": round(sla_compliance_rate, 2),
                "links": [
                    {"rel": "technician", "href": f"/api/field-services/technicians/{technician.id}"}
                ]
            })
        
        # Sort by completed jobs (descending)
        technician_metrics.sort(key=lambda x: x["completed_jobs"], reverse=True)
        
        # Create report
        report = {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "working_days": working_days
            },
            "filters": {
                "technician_id": technician_id
            },
            "technicians": technician_metrics
        }
        
        # Add HATEOAS links
        report["links"] = [
            {"rel": "self", "href": f"/api/field-services/reports/technician-efficiency"}
        ]
        
        return report
    
    def get_sla_compliance_report(
        self, 
        start_date: datetime,
        end_date: datetime,
        job_type: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate SLA compliance report for the specified period.
        
        Includes metrics like overall compliance rate, compliance by job type,
        compliance by priority, and trends over time.
        """
        # Base query for jobs with SLA within date range
        query = self.db.query(Job).filter(
            Job.sla_deadline.between(start_date, end_date),
            Job.sla_deadline.isnot(None)
        )
        
        # Apply filters if provided
        if job_type:
            query = query.filter(Job.job_type == job_type)
        
        if priority:
            query = query.filter(Job.priority == priority)
        
        # Execute query
        jobs = query.all()
        
        # Calculate metrics
        total_jobs = len(jobs)
        completed_jobs = [job for job in jobs if job.status == JobStatusEnum.COMPLETED]
        
        # Overall SLA compliance
        sla_met = sum(1 for job in completed_jobs if job.actual_end_time <= job.sla_deadline)
        overall_compliance_rate = (sla_met / len(completed_jobs) * 100) if completed_jobs else 0
        
        # SLA compliance by job type
        compliance_by_type = {}
        for job_type in JobTypeEnum:
            type_jobs = [job for job in completed_jobs if job.job_type == job_type]
            if type_jobs:
                type_sla_met = sum(1 for job in type_jobs if job.actual_end_time <= job.sla_deadline)
                compliance_rate = (type_sla_met / len(type_jobs) * 100)
                compliance_by_type[job_type.value] = {
                    "total": len(type_jobs),
                    "met": type_sla_met,
                    "compliance_rate": round(compliance_rate, 2)
                }
        
        # SLA compliance by priority
        compliance_by_priority = {}
        for priority in JobPriorityEnum:
            priority_jobs = [job for job in completed_jobs if job.priority == priority]
            if priority_jobs:
                priority_sla_met = sum(1 for job in priority_jobs if job.actual_end_time <= job.sla_deadline)
                compliance_rate = (priority_sla_met / len(priority_jobs) * 100)
                compliance_by_priority[priority.value] = {
                    "total": len(priority_jobs),
                    "met": priority_sla_met,
                    "compliance_rate": round(compliance_rate, 2)
                }
        
        # Average SLA breach time (for breached SLAs)
        breach_times = []
        for job in completed_jobs:
            if job.actual_end_time > job.sla_deadline:
                breach_time = (job.actual_end_time - job.sla_deadline).total_seconds() / 60  # minutes
                breach_times.append(breach_time)
        
        avg_breach_time = sum(breach_times) / len(breach_times) if breach_times else 0
        
        # Create report
        report = {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "filters": {
                "job_type": job_type,
                "priority": priority
            },
            "summary": {
                "total_jobs_with_sla": total_jobs,
                "completed_jobs": len(completed_jobs),
                "sla_met": sla_met,
                "sla_breached": len(completed_jobs) - sla_met,
                "overall_compliance_rate": round(overall_compliance_rate, 2),
                "avg_breach_time_minutes": round(avg_breach_time, 2)
            },
            "compliance_by_type": compliance_by_type,
            "compliance_by_priority": compliance_by_priority
        }
        
        # Add HATEOAS links
        report["links"] = [
            {"rel": "self", "href": f"/api/field-services/reports/sla-compliance"}
        ]
        
        return report
    
    def get_inventory_usage_report(
        self, 
        start_date: datetime,
        end_date: datetime,
        inventory_id: Optional[int] = None,
        technician_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate inventory usage report for the specified period.
        
        Includes metrics like total usage by inventory type, usage by technician,
        and inventory turnover rate.
        """
        # Base query for inventory transactions within date range
        query = self.db.query(InventoryTransaction).filter(
            InventoryTransaction.created_at.between(start_date, end_date),
            InventoryTransaction.transaction_type == InventoryTransactionTypeEnum.USAGE
        )
        
        # Apply filters if provided
        if inventory_id:
            query = query.filter(InventoryTransaction.inventory_id == inventory_id)
        
        if technician_id:
            query = query.filter(InventoryTransaction.technician_id == technician_id)
        
        # Execute query
        transactions = query.all()
        
        # Calculate metrics
        total_transactions = len(transactions)
        total_quantity_used = sum(abs(t.quantity) for t in transactions)
        
        # Usage by inventory type
        usage_by_inventory = {}
        for transaction in transactions:
            inventory_id = transaction.inventory_id
            if inventory_id not in usage_by_inventory:
                # Get inventory details
                inventory = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
                inventory_name = inventory.name if inventory else f"Item {inventory_id}"
                inventory_type = inventory.inventory_type.value if inventory else "Unknown"
                
                usage_by_inventory[inventory_id] = {
                    "inventory_id": inventory_id,
                    "name": inventory_name,
                    "type": inventory_type,
                    "quantity_used": 0,
                    "job_count": 0,
                    "links": [
                        {"rel": "inventory", "href": f"/api/field-services/inventory/{inventory_id}"}
                    ]
                }
            
            usage_by_inventory[inventory_id]["quantity_used"] += abs(transaction.quantity)
            if transaction.job_id:
                usage_by_inventory[inventory_id]["job_count"] += 1
        
        # Usage by technician
        usage_by_technician = {}
        for transaction in transactions:
            technician_id = transaction.technician_id
            if technician_id and technician_id not in usage_by_technician:
                # Get technician details
                technician = self.db.query(Technician).filter(Technician.id == technician_id).first()
                technician_name = f"{technician.first_name} {technician.last_name}" if technician else f"Technician {technician_id}"
                
                usage_by_technician[technician_id] = {
                    "technician_id": technician_id,
                    "name": technician_name,
                    "quantity_used": 0,
                    "unique_inventory_items": set(),
                    "links": [
                        {"rel": "technician", "href": f"/api/field-services/technicians/{technician_id}"}
                    ]
                }
            
            if technician_id:
                usage_by_technician[technician_id]["quantity_used"] += abs(transaction.quantity)
                usage_by_technician[technician_id]["unique_inventory_items"].add(transaction.inventory_id)
        
        # Convert sets to counts for JSON serialization
        for tech_id in usage_by_technician:
            usage_by_technician[tech_id]["unique_inventory_count"] = len(usage_by_technician[tech_id]["unique_inventory_items"])
            del usage_by_technician[tech_id]["unique_inventory_items"]
        
        # Create report
        report = {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "filters": {
                "inventory_id": inventory_id,
                "technician_id": technician_id
            },
            "summary": {
                "total_transactions": total_transactions,
                "total_quantity_used": total_quantity_used
            },
            "usage_by_inventory": list(usage_by_inventory.values()),
            "usage_by_technician": list(usage_by_technician.values())
        }
        
        # Add HATEOAS links
        report["links"] = [
            {"rel": "self", "href": f"/api/field-services/reports/inventory-usage"}
        ]
        
        return report
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get key metrics for the field services dashboard.
        
        Includes summary metrics for today, this week, and this month.
        """
        # Calculate date ranges
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
        today_end = datetime(now.year, now.month, now.day, 23, 59, 59)
        
        # Calculate week start (Monday) and end (Sunday)
        week_start = now - timedelta(days=now.weekday())
        week_start = datetime(week_start.year, week_start.month, week_start.day, 0, 0, 0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # Calculate month start and end
        month_start = datetime(now.year, now.month, 1, 0, 0, 0)
        month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1], 23, 59, 59)
        
        # Get metrics for each time period
        today_metrics = self._get_period_metrics(today_start, today_end)
        week_metrics = self._get_period_metrics(week_start, week_end)
        month_metrics = self._get_period_metrics(month_start, month_end)
        
        # Get active technicians
        active_technicians = self.db.query(Technician).filter(
            Technician.status == TechnicianStatusEnum.AVAILABLE
        ).count()
        
        # Get jobs at risk of SLA breach
        jobs_at_risk = self.db.query(Job).filter(
            Job.status.in_([JobStatusEnum.ASSIGNED, JobStatusEnum.IN_PROGRESS]),
            Job.sla_deadline.between(now, now + timedelta(hours=4))
        ).count()
        
        # Create dashboard metrics
        dashboard = {
            "current_time": now,
            "active_technicians": active_technicians,
            "jobs_at_risk": jobs_at_risk,
            "today": {
                "period": {
                    "start": today_start,
                    "end": today_end
                },
                "metrics": today_metrics
            },
            "this_week": {
                "period": {
                    "start": week_start,
                    "end": week_end
                },
                "metrics": week_metrics
            },
            "this_month": {
                "period": {
                    "start": month_start,
                    "end": month_end
                },
                "metrics": month_metrics
            }
        }
        
        # Add HATEOAS links
        dashboard["links"] = [
            {"rel": "self", "href": f"/api/field-services/reports/dashboard"},
            {"rel": "job_performance", "href": f"/api/field-services/reports/job-performance"},
            {"rel": "technician_efficiency", "href": f"/api/field-services/reports/technician-efficiency"},
            {"rel": "sla_compliance", "href": f"/api/field-services/reports/sla-compliance"},
            {"rel": "inventory_usage", "href": f"/api/field-services/reports/inventory-usage"}
        ]
        
        return dashboard
    
    def _get_period_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get key metrics for a specific time period."""
        # Get jobs created in period
        jobs_created = self.db.query(Job).filter(
            Job.created_at.between(start_date, end_date)
        ).count()
        
        # Get jobs completed in period
        jobs_completed = self.db.query(Job).filter(
            Job.status == JobStatusEnum.COMPLETED,
            Job.actual_end_time.between(start_date, end_date)
        ).count()
        
        # Get SLA compliance for completed jobs
        completed_jobs_with_sla = self.db.query(Job).filter(
            Job.status == JobStatusEnum.COMPLETED,
            Job.actual_end_time.between(start_date, end_date),
            Job.sla_deadline.isnot(None)
        ).all()
        
        sla_met = sum(1 for job in completed_jobs_with_sla if job.actual_end_time <= job.sla_deadline)
        sla_compliance = (sla_met / len(completed_jobs_with_sla) * 100) if completed_jobs_with_sla else 0
        
        # Get average resolution time
        completed_jobs = self.db.query(Job).filter(
            Job.status == JobStatusEnum.COMPLETED,
            Job.actual_end_time.between(start_date, end_date),
            Job.actual_start_time.isnot(None)
        ).all()
        
        resolution_times = [(job.actual_end_time - job.actual_start_time).total_seconds() / 60 for job in completed_jobs]
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Return metrics
        return {
            "jobs_created": jobs_created,
            "jobs_completed": jobs_completed,
            "sla_compliance_rate": round(sla_compliance, 2),
            "avg_resolution_time_minutes": round(avg_resolution_time, 2)
        }
    
    def _calculate_working_days(self, start_date: datetime, end_date: datetime) -> int:
        """Calculate the number of working days (Mon-Fri) between two dates."""
        # Convert to date objects
        start = start_date.date()
        end = end_date.date()
        
        # Calculate total days
        days = (end - start).days + 1
        
        # Calculate complete weeks
        weeks = days // 7
        
        # Calculate remaining days
        remaining_days = days % 7
        
        # Calculate start weekday (0 = Monday, 6 = Sunday)
        start_weekday = start.weekday()
        
        # Calculate working days in complete weeks
        working_days = weeks * 5
        
        # Add working days in remaining days
        for i in range(remaining_days):
            weekday = (start_weekday + i) % 7
            if weekday < 5:  # Monday to Friday
                working_days += 1
        
        return working_days
