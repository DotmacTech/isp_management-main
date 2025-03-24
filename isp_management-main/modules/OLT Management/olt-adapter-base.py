"""
Base OLT Adapter Module

This module defines the abstract base class for all OLT adapter implementations,
providing a common interface for different OLT vendor equipment.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any, Tuple


class OLTAdapter(ABC):
    """
    Abstract base class for OLT adapters.
    
    All vendor-specific OLT adapters must implement this interface to ensure
    consistent functionality across different hardware platforms.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the OLT device.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the OLT device."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to the OLT device.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information from the OLT.
        
        Returns:
            Dict: Information about the OLT including model, version, etc.
        """
        pass
    
    # OLT Management
    @abstractmethod
    def get_olts(self) -> List[Dict[str, Any]]:
        """
        Get a list of all OLTs in the system.
        
        Returns:
            List[Dict]: List of OLT information dictionaries.
        """
        pass
    
    # ONT Management
    @abstractmethod
    def get_onts(self, frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all ONTs managed by this OLT.
        
        Args:
            frame_id: Optional frame ID to filter ONTs
            slot_id: Optional slot ID to filter ONTs
            
        Returns:
            List[Dict]: List of ONT information dictionaries.
        """
        pass
    
    @abstractmethod
    def get_ont_details(self, ont_id: str, frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific ONT.
        
        Args:
            ont_id: The ID of the ONT to query
            frame_id: Optional frame ID where the ONT is connected
            slot_id: Optional slot ID where the ONT is connected
            
        Returns:
            Dict: Detailed ONT information.
        """
        pass
    
    @abstractmethod
    def provision_ont(self, serial_number: str, frame_id: Optional[str] = None, 
                      slot_id: Optional[str] = None, name: Optional[str] = None, 
                      description: Optional[str] = None) -> Dict[str, Any]:
        """
        Provision a new ONT with the given serial number.
        
        Args:
            serial_number: The ONT's serial number
            frame_id: Optional frame ID for the ONT
            slot_id: Optional slot ID for the ONT
            name: Optional name for the ONT
            description: Optional description for the ONT
            
        Returns:
            Dict: Information about the newly provisioned ONT including its ID.
        """
        pass
    
    @abstractmethod
    def provision_multiple_onts(self, serial_numbers: List[str], frame_id: Optional[str] = None,
                               slot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Provision multiple ONTs in a batch operation.
        
        Args:
            serial_numbers: List of ONT serial numbers to provision
            frame_id: Optional frame ID for the ONTs
            slot_id: Optional slot ID for the ONTs
            
        Returns:
            List[Dict]: Information about each provisioned ONT.
        """
        pass
    
    @abstractmethod
    def deprovision_ont(self, ont_id: str, frame_id: Optional[str] = None, 
                        slot_id: Optional[str] = None) -> bool:
        """
        Deprovision an existing ONT.
        
        Args:
            ont_id: The ID of the ONT to deprovision
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    # ONT Configuration
    @abstractmethod
    def configure_ont_interface(self, ont_id: str, interface_id: str, vlan_mode: str, 
                              vlan_id: Optional[int] = None, frame_id: Optional[str] = None, 
                              slot_id: Optional[str] = None) -> bool:
        """
        Configure VLAN settings on an ONT interface.
        
        Args:
            ont_id: The ONT ID
            interface_id: The interface identifier
            vlan_mode: VLAN mode (e.g., 'access', 'trunk')
            vlan_id: Optional VLAN ID
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def set_ont_ip_configuration(self, ont_id: str, ip_address: Optional[str] = None,
                              subnet_mask: Optional[str] = None, gateway: Optional[str] = None,
                              dhcp_enabled: Optional[bool] = None, pppoe_enabled: Optional[bool] = None,
                              frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> bool:
        """
        Configure IP settings for an ONT.
        
        Args:
            ont_id: The ONT ID
            ip_address: Optional static IP address
            subnet_mask: Optional subnet mask
            gateway: Optional default gateway
            dhcp_enabled: Whether DHCP is enabled
            pppoe_enabled: Whether PPPoE is enabled
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def enable_ont_port(self, ont_id: str, interface_id: str, enabled: bool,
                      frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> bool:
        """
        Enable or disable an ONT interface port.
        
        Args:
            ont_id: The ONT ID
            interface_id: The interface identifier
            enabled: True to enable, False to disable
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def reboot_ont(self, ont_id: str, frame_id: Optional[str] = None, 
                 slot_id: Optional[str] = None) -> bool:
        """
        Reboot an ONT device.
        
        Args:
            ont_id: The ONT ID
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def restore_ont_factory_settings(self, ont_id: str, frame_id: Optional[str] = None, 
                                   slot_id: Optional[str] = None) -> bool:
        """
        Restore an ONT device to factory settings.
        
        Args:
            ont_id: The ONT ID
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    # Monitoring and Alerts
    @abstractmethod
    def get_ont_status(self, ont_id: str, frame_id: Optional[str] = None, 
                     slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the current status of an ONT device.
        
        Args:
            ont_id: The ONT ID
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            Dict: Status information about the ONT.
        """
        pass
    
    @abstractmethod
    def get_ont_performance_metrics(self, ont_id: str, metric_type: str,
                                 start_time: Optional[int] = None,
                                 end_time: Optional[int] = None,
                                 frame_id: Optional[str] = None, 
                                 slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for an ONT device.
        
        Args:
            ont_id: The ONT ID
            metric_type: Type of metrics to retrieve (e.g., 'traffic', 'cpu', 'memory')
            start_time: Optional start time for metrics (Unix timestamp)
            end_time: Optional end time for metrics (Unix timestamp)
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            Dict: Performance metrics data.
        """
        pass
    
    @abstractmethod
    def get_ont_signal_history(self, ont_id: str, start_time: Optional[int] = None,
                            end_time: Optional[int] = None,
                            frame_id: Optional[str] = None, 
                            slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get signal history for an ONT device.
        
        Args:
            ont_id: The ONT ID
            start_time: Optional start time (Unix timestamp)
            end_time: Optional end time (Unix timestamp)
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            Dict: Signal history data.
        """
        pass
    
    @abstractmethod
    def get_ont_alerts(self, ont_id: str, start_time: Optional[int] = None,
                     end_time: Optional[int] = None,
                     frame_id: Optional[str] = None, 
                     slot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get alerts for an ONT device.
        
        Args:
            ont_id: The ONT ID
            start_time: Optional start time (Unix timestamp)
            end_time: Optional end time (Unix timestamp)
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            List[Dict]: List of alert information.
        """
        pass
    
    @abstractmethod
    def configure_alerts(self, ont_id: str, alert_type: str, threshold: float,
                       notification_methods: List[str],
                       frame_id: Optional[str] = None, 
                       slot_id: Optional[str] = None) -> bool:
        """
        Configure alerts for an ONT device.
        
        Args:
            ont_id: The ONT ID
            alert_type: Type of alert to configure
            threshold: Threshold value for the alert
            notification_methods: List of notification methods
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    # GPS Positioning
    @abstractmethod
    def get_ont_location(self, ont_id: str, frame_id: Optional[str] = None, 
                       slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the GPS location of an ONT device.
        
        Args:
            ont_id: The ONT ID
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            Dict: Location information.
        """
        pass
    
    @abstractmethod
    def update_ont_location(self, ont_id: str, latitude: float, longitude: float,
                          description: Optional[str] = None,
                          frame_id: Optional[str] = None, 
                          slot_id: Optional[str] = None) -> bool:
        """
        Update the GPS location of an ONT device.
        
        Args:
            ont_id: The ONT ID
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            description: Optional location description
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    # Speed Limiting and Traffic Control
    @abstractmethod
    def set_ont_speed_limit(self, ont_id: str, download_limit: Optional[int] = None,
                          upload_limit: Optional[int] = None,
                          frame_id: Optional[str] = None, 
                          slot_id: Optional[str] = None) -> bool:
        """
        Set speed limits for an ONT device.
        
        Args:
            ont_id: The ONT ID
            download_limit: Optional download speed limit in Kbps
            upload_limit: Optional upload speed limit in Kbps
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def configure_ont_dhcp(self, ont_id: str, enabled: bool, lease_time: Optional[int] = None,
                         dns_servers: Optional[List[str]] = None,
                         frame_id: Optional[str] = None, 
                         slot_id: Optional[str] = None) -> bool:
        """
        Configure DHCP settings for an ONT device.
        
        Args:
            ont_id: The ONT ID
            enabled: Whether DHCP is enabled
            lease_time: Optional DHCP lease time in seconds
            dns_servers: Optional list of DNS server IP addresses
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    # Advanced Configuration
    @abstractmethod
    def configure_ont_vlan(self, ont_id: str, interface_id: str, vlan_mode: str,
                         vlan_id: Optional[int] = None,
                         frame_id: Optional[str] = None, 
                         slot_id: Optional[str] = None) -> bool:
        """
        Configure VLAN settings on an ONT interface.
        
        Args:
            ont_id: The ONT ID
            interface_id: The interface identifier
            vlan_mode: VLAN mode (e.g., 'access', 'trunk')
            vlan_id: Optional VLAN ID
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def configure_ont_triple_play(self, ont_id: str, ip_enabled: bool, iptv_enabled: bool,
                               voice_enabled: bool,
                               frame_id: Optional[str] = None, 
                               slot_id: Optional[str] = None) -> bool:
        """
        Configure Triple Play services for an ONT device.
        
        Args:
            ont_id: The ONT ID
            ip_enabled: Whether IP service is enabled
            iptv_enabled: Whether IPTV service is enabled
            voice_enabled: Whether voice service is enabled
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def configure_ont_routing_mode(self, ont_id: str, routing_mode: str,
                                frame_id: Optional[str] = None, 
                                slot_id: Optional[str] = None) -> bool:
        """
        Configure routing mode for an ONT device.
        
        Args:
            ont_id: The ONT ID
            routing_mode: Routing mode (e.g., 'routing', 'bridging')
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    # TR-069 Configuration
    @abstractmethod
    def configure_ont_tr069(self, ont_id: str, acs_url: str, 
                          periodic_inform_interval: int,
                          connection_request_username: str,
                          connection_request_password: str,
                          frame_id: Optional[str] = None, 
                          slot_id: Optional[str] = None) -> bool:
        """
        Configure TR-069 settings on an ONT.
        
        Args:
            ont_id: The ONT ID
            acs_url: The URL of the TR-069 ACS server
            periodic_inform_interval: Interval in seconds for periodic informs
            connection_request_username: Username for connection requests
            connection_request_password: Password for connection requests
            frame_id: Optional frame ID
            slot_id: Optional slot ID
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def execute_custom_command(self, command: str) -> str:
        """
        Execute a custom command on the OLT.
        
        This method should be used with caution as it allows direct command execution.
        
        Args:
            command: The command to execute
            
        Returns:
            str: Command output.
        """
        pass
