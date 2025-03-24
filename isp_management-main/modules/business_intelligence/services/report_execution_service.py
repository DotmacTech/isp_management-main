"""
Report execution service for the Business Intelligence and Reporting module.

This module provides services for executing reports, generating report outputs,
and delivering reports to users.
"""

import logging
import json
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, status
from fastapi.responses import FileResponse

from backend_core.database import get_db_session
from backend_core.services.auth_service import get_user_permissions
from modules.file_manager.services.file_service import FileService
from modules.file_manager.models.file import FileType
from ..models.report import (
    ReportTemplate, ScheduledReport, ReportExecution, ReportOutput,
    ReportAccessLog, DataSource, report_template_data_sources,
    ReportStatus, ReportFormat, DeliveryMethod
)
from ..schemas.report import (
    ReportExecutionCreate, ReportExecutionResponse,
    ReportExecutionSearchParams, PaginationParams, PaginatedResponse,
    ReportAccessLogCreate
)
from .report_service import ReportService
from .report_scheduling_service import ReportSchedulingService
from ..utils.report_generators import (
    PDFReportGenerator, CSVReportGenerator, 
    ExcelReportGenerator, HTMLReportGenerator, JSONReportGenerator
)
from ..utils.data_fetchers import DataFetcher

logger = logging.getLogger(__name__)


class ReportExecutionService:
    """Service for executing reports and managing report outputs."""

    def __init__(self):
        """Initialize the report execution service."""
        self.report_service = ReportService()
        self.scheduling_service = ReportSchedulingService()
        self.file_service = FileService()
        
        # Map of report formats to generator classes
        self.format_generators = {
            ReportFormat.PDF: PDFReportGenerator(),
            ReportFormat.CSV: CSVReportGenerator(),
            ReportFormat.EXCEL: ExcelReportGenerator(),
            ReportFormat.HTML: HTMLReportGenerator(),
            ReportFormat.JSON: JSONReportGenerator()
        }

    async def execute_report(
        self, db: Session, execution_data: ReportExecutionCreate, user_id: int
    ) -> ReportExecution:
        """
        Execute a report based on a template.
        
        Args:
            db: Database session
            execution_data: Report execution data
            user_id: ID of the user executing the report
            
        Returns:
            Report execution record
        """
        # Get template
        template = self.report_service.get_report_template(
            db, execution_data.template_id, user_id
        )
        
        # Create execution record
        execution = ReportExecution(
            template_id=template.id,
            scheduled_report_id=execution_data.scheduled_report_id,
            parameters=execution_data.parameters,
            formats=execution_data.formats,
            status=ReportStatus.PENDING,
            requested_by_id=user_id,
            started_at=datetime.utcnow()
        )
        
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        # Execute report asynchronously
        asyncio.create_task(self._generate_report(execution.id))
        
        return execution

    async def execute_scheduled_report(
        self, db: Session, scheduled_report_id: int
    ) -> ReportExecution:
        """
        Execute a scheduled report.
        
        Args:
            db: Database session
            scheduled_report_id: ID of the scheduled report to execute
            
        Returns:
            Report execution record
        """
        # Get scheduled report
        scheduled_report = db.query(ScheduledReport).filter(
            ScheduledReport.id == scheduled_report_id
        ).first()
        
        if not scheduled_report or not scheduled_report.is_active:
            raise ValueError(f"Scheduled report {scheduled_report_id} not found or inactive")
        
        # Create execution record
        execution = ReportExecution(
            template_id=scheduled_report.template_id,
            scheduled_report_id=scheduled_report.id,
            parameters=scheduled_report.parameters,
            formats=[ReportFormat.PDF],  # Default format
            status=ReportStatus.PENDING,
            requested_by_id=scheduled_report.created_by_id,
            started_at=datetime.utcnow()
        )
        
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        # Update scheduled report's last/next execution time
        self.scheduling_service.update_next_execution_time(db, scheduled_report_id)
        
        # Execute report asynchronously
        asyncio.create_task(self._generate_report(execution.id))
        
        return execution

    async def _generate_report(self, execution_id: int) -> None:
        """
        Generate a report for a given execution ID.
        
        This method is meant to be run asynchronously.
        
        Args:
            execution_id: ID of the report execution
        """
        with get_db_session() as db:
            try:
                # Get execution record
                execution = db.query(ReportExecution).filter(
                    ReportExecution.id == execution_id
                ).first()
                
                if not execution:
                    logger.error(f"Report execution {execution_id} not found")
                    return
                
                # Update status to running
                execution.status = ReportStatus.RUNNING
                db.commit()
                
                # Get template
                template = db.query(ReportTemplate).filter(
                    ReportTemplate.id == execution.template_id
                ).first()
                
                if not template:
                    raise ValueError(f"Report template {execution.template_id} not found")
                
                # Get data sources
                data_sources = db.query(DataSource).join(
                    report_template_data_sources,
                    DataSource.id == report_template_data_sources.c.data_source_id
                ).filter(
                    report_template_data_sources.c.template_id == template.id,
                    DataSource.is_active == True
                ).all()
                
                # Fetch data
                start_time = datetime.utcnow()
                data_fetcher = DataFetcher()
                report_data = await data_fetcher.fetch_data(
                    template.query_definition,
                    execution.parameters,
                    data_sources
                )
                
                # Generate reports in each requested format
                output_files = []
                for format in execution.formats:
                    generator = self.format_generators.get(format)
                    if not generator:
                        logger.warning(f"No generator found for format {format}")
                        continue
                    
                    # Generate report
                    output_file = await generator.generate(
                        template.template_data,
                        report_data,
                        execution.parameters
                    )
                    
                    output_files.append((format, output_file))
                
                # Save outputs to database and file storage
                for format, file_path in output_files:
                    # Get file info
                    file_size = os.path.getsize(file_path)
                    
                    # Create output record
                    output = ReportOutput(
                        execution_id=execution.id,
                        format=format,
                        file_path=file_path,
                        file_size=file_size
                    )
                    
                    db.add(output)
                
                # Update execution record
                execution.status = ReportStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                execution.execution_time_ms = int((execution.completed_at - start_time).total_seconds() * 1000)
                
                db.commit()
                
                # Deliver report if this was a scheduled execution
                if execution.scheduled_report_id:
                    await self._deliver_scheduled_report(execution_id)
            
            except Exception as e:
                logger.exception(f"Error generating report for execution {execution_id}: {str(e)}")
                
                # Update execution record with error
                execution = db.query(ReportExecution).filter(
                    ReportExecution.id == execution_id
                ).first()
                
                if execution:
                    execution.status = ReportStatus.FAILED
                    execution.error_message = str(e)
                    execution.completed_at = datetime.utcnow()
                    
                    db.commit()

    async def _deliver_scheduled_report(self, execution_id: int) -> None:
        """
        Deliver a scheduled report to its recipients.
        
        Args:
            execution_id: ID of the report execution
        """
        with get_db_session() as db:
            # Get execution record
            execution = db.query(ReportExecution).filter(
                ReportExecution.id == execution_id
            ).first()
            
            if not execution or execution.status != ReportStatus.COMPLETED:
                logger.error(f"Report execution {execution_id} not found or not completed")
                return
            
            # Get scheduled report
            scheduled_report = db.query(ScheduledReport).filter(
                ScheduledReport.id == execution.scheduled_report_id
            ).first()
            
            if not scheduled_report:
                logger.error(f"Scheduled report {execution.scheduled_report_id} not found")
                return
            
            # Get outputs
            outputs = db.query(ReportOutput).filter(
                ReportOutput.execution_id == execution_id
            ).all()
            
            if not outputs:
                logger.error(f"No outputs found for execution {execution_id}")
                return
            
            # Deliver based on delivery method
            if scheduled_report.delivery_method == DeliveryMethod.EMAIL:
                await self._deliver_by_email(scheduled_report, execution, outputs)
            elif scheduled_report.delivery_method == DeliveryMethod.FILE_STORAGE:
                await self._deliver_to_file_storage(scheduled_report, execution, outputs)
            elif scheduled_report.delivery_method == DeliveryMethod.API:
                # API delivery is handled by the client
                pass
            elif scheduled_report.delivery_method == DeliveryMethod.DASHBOARD:
                # Dashboard delivery is handled by the UI
                pass
            else:
                logger.warning(f"Unsupported delivery method: {scheduled_report.delivery_method}")

    async def _deliver_by_email(
        self, 
        scheduled_report: ScheduledReport, 
        execution: ReportExecution,
        outputs: List[ReportOutput]
    ) -> None:
        """
        Deliver a report by email.
        
        Args:
            scheduled_report: Scheduled report
            execution: Report execution
            outputs: Report outputs
        """
        # TODO: Implement email delivery
        # This would typically use an email service to send the report to recipients
        logger.info(f"Email delivery not implemented yet for execution {execution.id}")

    async def _deliver_to_file_storage(
        self, 
        scheduled_report: ScheduledReport, 
        execution: ReportExecution,
        outputs: List[ReportOutput]
    ) -> None:
        """
        Deliver a report to file storage.
        
        Args:
            scheduled_report: Scheduled report
            execution: Report execution
            outputs: Report outputs
        """
        with get_db_session() as db:
            try:
                # Get template
                template = db.query(ReportTemplate).filter(
                    ReportTemplate.id == execution.template_id
                ).first()
                
                if not template:
                    logger.error(f"Template {execution.template_id} not found")
                    return
                
                # Store each output file
                for output in outputs:
                    # Determine file type based on format
                    file_type = FileType.DOCUMENT
                    
                    # Get file content
                    with open(output.file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Generate filename
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    filename = f"{template.name}_{timestamp}.{output.format.value}"
                    
                    # Store file
                    await self.file_service.create_file(
                        db=db,
                        file_content=file_content,
                        filename=filename,
                        file_type=file_type,
                        owner_id=scheduled_report.created_by_id,
                        folder_id=scheduled_report.delivery_config.get("folder_id"),
                        module="business_intelligence",
                        entity_type="report",
                        entity_id=execution.id,
                        title=f"{template.name} - {timestamp}",
                        description=f"Generated report: {template.description}"
                    )
                
                logger.info(f"Stored report outputs for execution {execution.id} in file storage")
            
            except Exception as e:
                logger.exception(f"Error storing report in file storage: {str(e)}")

    def get_report_execution(
        self, db: Session, execution_id: int, user_id: int
    ) -> ReportExecution:
        """
        Get a report execution by ID.
        
        Args:
            db: Database session
            execution_id: ID of the execution to retrieve
            user_id: ID of the user requesting the execution
            
        Returns:
            Report execution
        """
        execution = db.query(ReportExecution).filter(
            ReportExecution.id == execution_id
        ).first()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report execution with ID {execution_id} not found"
            )
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (execution.requested_by_id == user_id or 
                "reports:read_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this report execution"
            )
        
        # Log access
        access_log = ReportAccessLog(
            execution_id=execution_id,
            user_id=user_id,
            action="view"
        )
        db.add(access_log)
        db.commit()
        
        return execution

    def list_report_executions(
        self, 
        db: Session, 
        user_id: int,
        search_params: Optional[ReportExecutionSearchParams] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse:
        """
        List report executions with filtering and pagination.
        
        Args:
            db: Database session
            user_id: ID of the user requesting the executions
            search_params: Search parameters
            pagination: Pagination parameters
            
        Returns:
            Paginated list of report executions
        """
        # Default pagination
        if pagination is None:
            pagination = PaginationParams()
        
        # Base query
        query = db.query(ReportExecution)
        
        # Apply filters
        user_permissions = get_user_permissions(db, user_id)
        if "reports:read_all" not in user_permissions:
            query = query.filter(ReportExecution.requested_by_id == user_id)
        
        if search_params:
            if search_params.template_id:
                query = query.filter(ReportExecution.template_id == search_params.template_id)
            if search_params.scheduled_report_id:
                query = query.filter(ReportExecution.scheduled_report_id == search_params.scheduled_report_id)
            if search_params.status:
                query = query.filter(ReportExecution.status == search_params.status)
            if search_params.requested_by_id:
                query = query.filter(ReportExecution.requested_by_id == search_params.requested_by_id)
            if search_params.started_after:
                query = query.filter(ReportExecution.started_at >= search_params.started_after)
            if search_params.started_before:
                query = query.filter(ReportExecution.started_at <= search_params.started_before)
        
        # Count total
        total = query.count()
        
        # Apply pagination
        query = query.order_by(desc(ReportExecution.started_at))
        query = query.offset((pagination.page - 1) * pagination.page_size)
        query = query.limit(pagination.page_size)
        
        # Execute query
        executions = query.all()
        
        # Calculate total pages
        pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return PaginatedResponse(
            items=executions,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages
        )

    def download_report_output(
        self, db: Session, output_id: int, user_id: int
    ) -> Tuple[str, str]:
        """
        Download a report output.
        
        Args:
            db: Database session
            output_id: ID of the output to download
            user_id: ID of the user requesting the download
            
        Returns:
            Tuple of (file_path, filename)
        """
        # Get output
        output = db.query(ReportOutput).filter(
            ReportOutput.id == output_id
        ).first()
        
        if not output:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report output with ID {output_id} not found"
            )
        
        # Get execution
        execution = db.query(ReportExecution).filter(
            ReportExecution.id == output.execution_id
        ).first()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report execution for output {output_id} not found"
            )
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (execution.requested_by_id == user_id or 
                "reports:read_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to download this report"
            )
        
        # Check if file exists
        if not os.path.exists(output.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report file not found"
            )
        
        # Get template for filename
        template = db.query(ReportTemplate).filter(
            ReportTemplate.id == execution.template_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report template for execution {execution.id} not found"
            )
        
        # Generate filename
        timestamp = execution.started_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{template.name}_{timestamp}.{output.format.value}"
        
        # Log access
        access_log = ReportAccessLog(
            execution_id=execution.id,
            user_id=user_id,
            action="download"
        )
        db.add(access_log)
        db.commit()
        
        return output.file_path, filename

    def cancel_report_execution(
        self, db: Session, execution_id: int, user_id: int
    ) -> ReportExecution:
        """
        Cancel a report execution.
        
        Args:
            db: Database session
            execution_id: ID of the execution to cancel
            user_id: ID of the user canceling the execution
            
        Returns:
            Updated report execution
        """
        execution = self.get_report_execution(db, execution_id, user_id)
        
        # Check if execution can be canceled
        if execution.status not in [ReportStatus.PENDING, ReportStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution with status {execution.status}"
            )
        
        # Check permissions
        user_permissions = get_user_permissions(db, user_id)
        if not (execution.requested_by_id == user_id or 
                "reports:cancel_all" in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this report execution"
            )
        
        # Update status
        execution.status = ReportStatus.CANCELED
        execution.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(execution)
        
        return execution
