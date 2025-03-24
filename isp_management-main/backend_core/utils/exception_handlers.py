"""
Exception handlers for the ISP Management Platform.

This module provides standardized exception handlers for FastAPI applications,
ensuring consistent error responses across all API endpoints.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from backend_core.exceptions import (
    BaseISPException,
    NotFoundException,
    ValidationException,
    DuplicateException,
    AuthenticationException,
    AuthorizationException,
    ConfigurationException,
    DatabaseException,
    ExternalServiceException,
    RateLimitException,
    BusinessRuleException
)
from backend_core.schemas import ErrorResponse, DetailedErrorResponse

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
    path: Optional[str] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_type: Type of error
        message: Error message
        details: Detailed validation errors
        path: Request path that caused the error
        
    Returns:
        JSONResponse with standardized error format
    """
    error_content = ErrorResponse(
        status_code=status_code,
        error_type=error_type,
        message=message,
        details=[DetailedErrorResponse(**detail) for detail in details] if details else None,
        timestamp=datetime.utcnow(),
        path=path
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_content.dict()
    )


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """
    Handle ValidationException and return a standardized error response.
    
    Args:
        request: FastAPI request
        exc: ValidationException
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(f"Validation error: {exc.message}")
    
    details = exc.get_detailed_errors() if hasattr(exc, 'get_detailed_errors') else None
    
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_type="ValidationError",
        message=exc.message,
        details=details,
        path=request.url.path
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle RequestValidationError and return a standardized error response.
    
    Args:
        request: FastAPI request
        exc: RequestValidationError
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(f"Request validation error: {str(exc)}")
    
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:]) if len(error["loc"]) > 1 else error["loc"][0]
        details.append({
            "field": field,
            "message": error["msg"],
            "code": error["type"]
        })
    
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_type="RequestValidationError",
        message="Invalid request parameters",
        details=details,
        path=request.url.path
    )


async def not_found_exception_handler(request: Request, exc: NotFoundException) -> JSONResponse:
    """
    Handle NotFoundException and return a standardized error response.
    
    Args:
        request: FastAPI request
        exc: NotFoundException
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.info(f"Resource not found: {exc.message}")
    
    return create_error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        error_type="NotFoundError",
        message=exc.message,
        path=request.url.path
    )


async def duplicate_exception_handler(request: Request, exc: DuplicateException) -> JSONResponse:
    """
    Handle DuplicateException and return a standardized error response.
    
    Args:
        request: FastAPI request
        exc: DuplicateException
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.info(f"Duplicate resource: {exc.message}")
    
    return create_error_response(
        status_code=status.HTTP_409_CONFLICT,
        error_type="DuplicateError",
        message=exc.message,
        path=request.url.path
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationException) -> JSONResponse:
    """
    Handle AuthenticationException and return a standardized error response.
    
    Args:
        request: FastAPI request
        exc: AuthenticationException
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(f"Authentication error: {exc.message}")
    
    return create_error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        error_type="AuthenticationError",
        message=exc.message,
        path=request.url.path
    )


async def authorization_exception_handler(request: Request, exc: AuthorizationException) -> JSONResponse:
    """
    Handle AuthorizationException and return a standardized error response.
    
    Args:
        request: FastAPI request
        exc: AuthorizationException
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(f"Authorization error: {exc.message}")
    
    return create_error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        error_type="AuthorizationError",
        message=exc.message,
        path=request.url.path
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle general exceptions and return a standardized error response.
    
    Args:
        request: FastAPI request
        exc: Any exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type="InternalServerError",
        message="An unexpected error occurred",
        path=request.url.path
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with a FastAPI application.
    
    Args:
        app: FastAPI application
    """
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
    app.add_exception_handler(DuplicateException, duplicate_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(AuthorizationException, authorization_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
