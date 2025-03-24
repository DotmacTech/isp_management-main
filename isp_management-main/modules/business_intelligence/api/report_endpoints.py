"""
API endpoints for the Business Intelligence and Reporting module.

This module provides API endpoints for managing report templates, scheduled reports,
and report executions.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response, status
from sqlalchemy.orm import Session
import logging

from backend_core.database import get_db
from backend_core.dependencies import get_current_user, check_permissions
from backend_core.models.user import User
from ..schemas.report import (
    ReportTemplateCreate, ReportTemplateUpdate, ReportTemplateResponse,
    ReportTemplateListResponse, ScheduledReportCreate, ScheduledReportUpdate,
    ScheduledReportResponse, ScheduledReportListResponse, ReportExecutionCreate,
    ReportExecutionResponse, ReportExecutionListResponse, ReportOutputResponse,
    ReportAccessLogResponse
)
from ..services.report_service import ReportService
from ..services.report_scheduling_service import ReportSchedulingService
from ..services.report_execution_service import ReportExecutionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/business-intelligence",
    tags=["business-intelligence"],
    dependencies=[Depends(get_current_user)]
)

# Initialize services
report_service = ReportService()
report_scheduling_service = ReportSchedulingService(report_service)
report_execution_service = ReportExecutionService(report_service)


@router.post("/report-templates", response_model=ReportTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_report_template(
    template: ReportTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new report template.
    
    Requires 'report:create' permission.
    """
    check_permissions(current_user, "report:create")
    
    try:
        report_template = report_service.create_report_template(db, template, current_user.id)
        return report_template
    except Exception as e:
        logger.exception("Failed to create report template")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/report-templates", response_model=ReportTemplateListResponse)
async def list_report_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name: Optional[str] = None,
    report_type: Optional[str] = None,
    owner_id: Optional[int] = None,
    is_public: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List report templates with filtering and pagination.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        filters = {}
        if name:
            filters["name"] = name
        if report_type:
            filters["report_type"] = report_type
        if owner_id:
            filters["owner_id"] = owner_id
        if is_public is not None:
            filters["is_public"] = is_public
        
        templates, total = report_service.list_report_templates(
            db, current_user.id, skip, limit, filters
        )
        
        return {
            "items": templates,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.exception("Failed to list report templates")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/report-templates/{template_id}", response_model=ReportTemplateResponse)
async def get_report_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific report template by ID.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        template = report_service.get_report_template(db, template_id, current_user.id)
        if not template:
            raise HTTPException(status_code=404, detail="Report template not found")
        
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get report template {template_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/report-templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    template_id: int,
    template_update: ReportTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a report template.
    
    Requires 'report:update' permission.
    """
    check_permissions(current_user, "report:update")
    
    try:
        updated_template = report_service.update_report_template(
            db, template_id, template_update, current_user.id
        )
        if not updated_template:
            raise HTTPException(status_code=404, detail="Report template not found")
        
        return updated_template
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update report template {template_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/report-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a report template.
    
    Requires 'report:delete' permission.
    """
    check_permissions(current_user, "report:delete")
    
    try:
        success = report_service.delete_report_template(db, template_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Report template not found")
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete report template {template_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scheduled-reports", response_model=ScheduledReportResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_report(
    scheduled_report: ScheduledReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new scheduled report.
    
    Requires 'report:schedule' permission.
    """
    check_permissions(current_user, "report:schedule")
    
    try:
        result = report_scheduling_service.create_scheduled_report(
            db, scheduled_report, current_user.id
        )
        return result
    except Exception as e:
        logger.exception("Failed to create scheduled report")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scheduled-reports", response_model=ScheduledReportListResponse)
async def list_scheduled_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    template_id: Optional[int] = None,
    frequency: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List scheduled reports with filtering and pagination.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        filters = {}
        if template_id:
            filters["template_id"] = template_id
        if frequency:
            filters["frequency"] = frequency
        if is_active is not None:
            filters["is_active"] = is_active
        
        reports, total = report_scheduling_service.list_scheduled_reports(
            db, current_user.id, skip, limit, filters
        )
        
        return {
            "items": reports,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.exception("Failed to list scheduled reports")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scheduled-reports/{scheduled_report_id}", response_model=ScheduledReportResponse)
async def get_scheduled_report(
    scheduled_report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific scheduled report by ID.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        report = report_scheduling_service.get_scheduled_report(
            db, scheduled_report_id, current_user.id
        )
        if not report:
            raise HTTPException(status_code=404, detail="Scheduled report not found")
        
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get scheduled report {scheduled_report_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/scheduled-reports/{scheduled_report_id}", response_model=ScheduledReportResponse)
async def update_scheduled_report(
    scheduled_report_id: int,
    scheduled_report_update: ScheduledReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a scheduled report.
    
    Requires 'report:schedule' permission.
    """
    check_permissions(current_user, "report:schedule")
    
    try:
        updated_report = report_scheduling_service.update_scheduled_report(
            db, scheduled_report_id, scheduled_report_update, current_user.id
        )
        if not updated_report:
            raise HTTPException(status_code=404, detail="Scheduled report not found")
        
        return updated_report
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update scheduled report {scheduled_report_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/scheduled-reports/{scheduled_report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_report(
    scheduled_report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a scheduled report.
    
    Requires 'report:schedule' permission.
    """
    check_permissions(current_user, "report:schedule")
    
    try:
        success = report_scheduling_service.delete_scheduled_report(
            db, scheduled_report_id, current_user.id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled report not found")
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete scheduled report {scheduled_report_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/report-executions", response_model=ReportExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_report(
    execution_data: ReportExecutionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a report.
    
    Requires 'report:execute' permission.
    """
    check_permissions(current_user, "report:execute")
    
    try:
        # Create execution record
        execution = await report_execution_service.execute_report(
            db, execution_data, current_user.id
        )
        
        # Add background task to generate the report
        background_tasks.add_task(
            report_execution_service.process_report_execution,
            execution.id,
            current_user.id
        )
        
        return execution
    except Exception as e:
        logger.exception("Failed to execute report")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/report-executions", response_model=ReportExecutionListResponse)
async def list_report_executions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    template_id: Optional[int] = None,
    status: Optional[str] = None,
    scheduled_report_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List report executions with filtering and pagination.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        filters = {}
        if template_id:
            filters["template_id"] = template_id
        if status:
            filters["status"] = status
        if scheduled_report_id:
            filters["scheduled_report_id"] = scheduled_report_id
        
        executions, total = report_execution_service.list_report_executions(
            db, current_user.id, skip, limit, filters
        )
        
        return {
            "items": executions,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.exception("Failed to list report executions")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/report-executions/{execution_id}", response_model=ReportExecutionResponse)
async def get_report_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific report execution by ID.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        execution = report_execution_service.get_report_execution(
            db, execution_id, current_user.id
        )
        if not execution:
            raise HTTPException(status_code=404, detail="Report execution not found")
        
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get report execution {execution_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/report-executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_report_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a report execution.
    
    Requires 'report:execute' permission.
    """
    check_permissions(current_user, "report:execute")
    
    try:
        success = report_execution_service.cancel_report_execution(
            db, execution_id, current_user.id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Report execution not found or cannot be canceled")
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to cancel report execution {execution_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/report-outputs/{output_id}", response_model=ReportOutputResponse)
async def get_report_output(
    output_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get metadata for a specific report output by ID.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        output = report_execution_service.get_report_output(
            db, output_id, current_user.id
        )
        if not output:
            raise HTTPException(status_code=404, detail="Report output not found")
        
        return output
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get report output {output_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/report-outputs/{output_id}/download")
async def download_report_output(
    output_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download a report output file.
    
    Requires 'report:read' permission.
    """
    check_permissions(current_user, "report:read")
    
    try:
        file_path, file_name, content_type = await report_execution_service.download_report_output(
            db, output_id, current_user.id
        )
        
        # Log access
        await report_execution_service.log_report_access(
            db, output_id, current_user.id, "download"
        )
        
        # Return file
        with open(file_path, "rb") as f:
            content = f.read()
        
        headers = {
            "Content-Disposition": f"attachment; filename={file_name}"
        }
        
        return Response(
            content=content,
            media_type=content_type,
            headers=headers
        )
    except Exception as e:
        logger.exception(f"Failed to download report output {output_id}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/report-access-logs", response_model=List[ReportAccessLogResponse])
async def list_report_access_logs(
    output_id: Optional[int] = None,
    execution_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List report access logs with filtering and pagination.
    
    Requires 'report:admin' permission.
    """
    check_permissions(current_user, "report:admin")
    
    try:
        filters = {}
        if output_id:
            filters["output_id"] = output_id
        if execution_id:
            filters["execution_id"] = execution_id
        if user_id:
            filters["user_id"] = user_id
        
        logs = report_execution_service.list_report_access_logs(
            db, skip, limit, filters
        )
        
        return logs
    except Exception as e:
        logger.exception("Failed to list report access logs")
        raise HTTPException(status_code=400, detail=str(e))
