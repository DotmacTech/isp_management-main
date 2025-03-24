"""
Logging utility functions for the ISP Management Platform.

This module provides convenient functions and decorators for logging
throughout the application, making it easy to integrate with the central
logging service.
"""

import functools
import inspect
import time
import uuid
from typing import Dict, Any, Optional, Callable, Union, Type

from fastapi import Request, Response, Depends
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from isp_management.backend_core.logging_service import get_logger
from isp_management.backend_core.monitoring_service import get_monitoring_service

# Get the logger and monitoring service
logger = get_logger()
monitoring_service = get_monitoring_service()


def log_debug(
    message: str,
    module: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """
    Log a debug message.
    
    Args:
        message: Log message
        module: Module name (defaults to caller module)
        context: Additional context data
        request_id: Request ID for correlation
        user_id: User ID if available
    """
    if module is None:
        frame = inspect.currentframe().f_back
        module = frame.f_globals["__name__"]
    
    logger.debug(message, module, context=context, request_id=request_id, user_id=user_id)


def log_info(
    message: str,
    module: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """
    Log an info message.
    
    Args:
        message: Log message
        module: Module name (defaults to caller module)
        context: Additional context data
        request_id: Request ID for correlation
        user_id: User ID if available
    """
    if module is None:
        frame = inspect.currentframe().f_back
        module = frame.f_globals["__name__"]
    
    logger.info(message, module, context=context, request_id=request_id, user_id=user_id)


def log_warning(
    message: str,
    module: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """
    Log a warning message.
    
    Args:
        message: Log message
        module: Module name (defaults to caller module)
        context: Additional context data
        request_id: Request ID for correlation
        user_id: User ID if available
    """
    if module is None:
        frame = inspect.currentframe().f_back
        module = frame.f_globals["__name__"]
    
    logger.warning(message, module, context=context, request_id=request_id, user_id=user_id)


def log_error(
    message: str,
    module: Optional[str] = None,
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """
    Log an error message.
    
    Args:
        message: Log message
        module: Module name (defaults to caller module)
        exception: Exception object if any
        context: Additional context data
        request_id: Request ID for correlation
        user_id: User ID if available
    """
    if module is None:
        frame = inspect.currentframe().f_back
        module = frame.f_globals["__name__"]
    
    logger.error(
        message, 
        module, 
        exception=exception, 
        context=context, 
        request_id=request_id, 
        user_id=user_id
    )


def log_critical(
    message: str,
    module: Optional[str] = None,
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """
    Log a critical message.
    
    Args:
        message: Log message
        module: Module name (defaults to caller module)
        exception: Exception object if any
        context: Additional context data
        request_id: Request ID for correlation
        user_id: User ID if available
    """
    if module is None:
        frame = inspect.currentframe().f_back
        module = frame.f_globals["__name__"]
    
    logger.critical(
        message, 
        module, 
        exception=exception, 
        context=context, 
        request_id=request_id, 
        user_id=user_id
    )


def log_function(
    log_args: bool = False,
    log_result: bool = False,
    log_level: str = "info"
) -> Callable:
    """
    Decorator to log function entry and exit.
    
    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        log_level: Log level (debug, info, warning, error)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate request ID
            request_id = str(uuid.uuid4())
            
            # Get module name
            module = func.__module__
            
            # Prepare context
            context = {}
            if log_args:
                # Be careful not to log sensitive information
                safe_kwargs = {k: v for k, v in kwargs.items() 
                              if k not in ['password', 'token', 'secret']}
                context["args"] = str(args)
                context["kwargs"] = str(safe_kwargs)
            
            # Log function entry
            log_method = getattr(logger, log_level)
            log_method(
                f"Entering {func.__name__}",
                module,
                context=context,
                request_id=request_id
            )
            
            # Measure execution time
            start_time = time.time()
            
            try:
                # Call the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Prepare exit context
                exit_context = {"duration": duration}
                if log_result and result is not None:
                    # Be careful not to log sensitive information
                    if isinstance(result, dict) and any(k in result for k in ['password', 'token', 'secret']):
                        exit_context["result"] = "Result contains sensitive information"
                    else:
                        exit_context["result"] = str(result)
                
                # Log function exit
                log_method(
                    f"Exiting {func.__name__} (duration: {duration:.3f}s)",
                    module,
                    context=exit_context,
                    request_id=request_id
                )
                
                return result
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                
                # Log exception
                logger.error(
                    f"Exception in {func.__name__}: {str(e)}",
                    module,
                    exception=e,
                    context={"duration": duration},
                    request_id=request_id
                )
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    return decorator


def log_db_query(operation: str, table: str, duration: float) -> None:
    """
    Log a database query.
    
    Args:
        operation: Database operation (select, insert, update, delete)
        table: Database table
        duration: Query duration in seconds
    """
    logger.info(
        f"Database {operation} on {table} (duration: {duration:.3f}s)",
        "database",
        context={
            "operation": operation,
            "table": table,
            "duration": duration
        }
    )
    
    # Monitor database query
    monitoring_service.track_db_query(operation, duration)


def log_api_request(
    endpoint: str,
    method: str,
    status_code: int,
    duration: float,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> None:
    """
    Log an API request.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        status_code: HTTP status code
        duration: Request duration in seconds
        request_id: Request ID for correlation
        user_id: User ID if available
    """
    logger.info(
        f"API {method} {endpoint} -> {status_code} (duration: {duration:.3f}s)",
        "api",
        context={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration": duration
        },
        request_id=request_id,
        user_id=user_id
    )
    
    # Monitor API request
    monitoring_service.track_api_request(endpoint, method, status_code, duration)


class LoggingRoute(APIRoute):
    """Custom API route that logs requests and responses."""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Generate request ID
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
            
            # Get user ID if available
            user_id = None
            if hasattr(request.state, "user") and request.state.user:
                user_id = request.state.user.id
            
            # Log request
            logger.info(
                f"Request: {request.method} {request.url.path}",
                "api",
                context={
                    "method": request.method,
                    "url": str(request.url),
                    "client_host": request.client.host if request.client else "unknown",
                    "headers": dict(request.headers),
                },
                request_id=request_id,
                user_id=user_id
            )
            
            # Measure request processing time
            start_time = time.time()
            
            try:
                # Process the request
                response = await original_route_handler(request)
                
                # Calculate request duration
                duration = time.time() - start_time
                
                # Extract response details
                status_code = response.status_code
                
                # Log response
                logger.info(
                    f"Response: {status_code} (duration: {duration:.3f}s)",
                    "api",
                    context={
                        "status_code": status_code,
                        "duration": duration,
                        "headers": dict(response.headers),
                    },
                    request_id=request_id,
                    user_id=user_id
                )
                
                # Log API request for monitoring
                log_api_request(
                    request.url.path,
                    request.method,
                    status_code,
                    duration,
                    request_id,
                    user_id
                )
                
                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id
                
                return response
            except Exception as e:
                # Calculate request duration
                duration = time.time() - start_time
                
                # Log exception
                logger.error(
                    f"Exception during request processing: {str(e)}",
                    "api",
                    exception=e,
                    context={
                        "method": request.method,
                        "url": str(request.url),
                        "duration": duration,
                    },
                    request_id=request_id,
                    user_id=user_id
                )
                
                # Re-raise the exception
                raise
        
        return custom_route_handler


class LoggingDBMiddleware:
    """Middleware for logging database operations."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    def __call__(self, db: Session = Depends()):
        """
        Wrap a database session with logging.
        
        Args:
            db: Database session
            
        Returns:
            Wrapped database session
        """
        # Wrap database methods with logging
        original_execute = db.execute
        
        def execute_with_logging(statement, *args, **kwargs):
            # Measure execution time
            start_time = time.time()
            
            try:
                # Execute the statement
                result = original_execute(statement, *args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Determine operation type
                operation = str(statement).split(' ', 1)[0].lower()
                if operation not in ['select', 'insert', 'update', 'delete']:
                    operation = 'other'
                
                # Determine table name (if possible)
                table = 'unknown'
                if hasattr(statement, 'table') and hasattr(statement.table, 'name'):
                    table = statement.table.name
                
                # Log query
                log_db_query(operation, table, duration)
                
                return result
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                
                # Log exception
                logger.error(
                    f"Database error: {str(e)}",
                    "database",
                    exception=e,
                    context={
                        "duration": duration,
                        "statement": str(statement),
                    }
                )
                
                # Re-raise the exception
                raise
        
        # Replace the execute method
        db.execute = execute_with_logging
        
        return db
