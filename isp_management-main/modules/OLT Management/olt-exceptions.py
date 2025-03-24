"""
OLT Management Exceptions Module

This module defines custom exceptions for the OLT management module.
"""

class OLTManagementError(Exception):
    """Base exception for all OLT management errors."""
    pass


class OLTConnectionError(OLTManagementError):
    """
    Exception raised when a connection to an OLT device fails.
    
    This could be due to network issues, authentication failures,
    or device unavailability.
    """
    pass


class OLTCommandError(OLTManagementError):
    """
    Exception raised when a command to an OLT device fails.
    
    This could be due to invalid command syntax, insufficient permissions,
    or device-specific issues.
    """
    pass


class UnsupportedVendorError(OLTManagementError):
    """
    Exception raised when attempting to use an unsupported OLT vendor.
    
    This occurs when the factory is asked to create an adapter for
    a vendor that is not supported.
    """
    pass


class ONTProvisioningError(OLTManagementError):
    """
    Exception raised when ONT provisioning fails.
    
    This could be due to invalid serial number, duplicate ONT,
    or resource limitations on the OLT.
    """
    pass


class ONTConfigurationError(OLTManagementError):
    """
    Exception raised when ONT configuration fails.
    
    This could be due to invalid parameters, unsupported features,
    or ONT state issues.
    """
    pass


class ONTNotFoundError(OLTManagementError):
    """
    Exception raised when attempting to access a non-existent ONT.
    
    This occurs when an operation is attempted on an ONT that
    doesn't exist or has been deprovisioned.
    """
    pass


class PoolExhaustedError(OLTManagementError):
    """
    Exception raised when a connection pool is exhausted.
    
    This occurs when all available connections are in use and
    the maximum number of connections has been reached.
    """
    pass


class CredentialError(OLTManagementError):
    """
    Exception raised for credential-related issues.
    
    This could include missing, invalid, or inaccessible credentials.
    """
    pass


class ParseError(OLTManagementError):
    """
    Exception raised when parsing OLT output fails.
    
    This could be due to unexpected output format or incomplete responses.
    """
    pass