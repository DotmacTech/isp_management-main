"""
Exceptions for the UNMS API client.
"""


class UNMSAPIError(Exception):
    """Base exception for UNMS API errors."""
    
    def __init__(self, message, *args, **kwargs):
        self.message = message
        super().__init__(message, *args, **kwargs)


class AuthenticationError(UNMSAPIError):
    """Exception raised when authentication fails."""
    pass


class TokenExpiredError(AuthenticationError):
    """Exception raised when the authentication token has expired."""
    pass


class RateLimitError(UNMSAPIError):
    """Exception raised when the API rate limit is exceeded."""
    
    def __init__(self, message, retry_after=None, *args, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, *args, **kwargs)


class ConnectionError(UNMSAPIError):
    """Exception raised when a connection error occurs."""
    pass


class ValidationError(UNMSAPIError):
    """Exception raised when request validation fails."""
    
    def __init__(self, message, details=None, *args, **kwargs):
        self.details = details or {}
        super().__init__(message, *args, **kwargs)


class ResourceNotFoundError(UNMSAPIError):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, message, resource_id=None, resource_type=None, status_code=None, *args, **kwargs):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.status_code = status_code or 404
        super().__init__(message, *args, **kwargs)


class PermissionError(UNMSAPIError):
    """Exception raised when the user does not have permission to access a resource."""
    pass


class ConfigurationError(UNMSAPIError):
    """Exception raised when there is a configuration error."""
    pass
