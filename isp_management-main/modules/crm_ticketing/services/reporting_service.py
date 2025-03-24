"""
Reporting Service for CRM & Ticketing Module.

This module provides services for generating analytics and reports based on
ticket data, customer interactions, and SLA performance.
"""

import logging
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, text, select, extract
from fastapi import HTTPException, Depends, BackgroundTasks

from backend_core.database import get_db
from backend_core.config import settings
from modules.monitoring.elasticsearch import ElasticsearchClient
from ..models.ticket import Ticket, TicketComment, TicketAttachment, TicketHistory
from ..models.sla import SLA, SLAMetric
from ..models.customer import Customer
from ..models.common import TicketStatus, TicketPriority, TicketType

# Configure logging
logger = logging.getLogger(__name__)


class ReportingService:
    """Service for generating CRM and ticketing reports and analytics."""
    
    def __init__(self, db: Session):
        """Initialize the reporting service."""
        self.db = db
        self.es_client = ElasticsearchClient()
    
    def generate_ticket_volume_report(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day",
        ticket_type: Optional[TicketType] = None,
        ticket_status: Optional[TicketStatus] = None,
        ticket_priority: Optional[TicketPriority] = None,
        assigned_to: Optional[int] = None,
        assigned_team: Optional[int] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Build query
        query = self.db.query(
            func.date_trunc(group_by, Ticket.created_at).label('period'),
            func.count(Ticket.id).label('count')
        )
        
        # Apply filters
        query = self._apply_ticket_filters(
            query, 
            start_date, 
            end_date, 
            ticket_type,
            ticket_status,
            ticket_priority,
            assigned_to,
            assigned_team
        )
        
        # Group and order
        result = query.group_by(text('period')).order_by(text('period')).all()
        
        # Format the result
        data = {
            "title": "Ticket Volume Report",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "group_by": group_by,
            "filters": {
                "ticket_type": ticket_type.value if ticket_type else None,
                "ticket_status": ticket_status.value if ticket_status else None,
                "ticket_priority": ticket_priority.value if ticket_priority else None,
                "assigned_to": assigned_to,
                "assigned_team": assigned_team
            },
            "data": [
                {
                    "period": period.isoformat(),
                    "count": count
                } for period, count in result
            ]
        }
        
        # Return in requested format
        return self._format_report(data, report_format)
    
    def generate_resolution_time_report(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day",
        ticket_type: Optional[TicketType] = None,
        ticket_priority: Optional[TicketPriority] = None,
        assigned_to: Optional[int] = None,
        assigned_team: Optional[int] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Build query for resolved tickets
        query = self.db.query(
            func.date_trunc(group_by, Ticket.created_at).label('period'),
            func.avg(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('avg_hours'),
            func.min(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('min_hours'),
            func.max(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('max_hours'),
            func.count(Ticket.id).label('count')
        ).filter(Ticket.resolved_at.isnot(None))
        
        # Apply filters
        query = self._apply_ticket_filters(
            query, 
            start_date, 
            end_date, 
            ticket_type,
            None,  # Don't filter by status since we're looking at resolved tickets
            ticket_priority,
            assigned_to,
            assigned_team
        )
        
        # Group and order
        result = query.group_by(text('period')).order_by(text('period')).all()
        
        # Format the result
        data = {
            "title": "Ticket Resolution Time Report",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "group_by": group_by,
            "filters": {
                "ticket_type": ticket_type.value if ticket_type else None,
                "ticket_priority": ticket_priority.value if ticket_priority else None,
                "assigned_to": assigned_to,
                "assigned_team": assigned_team
            },
            "data": [
                {
                    "period": period.isoformat(),
                    "avg_resolution_hours": round(avg_hours, 2) if avg_hours else 0,
                    "min_resolution_hours": round(min_hours, 2) if min_hours else 0,
                    "max_resolution_hours": round(max_hours, 2) if max_hours else 0,
                    "ticket_count": count
                } for period, avg_hours, min_hours, max_hours, count in result
            ]
        }
        
        # Return in requested format
        return self._format_report(data, report_format)
    
    def generate_sla_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day",
        sla_id: Optional[int] = None,
        ticket_priority: Optional[TicketPriority] = None,
        assigned_to: Optional[int] = None,
        assigned_team: Optional[int] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Build query for first response compliance
        first_response_query = self.db.query(
            func.date_trunc(group_by, Ticket.created_at).label('period'),
            func.count(Ticket.id).label('total'),
            func.sum(
                case(
                    (Ticket.first_response_at <= Ticket.first_response_target, 1),
                    else_=0
                )
            ).label('compliant')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.first_response_target.isnot(None),
            Ticket.first_response_at.isnot(None)
        )
        
        # Apply filters
        if sla_id:
            first_response_query = first_response_query.filter(Ticket.sla_id == sla_id)
        if ticket_priority:
            first_response_query = first_response_query.filter(Ticket.priority == ticket_priority)
        if assigned_to:
            first_response_query = first_response_query.filter(Ticket.assigned_to == assigned_to)
        if assigned_team:
            first_response_query = first_response_query.filter(Ticket.assigned_team == assigned_team)
        
        # Group and order
        first_response_result = first_response_query.group_by(text('period')).order_by(text('period')).all()
        
        # Build query for resolution compliance
        resolution_query = self.db.query(
            func.date_trunc(group_by, Ticket.created_at).label('period'),
            func.count(Ticket.id).label('total'),
            func.sum(
                case(
                    (or_(
                        Ticket.resolved_at <= Ticket.resolution_target,
                        Ticket.closed_at <= Ticket.resolution_target
                    ), 1),
                    else_=0
                )
            ).label('compliant')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.resolution_target.isnot(None),
            or_(
                Ticket.resolved_at.isnot(None),
                Ticket.closed_at.isnot(None)
            )
        )
        
        # Apply filters
        if sla_id:
            resolution_query = resolution_query.filter(Ticket.sla_id == sla_id)
        if ticket_priority:
            resolution_query = resolution_query.filter(Ticket.priority == ticket_priority)
        if assigned_to:
            resolution_query = resolution_query.filter(Ticket.assigned_to == assigned_to)
        if assigned_team:
            resolution_query = resolution_query.filter(Ticket.assigned_team == assigned_team)
        
        # Group and order
        resolution_result = resolution_query.group_by(text('period')).order_by(text('period')).all()
        
        # Format the result
        data = {
            "title": "SLA Compliance Report",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "group_by": group_by,
            "filters": {
                "sla_id": sla_id,
                "ticket_priority": ticket_priority.value if ticket_priority else None,
                "assigned_to": assigned_to,
                "assigned_team": assigned_team
            },
            "first_response_data": [
                {
                    "period": period.isoformat(),
                    "total": total,
                    "compliant": compliant,
                    "compliance_percentage": round((compliant / total * 100), 2) if total > 0 else 100
                } for period, total, compliant in first_response_result
            ],
            "resolution_data": [
                {
                    "period": period.isoformat(),
                    "total": total,
                    "compliant": compliant,
                    "compliance_percentage": round((compliant / total * 100), 2) if total > 0 else 100
                } for period, total, compliant in resolution_result
            ]
        }
        
        # Return in requested format
        return self._format_report(data, report_format)
    
    def generate_agent_performance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_ids: Optional[List[int]] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Build query for ticket counts
        ticket_query = self.db.query(
            Ticket.assigned_to.label('user_id'),
            func.count(Ticket.id).label('total_tickets'),
            func.sum(case((Ticket.status == TicketStatus.RESOLVED, 1), else_=0)).label('resolved_tickets'),
            func.sum(case((Ticket.status == TicketStatus.CLOSED, 1), else_=0)).label('closed_tickets'),
            func.avg(func.extract('epoch', Ticket.first_response_at - Ticket.created_at) / 3600).label('avg_first_response_hours'),
            func.avg(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('avg_resolution_hours')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.assigned_to.isnot(None)
        )
        
        # Apply user filter if provided
        if user_ids:
            ticket_query = ticket_query.filter(Ticket.assigned_to.in_(user_ids))
        
        # Group by user
        ticket_result = ticket_query.group_by(Ticket.assigned_to).all()
        
        # Build query for SLA compliance
        sla_query = self.db.query(
            Ticket.assigned_to.label('user_id'),
            func.count(Ticket.id).label('total_sla_tickets'),
            func.sum(
                case(
                    (Ticket.first_response_at <= Ticket.first_response_target, 1),
                    else_=0
                )
            ).label('first_response_compliant'),
            func.sum(
                case(
                    (or_(
                        Ticket.resolved_at <= Ticket.resolution_target,
                        Ticket.closed_at <= Ticket.resolution_target
                    ), 1),
                    else_=0
                )
            ).label('resolution_compliant')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.assigned_to.isnot(None),
            Ticket.first_response_target.isnot(None)
        )
        
        # Apply user filter if provided
        if user_ids:
            sla_query = sla_query.filter(Ticket.assigned_to.in_(user_ids))
        
        # Group by user
        sla_result = sla_query.group_by(Ticket.assigned_to).all()
        
        # Build query for comment counts
        comment_query = self.db.query(
            TicketComment.created_by.label('user_id'),
            func.count(TicketComment.id).label('total_comments'),
            func.avg(func.length(TicketComment.content)).label('avg_comment_length')
        ).filter(
            TicketComment.created_at >= start_date,
            TicketComment.created_at <= end_date
        )
        
        # Apply user filter if provided
        if user_ids:
            comment_query = comment_query.filter(TicketComment.created_by.in_(user_ids))
        
        # Group by user
        comment_result = comment_query.group_by(TicketComment.created_by).all()
        
        # Combine results
        user_data = {}
        
        # Process ticket data
        for user_id, total, resolved, closed, first_response, resolution in ticket_result:
            if user_id not in user_data:
                user_data[user_id] = {
                    "user_id": user_id,
                    "total_tickets": 0,
                    "resolved_tickets": 0,
                    "closed_tickets": 0,
                    "avg_first_response_hours": 0,
                    "avg_resolution_hours": 0,
                    "total_sla_tickets": 0,
                    "first_response_compliant": 0,
                    "resolution_compliant": 0,
                    "first_response_compliance_percentage": 0,
                    "resolution_compliance_percentage": 0,
                    "total_comments": 0,
                    "avg_comment_length": 0
                }
            
            user_data[user_id]["total_tickets"] = total
            user_data[user_id]["resolved_tickets"] = resolved
            user_data[user_id]["closed_tickets"] = closed
            user_data[user_id]["avg_first_response_hours"] = round(first_response, 2) if first_response else 0
            user_data[user_id]["avg_resolution_hours"] = round(resolution, 2) if resolution else 0
        
        # Process SLA data
        for user_id, total, first_response, resolution in sla_result:
            if user_id not in user_data:
                continue
            
            user_data[user_id]["total_sla_tickets"] = total
            user_data[user_id]["first_response_compliant"] = first_response
            user_data[user_id]["resolution_compliant"] = resolution
            
            # Calculate compliance percentages
            if total > 0:
                user_data[user_id]["first_response_compliance_percentage"] = round((first_response / total * 100), 2)
                user_data[user_id]["resolution_compliance_percentage"] = round((resolution / total * 100), 2)
        
        # Process comment data
        for user_id, total, avg_length in comment_result:
            if user_id not in user_data:
                continue
            
            user_data[user_id]["total_comments"] = total
            user_data[user_id]["avg_comment_length"] = round(avg_length, 2) if avg_length else 0
        
        # Format the result
        data = {
            "title": "Agent Performance Report",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filters": {
                "user_ids": user_ids
            },
            "data": list(user_data.values())
        }
        
        # Return in requested format
        return self._format_report(data, report_format)
    
    def _apply_ticket_filters(
        self,
        query,
        start_date: datetime,
        end_date: datetime,
        ticket_type: Optional[TicketType] = None,
        ticket_status: Optional[TicketStatus] = None,
        ticket_priority: Optional[TicketPriority] = None,
        assigned_to: Optional[int] = None,
        assigned_team: Optional[int] = None
    ):
        """Apply common filters to a ticket query."""
        query = query.filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        if ticket_type:
            query = query.filter(Ticket.type == ticket_type)
        
        if ticket_status:
            query = query.filter(Ticket.status == ticket_status)
        
        if ticket_priority:
            query = query.filter(Ticket.priority == ticket_priority)
        
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)
        
        if assigned_team:
            query = query.filter(Ticket.assigned_team == assigned_team)
        
        return query
    
    def _format_report(self, data: Dict[str, Any], report_format: str) -> Dict[str, Any]:
        """Format report data in the requested format."""
        if report_format == "json":
            return data
        
        elif report_format == "csv":
            # Convert to CSV
            if "data" in data:
                df = pd.DataFrame(data["data"])
                csv_data = df.to_csv(index=False)
                return {
                    "format": "csv",
                    "filename": f"{data['title'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "content": csv_data
                }
            else:
                # Handle multi-dataset reports
                result = {
                    "format": "csv",
                    "filename": f"{data['title'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "content": {}
                }
                
                for key, dataset in data.items():
                    if isinstance(dataset, list) and key.endswith("_data"):
                        df = pd.DataFrame(dataset)
                        result["content"][key] = df.to_csv(index=False)
                
                return result
        
        elif report_format == "excel":
            # Convert to Excel
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            
            if "data" in data:
                df = pd.DataFrame(data["data"])
                df.to_excel(writer, sheet_name="Report", index=False)
            else:
                # Handle multi-dataset reports
                for key, dataset in data.items():
                    if isinstance(dataset, list) and key.endswith("_data"):
                        sheet_name = key.replace("_data", "").title()
                        df = pd.DataFrame(dataset)
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            writer.save()
            excel_data = output.getvalue()
            
            return {
                "format": "excel",
                "filename": f"{data['title'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "content": excel_data
            }
        
        elif report_format == "chart":
            # Generate chart data
            chart_data = {
                "title": data["title"],
                "type": "line",  # Default chart type
                "data": {}
            }
            
            if "data" in data:
                # Single dataset
                if "period" in data["data"][0]:
                    # Time series data
                    chart_data["labels"] = [item["period"] for item in data["data"]]
                    
                    # Extract numeric fields
                    numeric_fields = [k for k, v in data["data"][0].items() 
                                    if isinstance(v, (int, float)) and k != "period"]
                    
                    for field in numeric_fields:
                        chart_data["data"][field] = [item[field] for item in data["data"]]
            else:
                # Multi-dataset reports
                for key, dataset in data.items():
                    if isinstance(dataset, list) and key.endswith("_data") and dataset:
                        dataset_name = key.replace("_data", "").title()
                        
                        if "period" in dataset[0]:
                            # Time series data
                            if "labels" not in chart_data:
                                chart_data["labels"] = [item["period"] for item in dataset]
                            
                            # Extract numeric fields
                            numeric_fields = [k for k, v in dataset[0].items() 
                                            if isinstance(v, (int, float)) and k != "period"]
                            
                            for field in numeric_fields:
                                chart_data["data"][f"{dataset_name}_{field}"] = [item[field] for item in dataset]
            
            return chart_data
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported report format: {report_format}"
            )

from sqlalchemy.sql.expression import case
