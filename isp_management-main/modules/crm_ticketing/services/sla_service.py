"""
SLA service for the CRM & Ticketing module.

This service provides functionality for managing Service Level Agreements (SLAs),
including creation, updates, and SLA metrics tracking.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from fastapi import HTTPException, status

from modules.monitoring.services import LoggingService
from ..models.sla import SLA, SLAMetric
from ..models.common import TicketPriority, TicketStatus
from ..schemas.sla import SLACreate, SLAUpdate, SLAMetricCreate, SLAMetricUpdate


class SLAService:
    """Service for managing Service Level Agreements (SLAs)."""
    
    def __init__(self, db: Session):
        """Initialize the SLA service with a database session."""
        self.db = db
        self.logging_service = LoggingService(db)
    
    def get_sla(self, sla_id: int) -> SLA:
        """
        Get an SLA by ID.
        
        Args:
            sla_id: The ID of the SLA to retrieve
            
        Returns:
            The SLA object
            
        Raises:
            HTTPException: If the SLA is not found
        """
        sla = self.db.query(SLA).filter(SLA.id == sla_id).first()
        if not sla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SLA with ID {sla_id} not found"
            )
        return sla
    
    def get_default_sla(self) -> Optional[SLA]:
        """
        Get the default SLA.
        
        Returns:
            The default SLA object, or None if no default SLA is set
        """
        return self.db.query(SLA).filter(SLA.is_default == True).first()
    
    def list_slas(self, skip: int = 0, limit: int = 100) -> List[SLA]:
        """
        List all SLAs.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of SLA objects
        """
        return self.db.query(SLA).order_by(asc(SLA.name)).offset(skip).limit(limit).all()
    
    def create_sla(self, sla_data: SLACreate, user_id: int) -> SLA:
        """
        Create a new SLA.
        
        Args:
            sla_data: Data for the new SLA
            user_id: The ID of the user creating the SLA
            
        Returns:
            The created SLA object
            
        Raises:
            HTTPException: If an SLA with the same name already exists
        """
        # Check if an SLA with the same name already exists
        existing_sla = self.db.query(SLA).filter(SLA.name == sla_data.name).first()
        if existing_sla:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SLA with name '{sla_data.name}' already exists"
            )
        
        # If this is set as default, unset any existing default
        if sla_data.is_default:
            self._unset_default_sla()
        
        # Create SLA
        sla = SLA(
            name=sla_data.name,
            description=sla_data.description,
            is_default=sla_data.is_default,
            created_by=user_id
        )
        
        self.db.add(sla)
        self.db.commit()
        self.db.refresh(sla)
        
        # Log SLA creation
        self.logging_service.log_event(
            "sla_created",
            f"SLA '{sla.name}' created by user {user_id}",
            {
                "sla_id": sla.id,
                "sla_name": sla.name,
                "user_id": user_id
            }
        )
        
        return sla
    
    def update_sla(self, sla_id: int, sla_data: SLAUpdate, user_id: int) -> SLA:
        """
        Update an existing SLA.
        
        Args:
            sla_id: The ID of the SLA to update
            sla_data: New data for the SLA
            user_id: The ID of the user updating the SLA
            
        Returns:
            The updated SLA object
            
        Raises:
            HTTPException: If the SLA is not found or if an SLA with the same name already exists
        """
        # Get the SLA
        sla = self.get_sla(sla_id)
        
        # Check if name is being updated and if an SLA with the same name already exists
        if sla_data.name and sla_data.name != sla.name:
            existing_sla = self.db.query(SLA).filter(SLA.name == sla_data.name).first()
            if existing_sla:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SLA with name '{sla_data.name}' already exists"
                )
        
        # If this is being set as default, unset any existing default
        if sla_data.is_default is not None and sla_data.is_default and not sla.is_default:
            self._unset_default_sla()
        
        # Update SLA
        for field, value in sla_data.dict(exclude_unset=True).items():
            setattr(sla, field, value)
        
        sla.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(sla)
        
        # Log SLA update
        self.logging_service.log_event(
            "sla_updated",
            f"SLA '{sla.name}' updated by user {user_id}",
            {
                "sla_id": sla.id,
                "sla_name": sla.name,
                "user_id": user_id
            }
        )
        
        return sla
    
    def delete_sla(self, sla_id: int, user_id: int) -> None:
        """
        Delete an SLA.
        
        Args:
            sla_id: The ID of the SLA to delete
            user_id: The ID of the user deleting the SLA
            
        Raises:
            HTTPException: If the SLA is not found or if it is in use
        """
        # Get the SLA
        sla = self.get_sla(sla_id)
        
        # Check if the SLA is in use by any tickets
        if sla.tickets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete SLA '{sla.name}' as it is in use by {len(sla.tickets)} tickets"
            )
        
        # Get SLA info for logging
        sla_name = sla.name
        
        # Delete the SLA
        self.db.delete(sla)
        self.db.commit()
        
        # Log SLA deletion
        self.logging_service.log_event(
            "sla_deleted",
            f"SLA '{sla_name}' deleted by user {user_id}",
            {
                "sla_id": sla_id,
                "sla_name": sla_name,
                "user_id": user_id
            }
        )
    
    def _unset_default_sla(self) -> None:
        """
        Unset the current default SLA.
        """
        default_sla = self.get_default_sla()
        if default_sla:
            default_sla.is_default = False
            self.db.commit()
    
    # SLA Metric Methods
    
    def get_sla_metric(self, metric_id: int) -> SLAMetric:
        """
        Get an SLA metric by ID.
        
        Args:
            metric_id: The ID of the SLA metric to retrieve
            
        Returns:
            The SLA metric object
            
        Raises:
            HTTPException: If the SLA metric is not found
        """
        metric = self.db.query(SLAMetric).filter(SLAMetric.id == metric_id).first()
        if not metric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SLA metric with ID {metric_id} not found"
            )
        return metric
    
    def list_sla_metrics(
        self, 
        sla_id: Optional[int] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[SLAMetric]:
        """
        List SLA metrics, optionally filtered by SLA ID.
        
        Args:
            sla_id: Optional SLA ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of SLA metric objects
        """
        query = self.db.query(SLAMetric)
        
        if sla_id:
            query = query.filter(SLAMetric.sla_id == sla_id)
        
        return query.order_by(asc(SLAMetric.priority), asc(SLAMetric.metric_type)).offset(skip).limit(limit).all()
    
    def create_sla_metric(self, metric_data: SLAMetricCreate, user_id: int) -> SLAMetric:
        """
        Create a new SLA metric.
        
        Args:
            metric_data: Data for the new SLA metric
            user_id: The ID of the user creating the SLA metric
            
        Returns:
            The created SLA metric object
            
        Raises:
            HTTPException: If the SLA is not found or if a duplicate metric exists
        """
        # Check that the SLA exists
        sla = self.get_sla(metric_data.sla_id)
        
        # Check for duplicate metric (same SLA, priority, and metric type)
        existing_metric = self.db.query(SLAMetric).filter(
            SLAMetric.sla_id == metric_data.sla_id,
            SLAMetric.priority == metric_data.priority,
            SLAMetric.metric_type == metric_data.metric_type
        ).first()
        
        if existing_metric:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SLA metric for {metric_data.metric_type} with priority {metric_data.priority} already exists for this SLA"
            )
        
        # Create SLA metric
        metric = SLAMetric(
            sla_id=metric_data.sla_id,
            priority=metric_data.priority,
            metric_type=metric_data.metric_type,
            threshold_hours=metric_data.threshold_hours,
            threshold_minutes=metric_data.threshold_minutes,
            created_by=user_id
        )
        
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        
        # Log SLA metric creation
        self.logging_service.log_event(
            "sla_metric_created",
            f"SLA metric for {metric.metric_type} with priority {metric.priority} created for SLA '{sla.name}' by user {user_id}",
            {
                "sla_id": sla.id,
                "sla_name": sla.name,
                "metric_id": metric.id,
                "metric_type": metric.metric_type,
                "priority": metric.priority,
                "user_id": user_id
            }
        )
        
        return metric
    
    def update_sla_metric(
        self, 
        metric_id: int, 
        metric_data: SLAMetricUpdate, 
        user_id: int
    ) -> SLAMetric:
        """
        Update an existing SLA metric.
        
        Args:
            metric_id: The ID of the SLA metric to update
            metric_data: New data for the SLA metric
            user_id: The ID of the user updating the SLA metric
            
        Returns:
            The updated SLA metric object
            
        Raises:
            HTTPException: If the SLA metric is not found or if a duplicate metric would be created
        """
        # Get the SLA metric
        metric = self.get_sla_metric(metric_id)
        
        # Check for potential duplicate if priority or metric type is changing
        if (metric_data.priority and metric_data.priority != metric.priority) or \
           (metric_data.metric_type and metric_data.metric_type != metric.metric_type):
            
            # Determine the new values
            new_priority = metric_data.priority if metric_data.priority is not None else metric.priority
            new_metric_type = metric_data.metric_type if metric_data.metric_type is not None else metric.metric_type
            
            # Check for duplicate
            existing_metric = self.db.query(SLAMetric).filter(
                SLAMetric.sla_id == metric.sla_id,
                SLAMetric.priority == new_priority,
                SLAMetric.metric_type == new_metric_type,
                SLAMetric.id != metric_id
            ).first()
            
            if existing_metric:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SLA metric for {new_metric_type} with priority {new_priority} already exists for this SLA"
                )
        
        # Update SLA metric
        for field, value in metric_data.dict(exclude_unset=True).items():
            setattr(metric, field, value)
        
        metric.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(metric)
        
        # Log SLA metric update
        self.logging_service.log_event(
            "sla_metric_updated",
            f"SLA metric for {metric.metric_type} with priority {metric.priority} updated for SLA '{metric.sla.name}' by user {user_id}",
            {
                "sla_id": metric.sla_id,
                "sla_name": metric.sla.name,
                "metric_id": metric.id,
                "metric_type": metric.metric_type,
                "priority": metric.priority,
                "user_id": user_id
            }
        )
        
        return metric
    
    def delete_sla_metric(self, metric_id: int, user_id: int) -> None:
        """
        Delete an SLA metric.
        
        Args:
            metric_id: The ID of the SLA metric to delete
            user_id: The ID of the user deleting the SLA metric
            
        Raises:
            HTTPException: If the SLA metric is not found
        """
        # Get the SLA metric
        metric = self.get_sla_metric(metric_id)
        
        # Get metric info for logging
        sla_id = metric.sla_id
        sla_name = metric.sla.name
        metric_type = metric.metric_type
        priority = metric.priority
        
        # Delete the SLA metric
        self.db.delete(metric)
        self.db.commit()
        
        # Log SLA metric deletion
        self.logging_service.log_event(
            "sla_metric_deleted",
            f"SLA metric for {metric_type} with priority {priority} deleted from SLA '{sla_name}' by user {user_id}",
            {
                "sla_id": sla_id,
                "sla_name": sla_name,
                "metric_id": metric_id,
                "metric_type": metric_type,
                "priority": priority,
                "user_id": user_id
            }
        )
    
    def get_sla_target(
        self, 
        sla_id: int, 
        priority: TicketPriority, 
        metric_type: str
    ) -> Optional[timedelta]:
        """
        Get the SLA target time for a specific priority and metric type.
        
        Args:
            sla_id: The ID of the SLA
            priority: The ticket priority
            metric_type: The type of SLA metric (e.g., 'first_response', 'resolution')
            
        Returns:
            The target time as a timedelta, or None if no metric is defined
        """
        metric = self.db.query(SLAMetric).filter(
            SLAMetric.sla_id == sla_id,
            SLAMetric.priority == priority,
            SLAMetric.metric_type == metric_type
        ).first()
        
        if not metric:
            return None
        
        return timedelta(hours=metric.threshold_hours, minutes=metric.threshold_minutes)
    
    def calculate_sla_performance(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        sla_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate SLA performance metrics for a given time period.
        
        Args:
            start_date: The start date for the calculation
            end_date: The end date for the calculation
            sla_id: Optional SLA ID to filter by
            
        Returns:
            A dictionary containing SLA performance metrics
        """
        from ..models.ticket import Ticket
        
        # Build base query for tickets in the date range
        query = self.db.query(Ticket).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        # Filter by SLA if provided
        if sla_id:
            query = query.filter(Ticket.sla_id == sla_id)
        
        # Get all tickets in the range
        tickets = query.all()
        
        # Initialize results
        results = {
            "total_tickets": len(tickets),
            "resolved_tickets": 0,
            "first_response_breached": 0,
            "resolution_breached": 0,
            "sla_compliance_percentage": 0,
            "average_first_response_time": None,
            "average_resolution_time": None,
            "by_priority": {}
        }
        
        # Initialize priority-specific metrics
        for priority in TicketPriority:
            results["by_priority"][priority.value] = {
                "total": 0,
                "resolved": 0,
                "first_response_breached": 0,
                "resolution_breached": 0,
                "sla_compliance_percentage": 0,
                "average_first_response_time": None,
                "average_resolution_time": None
            }
        
        # Calculate metrics
        first_response_times = []
        resolution_times = []
        priority_first_response_times = {p.value: [] for p in TicketPriority}
        priority_resolution_times = {p.value: [] for p in TicketPriority}
        
        for ticket in tickets:
            priority = ticket.priority.value
            results["by_priority"][priority]["total"] += 1
            
            # First response metrics
            if ticket.first_response_at:
                response_time = (ticket.first_response_at - ticket.created_at).total_seconds() / 3600  # hours
                first_response_times.append(response_time)
                priority_first_response_times[priority].append(response_time)
                
                if ticket.first_response_target and ticket.first_response_at > ticket.first_response_target:
                    results["first_response_breached"] += 1
                    results["by_priority"][priority]["first_response_breached"] += 1
            
            # Resolution metrics
            if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                results["resolved_tickets"] += 1
                results["by_priority"][priority]["resolved"] += 1
                
                resolution_date = ticket.resolved_at or ticket.closed_at
                if resolution_date:
                    resolution_time = (resolution_date - ticket.created_at).total_seconds() / 3600  # hours
                    resolution_times.append(resolution_time)
                    priority_resolution_times[priority].append(resolution_time)
                    
                    if ticket.resolution_target and resolution_date > ticket.resolution_target:
                        results["resolution_breached"] += 1
                        results["by_priority"][priority]["resolution_breached"] += 1
        
        # Calculate averages and compliance
        if first_response_times:
            results["average_first_response_time"] = sum(first_response_times) / len(first_response_times)
        
        if resolution_times:
            results["average_resolution_time"] = sum(resolution_times) / len(resolution_times)
        
        # Calculate overall SLA compliance
        if results["resolved_tickets"] > 0:
            total_breaches = results["first_response_breached"] + results["resolution_breached"]
            total_possible_breaches = results["total_tickets"] + results["resolved_tickets"]
            compliance = 100 - (total_breaches / total_possible_breaches * 100)
            results["sla_compliance_percentage"] = round(compliance, 2)
        
        # Calculate priority-specific metrics
        for priority in TicketPriority:
            p_value = priority.value
            p_results = results["by_priority"][p_value]
            
            if priority_first_response_times[p_value]:
                p_results["average_first_response_time"] = sum(priority_first_response_times[p_value]) / len(priority_first_response_times[p_value])
            
            if priority_resolution_times[p_value]:
                p_results["average_resolution_time"] = sum(priority_resolution_times[p_value]) / len(priority_resolution_times[p_value])
            
            if p_results["resolved"] > 0:
                total_p_breaches = p_results["first_response_breached"] + p_results["resolution_breached"]
                total_p_possible_breaches = p_results["total"] + p_results["resolved"]
                p_compliance = 100 - (total_p_breaches / total_p_possible_breaches * 100)
                p_results["sla_compliance_percentage"] = round(p_compliance, 2)
        
        return results
