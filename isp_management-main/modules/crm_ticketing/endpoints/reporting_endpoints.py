"""
Reporting endpoints for the CRM & Ticketing module.

This module provides API endpoints for generating analytics and reports based on
ticket data, customer interactions, and SLA performance.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import json

from backend_core.database import get_db
from backend_core.auth import get_current_user, require_permissions
from ..services.reporting_service import ReportingService
from ..services.customer_analytics_service import CustomerAnalyticsService
from ..schemas.common import TicketStatus, TicketPriority, TicketType, InteractionType

router = APIRouter(
    prefix="/reports",
    tags=["CRM Reports"],
    responses={404: {"description": "Not found"}},
)


@router.get("/ticket-volume")
async def get_ticket_volume_report(
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    group_by: str = Query("day", description="Time grouping (day, week, month)"),
    ticket_type: Optional[TicketType] = Query(None, description="Filter by ticket type"),
    ticket_status: Optional[TicketStatus] = Query(None, description="Filter by ticket status"),
    ticket_priority: Optional[TicketPriority] = Query(None, description="Filter by ticket priority"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),
    assigned_team: Optional[int] = Query(None, description="Filter by assigned team ID"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on ticket volume over time.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
        group_by: Time grouping (day, week, month)
        ticket_type: Optional filter by ticket type
        ticket_status: Optional filter by ticket status
        ticket_priority: Optional filter by ticket priority
        assigned_to: Optional filter by assigned user ID
        assigned_team: Optional filter by assigned team ID
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    reporting_service = ReportingService(db)
    result = reporting_service.generate_ticket_volume_report(
        start_date=start_datetime,
        end_date=end_datetime,
        group_by=group_by,
        ticket_type=ticket_type,
        ticket_status=ticket_status,
        ticket_priority=ticket_priority,
        assigned_to=assigned_to,
        assigned_team=assigned_team,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


@router.get("/resolution-time")
async def get_resolution_time_report(
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    group_by: str = Query("day", description="Time grouping (day, week, month)"),
    ticket_type: Optional[TicketType] = Query(None, description="Filter by ticket type"),
    ticket_priority: Optional[TicketPriority] = Query(None, description="Filter by ticket priority"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),
    assigned_team: Optional[int] = Query(None, description="Filter by assigned team ID"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on ticket resolution times.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
        group_by: Time grouping (day, week, month)
        ticket_type: Optional filter by ticket type
        ticket_priority: Optional filter by ticket priority
        assigned_to: Optional filter by assigned user ID
        assigned_team: Optional filter by assigned team ID
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    reporting_service = ReportingService(db)
    result = reporting_service.generate_resolution_time_report(
        start_date=start_datetime,
        end_date=end_datetime,
        group_by=group_by,
        ticket_type=ticket_type,
        ticket_priority=ticket_priority,
        assigned_to=assigned_to,
        assigned_team=assigned_team,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


@router.get("/sla-compliance")
async def get_sla_compliance_report(
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    group_by: str = Query("day", description="Time grouping (day, week, month)"),
    sla_id: Optional[int] = Query(None, description="Filter by SLA ID"),
    ticket_priority: Optional[TicketPriority] = Query(None, description="Filter by ticket priority"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),
    assigned_team: Optional[int] = Query(None, description="Filter by assigned team ID"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on SLA compliance.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
        group_by: Time grouping (day, week, month)
        sla_id: Optional filter by SLA ID
        ticket_priority: Optional filter by ticket priority
        assigned_to: Optional filter by assigned user ID
        assigned_team: Optional filter by assigned team ID
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    reporting_service = ReportingService(db)
    result = reporting_service.generate_sla_compliance_report(
        start_date=start_datetime,
        end_date=end_datetime,
        group_by=group_by,
        sla_id=sla_id,
        ticket_priority=ticket_priority,
        assigned_to=assigned_to,
        assigned_team=assigned_team,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


@router.get("/agent-performance")
async def get_agent_performance_report(
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    user_ids: List[int] = Query(None, description="Optional list of user IDs to include"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on agent performance.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
        user_ids: Optional list of user IDs to include
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    reporting_service = ReportingService(db)
    result = reporting_service.generate_agent_performance_report(
        start_date=start_datetime,
        end_date=end_datetime,
        user_ids=user_ids,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


@router.get("/customer-ticket")
async def get_customer_ticket_report(
    customer_id: int = Query(..., description="The customer ID"),
    start_date: Optional[date] = Query(None, description="Optional start date for the report"),
    end_date: Optional[date] = Query(None, description="Optional end date for the report"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on a customer's ticket history.
    
    Args:
        customer_id: The customer ID
        start_date: Optional start date for the report
        end_date: Optional end date for the report
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes if provided
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None
    
    customer_analytics_service = CustomerAnalyticsService(db)
    result = customer_analytics_service.generate_customer_ticket_report(
        customer_id=customer_id,
        start_date=start_datetime,
        end_date=end_datetime,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


@router.get("/customer-satisfaction")
async def get_customer_satisfaction_report(
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    customer_id: Optional[int] = Query(None, description="Optional customer ID to filter by"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on customer satisfaction metrics.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
        customer_id: Optional customer ID to filter by
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    customer_analytics_service = CustomerAnalyticsService(db)
    result = customer_analytics_service.generate_customer_satisfaction_report(
        start_date=start_datetime,
        end_date=end_datetime,
        customer_id=customer_id,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


@router.get("/customer-interaction")
async def get_customer_interaction_report(
    customer_id: int = Query(..., description="The customer ID"),
    start_date: Optional[date] = Query(None, description="Optional start date for the report"),
    end_date: Optional[date] = Query(None, description="Optional end date for the report"),
    interaction_types: List[InteractionType] = Query(None, description="Optional list of interaction types to filter by"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on customer interactions.
    
    Args:
        customer_id: The customer ID
        start_date: Optional start date for the report
        end_date: Optional end date for the report
        interaction_types: Optional list of interaction types to filter by
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes if provided
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None
    
    customer_analytics_service = CustomerAnalyticsService(db)
    result = customer_analytics_service.generate_customer_interaction_report(
        customer_id=customer_id,
        start_date=start_datetime,
        end_date=end_datetime,
        interaction_types=interaction_types,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


@router.get("/customer-response-time")
async def get_customer_response_time_report(
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    customer_id: Optional[int] = Query(None, description="Optional customer ID to filter by"),
    report_format: str = Query("json", description="Output format (json, csv, excel, chart)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a report on customer response times.
    
    Args:
        start_date: Start date for the report
        end_date: End date for the report
        customer_id: Optional customer ID to filter by
        report_format: Output format (json, csv, excel, chart)
        
    Returns:
        Report data in the specified format
    """
    require_permissions(current_user, ["crm.view_reports"])
    
    # Convert dates to datetimes
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    customer_analytics_service = CustomerAnalyticsService(db)
    result = customer_analytics_service.generate_customer_response_time_report(
        start_date=start_datetime,
        end_date=end_datetime,
        customer_id=customer_id,
        report_format=report_format
    )
    
    return _format_response(result, report_format)


def _format_response(result: Dict[str, Any], report_format: str):
    """Format the response based on the report format."""
    if report_format == "json":
        return result
    
    elif report_format == "csv":
        if isinstance(result, dict) and "format" in result and result["format"] == "csv":
            if isinstance(result["content"], dict):
                # Multiple CSV files, return the first one
                first_key = next(iter(result["content"]))
                content = result["content"][first_key]
            else:
                content = result["content"]
                
            return StreamingResponse(
                io.StringIO(content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
            )
        return result
    
    elif report_format == "excel":
        if isinstance(result, dict) and "format" in result and result["format"] == "excel":
            return StreamingResponse(
                io.BytesIO(result["content"]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
            )
        return result
    
    elif report_format == "chart":
        return result
    
    else:
        return result
