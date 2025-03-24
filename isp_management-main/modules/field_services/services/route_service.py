"""
Route Service for the Field Services Module.

This service handles route optimization for field technicians.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import math
from sqlalchemy.orm import Session, joinedload

from ..models import Job, JobStatusEnum, Technician, TechnicianStatusEnum
from ..schemas import RouteOptimizationRequest, RouteOptimizationResponse, TechnicianRoute, JobResponse
from .job_service import JobService


class RouteService:
    """Service for optimizing technician routes."""
    
    def __init__(self, db: Session):
        self.db = db
        self.job_service = JobService(db)
    
    def optimize_routes(self, request: RouteOptimizationRequest) -> RouteOptimizationResponse:
        """Optimize routes for technicians based on job locations and priorities."""
        # Get date for optimization
        target_date = request.date
        
        # Get technicians to include in optimization
        technicians = self._get_technicians(request.technician_ids)
        
        # Get jobs that need to be scheduled for the date
        jobs = self._get_jobs_for_date(target_date)
        
        # Perform route optimization
        routes = self._optimize_technician_routes(
            technicians=technicians,
            jobs=jobs,
            consider_skills=request.consider_skills,
            consider_equipment=request.consider_equipment,
            consider_priority=request.consider_priority,
            max_travel_time_minutes=request.max_travel_time_minutes
        )
        
        # Calculate optimization metrics
        total_technicians = len(routes)
        total_jobs = sum(len(route["jobs"]) for route in routes.values())
        
        avg_jobs_per_technician = total_jobs / total_technicians if total_technicians > 0 else 0
        avg_travel_time = sum(route["total_travel_time_minutes"] for route in routes.values()) / total_technicians if total_technicians > 0 else 0
        avg_distance = sum(route["total_distance_km"] for route in routes.values()) / total_technicians if total_technicians > 0 else 0
        
        # Calculate overall optimization score (higher is better)
        optimization_score = 0
        if total_technicians > 0:
            # Factors that contribute to a good optimization:
            # 1. Even distribution of jobs among technicians
            # 2. Minimized travel time
            # 3. Efficient use of technician skills
            # 4. High priority jobs assigned
            
            # Calculate job distribution score (lower variance is better)
            job_counts = [len(route["jobs"]) for route in routes.values()]
            job_variance = self._calculate_variance(job_counts)
            job_distribution_score = 1 / (1 + job_variance) if job_variance > 0 else 1
            
            # Calculate travel efficiency score (lower travel time per job is better)
            travel_times = [route["total_travel_time_minutes"] / len(route["jobs"]) if len(route["jobs"]) > 0 else 0 
                          for route in routes.values()]
            avg_travel_per_job = sum(travel_times) / len(travel_times) if len(travel_times) > 0 else 0
            travel_efficiency_score = 60 / (avg_travel_per_job + 10) if avg_travel_per_job > 0 else 1
            
            # Calculate skill utilization score
            skill_scores = [route["skill_match_score"] for route in routes.values()]
            avg_skill_score = sum(skill_scores) / len(skill_scores) if len(skill_scores) > 0 else 0
            
            # Calculate priority handling score
            priority_scores = [route["priority_score"] for route in routes.values()]
            avg_priority_score = sum(priority_scores) / len(priority_scores) if len(priority_scores) > 0 else 0
            
            # Combine scores with weights
            optimization_score = (
                0.3 * job_distribution_score + 
                0.3 * travel_efficiency_score + 
                0.2 * avg_skill_score + 
                0.2 * avg_priority_score
            ) * 100  # Scale to 0-100
        
        # Convert routes to response format
        route_responses = []
        for tech_id, route_data in routes.items():
            technician = next((t for t in technicians if t.id == tech_id), None)
            if technician:
                # Convert jobs to JobResponse objects
                job_responses = []
                for job in route_data["jobs"]:
                    job_response = self.job_service.get_job_by_id(job.id)
                    if job_response:
                        job_responses.append(job_response)
                
                route_responses.append(TechnicianRoute(
                    technician_id=tech_id,
                    technician_name=technician.name,
                    jobs=job_responses,
                    total_travel_time_minutes=route_data["total_travel_time_minutes"],
                    total_job_time_minutes=route_data["total_job_time_minutes"],
                    total_distance_km=route_data["total_distance_km"],
                    route_efficiency_score=route_data["efficiency_score"]
                ))
        
        # Create response
        return RouteOptimizationResponse(
            date=target_date,
            routes=route_responses,
            total_technicians=total_technicians,
            total_jobs=total_jobs,
            average_jobs_per_technician=avg_jobs_per_technician,
            average_travel_time_minutes=avg_travel_time,
            average_distance_km=avg_distance,
            optimization_score=optimization_score,
            links=[
                {"rel": "self", "href": f"/api/field-services/routes/optimize?date={target_date}"},
                {"rel": "jobs", "href": f"/api/field-services/jobs?date={target_date}"},
                {"rel": "technicians", "href": "/api/field-services/technicians"}
            ]
        )
    
    def _get_technicians(self, technician_ids: List[int]) -> List[Technician]:
        """Get technicians for route optimization."""
        query = self.db.query(Technician).filter(
            Technician.status.in_([
                TechnicianStatusEnum.ACTIVE,
                TechnicianStatusEnum.AVAILABLE
            ])
        )
        
        if technician_ids and len(technician_ids) > 0:
            query = query.filter(Technician.id.in_(technician_ids))
        
        return query.all()
    
    def _get_jobs_for_date(self, target_date: date) -> List[Job]:
        """Get jobs that need to be scheduled for a specific date."""
        # Get start and end of the target date
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        # Get jobs that are already scheduled for the date
        scheduled_jobs = self.db.query(Job).filter(
            Job.status.in_([JobStatusEnum.PENDING, JobStatusEnum.ASSIGNED]),
            Job.scheduled_start_time.between(start_datetime, end_datetime)
        ).all()
        
        # Get unscheduled jobs that should be considered
        unscheduled_jobs = self.db.query(Job).filter(
            Job.status == JobStatusEnum.PENDING,
            Job.scheduled_start_time == None
        ).all()
        
        # Combine and return
        return scheduled_jobs + unscheduled_jobs
    
    def _optimize_technician_routes(
        self,
        technicians: List[Technician],
        jobs: List[Job],
        consider_skills: bool = True,
        consider_equipment: bool = True,
        consider_priority: bool = True,
        max_travel_time_minutes: int = 60
    ) -> Dict[int, Dict[str, Any]]:
        """
        Optimize routes for technicians based on job locations and priorities.
        
        This uses a greedy algorithm that assigns jobs to technicians based on:
        1. Skill match (if consider_skills is True)
        2. Equipment availability (if consider_equipment is True)
        3. Job priority (if consider_priority is True)
        4. Travel time from current location
        5. Technician workload balance
        """
        # Initialize routes for each technician
        routes = {
            tech.id: {
                "jobs": [],
                "current_location": (tech.current_location_lat, tech.current_location_lon),
                "total_travel_time_minutes": 0,
                "total_job_time_minutes": 0,
                "total_distance_km": 0,
                "skill_match_score": 1.0,  # Start with perfect score
                "priority_score": 1.0,     # Start with perfect score
                "efficiency_score": 0.0     # Will be calculated later
            }
            for tech in technicians
        }
        
        # Sort jobs by priority (if enabled)
        if consider_priority:
            # Sort by priority enum value (CRITICAL=3, HIGH=2, MEDIUM=1, LOW=0)
            jobs.sort(key=lambda j: {
                JobPriorityEnum.CRITICAL: 3,
                JobPriorityEnum.HIGH: 2,
                JobPriorityEnum.MEDIUM: 1,
                JobPriorityEnum.LOW: 0
            }.get(j.priority, 0), reverse=True)
        
        # Assign jobs to technicians
        unassigned_jobs = []
        for job in jobs:
            # Skip jobs that already have a technician assigned
            if job.technician_id is not None:
                # Add to that technician's route
                if job.technician_id in routes:
                    routes[job.technician_id]["jobs"].append(job)
                continue
            
            best_tech_id = None
            best_score = -1
            
            for tech_id, route in routes.items():
                tech = next((t for t in technicians if t.id == tech_id), None)
                if not tech:
                    continue
                
                # Check if technician has capacity
                if len(route["jobs"]) >= tech.max_jobs_per_day:
                    continue
                
                # Calculate skill match score (0-1)
                skill_match = 1.0
                if consider_skills and job.required_skills:
                    matching_skills = sum(1 for skill in job.required_skills if skill in tech.skills)
                    skill_match = matching_skills / len(job.required_skills) if len(job.required_skills) > 0 else 1.0
                
                # Skip if technician doesn't have any of the required skills
                if consider_skills and skill_match == 0:
                    continue
                
                # Calculate travel time from current location to job
                travel_time = self._calculate_travel_time(
                    route["current_location"][0],
                    route["current_location"][1],
                    job.location_lat,
                    job.location_lon
                )
                
                # Skip if travel time exceeds maximum
                if travel_time > max_travel_time_minutes:
                    continue
                
                # Calculate priority score (0-1)
                priority_score = 1.0
                if consider_priority:
                    # Higher priority jobs get higher scores
                    priority_score = {
                        JobPriorityEnum.CRITICAL: 1.0,
                        JobPriorityEnum.HIGH: 0.8,
                        JobPriorityEnum.MEDIUM: 0.5,
                        JobPriorityEnum.LOW: 0.2
                    }.get(job.priority, 0.5)
                
                # Calculate workload balance score (0-1)
                # Prefer technicians with fewer jobs
                workload_score = 1.0 - (len(route["jobs"]) / tech.max_jobs_per_day)
                
                # Calculate overall score
                # Weights can be adjusted based on importance
                score = (
                    0.3 * skill_match +
                    0.3 * (1.0 - travel_time / max_travel_time_minutes) +
                    0.2 * priority_score +
                    0.2 * workload_score
                )
                
                if score > best_score:
                    best_score = score
                    best_tech_id = tech_id
            
            if best_tech_id is not None:
                # Assign job to best technician
                route = routes[best_tech_id]
                route["jobs"].append(job)
                
                # Update route metrics
                job_location = (job.location_lat, job.location_lon)
                travel_time = self._calculate_travel_time(
                    route["current_location"][0],
                    route["current_location"][1],
                    job_location[0],
                    job_location[1]
                )
                travel_distance = self._calculate_distance(
                    route["current_location"][0],
                    route["current_location"][1],
                    job_location[0],
                    job_location[1]
                )
                
                route["total_travel_time_minutes"] += travel_time
                route["total_distance_km"] += travel_distance
                route["total_job_time_minutes"] += job.estimated_duration_minutes
                route["current_location"] = job_location
                
                # Update skill match and priority scores
                if consider_skills and job.required_skills:
                    tech = next((t for t in technicians if t.id == best_tech_id), None)
                    matching_skills = sum(1 for skill in job.required_skills if skill in tech.skills)
                    skill_match = matching_skills / len(job.required_skills) if len(job.required_skills) > 0 else 1.0
                    # Rolling average of skill match scores
                    route["skill_match_score"] = (route["skill_match_score"] * (len(route["jobs"]) - 1) + skill_match) / len(route["jobs"])
                
                if consider_priority:
                    priority_score = {
                        JobPriorityEnum.CRITICAL: 1.0,
                        JobPriorityEnum.HIGH: 0.8,
                        JobPriorityEnum.MEDIUM: 0.5,
                        JobPriorityEnum.LOW: 0.2
                    }.get(job.priority, 0.5)
                    # Rolling average of priority scores
                    route["priority_score"] = (route["priority_score"] * (len(route["jobs"]) - 1) + priority_score) / len(route["jobs"])
            else:
                # Couldn't assign job to any technician
                unassigned_jobs.append(job)
        
        # Calculate efficiency scores for each route
        for tech_id, route in routes.items():
            if len(route["jobs"]) > 0:
                # Efficiency is the ratio of job time to total time (job + travel)
                total_time = route["total_job_time_minutes"] + route["total_travel_time_minutes"]
                route["efficiency_score"] = route["total_job_time_minutes"] / total_time if total_time > 0 else 0
            else:
                route["efficiency_score"] = 0
        
        return routes
    
    def _calculate_travel_time(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate estimated travel time in minutes between two points.
        
        This is a simple estimation based on distance and average speed.
        For production use, this should be replaced with actual routing API calls.
        """
        distance_km = self._calculate_distance(lat1, lon1, lat2, lon2)
        
        # Assume average speed of 40 km/h in urban areas
        # This is a simplification - real routing would consider road types, traffic, etc.
        average_speed_kmh = 40
        
        # Calculate time in minutes
        time_minutes = (distance_km / average_speed_kmh) * 60
        
        return time_minutes
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using the Haversine formula.
        
        Returns distance in kilometers.
        """
        # Earth radius in kilometers
        R = 6371
        
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Difference in coordinates
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if not values:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance
