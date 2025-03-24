"""
Client utilities for the Monitoring Module.

This module provides client functions for other services to integrate with the
monitoring system, including logging, metrics reporting, and health checks.
"""

import logging
import datetime
import uuid
import json
import socket
from typing import Dict, Any, Optional, List, Union
import requests
import asyncio
import functools
import time
import traceback

from backend_core.config import settings
from backend_core.cache import get_redis

from .models import LogLevel, MetricType
from .utils import format_log_message, get_system_health

# Configure logger
logger = logging.getLogger(__name__)


class MonitoringClient:
    """
    Client for interacting with the monitoring system.
    
    This client provides methods for logging, reporting metrics, and checking
    system health from other services.
    """
    
    def __init__(
        self,
        service_name: str,
        api_base_url: Optional[str] = None,
        use_redis: bool = True,
        use_api: bool = True
    ):
        """
        Initialize the monitoring client.
        
        Args:
            service_name: Name of the service using the client
            api_base_url: Base URL for the monitoring API
            use_redis: Whether to use Redis for logging and metrics
            use_api: Whether to use the API for logging and metrics
        """
        self.service_name = service_name
        self.api_base_url = api_base_url or settings.API_GATEWAY_URL
        self.use_redis = use_redis
        self.use_api = use_api
        
        # Initialize Redis connection if needed
        self.redis = None
        if use_redis:
            try:
                self.redis = next(get_redis())
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {str(e)}")
    
    def log(
        self,
        level: Union[LogLevel, str],
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        source_ip: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        response_status: Optional[int] = None,
        execution_time: Optional[float] = None
    ) -> bool:
        """
        Log a message to the monitoring system.
        
        Args:
            level: Log level
            message: Log message
            metadata: Additional metadata to include in the log
            trace_id: Trace ID for distributed tracing
            correlation_id: Correlation ID for request correlation
            user_id: ID of the user associated with the log
            source_ip: Source IP address
            request_path: Request path
            request_method: Request method
            response_status: Response status code
            execution_time: Execution time in seconds
            
        Returns:
            True if the log was sent successfully, False otherwise
        """
        # Format log message
        log_data = format_log_message(
            service_name=self.service_name,
            log_level=level,
            message=message,
            metadata=metadata,
            trace_id=trace_id,
            correlation_id=correlation_id,
            user_id=user_id
        )
        
        # Add additional fields if provided
        if source_ip:
            log_data["source_ip"] = source_ip
        
        if request_path:
            log_data["request_path"] = request_path
        
        if request_method:
            log_data["request_method"] = request_method
        
        if response_status is not None:
            log_data["response_status"] = response_status
        
        if execution_time is not None:
            log_data["execution_time"] = execution_time
        
        # Send log to Redis if enabled
        redis_success = False
        if self.use_redis and self.redis:
            try:
                # Publish log to Redis channel
                channel = f"logs:{self.service_name}"
                self.redis.publish(channel, json.dumps(log_data))
                
                # Also add to a list for persistence
                logs_key = f"logs:{self.service_name}:recent"
                self.redis.lpush(logs_key, json.dumps(log_data))
                self.redis.ltrim(logs_key, 0, 999)  # Keep only the 1000 most recent logs
                
                redis_success = True
            except Exception as e:
                logger.warning(f"Failed to send log to Redis: {str(e)}")
        
        # Send log to API if enabled
        api_success = False
        if self.use_api:
            try:
                # Send log to API
                api_url = f"{self.api_base_url}/monitoring/logs"
                response = requests.post(
                    api_url,
                    json=log_data,
                    timeout=2  # Short timeout to avoid blocking
                )
                
                api_success = response.status_code < 400
            except Exception as e:
                logger.warning(f"Failed to send log to API: {str(e)}")
        
        # Log locally as fallback
        if not redis_success and not api_success:
            # Map log level to Python logging level
            if isinstance(level, str):
                level = level.upper()
            else:
                level = level.value
                
            if level == "ERROR":
                logger.error(message, extra=log_data)
            elif level == "WARNING":
                logger.warning(message, extra=log_data)
            elif level == "DEBUG":
                logger.debug(message, extra=log_data)
            elif level == "CRITICAL":
                logger.critical(message, extra=log_data)
            else:
                logger.info(message, extra=log_data)
        
        return redis_success or api_success
    
    def report_metric(
        self,
        metric_type: Union[MetricType, str],
        value: float,
        unit: str,
        host_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime.datetime] = None,
        sampling_rate: float = 1.0
    ) -> bool:
        """
        Report a metric to the monitoring system.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            unit: Unit of measurement
            host_name: Name of the host
            tags: Additional tags for the metric
            timestamp: Timestamp for the metric
            sampling_rate: Sampling rate for the metric
            
        Returns:
            True if the metric was sent successfully, False otherwise
        """
        # Get hostname if not provided
        if not host_name:
            host_name = socket.gethostname()
        
        # Get timestamp if not provided
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        
        # Format metric data
        metric_data = {
            "service_name": self.service_name,
            "host_name": host_name,
            "metric_type": metric_type.value if isinstance(metric_type, MetricType) else metric_type,
            "value": value,
            "unit": unit,
            "timestamp": timestamp.isoformat(),
            "tags": tags or {},
            "sampling_rate": sampling_rate
        }
        
        # Send metric to Redis if enabled
        redis_success = False
        if self.use_redis and self.redis:
            try:
                # Publish metric to Redis channel
                channel = f"metrics:{self.service_name}"
                self.redis.publish(channel, json.dumps(metric_data))
                
                # Also add to a list for persistence
                metrics_key = f"metrics:{self.service_name}:{metric_data['metric_type']}:recent"
                self.redis.lpush(metrics_key, json.dumps(metric_data))
                self.redis.ltrim(metrics_key, 0, 999)  # Keep only the 1000 most recent metrics
                
                redis_success = True
            except Exception as e:
                logger.warning(f"Failed to send metric to Redis: {str(e)}")
        
        # Send metric to API if enabled
        api_success = False
        if self.use_api:
            try:
                # Send metric to API
                api_url = f"{self.api_base_url}/monitoring/metrics"
                response = requests.post(
                    api_url,
                    json=metric_data,
                    timeout=2  # Short timeout to avoid blocking
                )
                
                api_success = response.status_code < 400
            except Exception as e:
                logger.warning(f"Failed to send metric to API: {str(e)}")
        
        return redis_success or api_success
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the service.
        
        Returns:
            Dictionary containing health information
        """
        return get_system_health()
    
    def report_health(self) -> bool:
        """
        Report service health to the monitoring system.
        
        Returns:
            True if the health report was sent successfully, False otherwise
        """
        # Get health information
        health_info = self.check_health()
        
        # Send health report to API if enabled
        api_success = False
        if self.use_api:
            try:
                # Send health report to API
                api_url = f"{self.api_base_url}/monitoring/health/report"
                response = requests.post(
                    api_url,
                    json={
                        "service_name": self.service_name,
                        "health_info": health_info
                    },
                    timeout=2  # Short timeout to avoid blocking
                )
                
                api_success = response.status_code < 400
            except Exception as e:
                logger.warning(f"Failed to send health report to API: {str(e)}")
        
        return api_success


def log_execution_time(service_name: str, operation_name: Optional[str] = None):
    """
    Decorator to log the execution time of a function.
    
    Args:
        service_name: Name of the service
        operation_name: Name of the operation (defaults to function name)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get operation name
            op_name = operation_name or func.__name__
            
            # Create monitoring client
            client = MonitoringClient(service_name)
            
            # Record start time
            start_time = time.time()
            
            try:
                # Call function
                result = func(*args, **kwargs)
                
                # Record end time
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Log execution time
                client.report_metric(
                    metric_type=MetricType.EXECUTION_TIME,
                    value=execution_time * 1000,  # Convert to milliseconds
                    unit="ms",
                    tags={
                        "operation": op_name,
                        "success": "true"
                    }
                )
                
                # Log success
                client.log(
                    level=LogLevel.INFO,
                    message=f"Operation {op_name} completed successfully in {execution_time:.3f}s",
                    metadata={
                        "operation": op_name,
                        "execution_time": execution_time
                    }
                )
                
                return result
            except Exception as e:
                # Record end time
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Log execution time
                client.report_metric(
                    metric_type=MetricType.EXECUTION_TIME,
                    value=execution_time * 1000,  # Convert to milliseconds
                    unit="ms",
                    tags={
                        "operation": op_name,
                        "success": "false"
                    }
                )
                
                # Log error
                client.log(
                    level=LogLevel.ERROR,
                    message=f"Operation {op_name} failed: {str(e)}",
                    metadata={
                        "operation": op_name,
                        "execution_time": execution_time,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                )
                
                # Re-raise exception
                raise
        
        return wrapper
    
    return decorator


def log_execution_time_async(service_name: str, operation_name: Optional[str] = None):
    """
    Decorator to log the execution time of an async function.
    
    Args:
        service_name: Name of the service
        operation_name: Name of the operation (defaults to function name)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get operation name
            op_name = operation_name or func.__name__
            
            # Create monitoring client
            client = MonitoringClient(service_name)
            
            # Record start time
            start_time = time.time()
            
            try:
                # Call function
                result = await func(*args, **kwargs)
                
                # Record end time
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Log execution time
                client.report_metric(
                    metric_type=MetricType.EXECUTION_TIME,
                    value=execution_time * 1000,  # Convert to milliseconds
                    unit="ms",
                    tags={
                        "operation": op_name,
                        "success": "true"
                    }
                )
                
                # Log success
                client.log(
                    level=LogLevel.INFO,
                    message=f"Operation {op_name} completed successfully in {execution_time:.3f}s",
                    metadata={
                        "operation": op_name,
                        "execution_time": execution_time
                    }
                )
                
                return result
            except Exception as e:
                # Record end time
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Log execution time
                client.report_metric(
                    metric_type=MetricType.EXECUTION_TIME,
                    value=execution_time * 1000,  # Convert to milliseconds
                    unit="ms",
                    tags={
                        "operation": op_name,
                        "success": "false"
                    }
                )
                
                # Log error
                client.log(
                    level=LogLevel.ERROR,
                    message=f"Operation {op_name} failed: {str(e)}",
                    metadata={
                        "operation": op_name,
                        "execution_time": execution_time,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                )
                
                # Re-raise exception
                raise
        
        return wrapper
    
    return decorator


# Create a default client for convenience
default_client = MonitoringClient("isp_management")

# Convenience functions using the default client
def log(
    level: Union[LogLevel, str],
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    user_id: Optional[int] = None,
    source_ip: Optional[str] = None,
    request_path: Optional[str] = None,
    request_method: Optional[str] = None,
    response_status: Optional[int] = None,
    execution_time: Optional[float] = None
) -> bool:
    """Convenience function to log a message using the default client."""
    return default_client.log(
        level=level,
        message=message,
        metadata=metadata,
        trace_id=trace_id,
        correlation_id=correlation_id,
        user_id=user_id,
        source_ip=source_ip,
        request_path=request_path,
        request_method=request_method,
        response_status=response_status,
        execution_time=execution_time
    )

def report_metric(
    metric_type: Union[MetricType, str],
    value: float,
    unit: str,
    host_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    timestamp: Optional[datetime.datetime] = None,
    sampling_rate: float = 1.0
) -> bool:
    """Convenience function to report a metric using the default client."""
    return default_client.report_metric(
        metric_type=metric_type,
        value=value,
        unit=unit,
        host_name=host_name,
        tags=tags,
        timestamp=timestamp,
        sampling_rate=sampling_rate
    )

def check_health() -> Dict[str, Any]:
    """Convenience function to check health using the default client."""
    return default_client.check_health()

def report_health() -> bool:
    """Convenience function to report health using the default client."""
    return default_client.report_health()
