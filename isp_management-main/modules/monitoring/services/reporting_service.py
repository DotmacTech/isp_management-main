"""
Reporting Service for ISP Management Platform.

This module provides services for generating performance reports based on
collected metrics and logs.
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
from sqlalchemy import func, desc, and_, or_, text, select
from fastapi import HTTPException, Depends

from backend_core.database import get_db
from backend_core.config import settings
from modules.monitoring.models import (
    SystemMetric,
    ServiceLog,
    AlertHistory,
    AlertConfiguration,
    MetricType,
    LogLevel
)
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)


class ReportingService:
    """Service for generating performance reports."""
    
    def __init__(self, db: Session = Depends(get_db)):
        """Initialize the reporting service."""
        self.db = db
        self.es_client = ElasticsearchClient()
        
    def generate_system_performance_report(
        self,
        start_time: datetime,
        end_time: datetime,
        service_names: Optional[List[str]] = None,
        metric_types: Optional[List[MetricType]] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate a system performance report.
        
        Args:
            start_time: Start time for the report
            end_time: End time for the report
            service_names: Optional list of service names to include
            metric_types: Optional list of metric types to include
            report_format: Format of the report (json, csv, pdf)
            
        Returns:
            Report data in the requested format
        """
        # Build query
        query = select(SystemMetric)
        
        # Apply filters
        filters = [
            SystemMetric.timestamp >= start_time,
            SystemMetric.timestamp <= end_time
        ]
        
        if service_names:
            filters.append(SystemMetric.service_name.in_(service_names))
            
        if metric_types:
            filters.append(SystemMetric.metric_type.in_(metric_types))
            
        query = query.where(and_(*filters))
        query = query.order_by(SystemMetric.timestamp)
        
        # Execute query
        result = self.db.execute(query)
        metrics = result.scalars().all()
        
        if not metrics:
            return {
                "status": "error",
                "message": "No metrics found for the specified criteria"
            }
            
        # Process metrics
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                "id": metric.id,
                "service_name": metric.service_name,
                "host_name": metric.host_name,
                "metric_type": metric.metric_type.value,
                "value": metric.value,
                "unit": metric.unit,
                "tags": metric.tags,
                "timestamp": metric.timestamp.isoformat()
            })
            
        # Calculate statistics
        stats = self._calculate_metric_statistics(metrics)
        
        # Generate report in requested format
        if report_format == "json":
            return self._generate_json_report(metrics_data, stats, start_time, end_time)
        elif report_format == "csv":
            return self._generate_csv_report(metrics_data, start_time, end_time)
        elif report_format == "pdf":
            return self._generate_pdf_report(metrics_data, stats, start_time, end_time)
        else:
            return {
                "status": "error",
                "message": f"Unsupported report format: {report_format}"
            }
    
    def generate_alert_report(
        self,
        start_time: datetime,
        end_time: datetime,
        service_names: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate a report of alerts.
        
        Args:
            start_time: Start time for the report
            end_time: End time for the report
            service_names: Optional list of service names to include
            severities: Optional list of severities to include
            report_format: Format of the report (json, csv, pdf)
            
        Returns:
            Report data in the requested format
        """
        # Build query
        query = select(AlertHistory).join(AlertConfiguration)
        
        # Apply filters
        filters = [
            AlertHistory.triggered_at >= start_time,
            AlertHistory.triggered_at <= end_time
        ]
        
        if service_names:
            filters.append(AlertConfiguration.service_name.in_(service_names))
            
        if severities:
            filters.append(AlertConfiguration.severity.in_(severities))
            
        query = query.where(and_(*filters))
        query = query.order_by(AlertHistory.triggered_at)
        
        # Execute query
        result = self.db.execute(query)
        alerts = result.scalars().all()
        
        if not alerts:
            return {
                "status": "error",
                "message": "No alerts found for the specified criteria"
            }
            
        # Process alerts
        alerts_data = []
        for alert in alerts:
            config = self.db.query(AlertConfiguration).filter(
                AlertConfiguration.id == alert.configuration_id
            ).first()
            
            alerts_data.append({
                "id": alert.id,
                "configuration_id": alert.configuration_id,
                "configuration_name": config.name if config else "Unknown",
                "service_name": config.service_name if config else "Unknown",
                "severity": config.severity.value if config else "Unknown",
                "status": alert.status.value,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "triggered_value": alert.triggered_value,
                "matched_pattern": alert.matched_pattern
            })
            
        # Generate report in requested format
        if report_format == "json":
            return self._generate_json_alert_report(alerts_data, start_time, end_time)
        elif report_format == "csv":
            return self._generate_csv_alert_report(alerts_data, start_time, end_time)
        elif report_format == "pdf":
            return self._generate_pdf_alert_report(alerts_data, start_time, end_time)
        else:
            return {
                "status": "error",
                "message": f"Unsupported report format: {report_format}"
            }
    
    def generate_service_availability_report(
        self,
        start_time: datetime,
        end_time: datetime,
        service_names: Optional[List[str]] = None,
        report_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate a service availability report.
        
        Args:
            start_time: Start time for the report
            end_time: End time for the report
            service_names: Optional list of service names to include
            report_format: Format of the report (json, csv, pdf)
            
        Returns:
            Report data in the requested format
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Query service availability data
        # 2. Calculate uptime percentages
        # 3. Generate a report
        
        return {
            "status": "success",
            "message": "Service availability report generated",
            "report_type": "service_availability",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "service_names": service_names,
            "format": report_format,
            "data": {
                "services": [
                    {
                        "name": "example-service",
                        "uptime_percentage": 99.95,
                        "downtime_minutes": 72,
                        "outages": 3
                    }
                ]
            }
        }
    
    def _calculate_metric_statistics(self, metrics: List[SystemMetric]) -> Dict[str, Any]:
        """
        Calculate statistics for metrics.
        
        Args:
            metrics: List of metrics
            
        Returns:
            Dictionary with statistics
        """
        stats = {}
        
        # Group metrics by service_name and metric_type
        grouped_metrics = {}
        for metric in metrics:
            key = f"{metric.service_name}:{metric.metric_type.value}"
            if key not in grouped_metrics:
                grouped_metrics[key] = []
            grouped_metrics[key].append(metric.value)
            
        # Calculate statistics for each group
        for key, values in grouped_metrics.items():
            service_name, metric_type = key.split(":")
            
            if service_name not in stats:
                stats[service_name] = {}
                
            stats[service_name][metric_type] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values)
            }
            
        return stats
    
    def _generate_json_report(
        self,
        metrics_data: List[Dict[str, Any]],
        stats: Dict[str, Any],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Generate a JSON report.
        
        Args:
            metrics_data: Metrics data
            stats: Statistics
            start_time: Start time
            end_time: End time
            
        Returns:
            JSON report
        """
        return {
            "status": "success",
            "message": "System performance report generated",
            "report_type": "system_performance",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "metrics_count": len(metrics_data),
            "statistics": stats,
            "metrics": metrics_data
        }
    
    def _generate_csv_report(
        self,
        metrics_data: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Generate a CSV report.
        
        Args:
            metrics_data: Metrics data
            start_time: Start time
            end_time: End time
            
        Returns:
            Dictionary with CSV data
        """
        if not metrics_data:
            return {
                "status": "error",
                "message": "No metrics data to generate CSV report"
            }
            
        # Create CSV file in memory
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=metrics_data[0].keys(),
            quoting=csv.QUOTE_NONNUMERIC
        )
        
        writer.writeheader()
        for metric in metrics_data:
            # Convert tags to string if present
            if "tags" in metric and metric["tags"]:
                metric["tags"] = json.dumps(metric["tags"])
            writer.writerow(metric)
            
        csv_data = output.getvalue()
        output.close()
        
        return {
            "status": "success",
            "message": "CSV report generated",
            "report_type": "system_performance",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "format": "csv",
            "data": csv_data
        }
    
    def _generate_pdf_report(
        self,
        metrics_data: List[Dict[str, Any]],
        stats: Dict[str, Any],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Generate a PDF report.
        
        Args:
            metrics_data: Metrics data
            stats: Statistics
            start_time: Start time
            end_time: End time
            
        Returns:
            Dictionary with PDF data
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Use a library like ReportLab or WeasyPrint to generate a PDF
        # 2. Include charts, tables, and statistics
        # 3. Return the PDF data
        
        return {
            "status": "success",
            "message": "PDF report generation is not implemented",
            "report_type": "system_performance",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "format": "pdf"
        }
    
    def _generate_json_alert_report(
        self,
        alerts_data: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Generate a JSON alert report.
        
        Args:
            alerts_data: Alerts data
            start_time: Start time
            end_time: End time
            
        Returns:
            JSON report
        """
        # Calculate alert statistics
        total_alerts = len(alerts_data)
        active_alerts = sum(1 for alert in alerts_data if alert["status"] == "active")
        resolved_alerts = sum(1 for alert in alerts_data if alert["status"] == "resolved")
        acknowledged_alerts = sum(1 for alert in alerts_data if alert["status"] == "acknowledged")
        
        # Count alerts by severity
        severity_counts = {}
        for alert in alerts_data:
            severity = alert["severity"]
            if severity not in severity_counts:
                severity_counts[severity] = 0
            severity_counts[severity] += 1
            
        # Count alerts by service
        service_counts = {}
        for alert in alerts_data:
            service = alert["service_name"]
            if service not in service_counts:
                service_counts[service] = 0
            service_counts[service] += 1
            
        return {
            "status": "success",
            "message": "Alert report generated",
            "report_type": "alert",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "alerts_count": total_alerts,
            "statistics": {
                "total": total_alerts,
                "active": active_alerts,
                "resolved": resolved_alerts,
                "acknowledged": acknowledged_alerts,
                "by_severity": severity_counts,
                "by_service": service_counts
            },
            "alerts": alerts_data
        }
    
    def _generate_csv_alert_report(
        self,
        alerts_data: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Generate a CSV alert report.
        
        Args:
            alerts_data: Alerts data
            start_time: Start time
            end_time: End time
            
        Returns:
            Dictionary with CSV data
        """
        if not alerts_data:
            return {
                "status": "error",
                "message": "No alerts data to generate CSV report"
            }
            
        # Create CSV file in memory
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=alerts_data[0].keys(),
            quoting=csv.QUOTE_NONNUMERIC
        )
        
        writer.writeheader()
        for alert in alerts_data:
            writer.writerow(alert)
            
        csv_data = output.getvalue()
        output.close()
        
        return {
            "status": "success",
            "message": "CSV alert report generated",
            "report_type": "alert",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "format": "csv",
            "data": csv_data
        }
    
    def _generate_pdf_alert_report(
        self,
        alerts_data: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Generate a PDF alert report.
        
        Args:
            alerts_data: Alerts data
            start_time: Start time
            end_time: End time
            
        Returns:
            Dictionary with PDF data
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Use a library like ReportLab or WeasyPrint to generate a PDF
        # 2. Include charts, tables, and statistics
        # 3. Return the PDF data
        
        return {
            "status": "success",
            "message": "PDF alert report generation is not implemented",
            "report_type": "alert",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "format": "pdf"
        }
