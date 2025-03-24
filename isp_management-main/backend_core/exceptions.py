"""
Common exceptions for the ISP Management Platform.

This module defines custom exceptions used throughout the application.
"""

from typing import List, Dict, Any, Optional


class ValidationErrorDetail:
    """Detailed validation error information."""
    def __init__(self, field: str, message: str, code: str = "invalid"):
        self.field = field
        self.message = message
        self.code = code

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            "field": self.field,
            "message": self.message,
            "code": self.code
        }


class BaseISPException(Exception):
    """Base exception for all ISP Management Platform exceptions."""
    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)


class NotFoundException(BaseISPException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class ValidationException(BaseISPException):
    """Exception raised when input validation fails."""
    def __init__(self, 
                message: str = "Validation failed", 
                errors: Optional[Dict[str, str]] = None,
                detailed_errors: Optional[List[ValidationErrorDetail]] = None):
        self.errors = errors or {}
        self.detailed_errors = detailed_errors or []
        super().__init__(message)
    
    def add_error(self, field: str, message: str, code: str = "invalid") -> None:
        """Add a detailed validation error."""
        self.detailed_errors.append(ValidationErrorDetail(field, message, code))
    
    def get_detailed_errors(self) -> List[Dict[str, str]]:
        """Get list of detailed errors in dictionary format."""
        return [error.to_dict() for error in self.detailed_errors]


class DuplicateException(BaseISPException):
    """Exception raised when attempting to create a duplicate resource."""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message)


class AuthenticationException(BaseISPException):
    """Exception raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthorizationException(BaseISPException):
    """Exception raised when a user is not authorized to perform an action."""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message)


class ConfigurationException(BaseISPException):
    """Exception raised when there is a configuration error."""
    def __init__(self, message: str = "Configuration error"):
        super().__init__(message)


class DatabaseException(BaseISPException):
    """Exception raised when there is a database error."""
    def __init__(self, message: str = "Database error"):
        super().__init__(message)


class ExternalServiceException(BaseISPException):
    """Exception raised when there is an error with an external service."""
    def __init__(self, message: str = "External service error", service_name: str = None):
        self.service_name = service_name
        super().__init__(message)


class RateLimitException(BaseISPException):
    """Exception raised when a rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message)


class BusinessRuleException(BaseISPException):
    """Exception raised when a business rule is violated."""
    def __init__(self, message: str = "Business rule violation"):
        super().__init__(message)


class ServiceException(BaseISPException):
    """Exception raised when a service operation fails."""
    def __init__(self, 
                message: str = "Service operation failed", 
                service_name: Optional[str] = None,
                operation: Optional[str] = None,
                details: Optional[Dict[str, Any]] = None):
        self.service_name = service_name
        self.operation = operation
        self.details = details or {}
        super().__init__(message)
