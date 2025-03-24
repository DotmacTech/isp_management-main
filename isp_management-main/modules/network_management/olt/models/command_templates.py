"""
Command Templates Module

This module defines command templates for different OLT vendors.
These templates are used by the adapters to construct commands
for interacting with OLT devices.
"""

from typing import Dict, Any


class CommandTemplates:
    """Base class for command templates."""
    
    @classmethod
    def get_commands(cls) -> Dict[str, str]:
        """
        Get all command templates.
        
        Returns:
            Dict[str, str]: Dictionary of command templates
        """
        return {
            name: value for name, value in cls.__dict__.items()
            if not name.startswith('_') and isinstance(value, str)
        }


class HuaweiCommandTemplates(CommandTemplates):
    """Command templates for Huawei OLT devices."""
    
    # System commands
    SYSTEM_INFO = "display version"
    SYSTEM_UPTIME = "display system uptime"
    SYSTEM_TEMPERATURE = "display temperature"
    
    # ONT management commands
    LIST_ONTS = "display ont info {frame} {slot} all"
    ONT_DETAILS = "display ont info {frame} {slot} {ont_id}"
    ONT_STATUS = "display ont status {frame} {slot} {ont_id}"
    ONT_OPTICAL_INFO = "display ont optical-info {frame} {slot} {ont_id}"
    ONT_VERSION = "display ont version {frame} {slot} {ont_id}"
    ONT_PORT_STATUS = "display ont port state {frame} {slot} {ont_id} eth-port all"
    
    # ONT provisioning commands
    PROVISION_ONT = (
        "interface gpon {frame}/{slot}\n"
        "ont add {ont_id} {serial_number} {profile_name}\n"
        "ont port native-vlan {ont_id} eth 1 vlan {vlan_id}\n"
        "ont ipconfig {ont_id} ip-index 0 address {ip_address} mask {subnet_mask} gateway {gateway}\n"
        "quit"
    )
    DEPROVISION_ONT = (
        "interface gpon {frame}/{slot}\n"
        "ont delete {ont_id}\n"
        "quit"
    )
    
    # ONT configuration commands
    ENABLE_ONT_PORT = (
        "interface gpon {frame}/{slot}\n"
        "ont port {ont_id} eth {port_id} admin-status enable\n"
        "quit"
    )
    DISABLE_ONT_PORT = (
        "interface gpon {frame}/{slot}\n"
        "ont port {ont_id} eth {port_id} admin-status disable\n"
        "quit"
    )
    CONFIGURE_ONT_VLAN = (
        "interface gpon {frame}/{slot}\n"
        "ont port vlan {ont_id} eth {port_id} translation {vlan_id} user-vlan {user_vlan_id}\n"
        "quit"
    )
    SET_ONT_SPEED_LIMIT = (
        "interface gpon {frame}/{slot}\n"
        "ont car {ont_id} inbound cir {download_limit} pir {download_limit} outbound cir {upload_limit} pir {upload_limit}\n"
        "quit"
    )
    
    # ONT operations
    REBOOT_ONT = (
        "interface gpon {frame}/{slot}\n"
        "ont reset {ont_id}\n"
        "quit"
    )
    RESTORE_ONT_FACTORY = (
        "interface gpon {frame}/{slot}\n"
        "ont restore factory-setting {ont_id}\n"
        "quit"
    )
    
    # TR-069 configuration
    CONFIGURE_TR069 = (
        "interface gpon {frame}/{slot}\n"
        "ont tr069-server-config {ont_id} profile-id {profile_id}\n"
        "quit"
    )


class ZTECommandTemplates(CommandTemplates):
    """Command templates for ZTE OLT devices."""
    
    # System commands
    SYSTEM_INFO = "show version"
    SYSTEM_UPTIME = "show uptime"
    SYSTEM_TEMPERATURE = "show temperature"
    
    # ONT management commands
    LIST_ONTS = "show gpon onu uncfg"
    LIST_CONFIGURED_ONTS = "show gpon onu by-sn {serial_number}"
    ONT_DETAILS = "show gpon onu detail-info gpon-onu_{gpon_index}:{ont_id}"
    ONT_STATUS = "show gpon remote-onu status gpon-onu_{gpon_index}:{ont_id}"
    ONT_OPTICAL_INFO = "show gpon remote-onu optical-info gpon-onu_{gpon_index}:{ont_id}"
    ONT_VERSION = "show gpon remote-onu equip gpon-onu_{gpon_index}:{ont_id}"
    ONT_PORT_STATUS = "show gpon remote-onu eth-port state gpon-onu_{gpon_index}:{ont_id}"
    
    # ONT provisioning commands
    PROVISION_ONT = (
        "conf t\n"
        "interface gpon-olt_{gpon_index}\n"
        "onu {ont_id} type {ont_type} sn {serial_number}\n"
        "exit\n"
        "interface gpon-onu_{gpon_index}:{ont_id}\n"
        "service-port {service_port} vport {vport} user-vlan {user_vlan} vlan {vlan_id}\n"
        "exit\n"
        "exit"
    )
    DEPROVISION_ONT = (
        "conf t\n"
        "interface gpon-olt_{gpon_index}\n"
        "no onu {ont_id}\n"
        "exit\n"
        "exit"
    )
    
    # ONT configuration commands
    ENABLE_ONT_PORT = (
        "conf t\n"
        "interface gpon-onu_{gpon_index}:{ont_id}\n"
        "port eth {port_id} state enable\n"
        "exit\n"
        "exit"
    )
    DISABLE_ONT_PORT = (
        "conf t\n"
        "interface gpon-onu_{gpon_index}:{ont_id}\n"
        "port eth {port_id} state disable\n"
        "exit\n"
        "exit"
    )
    CONFIGURE_ONT_VLAN = (
        "conf t\n"
        "interface gpon-onu_{gpon_index}:{ont_id}\n"
        "switchport vlan {vlan_id} tag eth {port_id}\n"
        "exit\n"
        "exit"
    )
    SET_ONT_SPEED_LIMIT = (
        "conf t\n"
        "traffic-profile stream {profile_id} cir {download_limit} pir {download_limit} cbs 1000 pbs 2000\n"
        "interface gpon-onu_{gpon_index}:{ont_id}\n"
        "traffic-profile {profile_id} ingress eth {port_id}\n"
        "exit\n"
        "exit"
    )
    
    # ONT operations
    REBOOT_ONT = (
        "conf t\n"
        "pon-onu-mng gpon-onu_{gpon_index}:{ont_id}\n"
        "reboot\n"
        "exit\n"
        "exit"
    )
    RESTORE_ONT_FACTORY = (
        "conf t\n"
        "pon-onu-mng gpon-onu_{gpon_index}:{ont_id}\n"
        "restore factory\n"
        "exit\n"
        "exit"
    )
    
    # TR-069 configuration
    CONFIGURE_TR069 = (
        "conf t\n"
        "pon-onu-mng gpon-onu_{gpon_index}:{ont_id}\n"
        "tr069-mgmt enable\n"
        "tr069-mgmt acs-url {acs_url}\n"
        "tr069-mgmt periodic-inform enable interval {interval}\n"
        "exit\n"
        "exit"
    )
