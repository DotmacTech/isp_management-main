"""
Monitoring service for the ISP Management Platform.

This module provides functionality for monitoring system health, performance metrics,
and resource usage across all modules of the platform.
"""

import os
import time
import psutil
import threading
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta

from fastapi import FastAPI
from prometheus_client import start_http_server, Gauge, Counter, Summary, Histogram
from sqlalchemy import text
from sqlalchemy.orm import Session

from isp_management.backend_core.config import settings
from isp_management.backend_core.database import get_db
from isp_management.backend_core.logging_service import get_logger, LoggingService

# Get the logger
logger = get_logger()


class MonitoringService:
    """Central monitoring service for the ISP Management Platform."""
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MonitoringService, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the monitoring service."""
        self.logger = logger
        self.monitoring_interval = int(os.getenv("MONITORING_INTERVAL", "60"))  # seconds
        self.prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9090"))
        self.prometheus_enabled = False
        self.monitoring_thread = None
        self.running = False
        self.alert_thresholds = {
            "cpu_usage": 80.0,  # percent
            "memory_usage": 80.0,  # percent
            "disk_usage": 80.0,  # percent
            "db_connection_count": 100,  # connections
            "api_error_rate": 5.0,  # percent
            "api_response_time": 1.0,  # seconds
        }
        self.alert_callbacks = []
        
        # Initialize metrics
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Set up monitoring metrics."""
        # System metrics
        self.cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage in percent')
        self.memory_usage = Gauge('system_memory_usage_percent', 'Memory usage in percent')
        self.disk_usage = Gauge('system_disk_usage_percent', 'Disk usage in percent')
        self.network_sent = Gauge('system_network_bytes_sent', 'Network bytes sent')
        self.network_received = Gauge('system_network_bytes_received', 'Network bytes received')
        
        # Database metrics
        self.db_connections = Gauge('db_connection_count', 'Number of database connections')
        self.db_size = Gauge('db_size_bytes', 'Database size in bytes')
        self.db_query_count = Counter('db_query_count', 'Number of database queries', ['operation'])
        self.db_query_time = Summary('db_query_time_seconds', 'Database query execution time', ['operation'])
        
        # API metrics
        self.api_request_count = Counter('api_request_count', 'Number of API requests', ['endpoint', 'method', 'status'])
        self.api_request_time = Histogram('api_request_time_seconds', 'API request execution time', ['endpoint', 'method'])
        self.api_error_count = Counter('api_error_count', 'Number of API errors', ['endpoint', 'error_type'])
        
        # Business metrics
        self.active_users = Gauge('business_active_users', 'Number of active users')
        self.active_sessions = Gauge('business_active_sessions', 'Number of active sessions')
        self.billing_revenue = Gauge('business_billing_revenue', 'Billing revenue')
        self.customer_count = Gauge('business_customer_count', 'Number of customers')
        
        # Cache metrics
        self.cache_hit_count = Counter('cache_hit_count', 'Number of cache hits')
        self.cache_miss_count = Counter('cache_miss_count', 'Number of cache misses')
        self.cache_size = Gauge('cache_size_bytes', 'Cache size in bytes')
        
        # Task queue metrics
        self.task_queue_length = Gauge('task_queue_length', 'Task queue length')
        self.task_processing_time = Summary('task_processing_time_seconds', 'Task processing time')
        self.task_error_count = Counter('task_error_count', 'Number of task errors', ['task_type'])
        
        self.prometheus_enabled = True
        self.logger.info("Monitoring metrics initialized", "monitoring")
    
    def start(self, app: Optional[FastAPI] = None):
        """
        Start the monitoring service.
        
        Args:
            app: FastAPI application instance
        """
        if self.running:
            return
        
        self.running = True
        
        # Start Prometheus HTTP server if enabled
        if self.prometheus_enabled:
            try:
                start_http_server(self.prometheus_port)
                self.logger.info(f"Prometheus metrics server started on port {self.prometheus_port}", "monitoring")
            except Exception as e:
                self.logger.error(f"Failed to start Prometheus metrics server: {str(e)}", "monitoring", exception=e)
                self.prometheus_enabled = False
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Register FastAPI middleware if app is provided
        if app:
            from isp_management.backend_core.logging_service import LoggingMiddleware
            app.add_middleware(LoggingMiddleware)
            self.logger.info("Monitoring middleware registered with FastAPI", "monitoring")
        
        self.logger.info("Monitoring service started", "monitoring")
    
    def stop(self):
        """Stop the monitoring service."""
        if not self.running:
            return
        
        self.running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
            self.monitoring_thread = None
        
        self.logger.info("Monitoring service stopped", "monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Collect database metrics
                self._collect_database_metrics()
                
                # Check for alert conditions
                self._check_alerts()
                
                # Sleep until next collection
                time.sleep(self.monitoring_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}", "monitoring", exception=e)
                time.sleep(10)  # Sleep for a shorter time on error
    
    def _collect_system_metrics(self):
        """Collect system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_usage.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.disk_usage.set(disk.percent)
            
            # Network usage
            network = psutil.net_io_counters()
            self.network_sent.set(network.bytes_sent)
            self.network_received.set(network.bytes_recv)
            
            self.logger.debug(
                "System metrics collected",
                "monitoring",
                context={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                }
            )
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {str(e)}", "monitoring", exception=e)
    
    def _collect_database_metrics(self):
        """Collect database metrics."""
        try:
            # Get a database session
            db = next(get_db())
            
            try:
                # Database connection count
                result = db.execute(text("SELECT count(*) FROM pg_stat_activity"))
                connection_count = result.scalar()
                self.db_connections.set(connection_count)
                
                # Database size
                result = db.execute(text("""
                    SELECT pg_database_size(current_database())
                """))
                db_size = result.scalar()
                self.db_size.set(db_size)
                
                self.logger.debug(
                    "Database metrics collected",
                    "monitoring",
                    context={
                        "connection_count": connection_count,
                        "db_size_bytes": db_size,
                    }
                )
            finally:
                db.close()
        except Exception as e:
            self.logger.error(f"Error collecting database metrics: {str(e)}", "monitoring", exception=e)
    
    def _check_alerts(self):
        """Check for alert conditions."""
        alerts = []
        
        # Check CPU usage
        if self.cpu_usage._value > self.alert_thresholds["cpu_usage"]:
            alerts.append({
                "type": "cpu_usage",
                "message": f"High CPU usage: {self.cpu_usage._value:.1f}%",
                "value": self.cpu_usage._value,
                "threshold": self.alert_thresholds["cpu_usage"],
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Check memory usage
        if self.memory_usage._value > self.alert_thresholds["memory_usage"]:
            alerts.append({
                "type": "memory_usage",
                "message": f"High memory usage: {self.memory_usage._value:.1f}%",
                "value": self.memory_usage._value,
                "threshold": self.alert_thresholds["memory_usage"],
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Check disk usage
        if self.disk_usage._value > self.alert_thresholds["disk_usage"]:
            alerts.append({
                "type": "disk_usage",
                "message": f"High disk usage: {self.disk_usage._value:.1f}%",
                "value": self.disk_usage._value,
                "threshold": self.alert_thresholds["disk_usage"],
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Check database connections
        if hasattr(self.db_connections, "_value") and self.db_connections._value > self.alert_thresholds["db_connection_count"]:
            alerts.append({
                "type": "db_connection_count",
                "message": f"High database connection count: {self.db_connections._value}",
                "value": self.db_connections._value,
                "threshold": self.alert_thresholds["db_connection_count"],
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Process alerts
        for alert in alerts:
            self.logger.warning(
                f"Alert: {alert['message']}",
                "monitoring",
                context=alert
            )
            
            # Call alert callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {str(e)}", "monitoring", exception=e)
    
    def register_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback function for alerts.
        
        Args:
            callback: Callback function that takes an alert dict as argument
        """
        self.alert_callbacks.append(callback)
    
    def set_alert_threshold(self, metric: str, threshold: float):
        """
        Set an alert threshold for a specific metric.
        
        Args:
            metric: Metric name
            threshold: Alert threshold value
        """
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = threshold
            self.logger.info(f"Alert threshold for {metric} set to {threshold}", "monitoring")
        else:
            self.logger.warning(f"Unknown metric for alert threshold: {metric}", "monitoring")
    
    def track_api_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """
        Track an API request.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        if not self.prometheus_enabled:
            return
        
        self.api_request_count.labels(endpoint=endpoint, method=method, status=str(status_code)).inc()
        self.api_request_time.labels(endpoint=endpoint, method=method).observe(duration)
        
        # Track errors (status code >= 400)
        if status_code >= 400:
            error_type = "client_error" if status_code < 500 else "server_error"
            self.api_error_count.labels(endpoint=endpoint, error_type=error_type).inc()
    
    def track_db_query(self, operation: str, duration: float):
        """
        Track a database query.
        
        Args:
            operation: Query operation (select, insert, update, delete)
            duration: Query duration in seconds
        """
        if not self.prometheus_enabled:
            return
        
        self.db_query_count.labels(operation=operation).inc()
        self.db_query_time.labels(operation=operation).observe(duration)
    
    def track_cache(self, hit: bool):
        """
        Track a cache access.
        
        Args:
            hit: Whether the cache access was a hit or miss
        """
        if not self.prometheus_enabled:
            return
        
        if hit:
            self.cache_hit_count.inc()
        else:
            self.cache_miss_count.inc()
    
    def track_task(self, task_type: str, duration: float, error: bool = False):
        """
        Track a background task.
        
        Args:
            task_type: Type of task
            duration: Task duration in seconds
            error: Whether the task resulted in an error
        """
        if not self.prometheus_enabled:
            return
        
        self.task_processing_time.observe(duration)
        
        if error:
            self.task_error_count.labels(task_type=task_type).inc()
    
    def update_business_metrics(
        self,
        active_users: Optional[int] = None,
        active_sessions: Optional[int] = None,
        billing_revenue: Optional[float] = None,
        customer_count: Optional[int] = None
    ):
        """
        Update business metrics.
        
        Args:
            active_users: Number of active users
            active_sessions: Number of active sessions
            billing_revenue: Billing revenue
            customer_count: Number of customers
        """
        if not self.prometheus_enabled:
            return
        
        if active_users is not None:
            self.active_users.set(active_users)
        
        if active_sessions is not None:
            self.active_sessions.set(active_sessions)
        
        if billing_revenue is not None:
            self.billing_revenue.set(billing_revenue)
        
        if customer_count is not None:
            self.customer_count.set(customer_count)
    
    def update_task_queue_length(self, queue_length: int):
        """
        Update task queue length.
        
        Args:
            queue_length: Current task queue length
        """
        if not self.prometheus_enabled:
            return
        
        self.task_queue_length.set(queue_length)
    
    def update_cache_size(self, size_bytes: int):
        """
        Update cache size.
        
        Args:
            size_bytes: Cache size in bytes
        """
        if not self.prometheus_enabled:
            return
        
        self.cache_size.set(size_bytes)


# Create a singleton instance
monitoring_service = MonitoringService()


def get_monitoring_service() -> MonitoringService:
    """
    Get the singleton monitoring service instance.
    
    Returns:
        The monitoring service instance
    """
    return monitoring_service


def track_api_request(endpoint: str, method: str, status_code: int, duration: float):
    """
    Track an API request.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        status_code: HTTP status code
        duration: Request duration in seconds
    """
    monitoring_service.track_api_request(endpoint, method, status_code, duration)


def track_db_query(operation: str, duration: float):
    """
    Track a database query.
    
    Args:
        operation: Query operation (select, insert, update, delete)
        duration: Query duration in seconds
    """
    monitoring_service.track_db_query(operation, duration)


def track_cache(hit: bool):
    """
    Track a cache access.
    
    Args:
        hit: Whether the cache access was a hit or miss
    """
    monitoring_service.track_cache(hit)


def track_task(task_type: str, duration: float, error: bool = False):
    """
    Track a background task.
    
    Args:
        task_type: Type of task
        duration: Task duration in seconds
        error: Whether the task resulted in an error
    """
    monitoring_service.track_task(task_type, duration, error)


def monitor_function(func):
    """
    Decorator to monitor function execution.
    
    Args:
        func: Function to monitor
        
    Returns:
        Decorated function
    """
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        error = False
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            error = True
            raise
        finally:
            duration = time.time() - start_time
            track_task(func.__name__, duration, error)
    
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        error = False
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error = True
            raise
        finally:
            duration = time.time() - start_time
            track_task(func.__name__, duration, error)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class DatabaseMonitoringMiddleware:
    """Middleware for monitoring database operations."""
    
    def __init__(self, engine):
        self.engine = engine
    
    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())
    
    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        start_time = conn.info['query_start_time'].pop(-1)
        duration = time.time() - start_time
        
        # Determine operation type
        operation = statement.split(' ', 1)[0].lower()
        if operation not in ['select', 'insert', 'update', 'delete']:
            operation = 'other'
        
        # Track query
        track_db_query(operation, duration)


def setup_database_monitoring(engine):
    """
    Set up database monitoring.
    
    Args:
        engine: SQLAlchemy engine
    """
    from sqlalchemy import event
    
    middleware = DatabaseMonitoringMiddleware(engine)
    event.listen(engine, 'before_cursor_execute', middleware.before_cursor_execute)
    event.listen(engine, 'after_cursor_execute', middleware.after_cursor_execute)
    
    logger.info("Database monitoring set up", "monitoring")


def email_alert_callback(alert: Dict[str, Any]):
    """
    Send an email alert.
    
    Args:
        alert: Alert information
    """
    from isp_management.backend_core.email_service import send_email
    
    subject = f"ISP Management Platform Alert: {alert['type']}"
    body = f"""
    Alert: {alert['message']}
    
    Value: {alert['value']}
    Threshold: {alert['threshold']}
    Timestamp: {alert['timestamp']}
    
    This is an automated alert from the ISP Management Platform monitoring system.
    """
    
    # Send to admin email
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    
    try:
        send_email(admin_email, subject, body)
        logger.info(f"Alert email sent to {admin_email}", "monitoring")
    except Exception as e:
        logger.error(f"Failed to send alert email: {str(e)}", "monitoring", exception=e)


def slack_alert_callback(alert: Dict[str, Any]):
    """
    Send a Slack alert.
    
    Args:
        alert: Alert information
    """
    import httpx
    
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        logger.warning("Slack webhook URL not configured", "monitoring")
        return
    
    message = {
        "text": f"ISP Management Platform Alert: {alert['message']}",
        "attachments": [
            {
                "color": "danger",
                "fields": [
                    {
                        "title": "Type",
                        "value": alert['type'],
                        "short": True
                    },
                    {
                        "title": "Value",
                        "value": str(alert['value']),
                        "short": True
                    },
                    {
                        "title": "Threshold",
                        "value": str(alert['threshold']),
                        "short": True
                    },
                    {
                        "title": "Timestamp",
                        "value": alert['timestamp'],
                        "short": True
                    }
                ]
            }
        ]
    }
    
    try:
        response = httpx.post(slack_webhook_url, json=message)
        if response.status_code == 200:
            logger.info("Alert sent to Slack", "monitoring")
        else:
            logger.warning(f"Failed to send alert to Slack: {response.status_code} {response.text}", "monitoring")
    except Exception as e:
        logger.error(f"Error sending alert to Slack: {str(e)}", "monitoring", exception=e)
