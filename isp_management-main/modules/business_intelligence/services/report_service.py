"""
Report service for the Business Intelligence and Reporting module.

This module provides services for managing report templates, scheduled reports,
and report executions.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, status

from backend_core.database import get_db_session
from backend_core.services.auth_service import get_user_permissions
from ..models.report import (
    ReportTemplate, ScheduledReport, ReportExecution, ReportOutput,
    ReportAccessLog, DataSource, report_template_data_sources,
    ReportStatus, ReportFormat
)
from ..schemas.report import (
    ReportTemplateCreate, ReportTemplateUpdate, ReportTemplateResponse,
    ScheduledReportCreate, ScheduledReportUpdate, ScheduledReportResponse,
    ReportExecutionCreate, ReportExecutionResponse,
    DataSourceCreate, DataSourceUpdate, DataSourceResponse,
    ReportSearchParams, ScheduledReportSearchParams, ReportExecutionSearchParams,
    PaginationParams, PaginatedResponse
)

logger = logging.getLogger(__name__)


class ReportService:
    """Service for managing report templates, scheduled reports, and executions."""

    def create_report_template(
        self, db: Session, template: ReportTemplateCreate, user_id: int
    ) -> ReportTemplate:
        """
        Create a new report template.
        
        Args:
            db: Database session
            template: Report template data
            user_id: ID of the user creating the template
            
        Returns:
            Created report template
        """
        # Validate data sources
        if template.data_source_ids:
            data_sources = db.query(DataSource).filter(
                DataSource.id.in_(template.data_source_ids),
                DataSource.is_active == True
            ).all()
            
            if len(data_sources) != len(template.data_source_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more data sources not found or inactive"
                )
        
        # Create template
        db_template = ReportTemplate(
            name=template.name,
            description=template.description,
            report_type=template.report_type,
            template_data=template.template_data,
            query_definition=template.query_definition,
            parameters_schema=template.parameters_schema,
            is_system=template.is_system,
            created_by_id=user_id
        )
        
        db.add(db_template)
        db.flush()  # Flush to get the ID
        
        # Add data sources
        if template.data_source_ids:
            for ds_id in template.data_source_ids:
                db.execute(
                    report_template_data_sources.insert().values(
                        template_id=db_template.id,
                        data_source_id=ds_id
                    )
                )
        
        db.commit()
        db.refresh(db_template)
        
        return db_template

    def get_report_template(
        self, db: Session, template_id: int, user_id: int
    ) -> ReportTemplate:
        """
        Get a report template by ID.
        
        Args:
            db: Database session
            template_id: ID of the template to retrieve
            user_id: ID of the user requesting the template
            
        Returns:
            Report template
        """
        template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report template with ID {template_id} not found"
            )
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (template.created_by_id == user_id or 
                "reports:read_all" in user_permissions or
                template.is_system):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this report template"
            )
        
        return template

    def update_report_template(
        self, db: Session, template_id: int, template_update: ReportTemplateUpdate, user_id: int
    ) -> ReportTemplate:
        """
        Update a report template.
        
        Args:
            db: Database session
            template_id: ID of the template to update
            template_update: Updated template data
            user_id: ID of the user updating the template
            
        Returns:
            Updated report template
        """
        template = self.get_report_template(db, template_id, user_id)
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (template.created_by_id == user_id or 
                "reports:update_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this report template"
            )
        
        # Update fields
        if template_update.name is not None:
            template.name = template_update.name
        if template_update.description is not None:
            template.description = template_update.description
        if template_update.template_data is not None:
            template.template_data = template_update.template_data
        if template_update.query_definition is not None:
            template.query_definition = template_update.query_definition
        if template_update.parameters_schema is not None:
            template.parameters_schema = template_update.parameters_schema
        
        # Update data sources if provided
        if template_update.data_source_ids is not None:
            # Validate data sources
            if template_update.data_source_ids:
                data_sources = db.query(DataSource).filter(
                    DataSource.id.in_(template_update.data_source_ids),
                    DataSource.is_active == True
                ).all()
                
                if len(data_sources) != len(template_update.data_source_ids):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="One or more data sources not found or inactive"
                    )
            
            # Remove existing associations
            db.execute(
                report_template_data_sources.delete().where(
                    report_template_data_sources.c.template_id == template_id
                )
            )
            
            # Add new associations
            for ds_id in template_update.data_source_ids:
                db.execute(
                    report_template_data_sources.insert().values(
                        template_id=template_id,
                        data_source_id=ds_id
                    )
                )
        
        db.commit()
        db.refresh(template)
        
        return template

    def delete_report_template(
        self, db: Session, template_id: int, user_id: int
    ) -> bool:
        """
        Delete a report template.
        
        Args:
            db: Database session
            template_id: ID of the template to delete
            user_id: ID of the user deleting the template
            
        Returns:
            True if successful
        """
        template = self.get_report_template(db, template_id, user_id)
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (template.created_by_id == user_id or 
                "reports:delete_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this report template"
            )
        
        # Check if template is used by scheduled reports
        scheduled_reports = db.query(ScheduledReport).filter(
            ScheduledReport.template_id == template_id,
            ScheduledReport.is_active == True
        ).first()
        
        if scheduled_reports:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete template that is used by active scheduled reports"
            )
        
        # Delete template
        db.delete(template)
        db.commit()
        
        return True

    def list_report_templates(
        self, 
        db: Session, 
        user_id: int,
        search_params: Optional[ReportSearchParams] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse:
        """
        List report templates with filtering and pagination.
        
        Args:
            db: Database session
            user_id: ID of the user requesting the templates
            search_params: Search parameters
            pagination: Pagination parameters
            
        Returns:
            Paginated list of report templates
        """
        # Default pagination
        if pagination is None:
            pagination = PaginationParams()
        
        # Base query
        query = db.query(ReportTemplate)
        
        # Apply filters
        user_permissions = get_user_permissions(db, user_id)
        if "reports:read_all" not in user_permissions:
            query = query.filter(
                or_(
                    ReportTemplate.created_by_id == user_id,
                    ReportTemplate.is_system == True
                )
            )
        
        if search_params:
            if search_params.name:
                query = query.filter(ReportTemplate.name.ilike(f"%{search_params.name}%"))
            if search_params.report_type:
                query = query.filter(ReportTemplate.report_type == search_params.report_type)
            if search_params.created_by_id:
                query = query.filter(ReportTemplate.created_by_id == search_params.created_by_id)
            if search_params.created_after:
                query = query.filter(ReportTemplate.created_at >= search_params.created_after)
            if search_params.created_before:
                query = query.filter(ReportTemplate.created_at <= search_params.created_before)
        
        # Count total
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(ReportTemplate.created_at))
        query = query.offset((pagination.page - 1) * pagination.page_size)
        query = query.limit(pagination.page_size)
        
        # Execute query
        templates = query.all()
        
        # Calculate total pages
        pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return PaginatedResponse(
            items=templates,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages
        )

    # Additional methods for scheduled reports, report executions, etc. will be implemented
    # in the report_scheduling_service.py and report_execution_service.py files
