"""
Utility functions for the Network Management Module.
"""

import asyncio
import ipaddress
import logging
import re
import jinja2
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime

import netmiko
import napalm
import paramiko
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException, NetMikoAuthenticationException

logger = logging.getLogger(__name__)


async def connect_to_device(
    device_type: str,
    host: str,
    username: str,
    password: str,
    enable_password: Optional[str] = None,
    port: int = 22,
    timeout: int = 30
) -> Any:
    """
    Connect to a network device using Netmiko.
    
    Args:
        device_type: Netmiko device type
        host: Device hostname or IP
        username: SSH username
        password: SSH password
        enable_password: Enable password (if required)
        port: SSH port
        timeout: Connection timeout in seconds
        
    Returns:
        Netmiko connection object
        
    Raises:
        Exception: If connection fails
    """
    device_params = {
        'device_type': device_type,
        'host': host,
        'username': username,
        'password': password,
        'port': port,
        'timeout': timeout
    }
    
    if enable_password:
        device_params['secret'] = enable_password
    
    try:
        # Run in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        connection = await loop.run_in_executor(
            None, 
            lambda: ConnectHandler(**device_params)
        )
        
        # Enter enable mode if enable password is provided
        if enable_password:
            await loop.run_in_executor(
                None,
                lambda: connection.enable()
            )
        
        return connection
    except NetMikoTimeoutException:
        raise Exception(f"Connection to {host} timed out")
    except NetMikoAuthenticationException:
        raise Exception(f"Authentication failed for {host}")
    except Exception as e:
        raise Exception(f"Failed to connect to {host}: {str(e)}")


async def execute_command(connection: Any, command: str) -> str:
    """
    Execute a command on a network device.
    
    Args:
        connection: Netmiko connection object
        command: Command to execute
        
    Returns:
        Command output
        
    Raises:
        Exception: If command execution fails
    """
    try:
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: connection.send_command(command)
        )
        return output
    except Exception as e:
        raise Exception(f"Failed to execute command: {str(e)}")


async def apply_configuration(
    connection: Any,
    config: str,
    save_config: bool = True
) -> str:
    """
    Apply a configuration to a network device.
    
    Args:
        connection: Netmiko connection object
        config: Configuration to apply
        save_config: Whether to save the configuration
        
    Returns:
        Configuration output
        
    Raises:
        Exception: If configuration application fails
    """
    try:
        loop = asyncio.get_event_loop()
        
        # Apply configuration
        output = await loop.run_in_executor(
            None,
            lambda: connection.send_config_set(config.splitlines())
        )
        
        # Save configuration if requested
        if save_config:
            save_output = await loop.run_in_executor(
                None,
                lambda: connection.save_config()
            )
            output += f"\n{save_output}"
        
        return output
    except Exception as e:
        raise Exception(f"Failed to apply configuration: {str(e)}")


async def backup_configuration(
    connection: Any,
    device_type: str
) -> str:
    """
    Backup the configuration of a network device.
    
    Args:
        connection: Netmiko connection object
        device_type: Device type
        
    Returns:
        Device configuration
        
    Raises:
        Exception: If backup fails
    """
    try:
        loop = asyncio.get_event_loop()
        
        # Different commands for different device types
        if 'cisco' in device_type:
            command = 'show running-config'
        elif 'juniper' in device_type:
            command = 'show configuration | display set'
        elif 'arista' in device_type:
            command = 'show running-config'
        elif 'mikrotik' in device_type:
            command = 'export'
        else:
            command = 'show running-config'
        
        # Get configuration
        config = await loop.run_in_executor(
            None,
            lambda: connection.send_command(command)
        )
        
        return config
    except Exception as e:
        raise Exception(f"Failed to backup configuration: {str(e)}")


def parse_configuration(config: str, device_type: str) -> Dict[str, Any]:
    """
    Parse a device configuration into a structured format.
    
    Args:
        config: Device configuration
        device_type: Device type
        
    Returns:
        Parsed configuration
        
    Raises:
        Exception: If parsing fails
    """
    # This is a simplified implementation
    # In a real-world scenario, you would use a more sophisticated parser
    
    parsed_config = {
        'interfaces': [],
        'routing': {
            'static_routes': [],
            'ospf': {},
            'bgp': {}
        },
        'acls': [],
        'vlans': [],
        'users': []
    }
    
    try:
        # Parse interfaces
        if 'cisco' in device_type:
            interface_pattern = r'interface (.+?)\n((?:(?! interface).+\n)+)'
            interfaces = re.finditer(interface_pattern, config, re.MULTILINE)
            
            for match in interfaces:
                interface_name = match.group(1)
                interface_config = match.group(2)
                
                ip_match = re.search(r'ip address ([\d\.]+) ([\d\.]+)', interface_config)
                ip_address = ip_match.group(1) if ip_match else None
                subnet_mask = ip_match.group(2) if ip_match else None
                
                status_match = re.search(r'(no )?shutdown', interface_config)
                is_shutdown = bool(status_match and status_match.group(1))
                
                parsed_config['interfaces'].append({
                    'name': interface_name,
                    'ip_address': ip_address,
                    'subnet_mask': subnet_mask,
                    'is_shutdown': is_shutdown
                })
            
            # Parse static routes
            static_route_pattern = r'ip route ([\d\.]+) ([\d\.]+) ([\d\.]+)'
            static_routes = re.finditer(static_route_pattern, config)
            
            for match in static_routes:
                parsed_config['routing']['static_routes'].append({
                    'destination': match.group(1),
                    'mask': match.group(2),
                    'next_hop': match.group(3)
                })
            
            # Parse VLANs
            vlan_pattern = r'vlan (\d+)\n((?:(?! vlan).+\n)*)'
            vlans = re.finditer(vlan_pattern, config)
            
            for match in vlans:
                vlan_id = match.group(1)
                vlan_config = match.group(2)
                
                name_match = re.search(r'name (.+)', vlan_config)
                name = name_match.group(1) if name_match else None
                
                parsed_config['vlans'].append({
                    'id': vlan_id,
                    'name': name
                })
        
        return parsed_config
    except Exception as e:
        raise Exception(f"Failed to parse configuration: {str(e)}")


def validate_ip_network(network: str) -> bool:
    """
    Validate an IP network in CIDR notation.
    
    Args:
        network: IP network in CIDR notation
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ipaddress.ip_network(network, strict=False)
        return True
    except ValueError:
        return False


def generate_configuration_from_template(
    template_content: str,
    variables: Dict[str, Any]
) -> str:
    """
    Generate a configuration from a Jinja2 template.
    
    Args:
        template_content: Jinja2 template content
        variables: Template variables
        
    Returns:
        Generated configuration
        
    Raises:
        Exception: If generation fails
    """
    try:
        template = jinja2.Template(template_content)
        config = template.render(**variables)
        return config
    except jinja2.exceptions.TemplateSyntaxError as e:
        raise Exception(f"Template syntax error: {str(e)}")
    except jinja2.exceptions.UndefinedError as e:
        raise Exception(f"Undefined variable in template: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to generate configuration: {str(e)}")


async def test_device_connectivity(host: str, timeout: int = 5) -> bool:
    """
    Test connectivity to a device using ping.
    
    Args:
        host: Device hostname or IP
        timeout: Ping timeout in seconds
        
    Returns:
        True if device is reachable, False otherwise
    """
    try:
        # Create ping command based on platform
        import platform
        
        if platform.system().lower() == 'windows':
            ping_cmd = f'ping -n 1 -w {timeout * 1000} {host}'
        else:
            ping_cmd = f'ping -c 1 -W {timeout} {host}'
        
        # Execute ping command
        proc = await asyncio.create_subprocess_shell(
            ping_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        # Check if ping was successful
        return proc.returncode == 0
    except Exception as e:
        logger.error(f"Error testing connectivity to {host}: {str(e)}")
        return False


def calculate_subnet_utilization(
    subnet: str,
    used_ips: List[str]
) -> Dict[str, Any]:
    """
    Calculate utilization of an IP subnet.
    
    Args:
        subnet: Subnet in CIDR notation
        used_ips: List of used IP addresses
        
    Returns:
        Dictionary with utilization statistics
        
    Raises:
        Exception: If calculation fails
    """
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        
        # Calculate total usable IPs
        total_ips = network.num_addresses
        if network.version == 4 and total_ips > 2:
            # Subtract network and broadcast addresses for IPv4
            usable_ips = total_ips - 2
        else:
            usable_ips = total_ips
        
        # Count used IPs
        valid_used_ips = []
        for ip in used_ips:
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj in network:
                    valid_used_ips.append(ip)
            except ValueError:
                continue
        
        used_count = len(valid_used_ips)
        
        # Calculate utilization
        if usable_ips > 0:
            utilization = (used_count / usable_ips) * 100
        else:
            utilization = 0
        
        return {
            'subnet': str(network),
            'total_ips': total_ips,
            'usable_ips': usable_ips,
            'used_ips': used_count,
            'free_ips': usable_ips - used_count,
            'utilization_percent': round(utilization, 2)
        }
    except Exception as e:
        raise Exception(f"Failed to calculate subnet utilization: {str(e)}")


def generate_device_config_diff(old_config: str, new_config: str) -> str:
    """
    Generate a diff between two device configurations.
    
    Args:
        old_config: Old configuration
        new_config: New configuration
        
    Returns:
        Configuration diff
        
    Raises:
        Exception: If diff generation fails
    """
    try:
        import difflib
        
        # Split configs into lines
        old_lines = old_config.splitlines()
        new_lines = new_config.splitlines()
        
        # Generate diff
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='old_config',
            tofile='new_config',
            lineterm=''
        )
        
        return '\n'.join(diff)
    except Exception as e:
        raise Exception(f"Failed to generate config diff: {str(e)}")


def validate_mac_address(mac: str) -> bool:
    """
    Validate a MAC address.
    
    Args:
        mac: MAC address
        
    Returns:
        True if valid, False otherwise
    """
    # Regular expression for MAC address validation
    # Supports formats: 00:11:22:33:44:55, 00-11-22-33-44-55, 001122334455
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$'
    return bool(re.match(mac_pattern, mac))
