"""
Device resource manager for the UNMS API.
"""
from typing import Dict, List, Any, Optional

from ..core import UNMSAPI

class DeviceManager:
    """
    Device management for UNMS API.
    
    This class provides methods for managing devices in UNMS.
    """
    
    def __init__(self, client):
        """
        Initialize the device manager.
        
        Args:
            client: UNMS API client instance.
        """
        self.client = client
    
    def get_all(self, site_id: Optional[str] = None, parent_id: Optional[str] = None,
               status: Optional[str] = None, model: Optional[str] = None,
               include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        Get a list of all devices in the network.
        
        Args:
            site_id (Optional[str]): Filter by site ID. Defaults to None.
            parent_id (Optional[str]): Filter by parent device ID. Defaults to None.
            status (Optional[str]): Filter by device status. Defaults to None.
            model (Optional[str]): Filter by device model. Defaults to None.
            include_disabled (bool): Whether to include disabled devices. Defaults to False.
            
        Returns:
            List[Dict[str, Any]]: List of devices.
        """
        params = {}
        if site_id:
            params['siteId'] = site_id
        if parent_id:
            params['parentId'] = parent_id
        if status:
            params['status'] = status
        if model:
            params['model'] = model
        if include_disabled:
            params['includeDisabled'] = 'true'
        
        return self.client.get("devices", params=params)
    
    def get_by_id(self, device_id: str) -> Dict[str, Any]:
        """
        Get a device by ID.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            Dict[str, Any]: Device data.
            
        Raises:
            ResourceNotFoundError: If the device does not exist.
        """
        try:
            return self.client.get(f"devices/{device_id}")
        except UNMSAPIError as e:
            if e.status_code == 404:
                raise ResourceNotFoundError(
                    message=f"Device with ID {device_id} not found",
                    status_code=404,
                    resource_id=device_id,
                    resource_type="device"
                ) from e
            raise
    
    def get_by_mac(self, mac_address: str) -> Dict[str, Any]:
        """
        Get a device by MAC address.
        
        Args:
            mac_address (str): MAC address.
            
        Returns:
            Dict[str, Any]: Device data.
        """
        # Normalize MAC address format
        mac = mac_address.replace(':', '').replace('-', '').lower()
        
        # Search for devices with matching MAC
        devices = self.get_all()
        for device in devices:
            if device.get('identification', {}).get('mac', '').replace(':', '').lower() == mac:
                return device
        
        raise UNMSAPIError(f"Device with MAC {mac_address} not found")
    
    def get_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get the status of a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            Dict[str, Any]: Device status.
        """
        return self.client.get(f"devices/{device_id}/status")
    
    def get_interfaces(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get the interfaces of a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            List[Dict[str, Any]]: List of interfaces.
        """
        return self.client.get(f"devices/{device_id}/interfaces")
    
    def get_statistics(self, device_id: str, start_time: Optional[str] = None,
                      end_time: Optional[str] = None, interval: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a device.
        
        Args:
            device_id (str): Device ID.
            start_time (Optional[str]): Start time in ISO format. Defaults to None.
            end_time (Optional[str]): End time in ISO format. Defaults to None.
            interval (Optional[str]): Interval for statistics aggregation. Defaults to None.
            
        Returns:
            Dict[str, Any]: Device statistics.
        """
        params = {}
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        if interval:
            params['interval'] = interval
        
        return self.client.get(f"devices/{device_id}/statistics", params=params)
    
    def get_outages(self, device_id: str, start_time: Optional[str] = None,
                   end_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get outages for a device.
        
        Args:
            device_id (str): Device ID.
            start_time (Optional[str]): Start time in ISO format. Defaults to None.
            end_time (Optional[str]): End time in ISO format. Defaults to None.
            
        Returns:
            List[Dict[str, Any]]: List of outages.
        """
        params = {}
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        return self.client.get(f"devices/{device_id}/outages", params=params)
    
    def reboot(self, device_id: str) -> bool:
        """
        Reboot a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            bool: Whether the reboot was successful.
        """
        self.client.post(f"devices/{device_id}/reboot", expected_status=[200, 202, 204])
        return True
    
    def factory_reset(self, device_id: str) -> bool:
        """
        Factory reset a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            bool: Whether the factory reset was successful.
        """
        self.client.post(f"devices/{device_id}/factory-reset", expected_status=[200, 202, 204])
        return True
    
    def upgrade_firmware(self, device_id: str, firmware_id: str) -> bool:
        """
        Upgrade the firmware of a device.
        
        Args:
            device_id (str): Device ID.
            firmware_id (str): Firmware ID.
            
        Returns:
            bool: Whether the firmware upgrade was initiated successfully.
        """
        data = {
            'firmwareId': firmware_id
        }
        
        self.client.post(f"devices/{device_id}/upgrade", json_data=data, expected_status=[200, 202, 204])
        return True
    
    def update(self, device_id: str, name: Optional[str] = None, site_id: Optional[str] = None,
              note: Optional[str] = None, location: Optional[Dict[str, str]] = None,
              tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Update a device.
        
        Args:
            device_id (str): Device ID.
            name (Optional[str]): Device name. Defaults to None.
            site_id (Optional[str]): Site ID. Defaults to None.
            note (Optional[str]): Device note. Defaults to None.
            location (Optional[Dict[str, str]]): Device location. Defaults to None.
            tags (Optional[List[str]]): Device tags. Defaults to None.
            
        Returns:
            Dict[str, Any]: Updated device data.
        """
        # Get current device data
        device = self.get_by_id(device_id)
        
        # Prepare update data
        data = {}
        
        if name is not None:
            data['name'] = name
        
        if site_id is not None:
            data['siteId'] = site_id
        
        if note is not None:
            data['note'] = note
        
        if location is not None:
            data['location'] = location
        
        if tags is not None:
            data['tags'] = tags
        
        # Only update if there are changes
        if not data:
            return device
        
        return self.client.put(f"devices/{device_id}", json_data=data)
    
    def delete(self, device_id: str) -> bool:
        """
        Delete a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            bool: Whether the deletion was successful.
        """
        self.client.delete(f"devices/{device_id}", expected_status=[200, 204])
        return True
    
    def authorize(self, device_id: str) -> bool:
        """
        Authorize a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            bool: Whether the authorization was successful.
        """
        self.client.post(f"devices/{device_id}/authorize", expected_status=[200, 204])
        return True
    
    def unauthorize(self, device_id: str) -> bool:
        """
        Unauthorize a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            bool: Whether the unauthorization was successful.
        """
        self.client.post(f"devices/{device_id}/unauthorize", expected_status=[200, 204])
        return True
    
    def get_config(self, device_id: str) -> Dict[str, Any]:
        """
        Get the configuration of a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            Dict[str, Any]: Device configuration.
        """
        return self.client.get(f"devices/{device_id}/config")
    
    def update_config(self, device_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the configuration of a device.
        
        Args:
            device_id (str): Device ID.
            config (Dict[str, Any]): Device configuration.
            
        Returns:
            Dict[str, Any]: Updated device configuration.
        """
        return self.client.put(f"devices/{device_id}/config", json_data=config)
    
    def get_backups(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get backups for a device.
        
        Args:
            device_id (str): Device ID.
            
        Returns:
            List[Dict[str, Any]]: List of backups.
        """
        return self.client.get(f"devices/{device_id}/backups")
    
    def create_backup(self, device_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a backup for a device.
        
        Args:
            device_id (str): Device ID.
            name (Optional[str]): Backup name. Defaults to None.
            
        Returns:
            Dict[str, Any]: Created backup data.
        """
        data = {}
        if name:
            data['name'] = name
        
        return self.client.post(f"devices/{device_id}/backups", json_data=data)
    
    def restore_backup(self, device_id: str, backup_id: str) -> bool:
        """
        Restore a backup for a device.
        
        Args:
            device_id (str): Device ID.
            backup_id (str): Backup ID.
            
        Returns:
            bool: Whether the backup restoration was initiated successfully.
        """
        self.client.post(f"devices/{device_id}/backups/{backup_id}/restore", expected_status=[200, 202, 204])
        return True


class AsyncDeviceManager:
    """
    Asynchronous device management for UNMS API.
    
    This class provides asynchronous methods for managing devices in UNMS.
    """
    
    def __init__(self, client):
        """
        Initialize the async device manager.
        
        Args:
            client: Async UNMS API client instance.
        """
        self.client = client
    
    async def get_all(self, site_id: Optional[str] = None, parent_id: Optional[str] = None,
                    status: Optional[str] = None, model: Optional[str] = None,
                    include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        Get a list of all devices in the network asynchronously.
        
        Args:
            site_id (Optional[str]): Filter by site ID. Defaults to None.
            parent_id (Optional[str]): Filter by parent device ID. Defaults to None.
            status (Optional[str]): Filter by device status. Defaults to None.
            model (Optional[str]): Filter by device model. Defaults to None.
            include_disabled (bool): Whether to include disabled devices. Defaults to False.
            
        Returns:
            List[Dict[str, Any]]: List of devices.
        """
        params = {}
        if site_id:
            params['siteId'] = site_id
        if parent_id:
            params['parentId'] = parent_id
        if status:
            params['status'] = status
        if model:
            params['model'] = model
        if include_disabled:
            params['includeDisabled'] = 'true'
        
        return await self.client.get("devices", params=params)


# Register the managers with the API clients
def init_device_managers(api_client):
    """
    Initialize device managers for API clients.
    
    Args:
        api_client: API client instance (sync or async).
    """
    from ..async_client import AsyncUNMSAPI
    
    if isinstance(api_client, AsyncUNMSAPI):
        api_client.devices = AsyncDeviceManager(api_client)
    else:
        api_client.devices = DeviceManager(api_client)
