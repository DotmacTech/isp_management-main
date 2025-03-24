"""
Services for the auth module.

This package contains services for the auth module as defined in the
authentication_workflow.md documentation.
"""

# Import and export service classes directly from the services.py file
import os
import sys
import importlib.util

# Import directly from the services.py file in the parent directory
services_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services.py')
spec = importlib.util.spec_from_file_location("auth_services", services_path)
auth_services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_services)

# Make the AuthService class available directly from this module
AuthService = auth_services.AuthService

__all__ = ['AuthService']
