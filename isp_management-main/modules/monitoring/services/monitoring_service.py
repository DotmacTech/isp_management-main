"""
Monitoring Service for the ISP Management Platform.

This service provides methods for checking the health of system components,
tracking component status, and generating health reports.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from fastapi import Depends
import statistics

from backend_core.database import get_db
from backend_core.cache import get_redis

from ..models import SystemHealthStatus
from ..models.monitoring_models import (
    HealthCheckResponse,
    HealthCheckComponentStatus,
    ServiceHealthReport,
    HealthStatusEnum,
    LogLevelEnum,
    MetricTypeEnum
)
from .logging_service import LoggingService
from .metrics_service import MetricsService


class MonitoringService:
    """
    Service for monitoring system health and component status.
    
    This service provides methods for checking the health of system components,
    tracking component status, and generating health reports.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the monitoring service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.logging_service = LoggingService(db)
        self.metrics_service = MetricsService(db)
    
    def check_system_health(self) -> HealthCheckResponse:
        """
        Check the health of all system components.
        
        Returns:
            Health check response
        """
        # Get health check services from configuration
        from ..config.settings import settings
        health_check_services = settings.health_check_services
        
        # Initialize response
        response = HealthCheckResponse(
            status=HealthStatusEnum.HEALTHY,
            timestamp=datetime.utcnow(),
            components=[]
        )
        
        # Check each service
        for service_name, service_url in health_check_services.items():
            try:
                # Attempt to connect to the service
                # In a real implementation, this would make actual health check requests
                # For now, we'll simulate the health check
                
                # Simulate a health check
                is_healthy = True  # Replace with actual health check logic
                
                # Add to response
                response.components.append(
                    HealthCheckComponentStatus(
                        name=service_name,
                        status=HealthStatusEnum.HEALTHY if is_healthy else HealthStatusEnum.UNHEALTHY,
                        details=f"Service is {'healthy' if is_healthy else 'unhealthy'}"
                    )
                )
                
                # Update system health status in database
                self._update_health_status(service_name, is_healthy)
                
            except Exception as e:
                # Service is unhealthy
                response.status = HealthStatusEnum.UNHEALTHY
                response.components.append(
                    HealthCheckComponentStatus(
                        name=service_name,
                        status=HealthStatusEnum.UNHEALTHY,
                        details=f"Error checking service health: {str(e)}"
                    )
                )
                
                # Update system health status in database
                self._update_health_status(service_name, False, str(e))
        
        return response
    
    def get_component_status(self, component_name: str) -> Optional[HealthCheckComponentStatus]:
        """
        Get the status of a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Component status or None if not found
        """
        # Query the database for the component's health status
        health_status = self.db.query(SystemHealthStatus).filter(
            SystemHealthStatus.component_name == component_name
        ).order_by(SystemHealthStatus.timestamp.desc()).first()
        
        if not health_status:
            return None
        
        return HealthCheckComponentStatus(
            name=component_name,
            status=HealthStatusEnum(health_status.status),
            details=health_status.details or ""
        )
    
    def get_component_metrics(
        self,
        component_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metric_type: Optional[MetricTypeEnum] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get metrics for a specific component.
        
        Args:
            component_name: Name of the component
            start_time: Start time for metrics
            end_time: End time for metrics
            metric_type: Type of metrics to retrieve
            limit: Maximum number of metrics to return
            
        Returns:
            List of metrics
        """
        # Use the metrics service to retrieve component metrics
        search_params = {
            "service_name": component_name,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit
        }
        
        if metric_type:
            search_params["metric_type"] = metric_type.value
        
        metrics = self.metrics_service.search_metrics(search_params)
        
        return metrics.items
    
    def get_service_logs(
        self,
        service_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        log_level: Optional[LogLevelEnum] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get logs for a specific service.
        
        Args:
            service_name: Name of the service
            start_time: Start time for logs
            end_time: End time for logs
            log_level: Minimum log level to retrieve
            limit: Maximum number of logs to return
            
        Returns:
            List of logs
        """
        # Use the logging service to retrieve service logs
        logs = self.logging_service.search_logs(
            service_name,
            start_time,
            end_time,
            log_level.value if log_level else None,
            limit
        )
        
        return logs.items
    
    def get_system_metrics_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of system metrics.
        
        Args:
            start_time: Start time for metrics
            end_time: End time for metrics
            
        Returns:
            Dictionary containing system metrics summary
        """
        # Initialize summary
        summary = {
            "cpu_usage": {
                "average": 0,
                "max": 0,
                "min": 0
            },
            "memory_usage": {
                "average": 0,
                "max": 0,
                "min": 0
            },
            "disk_usage": {
                "average": 0,
                "max": 0,
                "min": 0
            },
            "network_traffic": {
                "total_in": 0,
                "total_out": 0
            },
            "service_availability": {
                "total": 0,
                "available": 0,
                "percentage": 100.0
            }
        }
        
        # In a real implementation, this would query the database for metrics
        # and calculate the summary values
        
        return summary
    
    def generate_service_health_report(
        self,
        service_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> ServiceHealthReport:
        """
        Generate a health report for a specific service.
        
        Args:
            service_name: Name of the service
            start_time: Start time for the report
            end_time: End time for the report
            
        Returns:
            Service health report
        """
        # Get the most recent health status for the service
        health_status = self.db.query(SystemHealthStatus).filter(
            SystemHealthStatus.component_name == service_name,
            SystemHealthStatus.timestamp.between(start_time, end_time)
        ).order_by(SystemHealthStatus.timestamp.desc()).first()
        
        # Get all health status records for the service within the time range
        health_statuses = self.db.query(SystemHealthStatus).filter(
            SystemHealthStatus.component_name == service_name,
            SystemHealthStatus.timestamp.between(start_time, end_time)
        ).all()
        
        # Calculate uptime percentage
        total_records = len(health_statuses)
        healthy_records = sum(1 for status in health_statuses if status.status == HealthStatusEnum.HEALTHY.value)
        uptime_percentage = (healthy_records / total_records * 100) if total_records > 0 else 0
        
        # Get average response time
        average_response_time = self.metrics_service.get_average_metric(
            service_name,
            "response_time",
            start_time,
            end_time
        )
        
        # Count errors
        error_count = self.logging_service.count_logs(
            service_name,
            LogLevelEnum.ERROR.value,
            start_time,
            end_time
        )
        
        # Create report
        return ServiceHealthReport(
            service_name=service_name,
            status=HealthStatusEnum(health_status.status) if health_status else HealthStatusEnum.UNKNOWN,
            uptime_percentage=uptime_percentage,
            average_response_time=average_response_time,
            error_count=error_count,
            start_time=start_time,
            end_time=end_time
        )
    
    def _update_health_status(self, component_name: str, is_healthy: bool, details: str = None) -> None:
        """
        Update the health status of a component in the database.
        
        Args:
            component_name: Name of the component
            is_healthy: Whether the component is healthy
            details: Additional details about the health status
        """
        # Create a new health status record
        health_status = SystemHealthStatus(
            component_name=component_name,
            status=HealthStatusEnum.HEALTHY.value if is_healthy else HealthStatusEnum.UNHEALTHY.value,
            details=details,
            timestamp=datetime.utcnow()
        )
        
        # Add to database
        self.db.add(health_status)
        self.db.commit()
