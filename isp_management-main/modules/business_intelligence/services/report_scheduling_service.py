"""
Report scheduling service for the Business Intelligence and Reporting module.

This module provides services for managing scheduled reports, including
creation, updating, and scheduling of report executions.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
import croniter

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, status

from backend_core.database import get_db_session
from backend_core.services.auth_service import get_user_permissions
from ..models.report import (
    ReportTemplate, ScheduledReport, ReportExecution, ReportOutput,
    ReportStatus, ReportFormat, ReportFrequency
)
from ..schemas.report import (
    ScheduledReportCreate, ScheduledReportUpdate, ScheduledReportResponse,
    ScheduledReportSearchParams, PaginationParams, PaginatedResponse
)
from .report_service import ReportService

logger = logging.getLogger(__name__)


class ReportSchedulingService:
    """Service for managing scheduled reports."""

    def __init__(self):
        """Initialize the report scheduling service."""
        self.report_service = ReportService()

    def create_scheduled_report(
        self, db: Session, scheduled_report: ScheduledReportCreate, user_id: int
    ) -> ScheduledReport:
        """
        Create a new scheduled report.
        
        Args:
            db: Database session
            scheduled_report: Scheduled report data
            user_id: ID of the user creating the scheduled report
            
        Returns:
            Created scheduled report
        """
        # Validate template exists
        template = self.report_service.get_report_template(
            db, scheduled_report.template_id, user_id
        )
        
        # Validate parameters against template schema if provided
        if scheduled_report.parameters and template.parameters_schema:
            self._validate_parameters(scheduled_report.parameters, template.parameters_schema)
        
        # Calculate next execution time
        next_execution_time = self._calculate_next_execution_time(
            scheduled_report.frequency,
            scheduled_report.cron_expression
        )
        
        # Create scheduled report
        db_scheduled_report = ScheduledReport(
            name=scheduled_report.name,
            description=scheduled_report.description,
            template_id=scheduled_report.template_id,
            frequency=scheduled_report.frequency,
            cron_expression=scheduled_report.cron_expression,
            parameters=scheduled_report.parameters,
            delivery_method=scheduled_report.delivery_method,
            delivery_config=scheduled_report.delivery_config,
            is_active=scheduled_report.is_active,
            next_execution_time=next_execution_time,
            created_by_id=user_id
        )
        
        db.add(db_scheduled_report)
        db.commit()
        db.refresh(db_scheduled_report)
        
        return db_scheduled_report

    def get_scheduled_report(
        self, db: Session, scheduled_report_id: int, user_id: int
    ) -> ScheduledReport:
        """
        Get a scheduled report by ID.
        
        Args:
            db: Database session
            scheduled_report_id: ID of the scheduled report to retrieve
            user_id: ID of the user requesting the scheduled report
            
        Returns:
            Scheduled report
        """
        scheduled_report = db.query(ScheduledReport).filter(
            ScheduledReport.id == scheduled_report_id
        ).first()
        
        if not scheduled_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scheduled report with ID {scheduled_report_id} not found"
            )
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (scheduled_report.created_by_id == user_id or 
                "reports:read_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this scheduled report"
            )
        
        return scheduled_report

    def update_scheduled_report(
        self, db: Session, scheduled_report_id: int, 
        scheduled_report_update: ScheduledReportUpdate, user_id: int
    ) -> ScheduledReport:
        """
        Update a scheduled report.
        
        Args:
            db: Database session
            scheduled_report_id: ID of the scheduled report to update
            scheduled_report_update: Updated scheduled report data
            user_id: ID of the user updating the scheduled report
            
        Returns:
            Updated scheduled report
        """
        scheduled_report = self.get_scheduled_report(db, scheduled_report_id, user_id)
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (scheduled_report.created_by_id == user_id or 
                "reports:update_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this scheduled report"
            )
        
        # Update fields if provided
        if scheduled_report_update.name is not None:
            scheduled_report.name = scheduled_report_update.name
        if scheduled_report_update.description is not None:
            scheduled_report.description = scheduled_report_update.description
        
        # Update frequency and recalculate next execution time if needed
        frequency_updated = False
        if scheduled_report_update.frequency is not None:
            scheduled_report.frequency = scheduled_report_update.frequency
            frequency_updated = True
        if scheduled_report_update.cron_expression is not None:
            scheduled_report.cron_expression = scheduled_report_update.cron_expression
            frequency_updated = True
        
        if frequency_updated:
            scheduled_report.next_execution_time = self._calculate_next_execution_time(
                scheduled_report.frequency,
                scheduled_report.cron_expression
            )
        
        # Update other fields
        if scheduled_report_update.parameters is not None:
            # Validate parameters against template schema
            template = self.report_service.get_report_template(
                db, scheduled_report.template_id, user_id
            )
            if template.parameters_schema:
                self._validate_parameters(
                    scheduled_report_update.parameters, 
                    template.parameters_schema
                )
            scheduled_report.parameters = scheduled_report_update.parameters
        
        if scheduled_report_update.delivery_method is not None:
            scheduled_report.delivery_method = scheduled_report_update.delivery_method
        if scheduled_report_update.delivery_config is not None:
            scheduled_report.delivery_config = scheduled_report_update.delivery_config
        if scheduled_report_update.is_active is not None:
            scheduled_report.is_active = scheduled_report_update.is_active
        
        db.commit()
        db.refresh(scheduled_report)
        
        return scheduled_report

    def delete_scheduled_report(
        self, db: Session, scheduled_report_id: int, user_id: int
    ) -> bool:
        """
        Delete a scheduled report.
        
        Args:
            db: Database session
            scheduled_report_id: ID of the scheduled report to delete
            user_id: ID of the user deleting the scheduled report
            
        Returns:
            True if successful
        """
        scheduled_report = self.get_scheduled_report(db, scheduled_report_id, user_id)
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (scheduled_report.created_by_id == user_id or 
                "reports:delete_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this scheduled report"
            )
        
        # Delete scheduled report
        db.delete(scheduled_report)
        db.commit()
        
        return True

    def list_scheduled_reports(
        self, 
        db: Session, 
        user_id: int,
        search_params: Optional[ScheduledReportSearchParams] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse:
        """
        List scheduled reports with filtering and pagination.
        
        Args:
            db: Database session
            user_id: ID of the user requesting the scheduled reports
            search_params: Search parameters
            pagination: Pagination parameters
            
        Returns:
            Paginated list of scheduled reports
        """
        # Default pagination
        if pagination is None:
            pagination = PaginationParams()
        
        # Base query
        query = db.query(ScheduledReport)
        
        # Apply filters
        user_permissions = get_user_permissions(db, user_id)
        if "reports:read_all" not in user_permissions:
            query = query.filter(ScheduledReport.created_by_id == user_id)
        
        if search_params:
            if search_params.name:
                query = query.filter(ScheduledReport.name.ilike(f"%{search_params.name}%"))
            if search_params.template_id:
                query = query.filter(ScheduledReport.template_id == search_params.template_id)
            if search_params.frequency:
                query = query.filter(ScheduledReport.frequency == search_params.frequency)
            if search_params.is_active is not None:
                query = query.filter(ScheduledReport.is_active == search_params.is_active)
            if search_params.created_by_id:
                query = query.filter(ScheduledReport.created_by_id == search_params.created_by_id)
        
        # Count total
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(ScheduledReport.created_at))
        query = query.offset((pagination.page - 1) * pagination.page_size)
        query = query.limit(pagination.page_size)
        
        # Execute query
        scheduled_reports = query.all()
        
        # Calculate total pages
        pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return PaginatedResponse(
            items=scheduled_reports,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages
        )

    def get_due_scheduled_reports(self, db: Session) -> List[ScheduledReport]:
        """
        Get scheduled reports that are due for execution.
        
        Args:
            db: Database session
            
        Returns:
            List of scheduled reports due for execution
        """
        now = datetime.utcnow()
        
        # Get active scheduled reports with next_execution_time <= now
        scheduled_reports = db.query(ScheduledReport).filter(
            ScheduledReport.is_active == True,
            ScheduledReport.next_execution_time <= now
        ).all()
        
        return scheduled_reports

    def update_next_execution_time(
        self, db: Session, scheduled_report_id: int
    ) -> datetime:
        """
        Update the next execution time for a scheduled report.
        
        Args:
            db: Database session
            scheduled_report_id: ID of the scheduled report
            
        Returns:
            Next execution time
        """
        scheduled_report = db.query(ScheduledReport).filter(
            ScheduledReport.id == scheduled_report_id
        ).first()
        
        if not scheduled_report:
            raise ValueError(f"Scheduled report with ID {scheduled_report_id} not found")
        
        # Update last execution time
        scheduled_report.last_execution_time = datetime.utcnow()
        
        # Calculate next execution time
        next_execution_time = self._calculate_next_execution_time(
            scheduled_report.frequency,
            scheduled_report.cron_expression,
            base_time=scheduled_report.last_execution_time
        )
        
        scheduled_report.next_execution_time = next_execution_time
        
        db.commit()
        
        return next_execution_time

    def _calculate_next_execution_time(
        self, 
        frequency: ReportFrequency, 
        cron_expression: Optional[str] = None,
        base_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate the next execution time based on frequency and cron expression.
        
        Args:
            frequency: Report frequency
            cron_expression: Cron expression for custom frequency
            base_time: Base time to calculate from (default: now)
            
        Returns:
            Next execution time
        """
        if base_time is None:
            base_time = datetime.utcnow()
        
        if frequency == ReportFrequency.CUSTOM and cron_expression:
            # Use croniter to calculate next execution time
            cron = croniter.croniter(cron_expression, base_time)
            return cron.get_next(datetime)
        
        # Calculate based on predefined frequencies
        if frequency == ReportFrequency.DAILY:
            # Next day at midnight
            next_day = base_time.date() + timedelta(days=1)
            return datetime.combine(next_day, datetime.min.time())
        
        elif frequency == ReportFrequency.WEEKLY:
            # Next week on Monday at midnight
            days_ahead = 7 - base_time.weekday()
            if days_ahead == 0:
                days_ahead = 7
            next_monday = base_time.date() + timedelta(days=days_ahead)
            return datetime.combine(next_monday, datetime.min.time())
        
        elif frequency == ReportFrequency.MONTHLY:
            # First day of next month at midnight
            year = base_time.year + (base_time.month // 12)
            month = (base_time.month % 12) + 1
            next_month = datetime(year, month, 1)
            return next_month
        
        elif frequency == ReportFrequency.QUARTERLY:
            # First day of next quarter at midnight
            year = base_time.year
            month = base_time.month
            
            # Calculate next quarter
            next_quarter_month = ((month - 1) // 3 + 1) * 3 + 1
            if next_quarter_month > 12:
                next_quarter_month = 1
                year += 1
            
            return datetime(year, next_quarter_month, 1)
        
        elif frequency == ReportFrequency.YEARLY:
            # First day of next year at midnight
            return datetime(base_time.year + 1, 1, 1)
        
        else:
            # Default to daily
            next_day = base_time.date() + timedelta(days=1)
            return datetime.combine(next_day, datetime.min.time())

    def _validate_parameters(
        self, parameters: Dict[str, Any], parameters_schema: Dict[str, Any]
    ) -> None:
        """
        Validate report parameters against the parameters schema.
        
        Args:
            parameters: Parameters to validate
            parameters_schema: JSON schema for parameters
            
        Raises:
            HTTPException: If parameters are invalid
        """
        # TODO: Implement JSON schema validation
        # For now, just check that required parameters are present
        if "required" in parameters_schema:
            for required_param in parameters_schema["required"]:
                if required_param not in parameters:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing required parameter: {required_param}"
                    )
