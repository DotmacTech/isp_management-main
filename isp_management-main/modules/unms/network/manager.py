"""
UNMS Network Manager.
"""
import logging
from typing import Dict, List, Any, Optional

from ..core import UNMSAPI
from .client import NetworkClient

logger = logging.getLogger('unms')


class NetworkManager:
    """
    Manager for UNMS/UISP network operations.
    
    This class provides high-level methods for working with UNMS network data,
    including topology, devices, and configuration management.
    """
    
    def __init__(self, api_client: UNMSAPI):
        """
        Initialize the network manager.
        
        Args:
            api_client: UNMS API client instance
        """
        self.api = api_client
        self.client = NetworkClient(api_client)
    
    async def get_device_connections(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get all connections for a device.
        
        Args:
            device_id: ID of the device
            
        Returns:
            List of connection objects
        """
        # Get device interfaces
        interfaces = await self.client.get_device_interfaces(device_id)
        
        # Get device neighbors
        neighbors = await self.client.get_device_neighbors(device_id)
        
        # Combine information into connections
        connections = []
        
        for interface in interfaces:
            interface_id = interface.get('id')
            neighbor = next((n for n in neighbors if n.get('interface_id') == interface_id), None)
            
            if neighbor:
                connections.append({
                    'local_interface': interface,
                    'remote_device': neighbor.get('device'),
                    'remote_interface': neighbor.get('remote_interface'),
                    'type': neighbor.get('type', 'unknown')
                })
        
        return connections
    
    async def get_device_traffic(self, device_id: str, 
                              period: str = 'hour') -> Dict[str, Any]:
        """
        Get traffic statistics for a device.
        
        Args:
            device_id: ID of the device
            period: Time period for statistics ('hour', 'day', 'week', 'month')
            
        Returns:
            Traffic statistics
        """
        try:
            path = f"api/devices/{device_id}/stats/traffic"
            params = {'period': period}
            return await self.api.request('GET', path, params=params)
        except Exception as e:
            logger.error(f"Error getting traffic stats for device {device_id}: {e}")
            raise
