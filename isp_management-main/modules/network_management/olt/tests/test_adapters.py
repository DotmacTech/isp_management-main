"""
OLT Adapter Test Module

This module provides test functionality for the OLT adapters.
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

# Import the factory and adapters
from modules.network_management.olt.factory import OLTAdapterFactory
from modules.network_management.olt.adapters.huawei_adapter import HuaweiOLTAdapter
from modules.network_management.olt.adapters.zte_adapter import ZTEOLTAdapter
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


class MockTelnetClient(MockSSHClient):
    """Mock Telnet client for testing."""
    
    def __init__(self, host, username, password, port=23):
        super().__init__(host, username, password, port)


def test_huawei_adapter():
    """Test the Huawei OLT adapter functionality."""
    logger.info("Testing Huawei OLT adapter...")
    
    # Create a mock SSH client for testing
    with mock.patch.object(SSHClient, '__new__', return_value=MockSSHClient('192.168.1.1', 'admin', 'password')):
        # Create the Huawei adapter
        adapter = OLTAdapterFactory.create_adapter(
            vendor='huawei',
            host='192.168.1.1',
            username='admin',
            password='password',
            port=22,
            model='MA5800',
            default_frame='0',
            default_slot='0'
        )
        
        # Test connection
        logger.info("Testing connection...")
        connected = adapter.connect()
        if connected:
            logger.info("Connection successful!")
        else:
            logger.error("Connection failed!")
            return
        
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


def test_zte_adapter():
    """Test the ZTE OLT adapter functionality."""
    logger.info("Testing ZTE OLT adapter...")
    
    # Create a mock Telnet client for testing
    with mock.patch.object(TelnetClient, '__new__', return_value=MockTelnetClient('192.168.1.2', 'admin', 'password')):
        # Create the ZTE adapter
        adapter = OLTAdapterFactory.create_adapter(
            vendor='zte',
            host='192.168.1.2',
            username='admin',
            password='password',
            port=23,
            model='C320',
            connection_type='telnet',
            default_gpon_index='1/1/1'
        )
        
        # Test connection
        logger.info("Testing connection...")
        connected = adapter.connect()
        if connected:
            logger.info("Connection successful!")
        else:
            logger.error("Connection failed!")
            return
        
        # Test system info
        logger.info("Getting system information...")
        system_info = adapter.get_system_info()
        logger.info(f"System info: {json.dumps(system_info, indent=2)}")
        
        # Test ONT details
        logger.info("Getting ONT details...")
        try:
            ont_details = adapter.get_ont_details('1')
            logger.info(f"ONT details: {json.dumps(ont_details, indent=2)}")
        except Exception as e:
            logger.error(f"Error getting ONT details: {str(e)}")
        
        # Test disconnection
        logger.info("Testing disconnection...")
        adapter.disconnect()
        logger.info("Disconnection successful!")


def test_factory():
    """Test the OLT adapter factory functionality."""
    logger.info("Testing OLT adapter factory...")
    
    # Get list of supported vendors
    vendors = OLTAdapterFactory.get_supported_vendors()
    logger.info(f"Supported vendors: {vendors}")
    
    # Import the adapter classes
    from ..adapters.huawei_adapter import HuaweiOLTAdapter
    from ..adapters.zte_adapter import ZTEOLTAdapter
    
    # Import necessary utilities
    from ..adapters.utils.ssh_client import SSHClient
    from ..adapters.utils.telnet_client import TelnetClient
    
    # Test creating adapters for each vendor
    for vendor in vendors:
        logger.info(f"Testing factory creation for vendor: {vendor}")
        
        # Choose the appropriate mock client based on vendor
        if vendor == 'huawei':
            client_class = MockSSHClient
            adapter_class = HuaweiOLTAdapter
            host = '192.168.1.1'
        else:  # zte
            client_class = MockTelnetClient
            adapter_class = ZTEOLTAdapter
            host = '192.168.1.2'
        
        # Mock both client types to ensure we don't hit errors
        # regardless of which one is used
        mock_ssh = mock.patch.object(SSHClient, '__new__', 
                                    return_value=MockSSHClient(host, 'admin', 'password'))
        mock_telnet = mock.patch.object(TelnetClient, '__new__', 
                                      return_value=MockTelnetClient(host, 'admin', 'password'))
        
        # Apply both mocks
        with mock_ssh, mock_telnet:
            adapter = OLTAdapterFactory.create_adapter(
                vendor=vendor,
                host=host,
                username='admin',
                password='password'
            )
            logger.info(f"Successfully created {vendor} adapter")
            
            # Verify the adapter class type
            expected_class = HuaweiOLTAdapter if vendor == 'huawei' else ZTEOLTAdapter
            assert isinstance(adapter, expected_class), f"Expected {expected_class.__name__}, got {type(adapter).__name__}"


if __name__ == "__main__":
    logger.info("Starting OLT adapter tests...")
    
    # Test the adapter factory
    test_factory()
    
    # Test the Huawei adapter
    test_huawei_adapter()
    
    # Test the ZTE adapter
    test_zte_adapter()
    
    logger.info("All tests completed!")
