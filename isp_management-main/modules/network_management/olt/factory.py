"""
OLT Adapter Factory Module

This module provides a factory for creating OLT adapters based on vendor type.
"""

import logging
from typing import Dict, Any, Optional, Type

from .adapters.base import OLTAdapter
from .adapters.huawei_adapter import HuaweiOLTAdapter
from .adapters.zte_adapter import ZTEOLTAdapter
from .exceptions import UnsupportedVendorError

logger = logging.getLogger(__name__)


class OLTAdapterFactory:
    """
    Factory class for creating OLT adapters.
    
    This class provides methods for creating vendor-specific OLT adapters
    based on the provided vendor type.
    """
    
    # Mapping of vendor names to adapter classes
    _adapter_classes = {
        'huawei': HuaweiOLTAdapter,
        'zte': ZTEOLTAdapter,
    }
    
    @classmethod
    def create_adapter(cls, vendor: str, **kwargs) -> OLTAdapter:
        """
        Create an OLT adapter for the specified vendor.
        
        Args:
            vendor: Vendor name (e.g., 'huawei', 'zte')
            **kwargs: Additional arguments to pass to the adapter constructor
            
        Returns:
            OLTAdapter: An instance of the appropriate OLT adapter
            
        Raises:
            UnsupportedVendorError: If the vendor is not supported
        """
        vendor_lower = vendor.lower()
        
        if vendor_lower not in cls._adapter_classes:
            supported_vendors = ', '.join(cls._adapter_classes.keys())
            error_msg = f"Unsupported vendor: {vendor}. Supported vendors: {supported_vendors}"
            logger.error(error_msg)
            raise UnsupportedVendorError(error_msg)
        
        adapter_class = cls._adapter_classes[vendor_lower]
        logger.info(f"Creating {vendor} OLT adapter")
        return adapter_class(**kwargs)
    
    @classmethod
    def get_supported_vendors(cls) -> list:
        """
        Get a list of supported vendors.
        
        Returns:
            list: List of supported vendor names
        """
        return list(cls._adapter_classes.keys())
    
    @classmethod
    def register_adapter(cls, vendor: str, adapter_class: Type[OLTAdapter]) -> None:
        """
        Register a new adapter class for a vendor.
        
        This method allows for extending the factory with new vendor adapters
        without modifying the factory code.
        
        Args:
            vendor: Vendor name (e.g., 'nokia', 'fiberhome')
            adapter_class: Adapter class to register
        """
        vendor_lower = vendor.lower()
        cls._adapter_classes[vendor_lower] = adapter_class
        logger.info(f"Registered adapter class for vendor: {vendor}")
