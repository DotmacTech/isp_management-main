import time
import uuid
import json
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import asyncio

from backend_core.database import get_db
from .services import LoggingService
from .models import LogLevel
from .schemas import ServiceLogCreate

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatically logging all API requests and responses.
    This middleware captures request details, execution time, and response status,
    then logs them to the centralized logging system.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        service_name: str,
        exclude_paths: Optional[list] = None,
        exclude_methods: Optional[list] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        sensitive_headers: Optional[list] = None,
        sensitive_body_fields: Optional[list] = None
    ):
        super().__init__(app)
        self.service_name = service_name
        self.exclude_paths = exclude_paths or []
        self.exclude_methods = exclude_methods or []
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.sensitive_headers = sensitive_headers or ["authorization", "cookie", "x-api-key"]
        self.sensitive_body_fields = sensitive_body_fields or ["password", "token", "secret", "key", "credit_card"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
            
        # Skip logging for excluded methods
        if request.method.lower() in [m.lower() for m in self.exclude_methods]:
            return await call_next(request)
        
        # Generate trace and correlation IDs
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        
        # Extract user ID from request state if available
        user_id = None
        if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
            user_id = request.state.user.id
        
        # Capture request details
        start_time = time.time()
        request_body = None
        
        if self.log_request_body:
            try:
                # Clone the request body
                body_bytes = await request.body()
                request_body = body_bytes.decode()
                
                # Reset the request body
                async def receive():
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                request._receive = receive
                
                # Sanitize sensitive data
                if request_body:
                    try:
                        body_json = json.loads(request_body)
                        sanitized_body = self._sanitize_data(body_json, self.sensitive_body_fields)
                        request_body = json.dumps(sanitized_body)
                    except json.JSONDecodeError:
                        # Not JSON, keep as is
                        pass
            except Exception as e:
                logger.error(f"Error capturing request body: {str(e)}")
                request_body = None
        
        # Process the request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_detail = None
        except Exception as exc:
            status_code = 500
            error_detail = str(exc)
            raise exc
        finally:
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Capture response body if enabled
            response_body = None
            if self.log_response_body and status_code != 204:  # Skip for 204 No Content
                try:
                    # Get the original response body
                    original_body = b""
                    async for chunk in response.body_iterator:
                        original_body += chunk
                    
                    # Create a new response with the same body
                    response = Response(
                        content=original_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                    
                    # Decode and sanitize the response body
                    try:
                        response_text = original_body.decode()
                        try:
                            body_json = json.loads(response_text)
                            sanitized_body = self._sanitize_data(body_json, self.sensitive_body_fields)
                            response_body = json.dumps(sanitized_body)
                        except json.JSONDecodeError:
                            # Not JSON, keep as is
                            response_body = response_text
                    except UnicodeDecodeError:
                        # Binary data, don't log
                        response_body = "<binary data>"
                except Exception as e:
                    logger.error(f"Error capturing response body: {str(e)}")
                    response_body = None
            
            # Determine log level based on status code
            log_level = LogLevel.INFO
            if status_code >= 500:
                log_level = LogLevel.ERROR
            elif status_code >= 400:
                log_level = LogLevel.WARNING
            
            # Prepare headers (sanitized)
            headers = dict(request.headers)
            for header in self.sensitive_headers:
                if header.lower() in headers:
                    headers[header.lower()] = "***REDACTED***"
            
            # Prepare metadata
            metadata = {
                "request": {
                    "headers": headers,
                    "query_params": dict(request.query_params),
                    "client_host": request.client.host if request.client else None,
                }
            }
            
            if request_body:
                metadata["request"]["body"] = request_body
                
            if response_body:
                metadata["response"] = {"body": response_body}
                
            if error_detail:
                metadata["error"] = error_detail
            
            # Create log entry
            log_data = ServiceLogCreate(
                service_name=self.service_name,
                log_level=log_level,
                message=f"{request.method} {request.url.path} - {status_code}",
                trace_id=trace_id,
                correlation_id=correlation_id,
                source_ip=request.client.host if request.client else None,
                user_id=user_id,
                request_path=str(request.url.path),
                request_method=request.method,
                response_status=status_code,
                execution_time=execution_time,
                metadata=metadata
            )
            
            # Log asynchronously to avoid blocking the response
            asyncio.create_task(self._log_request(log_data))
            
        return response
    
    def _sanitize_data(self, data: Any, sensitive_fields: list) -> Any:
        """Sanitize sensitive data in dictionaries, lists, or other structures."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_data(value, sensitive_fields)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item, sensitive_fields) for item in data]
        else:
            return data
    
    async def _log_request(self, log_data: ServiceLogCreate) -> None:
        """Log the request to the centralized logging system."""
        try:
            # Get database session
            db = next(get_db())
            
            # Create logging service
            logging_service = LoggingService(db)
            
            # Create log entry
            await logging_service.create_log(log_data)
            
            # Close database session
            db.close()
        except Exception as e:
            # Fallback to standard logging if centralized logging fails
            logger.error(f"Failed to log request to centralized system: {str(e)}")
            logger.info(f"Request log: {log_data.service_name} - {log_data.message}")


def setup_request_logging(
    app: ASGIApp, 
    service_name: str,
    exclude_paths: Optional[list] = None,
    exclude_methods: Optional[list] = None,
    log_request_body: bool = False,
    log_response_body: bool = False,
    sensitive_headers: Optional[list] = None,
    sensitive_body_fields: Optional[list] = None
) -> None:
    """
    Helper function to set up request logging middleware.
    
    Args:
        app: The FastAPI application
        service_name: Name of the service for logging
        exclude_paths: List of path prefixes to exclude from logging
        exclude_methods: List of HTTP methods to exclude from logging
        log_request_body: Whether to log request bodies
        log_response_body: Whether to log response bodies
        sensitive_headers: List of headers to redact
        sensitive_body_fields: List of body fields to redact
    """
    app.add_middleware(
        LoggingMiddleware,
        service_name=service_name,
        exclude_paths=exclude_paths,
        exclude_methods=exclude_methods,
        log_request_body=log_request_body,
        log_response_body=log_response_body,
        sensitive_headers=sensitive_headers,
        sensitive_body_fields=sensitive_body_fields
    )
