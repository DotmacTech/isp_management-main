"""
UNMS Module - Unified API for UNMS/UISP integration.

This module provides a unified interface for interacting with UNMS/UISP APIs.
It combines functionality from the previous unms_api and UNMS Network modules
into a single coherent module organized according to domain-driven design principles.
"""

# Core functionality
from .core import UNMSAPI, AsyncUNMSAPI
from .config import get_config

# API endpoints
from .api import router

# Services
from .services import UNMSService

# Resources
from .resources import DeviceManager, SiteManager, UserManager

# Network management
from .network import NetworkClient, NetworkManager, TopologyService

__all__ = [
    # Core
    "UNMSAPI", 
    "AsyncUNMSAPI", 
    "get_config",
    
    # API
    "router",
    
    # Services
    "UNMSService",
    
    # Resources
    "DeviceManager", 
    "SiteManager", 
    "UserManager",
    
    # Network
    "NetworkClient",
    "NetworkManager",
    "TopologyService"
]
