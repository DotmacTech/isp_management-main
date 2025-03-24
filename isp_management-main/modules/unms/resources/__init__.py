"""
Resource managers for the UNMS API client.

This package contains resource managers for different UNMS API resources.
"""
import logging
from typing import Any

logger = logging.getLogger('unms_api')


def init_resource_managers(api_client: Any) -> None:
    """
    Initialize all resource managers for an API client.
    
    Args:
        api_client: UNMS API client.
    """
    # Import resource modules
    from . import devices, sites, users
    
    # Initialize resource managers
    devices.init_device_managers(api_client)
    sites.init_site_managers(api_client)
    users.init_user_managers(api_client)
    
    logger.debug("Resource managers initialized")
