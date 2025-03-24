"""
Simplified OLT Adapter Test Module

This module provides a simplified test approach for the OLT adapters.
"""

import os
import sys
import logging
import json
from unittest import mock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import the factory and adapters (we'll use mock implementations)
from modules.network_management.olt.factory import OLTAdapterFactory
from modules.network_management.olt.adapters.base import OLTAdapter
from modules.network_management.olt.adapters.utils.ssh_client import SSHClient
from modules.network_management.olt.adapters.utils.telnet_client import TelnetClient


class MockSSHClient:
    """Mock SSH client for testing."""
    
    def __init__(self, host, username, password, port=22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self._connected = False
        
        # Sample command responses
        self.responses = {
            'display version': """
            MA5800-X17 Huawei Integrated Access Software.
            VERSION: MA5800V100R019C10SPC300
            PRODUCT: MA5800-X17
            Uptime is 157 days, 23 hours, 36 minutes 
            """,
            'display ont info 0/0/1 all': """
            ONT-ID: 1    Status: online    SN: HWTC1234567
            ONT-ID: 2    Status: offline   SN: HWTC7654321
            ONT-ID: 3    Status: online    SN: HWTC0001111
            """,
            'display ont info 0/0/1 1': """
            ONT-ID: 1
            SN: HWTC1234567
            Password: 
            Type: Standard
            Status: online
            IPv4-address: 192.168.1.10
            IPv6-address: 
            Description: 
            Last-down-cause: SN Conflict
            Last-down-time: 2023-01-15 10:30:45+01:00
            Last-up-time: 2023-01-15 11:45:32+01:00
            """,
            'show version': """
            ZTE C320 System Software.
            VERSION: C320-V2.0.1
            PRODUCT: ZTE-C320
            Uptime is 98 days, 12 hours, 15 minutes, 30 seconds
            """,
            'show gpon onu detail-info gpon-onu_1/1/1:1': """
            ONU interface:        gpon-onu_1/1/1:1
            Name:                 GPON_ONU_1
            Type:                 ZTEG-F660
            State:                active
            Admin state:          enable
            Phase state:          working
            Serial number:        ZTEG12345678
            VLAN ID:              100
            Management IP:        192.168.2.100
            Original VLAN:        100
            MAC:                  aa:bb:cc:dd:ee:ff
            """
        }
    
    def connect(self):
        """Simulate a connection to the device."""
        logger.info(f"Mock connecting to {self.host} with user {self.username}")
        self._connected = True
        return True
    
    def disconnect(self):
        """Simulate disconnection from the device."""
        logger.info(f"Mock disconnecting from {self.host}")
        self._connected = False
    
    def is_connected(self):
        """Check if connected to the device."""
        return self._connected
    
    def execute_command(self, command):
        """Simulate command execution."""
        if not self._connected:
            raise Exception("Not connected")
        
        logger.info(f"Mock executing command: {command}")
        
        # Try to find an exact match first
        if command in self.responses:
            return self.responses[command]
        
        # If no exact match, try to find a partial match
        for cmd, response in self.responses.items():
            if cmd in command:
                return response
        
        # Default response if no match is found
        return "Command executed successfully"


# Create simple test adapter class that extends OLTAdapter and implements abstract methods
class SimpleHuaweiAdapter(OLTAdapter):
    """
    Simple implementation of the OLTAdapter for testing.
    """
    
    def __init__(self, host, username, password, port=22, model="MA5800", 
                 default_frame="0", default_slot="0"):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.model = model
        self.default_frame = default_frame
        self.default_slot = default_slot
        self.client = MockSSHClient(host, username, password, port)
    
    def connect(self):
        return self.client.connect()
    
    def disconnect(self):
        self.client.disconnect()
    
    def is_connected(self):
        return self.client.is_connected()
    
    def get_system_info(self):
        output = self.client.execute_command("display version")
        return {
            "vendor": "huawei",
            "model": self.model,
            "version": "MA5800V100R019C10SPC300",
            "uptime": "157 days, 23 hours, 36 minutes"
        }
    
    def get_olts(self):
        return [self.get_system_info()]
    
    def get_onts(self, frame_id=None, slot_id=None):
        frame = frame_id or self.default_frame
        slot = slot_id or self.default_slot
        output = self.client.execute_command(f"display ont info {frame}/{slot}/1 all")
        return [
            {"ont_id": "1", "status": "online", "serial_number": "HWTC1234567"},
            {"ont_id": "2", "status": "offline", "serial_number": "HWTC7654321"},
            {"ont_id": "3", "status": "online", "serial_number": "HWTC0001111"}
        ]
    
    def get_ont_details(self, ont_id, frame_id=None, slot_id=None):
        frame = frame_id or self.default_frame
        slot = slot_id or self.default_slot
        output = self.client.execute_command(f"display ont info {frame}/{slot}/1 {ont_id}")
        return {
            "ont_id": ont_id,
            "serial_number": "HWTC1234567",
            "status": "online",
            "ip_address": "192.168.1.10"
        }
    
    def provision_ont(self, serial_number, frame_id=None, slot_id=None, name=None, description=None):
        return {
            "success": True,
            "ont_id": "10",
            "serial_number": serial_number
        }
    
    def provision_multiple_onts(self, serial_numbers, frame_id=None, slot_id=None):
        return [
            {"success": True, "ont_id": str(i+10), "serial_number": sn} 
            for i, sn in enumerate(serial_numbers)
        ]
    
    def deprovision_ont(self, ont_id, frame_id=None, slot_id=None):
        return True
    
    def configure_ont_interface(self, ont_id, interface_id, vlan_mode, vlan_id=None, frame_id=None, slot_id=None):
        return True
    
    def set_ont_ip_configuration(self, ont_id, ip_address=None, subnet_mask=None, gateway=None, 
                                dhcp_enabled=None, pppoe_enabled=None, frame_id=None, slot_id=None):
        return True
    
    def enable_ont_port(self, ont_id, interface_id, enabled, frame_id=None, slot_id=None):
        return True
    
    def reboot_ont(self, ont_id, frame_id=None, slot_id=None):
        return True
    
    def restore_ont_factory_settings(self, ont_id, frame_id=None, slot_id=None):
        return True
    
    def get_ont_status(self, ont_id, frame_id=None, slot_id=None):
        return {
            "ont_id": ont_id,
            "status": "online",
            "last_up_time": "2023-01-15 11:45:32+01:00"
        }
    
    def get_ont_performance_metrics(self, ont_id, metric_type, start_time=None, end_time=None, 
                                   frame_id=None, slot_id=None):
        return {
            "ont_id": ont_id,
            "metric_type": metric_type,
            "values": [{"timestamp": 1697123456, "value": 95.5}]
        }
    
    def configure_ont_tr069(self, ont_id, acs_url, periodic_inform_interval, 
                           connection_request_username, connection_request_password, 
                           frame_id=None, slot_id=None):
        return True
    
    def set_ont_speed_limit(self, ont_id, download_limit=None, upload_limit=None, 
                           frame_id=None, slot_id=None):
        return True
    
    def execute_custom_command(self, command):
        return self.client.execute_command(command)


class SimpleZTEAdapter(OLTAdapter):
    """
    Simple implementation of the OLTAdapter for ZTE.
    """
    
    def __init__(self, host, username, password, port=23, model="C320", 
                 connection_type="telnet", default_gpon_index="1/1/1"):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.model = model
        self.connection_type = connection_type
        self.default_gpon_index = default_gpon_index
        self.client = MockSSHClient(host, username, password, port)
    
    def connect(self):
        return self.client.connect()
    
    def disconnect(self):
        self.client.disconnect()
    
    def is_connected(self):
        return self.client.is_connected()
    
    def get_system_info(self):
        output = self.client.execute_command("show version")
        return {
            "vendor": "zte",
            "model": self.model,
            "version": "C320-V2.0.1",
            "uptime": "98 days, 12 hours, 15 minutes, 30 seconds"
        }
    
    def get_olts(self):
        return [self.get_system_info()]
    
    def get_onts(self, frame_id=None, slot_id=None):
        return [
            {"ont_id": "1", "status": "active", "serial_number": "ZTEG12345678"},
            {"ont_id": "2", "status": "inactive", "serial_number": "ZTEG87654321"}
        ]
    
    def get_ont_details(self, ont_id, frame_id=None, slot_id=None):
        output = self.client.execute_command(f"show gpon onu detail-info gpon-onu_{self.default_gpon_index}:{ont_id}")
        return {
            "ont_id": ont_id,
            "serial_number": "ZTEG12345678",
            "status": "active",
            "ip_address": "192.168.2.100",
            "vlan_id": "100"
        }
    
    def provision_ont(self, serial_number, frame_id=None, slot_id=None, name=None, description=None):
        return {
            "success": True,
            "ont_id": "10",
            "serial_number": serial_number
        }
    
    def provision_multiple_onts(self, serial_numbers, frame_id=None, slot_id=None):
        return [
            {"success": True, "ont_id": str(i+10), "serial_number": sn} 
            for i, sn in enumerate(serial_numbers)
        ]
    
    def deprovision_ont(self, ont_id, frame_id=None, slot_id=None):
        return True
    
    def configure_ont_interface(self, ont_id, interface_id, vlan_mode, vlan_id=None, frame_id=None, slot_id=None):
        return True
    
    def set_ont_ip_configuration(self, ont_id, ip_address=None, subnet_mask=None, gateway=None, 
                                dhcp_enabled=None, pppoe_enabled=None, frame_id=None, slot_id=None):
        return True
    
    def enable_ont_port(self, ont_id, interface_id, enabled, frame_id=None, slot_id=None):
        return True
    
    def reboot_ont(self, ont_id, frame_id=None, slot_id=None):
        return True
    
    def restore_ont_factory_settings(self, ont_id, frame_id=None, slot_id=None):
        return True
    
    def get_ont_status(self, ont_id, frame_id=None, slot_id=None):
        return {
            "ont_id": ont_id,
            "status": "active",
            "admin_state": "enable"
        }
    
    def get_ont_performance_metrics(self, ont_id, metric_type, start_time=None, end_time=None, 
                                   frame_id=None, slot_id=None):
        return {
            "ont_id": ont_id,
            "metric_type": metric_type,
            "values": [{"timestamp": 1697123456, "value": 87.2}]
        }
    
    def configure_ont_tr069(self, ont_id, acs_url, periodic_inform_interval, 
                           connection_request_username, connection_request_password, 
                           frame_id=None, slot_id=None):
        return True
    
    def set_ont_speed_limit(self, ont_id, download_limit=None, upload_limit=None, 
                           frame_id=None, slot_id=None):
        return True
    
    def execute_custom_command(self, command):
        return self.client.execute_command(command)


# Override the factory class to use our simple adapters
class TestAdapterFactory:
    @staticmethod
    def test_factory():
        """Test the adapter factory with mocked implementations."""
        # Override the OLTAdapterFactory's _adapter_classes
        original_adapter_classes = OLTAdapterFactory._adapter_classes
        try:
            # Replace with our test implementations
            OLTAdapterFactory._adapter_classes = {
                'huawei': SimpleHuaweiAdapter,
                'zte': SimpleZTEAdapter,
            }
            
            logger.info("Testing OLT adapter factory...")
            
            # Get supported vendors
            supported_vendors = OLTAdapterFactory.get_supported_vendors()
            logger.info(f"Supported vendors: {supported_vendors}")
            
            # Test creating adapters for each supported vendor
            for vendor in supported_vendors:
                logger.info(f"Testing factory creation for vendor: {vendor}")
                
                adapter = OLTAdapterFactory.create_adapter(
                    vendor=vendor,
                    host=f"192.168.1.{1 if vendor == 'huawei' else 2}",
                    username='admin',
                    password='password'
                )
                logger.info(f"Successfully created {vendor} adapter")
                
                # Test connection
                logger.info(f"Testing connection for {vendor}...")
                connected = adapter.connect()
                if connected:
                    logger.info("Connection successful!")
                else:
                    logger.error("Connection failed!")
                    continue
                
                # Test system info
                logger.info("Getting system information...")
                system_info = adapter.get_system_info()
                logger.info(f"System info: {json.dumps(system_info, indent=2)}")
                
                # Test ONT listing
                logger.info("Getting ONT list...")
                onts = adapter.get_onts()
                logger.info(f"Found {len(onts)} ONTs")
                
                if onts:
                    # Test ONT details
                    ont_id = onts[0].get('ont_id', '1')
                    logger.info(f"Getting details for ONT {ont_id}...")
                    ont_details = adapter.get_ont_details(ont_id)
                    logger.info(f"ONT details: {json.dumps(ont_details, indent=2)}")
                
                # Test disconnection
                logger.info("Testing disconnection...")
                adapter.disconnect()
                logger.info("Disconnection successful!")
        finally:
            # Restore original adapter classes
            OLTAdapterFactory._adapter_classes = original_adapter_classes


if __name__ == "__main__":
    logger.info("Starting simplified OLT adapter tests...")
    TestAdapterFactory.test_factory()
    logger.info("All tests completed!")
