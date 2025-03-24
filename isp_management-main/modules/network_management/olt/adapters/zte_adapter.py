"""
ZTE OLT Adapter Module

This module provides an adapter implementation for ZTE OLT devices.
"""

import logging
import time
import re
from typing import Optional, Dict, List, Any, Tuple

from .base import OLTAdapter
from .utils.parsers import OutputParser
from .utils.ssh_client import SSHClient
from .utils.telnet_client import TelnetClient
from ..exceptions import (
    OLTConnectionError, 
    OLTCommandError, 
    ONTProvisioningError,
    ONTConfigurationError,
    ONTNotFoundError,
    ParseError
)
from ..models.command_templates import ZTECommandTemplates

logger = logging.getLogger(__name__)


class ZTEOLTAdapter(OLTAdapter):
    """
    Adapter implementation for ZTE OLT devices.
    
    This class implements the OLTAdapter interface for ZTE OLT devices,
    providing vendor-specific functionality.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 22,
                model: str = 'C320', connection_type: str = 'ssh',
                default_gpon_index: str = '1/1/1'):
        """
        Initialize the ZTE OLT adapter.
        
        Args:
            host: Hostname or IP address of the OLT device
            username: Username for authentication
            password: Password for authentication
            port: Port for connection (default: 22 for SSH, 23 for Telnet)
            model: OLT model (default: 'C320')
            connection_type: Connection type ('ssh' or 'telnet', default: 'ssh')
            default_gpon_index: Default GPON index (default: '1/1/1')
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.model = model
        self.connection_type = connection_type.lower()
        self.default_gpon_index = default_gpon_index
        
        # Initialize the appropriate client based on connection type
        if self.connection_type == 'ssh':
            self.client = self._create_ssh_client()
        elif self.connection_type == 'telnet':
            self.client = self._create_telnet_client()
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}. Must be 'ssh' or 'telnet'")
        
        self.parser = OutputParser()
        self.commands = ZTECommandTemplates()
    
    def _create_ssh_client(self):
        """Create and return an SSH client instance."""
        return SSHClient(self.host, self.username, self.password, self.port)
    
    def _create_telnet_client(self):
        """Create and return a Telnet client instance."""
        return TelnetClient(self.host, self.username, self.password, 
                           self.port if self.port != 22 else 23)
    
    def connect(self) -> bool:
        """
        Establish connection to the OLT device.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            return self.client.connect()
        except OLTConnectionError as e:
            logger.error(f"Failed to connect to ZTE OLT {self.host}: {str(e)}")
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
            system_info = self.parser.parse_system_info(output, 'zte')
            
            # Add additional information
            system_info['vendor'] = 'zte'
            system_info['host'] = self.host
            
            # Get uptime in seconds if available
            uptime_output = self.client.execute_command(self.commands.SYSTEM_UPTIME)
            uptime_match = re.search(r'(\d+) days, (\d+) hours, (\d+) minutes, (\d+) seconds', uptime_output)
            if uptime_match:
                days, hours, minutes, seconds = map(int, uptime_match.groups())
                total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
                system_info['uptime_seconds'] = total_seconds
                system_info['uptime'] = f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
            
            return system_info
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting system info from ZTE OLT {self.host}: {str(e)}")
            return {'vendor': 'zte', 'host': self.host, 'error': str(e)}
    
    def get_olts(self) -> List[Dict[str, Any]]:
        """
        Get a list of all OLTs in the system.
        
        For ZTE, this returns information about the current OLT only.
        
        Returns:
            List[Dict]: List of OLT information dictionaries.
        """
        system_info = self.get_system_info()
        return [system_info]
    
    def get_onts(self, gpon_index: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all ONTs managed by this OLT.
        
        Args:
            gpon_index: Optional GPON index to filter ONTs (e.g., '1/1/1')
            
        Returns:
            List[Dict]: List of ONT information dictionaries.
        """
        try:
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Execute command to list ONTs
            command = self.commands.LIST_CONFIGURED_ONTS.format(serial_number='*')
            output = self.client.execute_command(command)
            
            # Parse the output
            onts = self.parser.parse_ont_list(output, 'zte')
            
            # Filter by GPON index if specified
            if gpon_idx != '*':
                onts = [ont for ont in onts if ont.get('gpon_index') == gpon_idx]
            
            return onts
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting ONTs from ZTE OLT {self.host}: {str(e)}")
            return []
    
    def get_ont_details(self, ont_id: str, gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific ONT.
        
        Args:
            ont_id: ONT ID
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Detailed information about the ONT
            
        Raises:
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Execute command to get ONT details
            command = self.commands.ONT_DETAILS.format(
                gpon_index=gpon_idx, ont_id=ont_id
            )
            output = self.client.execute_command(command)
            
            # Check if ONT exists
            if "No related information to show" in output or "Failure" in output:
                raise ONTNotFoundError(f"ONT {ont_id} not found in GPON index {gpon_idx}")
            
            # Parse the output as key-value pairs
            details = self.parser.parse_key_value_output(output)
            
            # Add GPON index and ONT ID information
            details['gpon_index'] = gpon_idx
            details['ont_id'] = ont_id
            
            # Get additional status information
            status_command = self.commands.ONT_STATUS.format(
                gpon_index=gpon_idx, ont_id=ont_id
            )
            status_output = self.client.execute_command(status_command)
            status_info = self.parser.parse_ont_status(status_output, 'zte')
            
            # Merge status information with details
            details.update(status_info)
            
            # Get optical information if available
            try:
                optical_command = self.commands.ONT_OPTICAL_INFO.format(
                    gpon_index=gpon_idx, ont_id=ont_id
                )
                optical_output = self.client.execute_command(optical_command)
                optical_info = self.parser.parse_key_value_output(optical_output)
                
                # Extract and convert optical power values
                if 'Rx power(dBm)' in optical_info:
                    details['rx_power'] = optical_info['Rx power(dBm)']
                if 'Tx power(dBm)' in optical_info:
                    details['tx_power'] = optical_info['Tx power(dBm)']
            except (OLTCommandError, ParseError):
                # Optical information might not be available for all ONTs
                pass
            
            return details
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting ONT details from ZTE OLT {self.host}: {str(e)}")
            return {
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'error': str(e)
            }
    
    def get_ont_status(self, ont_id: str, gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current status of a specific ONT.
        
        Args:
            ont_id: ONT ID
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Status information about the ONT
            
        Raises:
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Execute command to get ONT status
            command = self.commands.ONT_STATUS.format(
                gpon_index=gpon_idx, ont_id=ont_id
            )
            output = self.client.execute_command(command)
            
            # Check if ONT exists
            if "No related information to show" in output or "Failure" in output:
                raise ONTNotFoundError(f"ONT {ont_id} not found in GPON index {gpon_idx}")
            
            # Parse the output
            status = self.parser.parse_ont_status(output, 'zte')
            
            # Add GPON index and ONT ID information
            status['gpon_index'] = gpon_idx
            status['ont_id'] = ont_id
            
            return status
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError, ParseError) as e:
            logger.error(f"Error getting ONT status from ZTE OLT {self.host}: {str(e)}")
            return {
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'error': str(e)
            }
    
    def provision_ont(self, serial_number: str, ont_id: str, ont_type: str,
                     vlan_id: str, service_port: str, vport: str = '1',
                     user_vlan: Optional[str] = None, gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Provision a new ONT on the OLT.
        
        Args:
            serial_number: ONT serial number
            ont_id: ONT ID to assign
            ont_type: ONT type (e.g., 'ZTEG-F660')
            vlan_id: VLAN ID to assign to the ONT
            service_port: Service port number
            vport: Virtual port number (default: '1')
            user_vlan: Optional user VLAN ID (default: same as vlan_id)
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the provisioning operation
            
        Raises:
            ONTProvisioningError: If provisioning fails
        """
        try:
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Use vlan_id as user_vlan if not provided
            user_vlan_id = user_vlan if user_vlan is not None else vlan_id
            
            # Prepare command parameters
            params = {
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'serial_number': serial_number,
                'ont_type': ont_type,
                'service_port': service_port,
                'vport': vport,
                'vlan_id': vlan_id,
                'user_vlan': user_vlan_id
            }
            
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
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'serial_number': serial_number,
                'message': f"Successfully provisioned ONT {ont_id} with serial {serial_number}"
            }
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error provisioning ONT {ont_id} with serial {serial_number}: {str(e)}"
            logger.error(error_msg)
            raise ONTProvisioningError(error_msg)
    
    def deprovision_ont(self, ont_id: str, gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Remove an ONT from the OLT configuration.
        
        Args:
            ont_id: ONT ID to deprovision
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the deprovisioning operation
            
        Raises:
            ONTProvisioningError: If deprovisioning fails
        """
        try:
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Format the command with the parameters
            command = self.commands.DEPROVISION_ONT.format(
                gpon_index=gpon_idx, ont_id=ont_id
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
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'message': f"Successfully deprovisioned ONT {ont_id}"
            }
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error deprovisioning ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTProvisioningError(error_msg)
    
    def reboot_ont(self, ont_id: str, gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Reboot a specific ONT.
        
        Args:
            ont_id: ONT ID to reboot
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the reboot operation
            
        Raises:
            ONTConfigurationError: If reboot fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, gpon_index)
            except ONTNotFoundError as e:
                raise e
            
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Format the command with the parameters
            command = self.commands.REBOOT_ONT.format(
                gpon_index=gpon_idx, ont_id=ont_id
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
                'gpon_index': gpon_idx,
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
                          gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Configure an ONT port.
        
        Args:
            ont_id: ONT ID
            port_id: Port ID on the ONT
            admin_status: Administrative status ('enable' or 'disable')
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the configuration operation
            
        Raises:
            ONTConfigurationError: If configuration fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, gpon_index)
            except ONTNotFoundError as e:
                raise e
            
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Select the appropriate command based on admin_status
            if admin_status.lower() == 'enable':
                command_template = self.commands.ENABLE_ONT_PORT
            elif admin_status.lower() == 'disable':
                command_template = self.commands.DISABLE_ONT_PORT
            else:
                raise ONTConfigurationError(f"Invalid admin_status: {admin_status}. Must be 'enable' or 'disable'")
            
            # Format the command with the parameters
            command = command_template.format(
                gpon_index=gpon_idx, ont_id=ont_id, port_id=port_id
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
                'gpon_index': gpon_idx,
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
                          gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Configure VLAN settings for an ONT port.
        
        Args:
            ont_id: ONT ID
            port_id: Port ID on the ONT
            vlan_id: VLAN ID to assign to the port
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the configuration operation
            
        Raises:
            ONTConfigurationError: If configuration fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, gpon_index)
            except ONTNotFoundError as e:
                raise e
            
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Format the command with the parameters
            command = self.commands.CONFIGURE_ONT_VLAN.format(
                gpon_index=gpon_idx, ont_id=ont_id, port_id=port_id, vlan_id=vlan_id
            )
            
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
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'port_id': port_id,
                'vlan_id': vlan_id,
                'message': f"Successfully configured VLAN {vlan_id} on ONT {ont_id} port {port_id}"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error configuring VLAN on ONT {ont_id} port {port_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)
    
    def set_ont_speed_limit(self, ont_id: str, download_limit: str, upload_limit: str,
                           port_id: str = '1', profile_id: str = '1',
                           gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Set speed limits for an ONT.
        
        Args:
            ont_id: ONT ID
            download_limit: Download speed limit in kbps
            upload_limit: Upload speed limit in kbps
            port_id: Port ID on the ONT (default: '1')
            profile_id: Traffic profile ID (default: '1')
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the configuration operation
            
        Raises:
            ONTConfigurationError: If configuration fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, gpon_index)
            except ONTNotFoundError as e:
                raise e
            
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Format the command with the parameters
            command = self.commands.SET_ONT_SPEED_LIMIT.format(
                gpon_index=gpon_idx, ont_id=ont_id, port_id=port_id,
                profile_id=profile_id, download_limit=download_limit
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
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'port_id': port_id,
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
    
    def restore_ont_factory_settings(self, ont_id: str, gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Restore factory settings for an ONT.
        
        Args:
            ont_id: ONT ID
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the operation
            
        Raises:
            ONTConfigurationError: If the operation fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, gpon_index)
            except ONTNotFoundError as e:
                raise e
            
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Format the command with the parameters
            command = self.commands.RESTORE_ONT_FACTORY.format(
                gpon_index=gpon_idx, ont_id=ont_id
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
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'message': f"Successfully restored factory settings for ONT {ont_id}"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error restoring factory settings for ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)
    
    def configure_tr069(self, ont_id: str, acs_url: str, interval: str = '86400',
                       gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Configure TR-069 settings for an ONT.
        
        Args:
            ont_id: ONT ID
            acs_url: ACS server URL
            interval: Inform interval in seconds (default: '86400')
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Result of the operation
            
        Raises:
            ONTConfigurationError: If the operation fails
            ONTNotFoundError: If the ONT is not found
        """
        try:
            # Check if ONT exists
            try:
                self.get_ont_status(ont_id, gpon_index)
            except ONTNotFoundError as e:
                raise e
            
            # Use default GPON index if not provided
            gpon_idx = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Format the command with the parameters
            command = self.commands.CONFIGURE_TR069.format(
                gpon_index=gpon_idx, ont_id=ont_id, acs_url=acs_url, interval=interval
            )
            
            # Execute the command
            output = self.client.execute_command(command)
            
            # Check for errors in the output
            if "Error" in output or "Failure" in output:
                error_msg = f"Failed to configure TR-069 for ONT {ont_id}: {output}"
                logger.error(error_msg)
                raise ONTConfigurationError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'gpon_index': gpon_idx,
                'ont_id': ont_id,
                'acs_url': acs_url,
                'interval': interval,
                'message': f"Successfully configured TR-069 for ONT {ont_id}"
            }
        except ONTNotFoundError:
            raise
        except (OLTConnectionError, OLTCommandError) as e:
            error_msg = f"Error configuring TR-069 for ONT {ont_id}: {str(e)}"
            logger.error(error_msg)
            raise ONTConfigurationError(error_msg)

    def configure_ont_interface(self, ont_id: str, interface_id: str, vlan_mode: str, 
                              vlan_id: str, gpon_index: Optional[str] = None) -> bool:
        """
        Configure an ONT interface with VLAN settings.
        
        Args:
            ont_id: ONT ID
            interface_id: Interface ID on the ONT
            vlan_mode: VLAN mode ('access', 'trunk', or 'hybrid')
            vlan_id: VLAN ID to assign
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            bool: True if configuration is successful, False otherwise
        """
        try:
            # Use default GPON index if not provided
            gpon = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, gpon)
            
            # Execute command to configure ONT interface
            port_command = f"interface gpon-onu_{gpon}:{ont_id}"
            self.client.execute_command(port_command)
            
            # Configure VLAN mode and ID based on the mode
            if vlan_mode == 'access':
                vlan_command = f"switchport port {interface_id} vlan {vlan_id} tag"
            elif vlan_mode == 'trunk':
                vlan_command = f"switchport port {interface_id} vlan {vlan_id} trunk"
            elif vlan_mode == 'hybrid':
                vlan_command = f"switchport port {interface_id} vlan {vlan_id} hybrid"
            else:
                raise ValueError(f"Unsupported VLAN mode: {vlan_mode}")
                
            self.client.execute_command(vlan_command)
            
            # Exit configuration mode
            self.client.execute_command("exit")
            
            logger.info(f"Successfully configured interface {interface_id} on ONT {ont_id} with VLAN {vlan_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError, ValueError) as e:
            logger.error(f"Error configuring ONT interface: {str(e)}")
            return False
    
    def configure_ont_tr069(self, ont_id: str, acs_url: str, 
                          periodic_inform_interval: int = 86400,
                          connection_request_username: Optional[str] = None,
                          connection_request_password: Optional[str] = None,
                          gpon_index: Optional[str] = None) -> bool:
        """
        Configure TR-069 settings for an ONT.
        
        Args:
            ont_id: ONT ID
            acs_url: URL of the ACS (Auto Configuration Server)
            periodic_inform_interval: Interval in seconds for periodic inform (default: 86400)
            connection_request_username: Username for connection requests
            connection_request_password: Password for connection requests
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            bool: True if configuration is successful, False otherwise
        """
        try:
            # Use default GPON index if not provided
            gpon = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, gpon)
            
            # Execute command to configure ONT TR-069
            port_command = f"interface gpon-onu_{gpon}:{ont_id}"
            self.client.execute_command(port_command)
            
            # Configure TR-069 settings
            tr069_command = f"tr069 acs-url {acs_url}"
            self.client.execute_command(tr069_command)
            
            # Configure periodic inform interval
            inform_command = f"tr069 periodic-inform interval {periodic_inform_interval}"
            self.client.execute_command(inform_command)
            
            # Configure connection request credentials if provided
            if connection_request_username and connection_request_password:
                cred_command = f"tr069 connect-request username {connection_request_username} password {connection_request_password}"
                self.client.execute_command(cred_command)
            
            # Exit configuration mode
            self.client.execute_command("exit")
            
            logger.info(f"Successfully configured TR-069 on ONT {ont_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error configuring TR-069 on ONT: {str(e)}")
            return False
    
    def enable_ont_port(self, ont_id: str, interface_id: str, enabled: bool = True,
                      gpon_index: Optional[str] = None) -> bool:
        """
        Enable or disable an ONT port.
        
        Args:
            ont_id: ONT ID
            interface_id: Interface ID on the ONT
            enabled: Whether to enable (True) or disable (False) the port
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            bool: True if operation is successful, False otherwise
        """
        try:
            # Use default GPON index if not provided
            gpon = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, gpon)
            
            # Execute command to access ONT interface
            port_command = f"interface gpon-onu_{gpon}:{ont_id}"
            self.client.execute_command(port_command)
            
            # Enable or disable the port
            status_word = "no shutdown" if enabled else "shutdown"
            status_command = f"port {interface_id} {status_word}"
            self.client.execute_command(status_command)
            
            # Exit configuration mode
            self.client.execute_command("exit")
            
            status_text = "enabled" if enabled else "disabled"
            logger.info(f"Successfully {status_text} port {interface_id} on ONT {ont_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            status_text = "enabling" if enabled else "disabling"
            logger.error(f"Error {status_text} ONT port: {str(e)}")
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
                                  gpon_index: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for an ONT.
        
        Args:
            ont_id: ONT ID
            metric_type: Type of metric to retrieve ('traffic', 'cpu', 'memory', etc.)
            start_time: Start time in Unix timestamp format (optional)
            end_time: End time in Unix timestamp format (optional)
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            Dict: Performance metrics data
        """
        try:
            # Use default GPON index if not provided
            gpon = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, gpon)
            
            # For demo purposes, we'll return mock metrics data
            # In a real implementation, you would execute commands to retrieve actual metrics
            
            # Create mock response
            metrics = {
                "ont_id": ont_id,
                "gpon_index": gpon,
                "metric_type": metric_type,
                "values": []
            }
            
            # Generate metrics based on type
            if metric_type == 'traffic':
                # Generate sample traffic data
                current_time = int(time.time())
                start = start_time or (current_time - 3600)
                end = end_time or current_time
                
                # Generate data points at 5-minute intervals
                interval = 300  # 5 minutes in seconds
                for timestamp in range(start, end + 1, interval):
                    # Generate random traffic values
                    rx_value = 10 + (timestamp % 100)
                    tx_value = 5 + (timestamp % 50)
                    
                    metrics["values"].append({
                        "timestamp": timestamp,
                        "rx_mbps": rx_value,
                        "tx_mbps": tx_value
                    })
            elif metric_type == 'optical':
                # Generate optical power readings
                metrics["values"].append({
                    "timestamp": int(time.time()),
                    "rx_power_dbm": -15.2,
                    "tx_power_dbm": 2.1
                })
            
            return metrics
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error getting ONT performance metrics: {str(e)}")
            return {
                "ont_id": ont_id,
                "gpon_index": gpon,
                "metric_type": metric_type,
                "error": str(e)
            }
    
    def provision_multiple_onts(self, serial_numbers: List[str], 
                              starting_ont_id: Optional[str] = None,
                              profile_name: Optional[str] = None,
                              vlan_id: Optional[str] = None,
                              gpon_index: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Provision multiple ONTs in a single operation.
        
        Args:
            serial_numbers: List of ONT serial numbers to provision
            starting_ont_id: Starting ONT ID (auto-generated if not provided)
            profile_name: Profile name to use for all ONTs
            vlan_id: VLAN ID to assign to all ONTs
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            List[Dict]: Results of provisioning operations for each ONT
        """
        results = []
        
        # Use default GPON index if not provided
        gpon = gpon_index if gpon_index is not None else self.default_gpon_index
        
        # Generate starting ONT ID if not provided
        current_ont_id = int(starting_ont_id) if starting_ont_id else 1
        
        # Set default profile and VLAN if not provided
        default_profile = profile_name or "Default"
        default_vlan = vlan_id or "100"
        
        for serial_number in serial_numbers:
            try:
                # Provision each ONT individually
                result = self.provision_ont(
                    serial_number=serial_number,
                    ont_id=str(current_ont_id),
                    profile_name=default_profile,
                    vlan_id=default_vlan,
                    gpon_index=gpon
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
                               gpon_index: Optional[str] = None) -> bool:
        """
        Configure IP settings for an ONT.
        
        Args:
            ont_id: ONT ID
            ip_address: IP address to assign to the ONT
            subnet_mask: Subnet mask for the ONT
            gateway: Default gateway for the ONT (optional)
            dhcp_enabled: Whether to enable DHCP (defaults to False)
            gpon_index: Optional GPON index (uses default if not provided)
            
        Returns:
            bool: True if configuration is successful, False otherwise
        """
        try:
            # Use default GPON index if not provided
            gpon = gpon_index if gpon_index is not None else self.default_gpon_index
            
            # Verify ONT exists
            self._verify_ont_exists(ont_id, gpon)
            
            # Execute command to access ONT interface
            port_command = f"interface gpon-onu_{gpon}:{ont_id}"
            self.client.execute_command(port_command)
            
            if dhcp_enabled:
                # Enable DHCP
                ip_command = "ip address dhcp"
                self.client.execute_command(ip_command)
            else:
                # Configure static IP with CIDR notation
                # Convert subnet mask to CIDR format
                cidr = sum([bin(int(x)).count('1') for x in subnet_mask.split('.')])
                ip_command = f"ip address {ip_address}/{cidr}"
                self.client.execute_command(ip_command)
                
                # Add default gateway if provided
                if gateway:
                    gateway_command = f"ip route 0.0.0.0/0 {gateway}"
                    self.client.execute_command(gateway_command)
            
            # Exit configuration mode
            self.client.execute_command("exit")
            
            logger.info(f"Successfully configured IP settings for ONT {ont_id}")
            return True
            
        except (OLTConnectionError, OLTCommandError, ONTNotFoundError) as e:
            logger.error(f"Error configuring ONT IP settings: {str(e)}")
            return False
