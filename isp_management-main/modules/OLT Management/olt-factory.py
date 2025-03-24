"""
OLT Adapter Factory Module

This module provides a factory class for creating OLT adapters based on vendor type.
It abstracts the creation of different vendor-specific adapters.
"""

import logging
from typing import Dict, Any, Optional

from .adapters.base import OLTAdapter
from .adapters.huawei_adapter import HuaweiOLTAdapter
from .adapters.zte_adapter import ZTEOLTAdapter
from .exceptions import UnsupportedVendorError

logger = logging.getLogger(__name__)

class OLTAdapterFactory:
    """
    Factory class for creating OLT adapters.
    
    This factory encapsulates the logic for instantiating different vendor-specific
    OLT adapters based on the provided vendor type.
    """
    
    # Map vendor names to adapter classes for easy lookup
    ADAPTER_MAP = {
        'huawei': HuaweiOLTAdapter,
        'zte': ZTEOLTAdapter
    }
    
    @classmethod
    def create_adapter(cls, vendor: str, host: str, username: str, password: str, 
                      port: Optional[int] = None, model: Optional[str] = None,
                      **kwargs) -> OLTAdapter:
        """
        Create an OLT adapter for the specified vendor.
        
        Args:
            vendor: Vendor name (e.g., 'huawei', 'zte')
            host: OLT hostname or IP address
            username: Authentication username
            password: Authentication password
            port: Optional port number (defaults to vendor-specific default if not provided)
            model: Optional model name (defaults to vendor-specific default if not provided)
            **kwargs: Additional vendor-specific parameters
            
        Returns:
            OLTAdapter: An instance of the appropriate OLT adapter
            
        Raises:
            UnsupportedVendorError: If the specified vendor is not supported
        """
        # Normalize vendor name
        vendor_lower = vendor.lower()
        
        # Check if vendor is supported
        if vendor_lower not in cls.ADAPTER_MAP:
            supported_vendors = ", ".join(cls.ADAPTER_MAP.keys())
            raise UnsupportedVendorError(
                f"Unsupported vendor '{vendor}'. Supported vendors: {supported_vendors}"
            )
        
        # Get the adapter class
        adapter_class = cls.ADAPTER_MAP[vendor_lower]
        
        # Determine port based on vendor if not specified
        if port is None:
            port = 22 if vendor_lower == 'huawei' else 23
        
        # Create the adapter instance
        logger.info(f"Creating {vendor} OLT adapter for {host}")
        
        # Configure adapter based on vendor
        if vendor_lower == 'huawei':
            return adapter_class(
                host=host,
                username=username,
                password=password,
                port=port,
                model=model or 'MA5800',
                default_frame=kwargs.get('default_frame', '0'),
                default_slot=kwargs.get('default_slot', '0')
            )
        elif vendor_lower == 'zte':
            return adapter_class(
                host=host,
                username=username,
                password=password,
                port=port,
                model=model or 'C320',
                default_gpon_index=kwargs.get('default_gpon_index', '1/1/1')
            )
        
        # This should never happen due to the earlier check, but just in case
        raise UnsupportedVendorError(f"Implementation missing for vendor '{vendor}'")
    
    @classmethod
    def get_supported_vendors(cls) -> list:
        """
        Get a list of supported vendors.
        
        Returns:
            list: List of supported vendor names
        """
        return list(cls.ADAPTER_MAP.keys())
    
    @classmethod
    def register_adapter(cls, vendor: str, adapter_class) -> None:
        """
        Register a new vendor adapter class.
        
        This method allows extending the factory with new adapter implementations
        without modifying the factory code.
        
        Args:
            vendor: Vendor name
            adapter_class: Adapter class to register
        """
        vendor_lower = vendor.lower()
        logger.info(f"Registering adapter for vendor: {vendor_lower}")
        cls.ADAPTER_MAP[vendor_lower] = adapter_class