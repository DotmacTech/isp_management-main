"""
UNMS Network Client for managing network devices and topology.
"""
import logging
from typing import Dict, List, Any, Optional

from ..core import UNMSAPI

logger = logging.getLogger('unms')


class NetworkClient:
    """
    Client for interacting with UNMS network management functionality.
    
    This client provides methods for managing network devices, topology,
    and configuration.
    """
    
    def __init__(self, api_client: UNMSAPI):
        """
        Initialize the network client.
        
        Args:
            api_client: UNMS API client instance
        """
        self.api = api_client
    
    async def get_topology(self) -> Dict[str, Any]:
        """
        Get the complete network topology.
        
        Returns:
            Dict containing the network topology
        """
        try:
            path = f"api/topology"
            return await self.api.request('GET', path)
        except Exception as e:
            logger.error(f"Error getting network topology: {e}")
            raise
    
    async def get_device_interfaces(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get all interfaces for a device.
        
        Args:
            device_id: ID of the device
            
        Returns:
            List of interface objects
        """
        try:
            path = f"api/devices/{device_id}/interfaces"
            return await self.api.request('GET', path)
        except Exception as e:
            logger.error(f"Error getting interfaces for device {device_id}: {e}")
            raise
    
    async def get_device_neighbors(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get all neighboring devices for a device.
        
        Args:
            device_id: ID of the device
            
        Returns:
            List of neighbor objects
        """
        try:
            path = f"api/devices/{device_id}/neighbors"
            return await self.api.request('GET', path)
        except Exception as e:
            logger.error(f"Error getting neighbors for device {device_id}: {e}")
            raise
