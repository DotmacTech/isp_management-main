"""
Central logging and monitoring service for the ISP Management Platform.

This module provides a unified interface for logging, monitoring, and tracking
system events, errors, and performance metrics across all modules.
"""

import logging
import json
import time
import uuid
import socket
import traceback
import threading
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Callable, List, Union

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, Summary, push_to_gateway, CollectorRegistry

from isp_management.backend_core.config import settings

# Configure the standard Python logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Create a global registry for Prometheus metrics
REGISTRY = CollectorRegistry()

class LoggingService:
    """Central logging service for the ISP Management Platform."""
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LoggingService, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the logging service."""
        self.hostname = socket.gethostname()
        self.es_client = None
        self.prometheus_enabled = False
        
        # Initialize Elasticsearch client if URL is provided
        if settings.ELASTICSEARCH_URL:
            try:
                self.es_client = Elasticsearch([settings.ELASTICSEARCH_URL])
                if self.es_client.ping():
                    logging.info(f"Connected to Elasticsearch at {settings.ELASTICSEARCH_URL}")
                else:
                    logging.warning(f"Failed to connect to Elasticsearch at {settings.ELASTICSEARCH_URL}")
                    self.es_client = None
            except Exception as e:
                logging.error(f"Error connecting to Elasticsearch: {str(e)}")
                self.es_client = None
        
        # Initialize Prometheus metrics
        self.setup_prometheus_metrics()
    
    def setup_prometheus_metrics(self):
        """Set up Prometheus metrics."""
        try:
            # HTTP request metrics
            self.http_requests_total = Counter(
                'http_requests_total', 
                'Total number of HTTP requests',
                ['method', 'endpoint', 'status'],
                registry=REGISTRY
            )
            
            self.http_request_duration_seconds = Histogram(
                'http_request_duration_seconds',
                'HTTP request duration in seconds',
                ['method', 'endpoint'],
                registry=REGISTRY
            )
            
            # Database metrics
            self.db_query_duration_seconds = Histogram(
                'db_query_duration_seconds',
                'Database query duration in seconds',
                ['operation', 'table'],
                registry=REGISTRY
            )
            
            # Application metrics
            self.app_errors_total = Counter(
                'app_errors_total',
                'Total number of application errors',
                ['module', 'error_type'],
                registry=REGISTRY
            )
            
            # System metrics
            self.system_memory_usage = Gauge(
                'system_memory_usage',
                'System memory usage in bytes',
                registry=REGISTRY
            )
            
            # Business metrics
            self.active_users = Gauge(
                'active_users',
                'Number of active users',
                registry=REGISTRY
            )
            
            self.message_processing_time = Summary(
                'message_processing_time',
                'Time to process a message',
                registry=REGISTRY
            )
            
            self.prometheus_enabled = True
            logging.info("Prometheus metrics initialized")
        except Exception as e:
            logging.error(f"Error initializing Prometheus metrics: {str(e)}")
            self.prometheus_enabled = False
    
    def log(
        self,
        level: str,
        message: str,
        module: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """
        Log a message with the specified level and context.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            module: Module name
            context: Additional context data
            exception: Exception object if any
            request_id: Request ID for correlation
            user_id: User ID if available
        """
        # Get the standard Python logger for the module
        logger = logging.getLogger(module)
        
        # Log to standard output
        log_method = getattr(logger, level.lower())
        log_method(message)
        
        # Prepare log data
        timestamp = datetime.utcnow().isoformat()
        log_data = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "module": module,
            "hostname": self.hostname,
            "request_id": request_id or str(uuid.uuid4()),
            "user_id": user_id,
        }
        
        # Add context if provided
        if context:
            log_data["context"] = context
        
        # Add exception details if provided
        if exception:
            log_data["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc(),
            }
            
            # Increment error counter in Prometheus
            if self.prometheus_enabled:
                self.app_errors_total.labels(
                    module=module,
                    error_type=type(exception).__name__
                ).inc()
        
        # Log to Elasticsearch if available
        if self.es_client:
            try:
                index_name = f"isp-logs-{datetime.utcnow().strftime('%Y-%m-%d')}"
                self.es_client.index(
                    index=index_name,
                    body=log_data,
                )
            except ElasticsearchException as e:
                logger.error(f"Failed to log to Elasticsearch: {str(e)}")
    
    def debug(self, message: str, module: str, **kwargs) -> None:
        """Log a debug message."""
        self.log("debug", message, module, **kwargs)
    
    def info(self, message: str, module: str, **kwargs) -> None:
        """Log an info message."""
        self.log("info", message, module, **kwargs)
    
    def warning(self, message: str, module: str, **kwargs) -> None:
        """Log a warning message."""
        self.log("warning", message, module, **kwargs)
    
    def error(self, message: str, module: str, **kwargs) -> None:
        """Log an error message."""
        self.log("error", message, module, **kwargs)
    
    def critical(self, message: str, module: str, **kwargs) -> None:
        """Log a critical message."""
        self.log("critical", message, module, **kwargs)
    
    def track_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Track a custom metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Metric labels
        """
        if not self.prometheus_enabled:
            return
        
        # Find the metric in the registry
        metric = None
        for m in REGISTRY._names_to_collectors.values():
            if m._name == metric_name:
                metric = m
                break
        
        if metric:
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
        else:
            logging.warning(f"Metric {metric_name} not found in registry")
    
    def push_metrics(self, job_name: str, push_gateway: str) -> None:
        """
        Push metrics to Prometheus Pushgateway.
        
        Args:
            job_name: Job name for the metrics
            push_gateway: Pushgateway URL
        """
        if not self.prometheus_enabled:
            return
        
        try:
            push_to_gateway(push_gateway, job=job_name, registry=REGISTRY)
            logging.info(f"Metrics pushed to {push_gateway}")
        except Exception as e:
            logging.error(f"Failed to push metrics: {str(e)}")
    
    def monitor_database(self, operation: str, table: str, duration: float) -> None:
        """
        Monitor database operations.
        
        Args:
            operation: Database operation (select, insert, update, delete)
            table: Database table
            duration: Operation duration in seconds
        """
        if self.prometheus_enabled:
            self.db_query_duration_seconds.labels(
                operation=operation,
                table=table
            ).observe(duration)
    
    def monitor_function(
        self,
        module: str,
        function_name: Optional[str] = None,
        track_args: bool = False
    ) -> Callable:
        """
        Decorator to monitor function execution.
        
        Args:
            module: Module name
            function_name: Function name (defaults to decorated function name)
            track_args: Whether to track function arguments
            
        Returns:
            Decorated function
        """
        def decorator(func):
            nonlocal function_name
            if function_name is None:
                function_name = func.__name__
                
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                request_id = str(uuid.uuid4())
                
                # Log function entry
                context = {}
                if track_args:
                    # Be careful not to log sensitive information
                    safe_kwargs = {k: v for k, v in kwargs.items() 
                                  if k not in ['password', 'token', 'secret']}
                    context["args"] = str(args)
                    context["kwargs"] = str(safe_kwargs)
                
                self.info(
                    f"Entering {function_name}",
                    module,
                    context=context,
                    request_id=request_id
                )
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Log function exit
                    self.info(
                        f"Exiting {function_name} (duration: {duration:.3f}s)",
                        module,
                        context={"duration": duration},
                        request_id=request_id
                    )
                    
                    # Track function duration
                    if self.prometheus_enabled:
                        histogram_name = f"{module.replace('.', '_')}_{function_name}_duration_seconds"
                        for m in REGISTRY._names_to_collectors.values():
                            if m._name == histogram_name:
                                m.observe(duration)
                                break
                    
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    
                    # Log exception
                    self.error(
                        f"Exception in {function_name}: {str(e)}",
                        module,
                        exception=e,
                        context={"duration": duration},
                        request_id=request_id
                    )
                    
                    # Re-raise the exception
                    raise
            
            return wrapper
        
        return decorator


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = LoggingService()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process an incoming request and log request/response details.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            The HTTP response
        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract request details
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"
        
        # Get user ID if available
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.id
        
        # Log request
        self.logger.info(
            f"Request: {method} {url}",
            "http",
            context={
                "method": method,
                "url": url,
                "client_host": client_host,
                "headers": dict(request.headers),
            },
            request_id=request_id,
            user_id=user_id
        )
        
        # Measure request processing time
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Extract response details
            status_code = response.status_code
            
            # Log response
            self.logger.info(
                f"Response: {status_code} (duration: {duration:.3f}s)",
                "http",
                context={
                    "status_code": status_code,
                    "duration": duration,
                    "headers": dict(response.headers),
                },
                request_id=request_id,
                user_id=user_id
            )
            
            # Update Prometheus metrics
            if self.logger.prometheus_enabled:
                endpoint = request.url.path
                self.logger.http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=str(status_code)
                ).inc()
                
                self.logger.http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
        except Exception as e:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log exception
            self.logger.error(
                f"Exception during request processing: {str(e)}",
                "http",
                exception=e,
                context={
                    "method": method,
                    "url": url,
                    "duration": duration,
                },
                request_id=request_id,
                user_id=user_id
            )
            
            # Re-raise the exception
            raise


# Create a singleton instance
logging_service = LoggingService()


def get_logger() -> LoggingService:
    """
    Get the singleton logging service instance.
    
    Returns:
        The logging service instance
    """
    return logging_service


def monitor_database_query(query_func):
    """
    Decorator to monitor database queries.
    
    Args:
        query_func: Database query function to monitor
        
    Returns:
        Decorated function
    """
    @wraps(query_func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Extract operation and table information if available
        operation = "query"
        table = "unknown"
        
        if len(args) > 0 and hasattr(args[0], "__tablename__"):
            table = args[0].__tablename__
        
        if query_func.__name__ in ["insert", "update", "delete", "select"]:
            operation = query_func.__name__
        
        try:
            result = query_func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Monitor database operation
            logging_service.monitor_database(operation, table, duration)
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            
            # Log exception
            logging_service.error(
                f"Database error in {operation} on {table}: {str(e)}",
                "database",
                exception=e,
                context={
                    "operation": operation,
                    "table": table,
                    "duration": duration,
                }
            )
            
            # Re-raise the exception
            raise
    
    return wrapper
