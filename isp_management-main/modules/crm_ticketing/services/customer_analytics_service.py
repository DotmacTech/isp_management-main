"""
Customer Analytics Service for CRM & Ticketing Module.

This module provides services for analyzing customer data, interactions,
and satisfaction metrics to provide insights for business decisions.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, text, select, extract, case
from fastapi import HTTPException, Depends

from backend_core.database import get_db
from backend_core.config import settings
from modules.monitoring.elasticsearch import ElasticsearchClient
from ..models.ticket import Ticket, TicketComment, TicketAttachment, TicketHistory
from ..models.customer import Customer, CustomerInteraction
from ..models.common import TicketStatus, TicketPriority, TicketType, InteractionType

# Configure logging
logger = logging.getLogger(__name__)


class CustomerAnalyticsService:
    """Service for analyzing customer data and interactions."""
    
    def __init__(self, db: Session):
        """Initialize the customer analytics service."""
        self.db = db
        self.es_client = ElasticsearchClient()
    
    def generate_customer_ticket_report(
        self,
        customer_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=365)  # Last year by default
        
        # Get customer details
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail=f"Customer with ID {customer_id} not found")
        
        # Build query for ticket summary
        ticket_summary = self.db.query(
            func.count(Ticket.id).label('total_tickets'),
            func.sum(case((Ticket.status == TicketStatus.OPEN, 1), else_=0)).label('open_tickets'),
            func.sum(case((Ticket.status == TicketStatus.IN_PROGRESS, 1), else_=0)).label('in_progress_tickets'),
            func.sum(case((Ticket.status == TicketStatus.RESOLVED, 1), else_=0)).label('resolved_tickets'),
            func.sum(case((Ticket.status == TicketStatus.CLOSED, 1), else_=0)).label('closed_tickets'),
            func.avg(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('avg_resolution_hours')
        ).filter(
            Ticket.customer_id == customer_id,
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        ).first()
        
        # Build query for ticket types
        ticket_types = self.db.query(
            Ticket.type,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.customer_id == customer_id,
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        ).group_by(Ticket.type).all()
        
        # Build query for ticket priorities
        ticket_priorities = self.db.query(
            Ticket.priority,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.customer_id == customer_id,
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        ).group_by(Ticket.priority).all()
        
        # Build query for monthly ticket volume
        monthly_volume = self.db.query(
            func.date_trunc('month', Ticket.created_at).label('month'),
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.customer_id == customer_id,
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        ).group_by(text('month')).order_by(text('month')).all()
        
        # Build query for recent tickets
        recent_tickets = self.db.query(Ticket).filter(
            Ticket.customer_id == customer_id,
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        ).order_by(desc(Ticket.created_at)).limit(10).all()
        
        # Format the result
        data = {
            "title": f"Customer Ticket Report - {customer.company_name or customer.first_name + ' ' + customer.last_name}",
            "customer_id": customer_id,
            "customer_name": customer.company_name or f"{customer.first_name} {customer.last_name}",
            "customer_email": customer.email,
            "customer_phone": customer.phone,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "summary": {
                "total_tickets": ticket_summary.total_tickets,
                "open_tickets": ticket_summary.open_tickets,
                "in_progress_tickets": ticket_summary.in_progress_tickets,
                "resolved_tickets": ticket_summary.resolved_tickets,
                "closed_tickets": ticket_summary.closed_tickets,
                "avg_resolution_hours": round(ticket_summary.avg_resolution_hours, 2) if ticket_summary.avg_resolution_hours else 0
            },
            "ticket_types": [
                {
                    "type": ticket_type.value,
                    "count": count
                } for ticket_type, count in ticket_types
            ],
            "ticket_priorities": [
                {
                    "priority": priority.value,
                    "count": count
                } for priority, count in ticket_priorities
            ],
            "monthly_volume": [
                {
                    "month": month.isoformat(),
                    "count": count
                } for month, count in monthly_volume
            ],
            "recent_tickets": [
                {
                    "id": ticket.id,
                    "ticket_number": ticket.ticket_number,
                    "subject": ticket.subject,
                    "status": ticket.status.value,
                    "priority": ticket.priority.value,
                    "type": ticket.type.value,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None
                } for ticket in recent_tickets
            ]
        }
        
        # Return in requested format
        return self._format_report(data, report_format)
    
    def generate_customer_satisfaction_report(
        self,
        start_date: datetime,
        end_date: datetime,
        customer_id: Optional[int] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Build query for satisfaction ratings
        from ..models.ticket import TicketSatisfactionSurvey
        
        satisfaction_query = self.db.query(
            func.date_trunc('month', TicketSatisfactionSurvey.submitted_at).label('month'),
            func.avg(TicketSatisfactionSurvey.rating).label('avg_rating'),
            func.count(TicketSatisfactionSurvey.id).label('count')
        ).filter(
            TicketSatisfactionSurvey.submitted_at >= start_date,
            TicketSatisfactionSurvey.submitted_at <= end_date
        )
        
        # Apply customer filter if provided
        if customer_id:
            satisfaction_query = satisfaction_query.join(Ticket).filter(Ticket.customer_id == customer_id)
        
        # Group and order
        satisfaction_result = satisfaction_query.group_by(text('month')).order_by(text('month')).all()
        
        # Build query for satisfaction by category
        category_query = self.db.query(
            TicketSatisfactionSurvey.category,
            func.avg(TicketSatisfactionSurvey.rating).label('avg_rating'),
            func.count(TicketSatisfactionSurvey.id).label('count')
        ).filter(
            TicketSatisfactionSurvey.submitted_at >= start_date,
            TicketSatisfactionSurvey.submitted_at <= end_date
        )
        
        # Apply customer filter if provided
        if customer_id:
            category_query = category_query.join(Ticket).filter(Ticket.customer_id == customer_id)
        
        # Group and order
        category_result = category_query.group_by(TicketSatisfactionSurvey.category).all()
        
        # Build query for satisfaction by ticket type
        type_query = self.db.query(
            Ticket.type,
            func.avg(TicketSatisfactionSurvey.rating).label('avg_rating'),
            func.count(TicketSatisfactionSurvey.id).label('count')
        ).filter(
            TicketSatisfactionSurvey.submitted_at >= start_date,
            TicketSatisfactionSurvey.submitted_at <= end_date
        ).join(Ticket)
        
        # Apply customer filter if provided
        if customer_id:
            type_query = type_query.filter(Ticket.customer_id == customer_id)
        
        # Group and order
        type_result = type_query.group_by(Ticket.type).all()
        
        # Format the result
        data = {
            "title": "Customer Satisfaction Report",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filters": {
                "customer_id": customer_id
            },
            "monthly_satisfaction": [
                {
                    "month": month.isoformat(),
                    "avg_rating": round(avg_rating, 2),
                    "count": count
                } for month, avg_rating, count in satisfaction_result
            ],
            "satisfaction_by_category": [
                {
                    "category": category,
                    "avg_rating": round(avg_rating, 2),
                    "count": count
                } for category, avg_rating, count in category_result
            ],
            "satisfaction_by_ticket_type": [
                {
                    "type": ticket_type.value,
                    "avg_rating": round(avg_rating, 2),
                    "count": count
                } for ticket_type, avg_rating, count in type_result
            ]
        }
        
        # Calculate overall metrics
        total_surveys = sum(item[2] for item in satisfaction_result)
        if total_surveys > 0:
            weighted_sum = sum(item[1] * item[2] for item in satisfaction_result)
            overall_avg = weighted_sum / total_surveys
            data["overall_satisfaction"] = round(overall_avg, 2)
        else:
            data["overall_satisfaction"] = 0
        
        # Return in requested format
        return self._format_report(data, report_format)
    
    def generate_customer_interaction_report(
        self,
        customer_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interaction_types: Optional[List[InteractionType]] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=365)  # Last year by default
        
        # Get customer details
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail=f"Customer with ID {customer_id} not found")
        
        # Build query for interaction summary
        interaction_query = self.db.query(
            CustomerInteraction.type,
            func.count(CustomerInteraction.id).label('count')
        ).filter(
            CustomerInteraction.customer_id == customer_id,
            CustomerInteraction.created_at >= start_date,
            CustomerInteraction.created_at <= end_date
        )
        
        # Apply interaction type filter if provided
        if interaction_types:
            interaction_query = interaction_query.filter(CustomerInteraction.type.in_(interaction_types))
        
        # Group and order
        interaction_summary = interaction_query.group_by(CustomerInteraction.type).all()
        
        # Build query for monthly interaction volume
        monthly_query = self.db.query(
            func.date_trunc('month', CustomerInteraction.created_at).label('month'),
            CustomerInteraction.type,
            func.count(CustomerInteraction.id).label('count')
        ).filter(
            CustomerInteraction.customer_id == customer_id,
            CustomerInteraction.created_at >= start_date,
            CustomerInteraction.created_at <= end_date
        )
        
        # Apply interaction type filter if provided
        if interaction_types:
            monthly_query = monthly_query.filter(CustomerInteraction.type.in_(interaction_types))
        
        # Group and order
        monthly_interactions = monthly_query.group_by(text('month'), CustomerInteraction.type).order_by(text('month')).all()
        
        # Build query for recent interactions
        recent_query = self.db.query(CustomerInteraction).filter(
            CustomerInteraction.customer_id == customer_id,
            CustomerInteraction.created_at >= start_date,
            CustomerInteraction.created_at <= end_date
        )
        
        # Apply interaction type filter if provided
        if interaction_types:
            recent_query = recent_query.filter(CustomerInteraction.type.in_(interaction_types))
        
        # Order and limit
        recent_interactions = recent_query.order_by(desc(CustomerInteraction.created_at)).limit(10).all()
        
        # Format the result
        data = {
            "title": f"Customer Interaction Report - {customer.company_name or customer.first_name + ' ' + customer.last_name}",
            "customer_id": customer_id,
            "customer_name": customer.company_name or f"{customer.first_name} {customer.last_name}",
            "customer_email": customer.email,
            "customer_phone": customer.phone,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filters": {
                "interaction_types": [t.value for t in interaction_types] if interaction_types else None
            },
            "interaction_summary": [
                {
                    "type": interaction_type.value,
                    "count": count
                } for interaction_type, count in interaction_summary
            ],
            "monthly_interactions": [
                {
                    "month": month.isoformat(),
                    "type": interaction_type.value,
                    "count": count
                } for month, interaction_type, count in monthly_interactions
            ],
            "recent_interactions": [
                {
                    "id": interaction.id,
                    "type": interaction.type.value,
                    "subject": interaction.subject,
                    "description": interaction.description[:100] + "..." if len(interaction.description) > 100 else interaction.description,
                    "created_at": interaction.created_at.isoformat(),
                    "created_by": interaction.created_by
                } for interaction in recent_interactions
            ]
        }
        
        # Calculate total interactions
        data["total_interactions"] = sum(item["count"] for item in data["interaction_summary"])
        
        # Return in requested format
        return self._format_report(data, report_format)
    
    def generate_customer_response_time_report(
        self,
        start_date: datetime,
        end_date: datetime,
        customer_id: Optional[int] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
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
        # Build query for customer first response times
        first_response_query = self.db.query(
            Ticket.customer_id,
            func.avg(func.extract('epoch', Ticket.first_response_at - Ticket.created_at) / 3600).label('avg_first_response_hours'),
            func.min(func.extract('epoch', Ticket.first_response_at - Ticket.created_at) / 3600).label('min_first_response_hours'),
            func.max(func.extract('epoch', Ticket.first_response_at - Ticket.created_at) / 3600).label('max_first_response_hours'),
            func.count(Ticket.id).label('ticket_count')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.first_response_at.isnot(None)
        )
        
        # Apply customer filter if provided
        if customer_id:
            first_response_query = first_response_query.filter(Ticket.customer_id == customer_id)
        
        # Group by customer
        first_response_result = first_response_query.group_by(Ticket.customer_id).all()
        
        # Build query for customer resolution times
        resolution_query = self.db.query(
            Ticket.customer_id,
            func.avg(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('avg_resolution_hours'),
            func.min(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('min_resolution_hours'),
            func.max(func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600).label('max_resolution_hours'),
            func.count(Ticket.id).label('ticket_count')
        ).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.resolved_at.isnot(None)
        )
        
        # Apply customer filter if provided
        if customer_id:
            resolution_query = resolution_query.filter(Ticket.customer_id == customer_id)
        
        # Group by customer
        resolution_result = resolution_query.group_by(Ticket.customer_id).all()
        
        # Get customer details for each customer ID
        customer_ids = set([r[0] for r in first_response_result] + [r[0] for r in resolution_result])
        customers = {}
        
        if customer_ids:
            customer_records = self.db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
            for customer in customer_records:
                customers[customer.id] = {
                    "id": customer.id,
                    "name": customer.company_name or f"{customer.first_name} {customer.last_name}",
                    "email": customer.email
                }
        
        # Format the result
        data = {
            "title": "Customer Response Time Report",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filters": {
                "customer_id": customer_id
            },
            "first_response_data": [
                {
                    "customer_id": cust_id,
                    "customer_name": customers.get(cust_id, {}).get("name", f"Customer {cust_id}"),
                    "avg_first_response_hours": round(avg_hours, 2) if avg_hours else 0,
                    "min_first_response_hours": round(min_hours, 2) if min_hours else 0,
                    "max_first_response_hours": round(max_hours, 2) if max_hours else 0,
                    "ticket_count": count
                } for cust_id, avg_hours, min_hours, max_hours, count in first_response_result
            ],
            "resolution_data": [
                {
                    "customer_id": cust_id,
                    "customer_name": customers.get(cust_id, {}).get("name", f"Customer {cust_id}"),
                    "avg_resolution_hours": round(avg_hours, 2) if avg_hours else 0,
                    "min_resolution_hours": round(min_hours, 2) if min_hours else 0,
                    "max_resolution_hours": round(max_hours, 2) if max_hours else 0,
                    "ticket_count": count
                } for cust_id, avg_hours, min_hours, max_hours, count in resolution_result
            ]
        }
        
        # Calculate overall metrics
        if first_response_result:
            total_tickets = sum(item[4] for item in first_response_result)
            if total_tickets > 0:
                weighted_sum = sum(item[1] * item[4] for item in first_response_result if item[1])
                overall_avg = weighted_sum / total_tickets
                data["overall_first_response_hours"] = round(overall_avg, 2)
        
        if resolution_result:
            total_tickets = sum(item[4] for item in resolution_result)
            if total_tickets > 0:
                weighted_sum = sum(item[1] * item[4] for item in resolution_result if item[1])
                overall_avg = weighted_sum / total_tickets
                data["overall_resolution_hours"] = round(overall_avg, 2)
        
        # Return in requested format
        return self._format_report(data, report_format)
    
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
                    if isinstance(dataset, list) and len(dataset) > 0:
                        df = pd.DataFrame(dataset)
                        result["content"][key] = df.to_csv(index=False)
                
                return result
        
        elif report_format == "excel":
            # Convert to Excel
            import io
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            
            if "data" in data:
                df = pd.DataFrame(data["data"])
                df.to_excel(writer, sheet_name="Report", index=False)
            else:
                # Handle multi-dataset reports
                for key, dataset in data.items():
                    if isinstance(dataset, list) and len(dataset) > 0:
                        sheet_name = key[:31]  # Excel sheet names limited to 31 chars
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
            
            if "monthly_volume" in data:
                chart_data["labels"] = [item["month"] for item in data["monthly_volume"]]
                chart_data["data"]["ticket_count"] = [item["count"] for item in data["monthly_volume"]]
            
            elif "monthly_interactions" in data:
                # Group by month
                months = {}
                for item in data["monthly_interactions"]:
                    month = item["month"]
                    if month not in months:
                        months[month] = {}
                    
                    months[month][item["type"]] = item["count"]
                
                chart_data["labels"] = sorted(months.keys())
                
                # Get all interaction types
                interaction_types = set()
                for item in data["monthly_interactions"]:
                    interaction_types.add(item["type"])
                
                # Create series for each interaction type
                for interaction_type in interaction_types:
                    chart_data["data"][interaction_type] = [
                        months.get(month, {}).get(interaction_type, 0)
                        for month in chart_data["labels"]
                    ]
            
            elif "monthly_satisfaction" in data:
                chart_data["labels"] = [item["month"] for item in data["monthly_satisfaction"]]
                chart_data["data"]["avg_rating"] = [item["avg_rating"] for item in data["monthly_satisfaction"]]
                chart_data["data"]["count"] = [item["count"] for item in data["monthly_satisfaction"]]
            
            return chart_data
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported report format: {report_format}"
            )
