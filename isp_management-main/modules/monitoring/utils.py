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

from .models import LogLevel, MetricType, AlertSeverity


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
    # Convert string log level to enum if needed
    if isinstance(log_level, str):
        try:
            log_level = LogLevel[log_level.upper()]
        except KeyError:
            log_level = LogLevel.INFO
    
    # Generate trace and correlation IDs if not provided
    if not trace_id:
        trace_id = str(uuid.uuid4())
    
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    
    # Get hostname
    hostname = socket.gethostname()
    
    # Format timestamp
    timestamp = datetime.datetime.utcnow().isoformat()
    
    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "service_name": service_name,
        "log_level": log_level.value,
        "message": message,
        "hostname": hostname,
        "trace_id": trace_id,
        "correlation_id": correlation_id
    }
    
    # Add user ID if provided
    if user_id is not None:
        log_entry["user_id"] = user_id
    
    # Add metadata if provided
    if metadata:
        log_entry["metadata"] = metadata
    
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
    
    # Handle edge cases
    if index.is_integer():
        return sorted_values[int(index)]
    else:
        # Interpolate between two values
        lower_index = math.floor(index)
        upper_index = math.ceil(index)
        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
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
    
    import numpy as np
    
    # Calculate statistics
    min_value = min(values)
    max_value = max(values)
    avg_value = sum(values) / len(values)
    
    # Calculate percentiles
    median = np.median(values)
    p95 = np.percentile(values, 95)
    p99 = np.percentile(values, 99)
    
    return {
        "min": float(min_value),
        "max": float(max_value),
        "avg": float(avg_value),
        "median": float(median),
        "p95": float(p95),
        "p99": float(p99),
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
        # Get Redis connection
        redis_client = next(get_redis())
        
        # Format alert data
        alert_data = {
            "alert_id": alert_id,
            "service_name": service_name,
            "severity": severity.value if isinstance(severity, Enum) else severity,
            "message": message,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata or {}
        }
        
        # Publish alert to Redis
        channel = f"alerts:{service_name}"
        redis_client.publish(channel, json.dumps(alert_data))
        
        # Also publish to the global alerts channel
        redis_client.publish("alerts:all", json.dumps(alert_data))
        
        # Store the alert in a Redis list for persistence
        alerts_key = f"alerts:{service_name}:history"
        redis_client.lpush(alerts_key, json.dumps(alert_data))
        redis_client.ltrim(alerts_key, 0, 99)  # Keep only the 100 most recent alerts
        
        return True
    except Exception as e:
        logger.error(f"Error publishing alert to Redis: {str(e)}")
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
        # Get Redis connection
        redis_client = next(get_redis())
        
        # Get alerts from Redis
        if service_name:
            alerts_key = f"alerts:{service_name}:history"
        else:
            alerts_key = "alerts:all:history"
        
        # Get alerts from Redis list
        alerts_json = redis_client.lrange(alerts_key, 0, limit - 1)
        
        # Parse JSON
        alerts = [json.loads(alert) for alert in alerts_json]
        
        return alerts
    except Exception as e:
        logger.error(f"Error getting recent alerts from Redis: {str(e)}")
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
    # Regular expression to match duration string
    pattern = r"^(\d+)([smhdw])$"
    match = re.match(pattern, duration_str.lower())
    
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")
    
    value, unit = match.groups()
    value = int(value)
    
    # Convert to timedelta
    if unit == "s":
        return datetime.timedelta(seconds=value)
    elif unit == "m":
        return datetime.timedelta(minutes=value)
    elif unit == "h":
        return datetime.timedelta(hours=value)
    elif unit == "d":
        return datetime.timedelta(days=value)
    elif unit == "w":
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
    # Calculate time range in seconds
    time_range = (end_time - start_time).total_seconds()
    
    # Determine aggregation window
    if time_range <= 3600:  # 1 hour
        return "1m"  # 1 minute
    elif time_range <= 86400:  # 1 day
        return "5m"  # 5 minutes
    elif time_range <= 604800:  # 1 week
        return "1h"  # 1 hour
    else:
        return "1d"  # 1 day


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
    # Parse aggregation window
    window_delta = parse_duration(aggregation_window)
    
    # Group metrics by time window
    grouped_metrics = {}
    
    for metric in metrics:
        # Parse timestamp
        timestamp = datetime.datetime.fromisoformat(metric["timestamp"])
        
        # Calculate window start time
        window_seconds = window_delta.total_seconds()
        timestamp_seconds = timestamp.timestamp()
        window_start_seconds = (timestamp_seconds // window_seconds) * window_seconds
        window_start = datetime.datetime.fromtimestamp(window_start_seconds, tz=datetime.timezone.utc)
        
        # Group metrics by window start time
        window_key = window_start.isoformat()
        if window_key not in grouped_metrics:
            grouped_metrics[window_key] = []
        
        grouped_metrics[window_key].append(metric)
    
    # Aggregate metrics for each window
    aggregated_metrics = []
    
    for window_key, window_metrics in grouped_metrics.items():
        # Extract values
        values = [float(metric[value_field]) for metric in window_metrics]
        
        # Calculate statistics
        stats = calculate_statistics(values)
        
        # Create aggregated metric
        aggregated_metric = {
            "timestamp": window_key,
            "count": stats["count"],
            "min": stats["min"],
            "max": stats["max"],
            "avg": stats["avg"],
            "median": stats["median"],
            "p95": stats["p95"],
            "p99": stats["p99"]
        }
        
        # Copy metadata from first metric
        if window_metrics:
            for key, value in window_metrics[0].items():
                if key not in ["timestamp", value_field]:
                    aggregated_metric[key] = value
        
        aggregated_metrics.append(aggregated_metric)
    
    # Sort by timestamp
    aggregated_metrics.sort(key=lambda m: m["timestamp"])
    
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
    if sensitive_fields is None:
        sensitive_fields = [
            "password", "token", "secret", "key", "authorization",
            "credit_card", "ssn", "social_security", "auth"
        ]
    
    def _sanitize_value(key: str, value: Any) -> Any:
        """Recursively sanitize values."""
        if isinstance(value, dict):
            return {k: _sanitize_value(k, v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_sanitize_value(key, item) for item in value]
        elif isinstance(value, str) and any(sensitive in key.lower() for sensitive in sensitive_fields):
            return "***REDACTED***"
        else:
            return value
    
    # Create a copy of the log data
    sanitized_data = {}
    
    # Sanitize each field
    for key, value in log_data.items():
        sanitized_data[key] = _sanitize_value(key, value)
    
    return sanitized_data


def get_system_health() -> Dict[str, Any]:
    """
    Get system health information.
    
    Returns:
        Dictionary containing system health information
    """
    import psutil
    
    # Get system information
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get network information
    net_io = psutil.net_io_counters()
    
    # Get process information
    process = psutil.Process()
    process_memory = process.memory_info()
    
    # Get hostname
    hostname = socket.gethostname()
    
    # Create health information
    health_info = {
        "hostname": hostname,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "cpu": {
            "percent": cpu_percent
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent
        },
        "disk": {
            "total": disk.total,
            "free": disk.free,
            "percent": disk.percent
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        },
        "process": {
            "pid": process.pid,
            "memory_rss": process_memory.rss,
            "memory_vms": process_memory.vms,
            "cpu_percent": process.cpu_percent(interval=None)
        }
    }
    
    # Check Redis if available
    try:
        redis_client = next(get_redis())
        redis_info = redis_client.info()
        
        health_info["redis"] = {
            "used_memory": redis_info.get("used_memory", 0),
            "connected_clients": redis_info.get("connected_clients", 0),
            "uptime_in_seconds": redis_info.get("uptime_in_seconds", 0)
        }
    except Exception:
        pass
    
    return health_info


def check_service_health(
    service_url: str,
    timeout: int = 5,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None
) -> Tuple[bool, Optional[float]]:
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
    
    try:
        # Make request
        start_time = datetime.datetime.now()
        response = requests.request(
            method=method,
            url=service_url,
            timeout=timeout,
            headers=headers or {}
        )
        end_time = datetime.datetime.now()
        
        # Calculate response time
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Check if response is successful
        is_healthy = response.status_code < 400
        
        return is_healthy, response_time_ms
    except Exception:
        return False, None
