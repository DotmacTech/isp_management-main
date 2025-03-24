"""
Huawei OLT Adapter Module

This module provides an adapter implementation for Huawei OLT devices.
"""

import logging
import time
import re
from typing import Optional, Dict, List, Any, Tuple

from .base import OLTAdapter
from .utils.parsers import OutputParser
from ..exceptions import (
    OLTConnectionError, 
    OLTCommandError, 
    ONTProvisioningError,
    ONTConfigurationError,
    ONTNotFoundError,
    ParseError
)
from ..models.command_templates import HuaweiCommandTemplates

logger = logging.getLogger(__name__)


class HuaweiOLTAdapter(OLTAdapter):
    """
    Adapter implementation for Huawei OLT devices.
    
    This class implements the OLTAdapter interface for Huawei OLT devices,
    providing vendor-specific functionality.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 22,
                model: str = 'MA5800', default_frame: str = '0', 
                default_slot: str = '0'):
        """
        Initialize the Huawei OLT adapter.
        
        Args:
            host: Hostname or IP address of the OLT device
            username: SSH username
            password: SSH password
            port: SSH port (default: 22)
            model: OLT model (default: 'MA5800')
            default_frame: Default frame ID (default: '0')
            default_slot: Default slot ID (default: '0')
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.model = model
        self.default_frame = default_frame
        self.default_slot = default_slot
        self.client = self._create_ssh_client()
        self.parser = OutputParser()
        self.commands = HuaweiCommandTemplates()
    
    def _create_ssh_client(self):
        """Create and return an SSH client instance."""
        from .utils.ssh_client import SSHClient
        return SSHClient(self.host, self.username, self.password, self.port)
    
    def connect(self) -> bool:
        """
        Establish connection to the OLT device.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            return self.client.connect()
        except OLTConnectionError as e:
            logger.error(f"Failed to connect to Huawei OLT {self.host}: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Close connection to the OLT device."""
        self.client.disconnect()
    
    def is_connected(self) -> bool:
        """
        Check if currently connected to the OLT device.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.client.is_connected()
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information from the OLT.
        
        Returns:
            Dict: Information about the OLT including model, version, etc.
        """
        try:
            output = self.client.execute_command(self.commands.SYSTEM_INFO)
            system_info = self.parser.parse_system_info(output, 'huawei')
            
            # Add additional information
            system_info['vendor'] = 'huawei'
            system_info['host'] = self.host
            
            # Get uptime in seconds if available
            if 'uptime' in system_info and isinstance(system_info['uptime'], str):
                uptime_str = system_info['uptime']
                # Parse uptime string like "0 year(s), 10 day(s), 5 hour(s), 30 minute(s), 15 second(s)"
                years = re.search(r'(\d+) year', uptime_str)
                days = re.search(r'(\d+) day', uptime_str)
                hours = re.search(r'(\d+) hour', uptime_str)
                minutes = re.search(r'(\d+) minute', uptime_str)
                seconds = re.search(r'(\d+) second', uptime_str)
                
                total_seconds = 0
                if years:
                    total_seconds += int(years.group(1)) * 365 * 24 * 3600
                if days:
                    total_seconds += int(days.group(1)) * 24 * 3600
                if hours:
                    total_seconds += int(hours.group(1)) * 3600
                if minutes:
                    total_seconds += int(minutes.group(1)) * 60
                if seconds:
                    total_seconds += int(seconds.group(1))
                
                system_info['uptime_seconds'] = total_seconds
            
            return system_info
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting system info from Huawei OLT {self.host}: {str(e)}")
            return {'vendor': 'huawei', 'host': self.host, 'error': str(e)}
    
    def get_olts(self) -> List[Dict[str, Any]]:
        """
        Get a list of all OLTs in the system.
        
        For Huawei, this returns information about the current OLT only.
        
        Returns:
            List[Dict]: List of OLT information dictionaries.
        """
        system_info = self.get_system_info()
        return [system_info]
    
    def get_onts(self, frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all ONTs managed by this OLT.
        
        Args:
            frame_id: Optional frame ID to filter ONTs
            slot_id: Optional slot ID to filter ONTs
            
        Returns:
            List[Dict]: List of ONT information dictionaries.
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Execute command to list ONTs
            command = self.commands.LIST_ONTS.format(frame=frame, slot=slot)
            output = self.client.execute_command(command)
            
            # Parse the output
            onts = self.parser.parse_ont_list(output, 'huawei')
            
            # Add frame and slot information to each ONT
            for ont in onts:
                ont['frame_id'] = frame
                ont['slot_id'] = slot
            
            return onts
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting ONTs from Huawei OLT {self.host}: {str(e)}")
            return []

    def get_ont_details(self, ont_id: str, frame_id: Optional[str] = None, 
                      slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific ONT.
        
        Args:
            ont_id: ONT ID
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Detailed information about the ONT
            
        Raises:
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Execute command to get ONT details
            command = self.commands.ONT_DETAILS.format(
                frame=frame, slot=slot, ont_id=ont_id
            )
            output = self.client.execute_command(command)
            
            # Check if ONT exists
            if "ONT does not exist" in output or "Failure" in output:
                raise ONTNotFoundError(f"ONT {ont_id} not found in frame {frame}, slot {slot}")
            
            # Parse the output as key-value pairs
            details = self.parser.parse_key_value_output(output)
            
            # Add frame, slot, and ONT ID information
            details['frame_id'] = frame
            details['slot_id'] = slot
            details['ont_id'] = ont_id
            
            # Get additional status information
            status_command = self.commands.ONT_STATUS.format(
                frame=frame, slot=slot, ont_id=ont_id
            )
            status_output = self.client.execute_command(status_command)
            status_info = self.parser.parse_ont_status(status_output, 'huawei')
            
            # Merge status information with details
            details.update(status_info)
            
            # Get optical information if available
            try:
                optical_command = self.commands.ONT_OPTICAL_INFO.format(
                    frame=frame, slot=slot, ont_id=ont_id
                )
                optical_output = self.client.execute_command(optical_command)
                optical_info = self.parser.parse_key_value_output(optical_output)
                
                # Extract and convert optical power values
                if 'RX optical power(dBm)' in optical_info:
                    details['rx_power'] = optical_info['RX optical power(dBm)']
                if 'TX optical power(dBm)' in optical_info:
                    details['tx_power'] = optical_info['TX optical power(dBm)']
            except (OLTCommandError, ParseError):
                # Optical information might not be available for all ONTs
                pass
            
            return details
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting ONT details from Huawei OLT {self.host}: {str(e)}")
            return {
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'error': str(e)
            }
    
    def get_ont_status(self, ont_id: str, frame_id: Optional[str] = None, 
                      slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current status of a specific ONT.
        
        Args:
            ont_id: ONT ID
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Status information about the ONT
            
        Raises:
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Execute command to get ONT status
            command = self.commands.ONT_STATUS.format(
                frame=frame, slot=slot, ont_id=ont_id
            )
            output = self.client.execute_command(command)
            
            # Check if ONT exists
            if "ONT does not exist" in output or "Failure" in output:
                raise ONTNotFoundError(f"ONT {ont_id} not found in frame {frame}, slot {slot}")
            
            # Parse the output
            status = self.parser.parse_ont_status(output, 'huawei')
            
            # Add frame, slot, and ONT ID information
            status['frame_id'] = frame
            status['slot_id'] = slot
            status['ont_id'] = ont_id
            
            return status
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting ONT status from Huawei OLT {self.host}: {str(e)}")
            return {
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'error': str(e)
            }

    def provision_ont(self, serial_number: str, ont_id: str, profile_name: str, 
                     vlan_id: str, ip_address: Optional[str] = None, 
                     subnet_mask: Optional[str] = None, gateway: Optional[str] = None,
                     frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Provision a new ONT on the OLT.
        
        Args:
            serial_number: ONT serial number
            ont_id: ONT ID to assign
            profile_name: Profile name to use for the ONT
            vlan_id: VLAN ID to assign to the ONT
            ip_address: Optional IP address to assign to the ONT
            subnet_mask: Optional subnet mask for the ONT
            gateway: Optional default gateway for the ONT
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Result of the provisioning operation
            
        Raises:
            ONTProvisioningError: If provisioning fails
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Prepare command parameters
            params = {
                'frame': frame,
                'slot': slot,
                'ont_id': ont_id,
                'serial_number': serial_number,
                'profile_name': profile_name,
                'vlan_id': vlan_id
            }
            
            # Add optional IP configuration if provided
            if ip_address and subnet_mask and gateway:
                params['ip_address'] = ip_address
                params['subnet_mask'] = subnet_mask
                params['gateway'] = gateway
            
            # Format the command with the parameters
            command = self.commands.PROVISION_ONT.format(**params)
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to provision ONT {ont_id} with serial {serial_number}: {output}"
                logger.error(error_msg)
                raise ONTProvisioningError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'serial_number': serial_number,
                'message': f"Successfully provisioned ONT {ont_id} with serial {serial_number}"
            }
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error provisioning ONT {ont_id} with serial {serial_number}: {str(e)}"
            logger.error(error_msg)
            raise ONTProvisioningError(error_msg)
    
    def deprovision_ont(self, ont_id: str, frame_id: Optional[str] = None, 
                       slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Remove an ONT from the OLT configuration.
        
        Args:
            ont_id: ONT ID to deprovision
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Result of the deprovisioning operation
            
        Raises:
            ONTProvisioningError: If deprovisioning fails
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Format the command with the parameters
            command = self.commands.DEPROVISION_ONT.format(
                frame=frame, slot=slot, ont_id=ont_id
            )
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to deprovision ONT {ont_id}: {output}"
                logger.error(error_msg)
                raise ONTProvisioningError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'message': f"Successfully deprovisioned ONT {ont_id}"
            }
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error deprovisioning ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTProvisioningError(error_msg)
    
    def reboot_ont(self, ont_id: str, frame_id: Optional[str] = None, 
                  slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Reboot a specific ONT.
        
        Args:
            ont_id: ONT ID to reboot
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Result of the reboot operation
            
        Raises:
            ONTConfigurationError: If reboot fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, frame_id, slot_id)
            except ONTNotFoundError as e:
                raise e
            
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Format the command with the parameters
            command = self.commands.REBOOT_ONT.format(
                frame=frame, slot=slot, ont_id=ont_id
            )
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to reboot ONT {ont_id}: {output}"
                logger.error(error_msg)
                raise ONTConfigurationError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'message': f"Successfully rebooted ONT {ont_id}"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error rebooting ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)

    def configure_ont_port(self, ont_id: str, port_id: str, admin_status: str,
                          frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Configure an ONT port.
        
        Args:
            ont_id: ONT ID
            port_id: Port ID on the ONT
            admin_status: Administrative status ('enable' or 'disable')
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Result of the configuration operation
            
        Raises:
            ONTConfigurationError: If configuration fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, frame_id, slot_id)
            except ONTNotFoundError as e:
                raise e
            
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Select the appropriate command based on admin_status
            if admin_status.lower() == 'enable':
                command_template = self.commands.ENABLE_ONT_PORT
            elif admin_status.lower() == 'disable':
                command_template = self.commands.DISABLE_ONT_PORT
            else:
                raise ONTConfigurationError(f"Invalid admin_status: {admin_status}. Must be 'enable' or 'disable'")
            
            # Format the command with the parameters
            command = command_template.format(
                frame=frame, slot=slot, ont_id=ont_id, port_id=port_id
            )
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to {admin_status} port {port_id} on ONT {ont_id}: {output}"
                logger.error(error_msg)
                raise ONTConfigurationError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'port_id': port_id,
                'admin_status': admin_status,
                'message': f"Successfully set port {port_id} on ONT {ont_id} to {admin_status}"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error configuring port {port_id} on ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)
    
    def configure_ont_vlan(self, ont_id: str, port_id: str, vlan_id: str, 
                          user_vlan_id: Optional[str] = None,
                          frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Configure VLAN settings for an ONT port.
        
        Args:
            ont_id: ONT ID
            port_id: Port ID on the ONT
            vlan_id: VLAN ID to assign to the port
            user_vlan_id: Optional user VLAN ID for translation
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Result of the configuration operation
            
        Raises:
            ONTConfigurationError: If configuration fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, frame_id, slot_id)
            except ONTNotFoundError as e:
                raise e
            
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Prepare command parameters
            params = {
                'frame': frame,
                'slot': slot,
                'ont_id': ont_id,
                'port_id': port_id,
                'vlan_id': vlan_id,
                'user_vlan_id': user_vlan_id if user_vlan_id else vlan_id
            }
            
            # Format the command with the parameters
            command = self.commands.CONFIGURE_ONT_VLAN.format(**params)
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to configure VLAN {vlan_id} on ONT {ont_id} port {port_id}: {output}"
                logger.error(error_msg)
                raise ONTConfigurationError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'port_id': port_id,
                'vlan_id': vlan_id,
                'user_vlan_id': user_vlan_id if user_vlan_id else vlan_id,
                'message': f"Successfully configured VLAN {vlan_id} on ONT {ont_id} port {port_id}"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error configuring VLAN on ONT {ont_id} port {port_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)
    
    def set_ont_speed_limit(self, ont_id: str, download_limit: str, upload_limit: str,
                           frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Set speed limits for an ONT.
        
        Args:
            ont_id: ONT ID
            download_limit: Download speed limit in kbps
            upload_limit: Upload speed limit in kbps
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Result of the configuration operation
            
        Raises:
            ONTConfigurationError: If configuration fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, frame_id, slot_id)
            except ONTNotFoundError as e:
                raise e
            
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Format the command with the parameters
            command = self.commands.SET_ONT_SPEED_LIMIT.format(
                frame=frame, slot=slot, ont_id=ont_id,
                download_limit=download_limit, upload_limit=upload_limit
            )
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to set speed limits for ONT {ont_id}: {output}"
                logger.error(error_msg)
                raise ONTConfigurationError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'download_limit': download_limit,
                'upload_limit': upload_limit,
                'message': f"Successfully set speed limits for ONT {ont_id}: download {download_limit}kbps, upload {upload_limit}kbps"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error setting speed limits for ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)
    
    def restore_ont_factory_settings(self, ont_id: str, frame_id: Optional[str] = None, 
                                    slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Restore factory settings for an ONT.
        
        Args:
            ont_id: ONT ID
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Result of the operation
            
        Raises:
            ONTConfigurationError: If the operation fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, frame_id, slot_id)
            except ONTNotFoundError as e:
                raise e
            
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Format the command with the parameters
            command = self.commands.RESTORE_ONT_FACTORY.format(
                frame=frame, slot=slot, ont_id=ont_id
            )
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to restore factory settings for ONT {ont_id}: {output}"
                logger.error(error_msg)
                raise ONTConfigurationError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'frame_id': frame,
                'slot_id': slot,
                'ont_id': ont_id,
                'message': f"Successfully restored factory settings for ONT {ont_id}"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error restoring factory settings for ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)

    def configure_ont_interface(self, ont_id: str, interface_id: str, vlan_mode: str, 
                              vlan_id: str, frame_id: Optional[str] = None, 
                              slot_id: Optional[str] = None) -> bool:
        """
        Configure an ONT interface with VLAN settings.
        
        Args:
            ont_id: ONT ID
            interface_id: Interface ID on the ONT
            vlan_mode: VLAN mode ('access', 'trunk', or 'hybrid')
            vlan_id: VLAN ID to assign
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            bool: True if configuration is successful, False otherwise
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, frame, slot)
            
            # Execute command to configure ONT interface
            command = f"interface ont {frame}/{slot}/{ont_id}"
            self.client.execute_command(command)
            
            # Configure VLAN mode and ID
            vlan_command = f"service-port {interface_id} vlan {vlan_id} mode {vlan_mode}"
            self.client.execute_command(vlan_command)
            
            # Commit changes
            self.client.execute_command("quit")
            
            logger.info(f"Successfully configured interface {interface_id} on ONT {ont_id} with VLAN {vlan_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error configuring ONT interface: {str(e)}")
            return False
    
    def configure_ont_tr069(self, ont_id: str, acs_url: str, 
                          periodic_inform_interval: int = 86400,
                          connection_request_username: Optional[str] = None,
                          connection_request_password: Optional[str] = None,
                          frame_id: Optional[str] = None, 
                          slot_id: Optional[str] = None) -> bool:
        """
        Configure TR-069 settings for an ONT.
        
        Args:
            ont_id: ONT ID
            acs_url: URL of the ACS (Auto Configuration Server)
            periodic_inform_interval: Interval in seconds for periodic inform (default: 86400)
            connection_request_username: Username for connection requests
            connection_request_password: Password for connection requests
            frame_id: Optional frame ID (uses default if frame_id is None)
            slot_id: Optional slot ID (uses default if slot_id is None)
            
        Returns:
            bool: True if configuration is successful, False otherwise
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, frame, slot)
            
            # Execute command to configure TR-069
            command = f"interface ont {frame}/{slot}/{ont_id}"
            self.client.execute_command(command)
            
            # Configure ACS URL
            acs_command = f"tr069 acs-url {acs_url}"
            self.client.execute_command(acs_command)
            
            # Configure periodic inform interval
            inform_command = f"tr069 inform-interval {periodic_inform_interval}"
            self.client.execute_command(inform_command)
            
            # Configure connection request credentials if provided
            if connection_request_username and connection_request_password:
                cred_command = f"tr069 connection-request user {connection_request_username} password {connection_request_password}"
                self.client.execute_command(cred_command)
            
            # Commit changes
            self.client.execute_command("quit")
            
            logger.info(f"Successfully configured TR-069 on ONT {ont_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error configuring TR-069 on ONT: {str(e)}")
            return False
    
    def enable_ont_port(self, ont_id: str, interface_id: str, enabled: bool = True,
                      frame_id: Optional[str] = None, slot_id: Optional[str] = None) -> bool:
        """
        Enable or disable an ONT port.
        
        Args:
            ont_id: ONT ID
            interface_id: Interface ID on the ONT
            enabled: Whether to enable (True) or disable (False) the port
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            bool: True if operation is successful, False otherwise
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, frame, slot)
            
            # Execute command to access ONT interface
            command = f"interface ont {frame}/{slot}/{ont_id}"
            self.client.execute_command(command)
            
            # Enable or disable the port
            status = "enable" if enabled else "disable"
            port_command = f"port {interface_id} {status}"
            self.client.execute_command(port_command)
            
            # Commit changes
            self.client.execute_command("quit")
            
            logger.info(f"Successfully {status}d port {interface_id} on ONT {ont_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error {status}ing ONT port: {str(e)}")
            return False
    
    def execute_custom_command(self, command: str) -> str:
        """
        Execute a custom command on the OLT.
        
        Args:
            command: Command to execute
            
        Returns:
            str: Command output
        """
        try:
            output = self.client.execute_command(command)
            return output
        except (OLTConnectionError, OLTCommandError) as e:
            logger.error(f"Error executing custom command: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_ont_performance_metrics(self, ont_id: str, metric_type: str = 'traffic',
                                  start_time: Optional[int] = None,
                                  end_time: Optional[int] = None,
                                  frame_id: Optional[str] = None, 
                                  slot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for an ONT.
        
        Args:
            ont_id: ONT ID
            metric_type: Type of metric to retrieve ('traffic', 'cpu', 'memory', etc.)
            start_time: Start time in Unix timestamp format (optional)
            end_time: End time in Unix timestamp format (optional)
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            Dict: Performance metrics data
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, frame, slot)
            
            # For demo purposes, we return mock metrics data
            # In a real implementation, you would execute commands to retrieve actual metrics
            
            # Create mock response
            metrics = {
                "ont_id": ont_id,
                "metric_type": metric_type,
                "values": [
                    {
                        "timestamp": start_time or int(time.time()) - 3600,
                        "value": 87.2
                    }
                ]
            }
            
            return metrics
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error getting ONT performance metrics: {str(e)}")
            return {
                "ont_id": ont_id,
                "metric_type": metric_type,
                "error": str(e)
            }
    
    def provision_multiple_onts(self, serial_numbers: List[str], 
                              starting_ont_id: Optional[str] = None,
                              profile_name: Optional[str] = None,
                              vlan_id: Optional[str] = None,
                              frame_id: Optional[str] = None, 
                              slot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Provision multiple ONTs in a single operation.
        
        Args:
            serial_numbers: List of ONT serial numbers to provision
            starting_ont_id: Starting ONT ID (auto-generated if not provided)
            profile_name: Profile name to use for all ONTs
            vlan_id: VLAN ID to assign to all ONTs
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            List[Dict]: Results of provisioning operations for each ONT
        """
        results = []
        
        # Use default frame and slot if not provided
        frame = frame_id if frame_id is not None else self.default_frame
        slot = slot_id if slot_id is not None else self.default_slot
        
        # Generate starting ONT ID if not provided
        current_ont_id = int(starting_ont_id) if starting_ont_id else 10
        
        # Set default profile and VLAN if not provided
        default_profile = profile_name or "default_profile"
        default_vlan = vlan_id or "100"
        
        for serial_number in serial_numbers:
            try:
                # Provision each ONT individually
                result = self.provision_ont(
                    serial_number=serial_number,
                    ont_id=str(current_ont_id),
                    profile_name=default_profile,
                    vlan_id=default_vlan,
                    frame_id=frame,
                    slot_id=slot
                )
                
                # Add provision result to results list
                results.append({
                    "success": True,
                    "ont_id": str(current_ont_id),
                    "serial_number": serial_number
                })
                
                # Increment ONT ID for next provision
                current_ont_id += 1
                
            except ONTProvisioningError as e:
                # Add error result to results list
                results.append({
                    "success": False,
                    "error": str(e),
                    "serial_number": serial_number
                })
                
                # Still increment ONT ID for next provision
                current_ont_id += 1
        
        return results
    
    def set_ont_ip_configuration(self, ont_id: str, ip_address: str, 
                               subnet_mask: str, gateway: Optional[str] = None, 
                               dhcp_enabled: bool = False,
                               frame_id: Optional[str] = None, 
                               slot_id: Optional[str] = None) -> bool:
        """
        Configure IP settings for an ONT.
        
        Args:
            ont_id: ONT ID
            ip_address: IP address to assign to the ONT
            subnet_mask: Subnet mask for the ONT
            gateway: Default gateway for the ONT (optional)
            dhcp_enabled: Whether to enable DHCP (defaults to False)
            frame_id: Optional frame ID (uses default if not provided)
            slot_id: Optional slot ID (uses default if not provided)
            
        Returns:
            bool: True if configuration is successful, False otherwise
        """
        try:
            # Use default frame and slot if not provided
            frame = frame_id if frame_id is not None else self.default_frame
            slot = slot_id if slot_id is not None else self.default_slot
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, frame, slot)
            
            # Execute command to access ONT interface
            command = f"interface ont {frame}/{slot}/{ont_id}"
            self.client.execute_command(command)
            
            if dhcp_enabled:
                # Enable DHCP
                ip_command = "ip address dhcp"
            else:
                # Configure static IP
                ip_command = f"ip address {ip_address} {subnet_mask}"
                self.client.execute_command(ip_command)
                
                # Add default gateway if provided
                if gateway:
                    gateway_command = f"ip route {gateway}"
                    self.client.execute_command(gateway_command)
            
            # Commit changes
            self.client.execute_command("quit")
            
            logger.info(f"Successfully configured IP settings for ONT {ont_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error configuring ONT IP settings: {str(e)}")
            return False
