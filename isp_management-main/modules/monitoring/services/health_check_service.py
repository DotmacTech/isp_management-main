"""
Service for managing system health checks in the monitoring module.
"""

import logging
import json
import socket
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from redis import Redis

from modules.monitoring.models.system_health import (
    SystemHealthCheck as HealthCheck, SystemHealthStatus as HealthStatus, SystemHealthStatus as HealthCheckResult
)
from modules.monitoring.schemas.system_health import (
    HealthCheckCreate, HealthCheckResponse, HealthCheckResultCreate,
    HealthCheckResultResponse, ServiceHealthReport, HealthStatusEnum,
    HealthCheckComponentStatus, HealthCheckSummary
)
from modules.monitoring.schemas.dashboard import PaginatedResponse
from modules.monitoring.elasticsearch import ElasticsearchClient

# Configure logging
logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for managing system health checks in the monitoring module."""

    def __init__(self, db: Session, redis: Optional[Redis] = None):
        """Initialize the service with database session and Redis client."""
        self.db = db
        self.redis = redis
        self.es_client = ElasticsearchClient()

    def create_health_check(self, health_check_data: HealthCheckCreate) -> HealthCheck:
        """
        Create a new health check configuration.
        
        Args:
            health_check_data: Health check configuration data.
            
        Returns:
            Created health check configuration.
        """
        health_check = HealthCheck(**health_check_data.dict())
        self.db.add(health_check)
        self.db.commit()
        self.db.refresh(health_check)
        
        # Cache configuration in Redis if available
        if self.redis:
            cache_key = f"health_check:{health_check.id}"
            self.redis.set(cache_key, json.dumps(health_check.to_dict()), ex=3600)  # 1 hour expiry
        
        return health_check

    def get_health_checks(
        self,
        service_name: Optional[str] = None,
        active_only: bool = True
    ) -> List[HealthCheckResponse]:
        """
        Get all health check configurations, optionally filtered by service name.
        
        Args:
            service_name: Filter by service name.
            active_only: Only return active health checks.
            
        Returns:
            List of health check configurations.
        """
        query = self.db.query(HealthCheck)
        
        if service_name:
            query = query.filter(HealthCheck.service_name == service_name)
        
        if active_only:
            query = query.filter(HealthCheck.is_active == True)
        
        health_checks = query.all()
        
        return [HealthCheckResponse.from_orm(hc) for hc in health_checks]

    def update_health_check(
        self,
        health_check_id: int,
        health_check_data: HealthCheckCreate
    ) -> Optional[HealthCheck]:
        """
        Update an existing health check configuration.
        
        Args:
            health_check_id: ID of the health check to update.
            health_check_data: New configuration data.
            
        Returns:
            Updated health check or None if not found.
        """
        health_check = self.db.query(HealthCheck).filter(
            HealthCheck.id == health_check_id
        ).first()
        
        if not health_check:
            return None
        
        # Update fields
        for key, value in health_check_data.dict().items():
            setattr(health_check, key, value)
        
        self.db.commit()
        self.db.refresh(health_check)
        
        # Update cache
        if self.redis:
            cache_key = f"health_check:{health_check.id}"
            self.redis.set(cache_key, json.dumps(health_check.to_dict()), ex=3600)  # 1 hour expiry
        
        return health_check

    def delete_health_check(self, health_check_id: int) -> bool:
        """
        Delete a health check configuration.
        
        Args:
            health_check_id: ID of the health check to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        health_check = self.db.query(HealthCheck).filter(
            HealthCheck.id == health_check_id
        ).first()
        
        if not health_check:
            return False
        
        self.db.delete(health_check)
        self.db.commit()
        
        # Remove from cache
        if self.redis:
            cache_key = f"health_check:{health_check_id}"
            self.redis.delete(cache_key)
        
        return True

    def create_health_check_result(self, result_data: HealthCheckResultCreate) -> HealthCheckResult:
        """
        Record a new health check result.
        
        Args:
            result_data: Health check result data.
            
        Returns:
            Created health check result.
        """
        result = HealthCheckResult(**result_data.dict())
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        
        # Index to Elasticsearch if connected
        if self.es_client.is_connected():
            self.es_client.index(
                index="health_check_results",
                id=result.id,
                document=result.to_dict()
            )
        
        return result

    def get_health_check_results(
        self,
        health_check_id: Optional[int] = None,
        service_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[HealthCheckResult] = None,
        offset: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[HealthCheckResultResponse]:
        """
        Get health check results with filtering options.
        
        Args:
            health_check_id: Filter by health check ID.
            service_name: Filter by service name.
            start_time: Filter by start time.
            end_time: Filter by end time.
            status: Filter by status.
            offset: Pagination offset.
            limit: Pagination limit.
            
        Returns:
            Paginated response with health check results.
        """
        # Build query
        query = self.db.query(HealthCheckResult)
        
        if health_check_id:
            query = query.filter(HealthCheckResult.health_check_id == health_check_id)
        
        if service_name:
            query = query.join(HealthCheck).filter(HealthCheck.service_name == service_name)
        
        if start_time:
            query = query.filter(HealthCheckResult.check_time >= start_time)
        
        if end_time:
            query = query.filter(HealthCheckResult.check_time <= end_time)
        
        if status:
            query = query.filter(HealthCheckResult.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        results = query.order_by(desc(HealthCheckResult.check_time)).offset(offset).limit(limit).all()
        
        # Create paginated response
        return PaginatedResponse[HealthCheckResultResponse](
            items=[HealthCheckResultResponse.from_orm(result) for result in results],
            total=total,
            page=(offset // limit) + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )

    def get_latest_health_status(
        self,
        service_name: Optional[str] = None
    ) -> List[ServiceHealthReport]:
        """
        Get the latest health status for all services or a specific service.
        
        Args:
            service_name: Filter by service name.
            
        Returns:
            List of service health reports.
        """
        # Get unique service names
        service_query = self.db.query(HealthCheck.service_name).distinct()
        
        if service_name:
            service_query = service_query.filter(HealthCheck.service_name == service_name)
        
        service_names = [row[0] for row in service_query.all()]
        
        # Get latest health status for each service
        reports = []
        for svc_name in service_names:
            # Get the latest result for each health check in this service
            subquery = self.db.query(
                HealthCheckResult.health_check_id,
                func.max(HealthCheckResult.check_time).label("max_time")
            ).join(
                HealthCheck, HealthCheck.id == HealthCheckResult.health_check_id
            ).filter(
                HealthCheck.service_name == svc_name
            ).group_by(
                HealthCheckResult.health_check_id
            ).subquery()
            
            # Join with the main table to get the full records
            latest_results = self.db.query(HealthCheckResult).join(
                subquery,
                and_(
                    HealthCheckResult.health_check_id == subquery.c.health_check_id,
                    HealthCheckResult.check_time == subquery.c.max_time
                )
            ).all()
            
            # Determine overall status (worst status wins)
            overall_status = HealthStatusEnum.HEALTHY
            for result in latest_results:
                if result.status == HealthCheckResult.CRITICAL:
                    overall_status = HealthStatusEnum.CRITICAL
                    break
                elif result.status == HealthCheckResult.WARNING and overall_status != HealthStatusEnum.CRITICAL:
                    overall_status = HealthStatusEnum.WARNING
                elif result.status == HealthCheckResult.DEGRADED and overall_status not in [HealthStatusEnum.CRITICAL, HealthStatusEnum.WARNING]:
                    overall_status = HealthStatusEnum.DEGRADED
            
            # Create service health report
            report = ServiceHealthReport(
                service_name=svc_name,
                status=overall_status,
                timestamp=datetime.utcnow(),
                components=[
                    HealthCheckComponentStatus(
                        name=self.db.query(HealthCheck).filter(HealthCheck.id == result.health_check_id).first().name,
                        status=HealthStatusEnum(result.status.value),
                        message=result.message,
                        response_time_ms=result.response_time_ms,
                        last_check_time=result.check_time
                    )
                    for result in latest_results
                ]
            )
            
            reports.append(report)
        
        return reports

    def run_health_check(self, health_check_id: int) -> HealthCheckResult:
        """
        Run a specific health check and record the result.
        
        Args:
            health_check_id: ID of the health check to run.
            
        Returns:
            Health check result.
        """
        health_check = self.db.query(HealthCheck).filter(
            HealthCheck.id == health_check_id
        ).first()
        
        if not health_check:
            raise ValueError(f"Health check with ID {health_check_id} not found")
        
        start_time = datetime.utcnow()
        status = HealthCheckResult.HEALTHY
        message = "Health check passed"
        
        try:
            if health_check.check_type == "http":
                status, message = self._run_http_check(health_check)
            elif health_check.check_type == "tcp":
                status, message = self._run_tcp_check(health_check)
            elif health_check.check_type == "ping":
                status, message = self._run_ping_check(health_check)
            elif health_check.check_type == "custom":
                status, message = self._run_custom_check(health_check)
            else:
                status = HealthCheckResult.WARNING
                message = f"Unsupported check type: {health_check.check_type}"
        except Exception as e:
            status = HealthCheckResult.CRITICAL
            message = f"Error running health check: {str(e)}"
        
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Create result
        result_data = HealthCheckResultCreate(
            health_check_id=health_check.id,
            check_time=start_time,
            status=status,
            message=message,
            response_time_ms=response_time_ms
        )
        
        return self.create_health_check_result(result_data)

    def _run_http_check(self, health_check: HealthCheck) -> tuple:
        """
        Run an HTTP health check.
        
        Args:
            health_check: Health check configuration.
            
        Returns:
            Tuple of (status, message).
        """
        endpoint = health_check.endpoint
        timeout = health_check.timeout_seconds or 5
        
        try:
            response = requests.get(endpoint, timeout=timeout)
            
            if response.status_code >= 500:
                return HealthCheckResult.CRITICAL, f"HTTP {response.status_code}: {response.reason}"
            elif response.status_code >= 400:
                return HealthCheckResult.WARNING, f"HTTP {response.status_code}: {response.reason}"
            elif response.status_code >= 300:
                return HealthCheckResult.DEGRADED, f"HTTP {response.status_code}: {response.reason}"
            else:
                return HealthCheckResult.HEALTHY, f"HTTP {response.status_code}: {response.reason}"
        except requests.exceptions.Timeout:
            return HealthCheckResult.CRITICAL, "Request timed out"
        except requests.exceptions.ConnectionError:
            return HealthCheckResult.CRITICAL, "Connection error"
        except Exception as e:
            return HealthCheckResult.CRITICAL, f"Error: {str(e)}"

    def _run_tcp_check(self, health_check: HealthCheck) -> tuple:
        """
        Run a TCP health check.
        
        Args:
            health_check: Health check configuration.
            
        Returns:
            Tuple of (status, message).
        """
        endpoint = health_check.endpoint
        timeout = health_check.timeout_seconds or 5
        
        try:
            # Parse host and port
            host, port = endpoint.split(":")
            port = int(port)
            
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # Connect
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return HealthCheckResult.HEALTHY, "TCP connection successful"
            else:
                return HealthCheckResult.CRITICAL, f"TCP connection failed with error code {result}"
        except socket.timeout:
            return HealthCheckResult.CRITICAL, "TCP connection timed out"
        except Exception as e:
            return HealthCheckResult.CRITICAL, f"Error: {str(e)}"

    def _run_ping_check(self, health_check: HealthCheck) -> tuple:
        """
        Run a ping health check.
        
        Args:
            health_check: Health check configuration.
            
        Returns:
            Tuple of (status, message).
        """
        endpoint = health_check.endpoint
        
        try:
            # Simple implementation using socket
            host = endpoint
            
            # Try to resolve the hostname
            try:
                socket.gethostbyname(host)
                return HealthCheckResult.HEALTHY, "Host is reachable"
            except socket.gaierror:
                return HealthCheckResult.CRITICAL, "Host is not reachable"
        except Exception as e:
            return HealthCheckResult.CRITICAL, f"Error: {str(e)}"

    def _run_custom_check(self, health_check: HealthCheck) -> tuple:
        """
        Run a custom health check.
        
        Args:
            health_check: Health check configuration.
            
        Returns:
            Tuple of (status, message).
        """
        # Custom checks would typically call an external script or function
        # For now, return a placeholder result
        return HealthCheckResult.WARNING, "Custom check not implemented"

    def run_all_health_checks(self, service_name: Optional[str] = None) -> List[HealthCheckResult]:
        """
        Run all active health checks, optionally filtered by service name.
        
        Args:
            service_name: Filter by service name.
            
        Returns:
            List of health check results.
        """
        query = self.db.query(HealthCheck).filter(HealthCheck.is_active == True)
        
        if service_name:
            query = query.filter(HealthCheck.service_name == service_name)
        
        health_checks = query.all()
        
        results = []
        for health_check in health_checks:
            try:
                result = self.run_health_check(health_check.id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error running health check {health_check.id}: {str(e)}")
        
        return results

    def get_health_check_summary(
        self,
        days: int = 7,
        service_name: Optional[str] = None
    ) -> HealthCheckSummary:
        """
        Get a summary of health check results for the specified number of days.
        
        Args:
            days: Number of days to include in the summary.
            service_name: Filter by service name.
            
        Returns:
            Health check summary.
        """
        # Calculate start time
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Build base query
        base_query = self.db.query(HealthCheckResult).join(
            HealthCheck, HealthCheck.id == HealthCheckResult.health_check_id
        ).filter(
            HealthCheckResult.check_time >= start_time
        )
        
        if service_name:
            base_query = base_query.filter(HealthCheck.service_name == service_name)
        
        # Get total count
        total_count = base_query.count()
        
        # Get counts by status
        status_counts = {}
        for status in HealthCheckResult:
            count = base_query.filter(HealthCheckResult.status == status).count()
            status_counts[status.value] = count
        
        # Get average response time
        avg_response_time = base_query.with_entities(
            func.avg(HealthCheckResult.response_time_ms)
        ).scalar() or 0
        
        # Get success rate
        success_count = base_query.filter(HealthCheckResult.status == HealthCheckResult.HEALTHY).count()
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        
        return HealthCheckSummary(
            total_checks=total_count,
            status_counts=status_counts,
            avg_response_time_ms=avg_response_time,
            success_rate_percent=success_rate,
            period_days=days
        )
