"""
Utility functions for the Monitoring Module.

This module provides helper functions for logging, metrics calculation,
alert notification, and other monitoring-related tasks.
"""

import json
import logging
import datetime
import uuid
from typing import Dict, Any, Optional, List, Union, Tuple
import socket
import re
import math
from enum import Enum
import redis
import numpy as np

from backend_core.config import settings
from backend_core.cache import get_redis

from ..models import LogLevel, MetricType, AlertSeverity


# Configure logger
logger = logging.getLogger(__name__)


def format_log_message(
    service_name: str,
    log_level: Union[LogLevel, str],
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Format a log message for consistent logging across services.
    
    Args:
        service_name: Name of the service generating the log
        log_level: Log level (INFO, WARNING, ERROR, DEBUG, CRITICAL)
        message: Log message
        metadata: Additional metadata to include in the log
        trace_id: Trace ID for distributed tracing
        correlation_id: Correlation ID for request correlation
        user_id: ID of the user associated with the log
        
    Returns:
        Formatted log message as a dictionary
    """
    # Convert log level to string if it's an enum
    if isinstance(log_level, LogLevel):
        log_level = log_level.value
    
    # Ensure log level is uppercase
    log_level = log_level.upper()
    
    # Generate trace ID if not provided
    if not trace_id:
        trace_id = str(uuid.uuid4())
    
    # Create log entry
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": service_name,
        "level": log_level,
        "message": message,
        "trace_id": trace_id
    }
    
    # Add optional fields if provided
    if correlation_id:
        log_entry["correlation_id"] = correlation_id
    
    if user_id:
        log_entry["user_id"] = user_id
    
    if metadata:
        log_entry["metadata"] = metadata
    
    # Add host information
    log_entry["host"] = socket.gethostname()
    
    return log_entry


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Calculate the specified percentile of a list of values.
    
    Args:
        values: List of values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Percentile value
    """
    if not values:
        return 0.0
    
    # Sort values
    sorted_values = sorted(values)
    
    # Calculate index
    index = (percentile / 100.0) * (len(sorted_values) - 1)
    
    # Handle exact index
    if index.is_integer():
        return sorted_values[int(index)]
    
    # Interpolate between two values
    lower_index = math.floor(index)
    upper_index = math.ceil(index)
    
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    
    # Linear interpolation
    fraction = index - lower_index
    return lower_value + (upper_value - lower_value) * fraction


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    Calculate statistics for a list of values.
    
    Args:
        values: List of values to calculate statistics for
        
    Returns:
        Dictionary containing statistics (min, max, avg, median, p95, p99)
    """
    if not values:
        return {
            "min": 0.0,
            "max": 0.0,
            "avg": 0.0,
            "median": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "count": 0
        }
    
    # Calculate basic statistics
    min_value = min(values)
    max_value = max(values)
    avg_value = sum(values) / len(values)
    
    # Calculate percentiles
    median = calculate_percentile(values, 50)
    p95 = calculate_percentile(values, 95)
    p99 = calculate_percentile(values, 99)
    
    return {
        "min": min_value,
        "max": max_value,
        "avg": avg_value,
        "median": median,
        "p95": p95,
        "p99": p99,
        "count": len(values)
    }


def publish_alert(
    alert_id: int,
    service_name: str,
    severity: AlertSeverity,
    message: str,
    timestamp: datetime.datetime,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Publish an alert to Redis for real-time notification.
    
    Args:
        alert_id: ID of the alert in the database
        service_name: Name of the service generating the alert
        severity: Alert severity
        message: Alert message
        timestamp: Alert timestamp
        metadata: Additional metadata to include in the alert
        
    Returns:
        True if the alert was published successfully, False otherwise
    """
    try:
        # Get Redis client
        redis_client = get_redis()
        
        # Convert severity to string if it's an enum
        if isinstance(severity, AlertSeverity):
            severity = severity.value
        
        # Create alert message
        alert_message = {
            "alert_id": alert_id,
            "service": service_name,
            "severity": severity,
            "message": message,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata or {}
        }
        
        # Publish to Redis
        redis_client.publish(
            settings.redis_alert_channel,
            json.dumps(alert_message)
        )
        
        # Add to recent alerts list
        redis_client.lpush(
            f"{settings.redis_alert_prefix}:recent",
            json.dumps(alert_message)
        )
        
        # Trim list to limit
        redis_client.ltrim(
            f"{settings.redis_alert_prefix}:recent",
            0,
            settings.redis_alert_recent_limit - 1
        )
        
        # Add to service-specific list
        redis_client.lpush(
            f"{settings.redis_alert_prefix}:{service_name}:recent",
            json.dumps(alert_message)
        )
        
        # Trim service-specific list
        redis_client.ltrim(
            f"{settings.redis_alert_prefix}:{service_name}:recent",
            0,
            settings.redis_alert_recent_limit - 1
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error publishing alert: {str(e)}")
        return False


def get_recent_alerts(
    service_name: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get recent alerts from Redis.
    
    Args:
        service_name: Name of the service to get alerts for (None for all services)
        limit: Maximum number of alerts to return
        
    Returns:
        List of recent alerts
    """
    try:
        # Get Redis client
        redis_client = get_redis()
        
        # Determine key
        key = f"{settings.redis_alert_prefix}:{service_name}:recent" if service_name else f"{settings.redis_alert_prefix}:recent"
        
        # Get alerts
        alerts_json = redis_client.lrange(key, 0, limit - 1)
        
        # Parse JSON
        alerts = [json.loads(alert.decode('utf-8')) for alert in alerts_json]
        
        return alerts
    
    except Exception as e:
        logger.error(f"Error getting recent alerts: {str(e)}")
        return []


def parse_duration(duration_str: str) -> datetime.timedelta:
    """
    Parse a duration string into a timedelta object.
    
    Supported formats:
    - Xs: X seconds
    - Xm: X minutes
    - Xh: X hours
    - Xd: X days
    - Xw: X weeks
    
    Args:
        duration_str: Duration string
        
    Returns:
        Timedelta object
    """
    # Define regex pattern
    pattern = r'^(\d+)([smhdw])$'
    
    # Match pattern
    match = re.match(pattern, duration_str)
    
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")
    
    # Extract value and unit
    value = int(match.group(1))
    unit = match.group(2)
    
    # Convert to timedelta
    if unit == 's':
        return datetime.timedelta(seconds=value)
    elif unit == 'm':
        return datetime.timedelta(minutes=value)
    elif unit == 'h':
        return datetime.timedelta(hours=value)
    elif unit == 'd':
        return datetime.timedelta(days=value)
    elif unit == 'w':
        return datetime.timedelta(weeks=value)
    else:
        raise ValueError(f"Invalid duration unit: {unit}")


def get_metric_aggregation_window(
    start_time: datetime.datetime,
    end_time: datetime.datetime
) -> str:
    """
    Determine the appropriate aggregation window based on the time range.
    
    Args:
        start_time: Start time of the range
        end_time: End time of the range
        
    Returns:
        Aggregation window (1m, 5m, 1h, 1d)
    """
    # Calculate time difference in seconds
    time_diff = (end_time - start_time).total_seconds()
    
    # Determine appropriate aggregation window
    if time_diff <= 3600:  # 1 hour
        return "1m"
    elif time_diff <= 86400:  # 1 day
        return "5m"
    elif time_diff <= 604800:  # 1 week
        return "1h"
    else:
        return "1d"


def aggregate_metrics(
    metrics: List[Dict[str, Any]],
    aggregation_window: str,
    value_field: str = "value"
) -> List[Dict[str, Any]]:
    """
    Aggregate metrics by time window.
    
    Args:
        metrics: List of metrics
        aggregation_window: Aggregation window (1m, 5m, 1h, 1d)
        value_field: Field containing the metric value
        
    Returns:
        List of aggregated metrics
    """
    if not metrics:
        return []
    
    # Parse aggregation window
    window_value = int(aggregation_window[:-1])
    window_unit = aggregation_window[-1]
    
    # Convert to seconds
    if window_unit == 'm':
        window_seconds = window_value * 60
    elif window_unit == 'h':
        window_seconds = window_value * 3600
    elif window_unit == 'd':
        window_seconds = window_value * 86400
    else:
        raise ValueError(f"Invalid aggregation window unit: {window_unit}")
    
    # Group metrics by time window
    grouped_metrics = {}
    
    for metric in metrics:
        # Parse timestamp
        timestamp = datetime.datetime.fromisoformat(metric["timestamp"])
        
        # Calculate window start time
        window_start = timestamp.replace(
            microsecond=0,
            second=0,
            minute=(timestamp.minute // window_value) * window_value
        )
        
        if window_unit == 'h':
            window_start = window_start.replace(minute=0)
        elif window_unit == 'd':
            window_start = window_start.replace(minute=0, hour=0)
        
        # Convert to ISO format for grouping
        window_key = window_start.isoformat()
        
        # Initialize group if not exists
        if window_key not in grouped_metrics:
            grouped_metrics[window_key] = {
                "values": [],
                "timestamp": window_start.isoformat(),
                "tags": metric.get("tags", {})
            }
        
        # Add value to group
        grouped_metrics[window_key]["values"].append(metric[value_field])
    
    # Calculate statistics for each group
    aggregated_metrics = []
    
    for window_key, group in grouped_metrics.items():
        # Calculate statistics
        stats = calculate_statistics(group["values"])
        
        # Create aggregated metric
        aggregated_metric = {
            "timestamp": group["timestamp"],
            "min": stats["min"],
            "max": stats["max"],
            "avg": stats["avg"],
            "median": stats["median"],
            "p95": stats["p95"],
            "p99": stats["p99"],
            "count": stats["count"],
            "tags": group["tags"]
        }
        
        aggregated_metrics.append(aggregated_metric)
    
    # Sort by timestamp
    aggregated_metrics.sort(key=lambda x: x["timestamp"])
    
    return aggregated_metrics


def sanitize_log_data(
    log_data: Dict[str, Any],
    sensitive_fields: List[str] = None
) -> Dict[str, Any]:
    """
    Sanitize sensitive data in log entries.
    
    Args:
        log_data: Log data to sanitize
        sensitive_fields: List of sensitive field names to redact
        
    Returns:
        Sanitized log data
    """
    # Use default sensitive fields if not provided
    if sensitive_fields is None:
        sensitive_fields = [
            "password",
            "token",
            "api_key",
            "secret",
            "credential",
            "auth",
            "key",
            "private"
        ]
    
    # Create a copy of the log data
    sanitized_data = log_data.copy()
    
    # Recursively sanitize dictionaries
    def sanitize_dict(data):
        for key, value in data.items():
            # Check if key contains sensitive information
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                data[key] = "***REDACTED***"
            # Recursively sanitize nested dictionaries
            elif isinstance(value, dict):
                sanitize_dict(value)
            # Sanitize lists of dictionaries
            elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
                for item in value:
                    sanitize_dict(item)
    
    # Sanitize the data
    if isinstance(sanitized_data, dict):
        sanitize_dict(sanitized_data)
    
    return sanitized_data


def get_system_health() -> Dict[str, Any]:
    """
    Get system health information.
    
    Returns:
        Dictionary containing system health information
    """
    try:
        # Get host information
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # Get system metrics
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_total = memory.total
        memory_available = memory.available
        memory_used = memory.used
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_total = disk.total
        disk_free = disk.free
        disk_used = disk.used
        disk_percent = disk.percent
        
        # Network information
        net_io = psutil.net_io_counters()
        net_bytes_sent = net_io.bytes_sent
        net_bytes_recv = net_io.bytes_recv
        net_packets_sent = net_io.packets_sent
        net_packets_recv = net_io.packets_recv
        
        # System uptime
        boot_time = psutil.boot_time()
        uptime_seconds = datetime.datetime.now().timestamp() - boot_time
        
        # Format uptime
        uptime_days = int(uptime_seconds // 86400)
        uptime_hours = int((uptime_seconds % 86400) // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)
        uptime_formatted = f"{uptime_days}d {uptime_hours}h {uptime_minutes}m"
        
        # Return health information
        return {
            "hostname": hostname,
            "ip_address": ip_address,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count
            },
            "memory": {
                "total": memory_total,
                "available": memory_available,
                "used": memory_used,
                "percent": memory_percent
            },
            "disk": {
                "total": disk_total,
                "free": disk_free,
                "used": disk_used,
                "percent": disk_percent
            },
            "network": {
                "bytes_sent": net_bytes_sent,
                "bytes_recv": net_bytes_recv,
                "packets_sent": net_packets_sent,
                "packets_recv": net_packets_recv
            },
            "uptime": {
                "seconds": uptime_seconds,
                "formatted": uptime_formatted
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }


def check_service_health(
    service_url: str,
    timeout: int = 5,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None
) -> Tuple[bool, float]:
    """
    Check the health of a service by making an HTTP request.
    
    Args:
        service_url: URL of the service health endpoint
        timeout: Request timeout in seconds
        method: HTTP method to use
        headers: HTTP headers to include
        
    Returns:
        Tuple of (is_healthy, response_time_ms)
    """
    import requests
    from requests.exceptions import RequestException
    
    try:
        # Record start time
        start_time = datetime.datetime.now()
        
        # Make request
        response = requests.request(
            method=method,
            url=service_url,
            timeout=timeout,
            headers=headers or {}
        )
        
        # Calculate response time
        end_time = datetime.datetime.now()
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Check if response is successful
        is_healthy = response.status_code < 400
        
        return is_healthy, response_time_ms
    
    except RequestException as e:
        logger.warning(f"Error checking service health at {service_url}: {str(e)}")
        return False, 0
