"""
Routes for the Configuration Management Module.

This module imports all route handlers for the configuration management module
to make them available through a single import statement.
"""

from modules.config_management.routes.configuration_routes import configuration_router

__all__ = [
    'configuration_router'
]
