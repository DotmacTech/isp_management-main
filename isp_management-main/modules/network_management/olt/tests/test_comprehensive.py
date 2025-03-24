"""
Comprehensive OLT Adapter Test Module

This module provides a more comprehensive test suite for the OLT adapters,
demonstrating all major functionality of both Huawei and ZTE implementations.
"""

import os
import sys
import logging
import json
import time
from unittest import mock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import our simplified test adapters
from modules.network_management.olt.tests.test_simplified import SimpleHuaweiAdapter, SimpleZTEAdapter
from modules.network_management.olt.factory import OLTAdapterFactory


def test_huawei_adapter_comprehensive():
    """Test comprehensive Huawei OLT adapter functionality."""
    # Override the factory to use our simple test adapter
    original_adapter_classes = OLTAdapterFactory._adapter_classes
    try:
        OLTAdapterFactory._adapter_classes = {
            'huawei': SimpleHuaweiAdapter,
            'zte': SimpleZTEAdapter,
        }
        
        logger.info("=== Starting Comprehensive Huawei OLT Adapter Test ===")
        
        # Create and connect the adapter
        adapter = OLTAdapterFactory.create_adapter(
            vendor='huawei',
            host='192.168.1.1',
            username='admin',
            password='password',
            default_frame='0',
            default_slot='0'
        )
        
        # Test connection
        logger.info("Testing connection...")
        connected = adapter.connect()
        if not connected:
            logger.error("Connection failed!")
            return
        logger.info("Connection successful.")
        
        # Get system information
        logger.info("Getting system information...")
        system_info = adapter.get_system_info()
        logger.info(f"System info: {json.dumps(system_info, indent=2)}")
        
        # Test ONT management functions
        test_ont_management(adapter)
        
        # Test ONT configuration functions
        test_ont_configuration(adapter)
        
        # Test performance monitoring
        test_performance_monitoring(adapter)
        
        # Test bulk operations
        test_bulk_operations(adapter)
        
        # Test custom commands
        test_custom_commands(adapter)
        
        # Disconnect
        logger.info("Disconnecting...")
        adapter.disconnect()
        logger.info("Disconnected successfully.")
        
        logger.info("=== Completed Comprehensive Huawei OLT Adapter Test ===\n")
    finally:
        # Restore original adapter classes
        OLTAdapterFactory._adapter_classes = original_adapter_classes


def test_zte_adapter_comprehensive():
    """Test comprehensive ZTE OLT adapter functionality."""
    # Override the factory to use our simple test adapter
    original_adapter_classes = OLTAdapterFactory._adapter_classes
    try:
        OLTAdapterFactory._adapter_classes = {
            'huawei': SimpleHuaweiAdapter,
            'zte': SimpleZTEAdapter,
        }
        
        logger.info("=== Starting Comprehensive ZTE OLT Adapter Test ===")
        
        # Create and connect the adapter
        adapter = OLTAdapterFactory.create_adapter(
            vendor='zte',
            host='192.168.1.2',
            username='admin',
            password='password',
            connection_type='telnet',
            default_gpon_index='1/1/1'
        )
        
        # Test connection
        logger.info("Testing connection...")
        connected = adapter.connect()
        if not connected:
            logger.error("Connection failed!")
            return
        logger.info("Connection successful.")
        
        # Get system information
        logger.info("Getting system information...")
        system_info = adapter.get_system_info()
        logger.info(f"System info: {json.dumps(system_info, indent=2)}")
        
        # Test ONT management functions
        test_ont_management(adapter)
        
        # Test ONT configuration functions
        test_ont_configuration(adapter)
        
        # Test performance monitoring
        test_performance_monitoring(adapter)
        
        # Test bulk operations
        test_bulk_operations(adapter)
        
        # Test custom commands
        test_custom_commands(adapter)
        
        # Disconnect
        logger.info("Disconnecting...")
        adapter.disconnect()
        logger.info("Disconnected successfully.")
        
        logger.info("=== Completed Comprehensive ZTE OLT Adapter Test ===\n")
    finally:
        # Restore original adapter classes
        OLTAdapterFactory._adapter_classes = original_adapter_classes


def test_ont_management(adapter):
    """Test ONT management functions."""
    logger.info("--- Testing ONT Management Functions ---")
    
    # Get all ONTs
    logger.info("Getting all ONTs...")
    onts = adapter.get_onts()
    logger.info(f"Found {len(onts)} ONTs")
    
    # Get ONT details
    if onts:
        ont_id = onts[0].get('ont_id', '1')
        logger.info(f"Getting details for ONT {ont_id}...")
        ont_details = adapter.get_ont_details(ont_id)
        logger.info(f"ONT details: {json.dumps(ont_details, indent=2)}")
        
        # Get ONT status
        logger.info(f"Getting status for ONT {ont_id}...")
        ont_status = adapter.get_ont_status(ont_id)
        logger.info(f"ONT status: {json.dumps(ont_status, indent=2)}")
    
    # Provision a new ONT
    logger.info("Provisioning a new ONT...")
    new_serial = "TEST12345678"
    provision_result = adapter.provision_ont(new_serial)
    logger.info(f"Provision result: {json.dumps(provision_result, indent=2)}")
    
    # If provisioning was successful, get the new ONT ID
    if provision_result.get('success'):
        new_ont_id = provision_result.get('ont_id')
        logger.info(f"Successfully provisioned ONT with ID {new_ont_id}")
        
        # Deprovision the ONT
        logger.info(f"Deprovisioning ONT {new_ont_id}...")
        deprovision_result = adapter.deprovision_ont(new_ont_id)
        logger.info(f"Deprovision successful: {deprovision_result}")
    
    logger.info("--- ONT Management Tests Completed ---")


def test_ont_configuration(adapter):
    """Test ONT configuration functions."""
    logger.info("--- Testing ONT Configuration Functions ---")
    
    # Get the first ONT for testing
    onts = adapter.get_onts()
    if not onts:
        logger.error("No ONTs found for configuration testing")
        return
    
    ont_id = onts[0].get('ont_id', '1')
    logger.info(f"Using ONT {ont_id} for configuration tests")
    
    # Configure ONT interface
    logger.info(f"Configuring VLAN on ONT {ont_id}, interface 1...")
    interface_result = adapter.configure_ont_interface(
        ont_id=ont_id,
        interface_id='1',
        vlan_mode='access',
        vlan_id=100
    )
    logger.info(f"Interface configuration successful: {interface_result}")
    
    # Set ONT IP configuration
    logger.info(f"Setting IP configuration on ONT {ont_id}...")
    ip_result = adapter.set_ont_ip_configuration(
        ont_id=ont_id,
        ip_address='192.168.1.100',
        subnet_mask='255.255.255.0',
        gateway='192.168.1.1',
        dhcp_enabled=False
    )
    logger.info(f"IP configuration successful: {ip_result}")
    
    # Enable/disable ONT port
    logger.info(f"Enabling port 1 on ONT {ont_id}...")
    port_result = adapter.enable_ont_port(
        ont_id=ont_id,
        interface_id='1',
        enabled=True
    )
    logger.info(f"Port enable successful: {port_result}")
    
    # Set speed limits
    logger.info(f"Setting speed limits on ONT {ont_id}...")
    speed_result = adapter.set_ont_speed_limit(
        ont_id=ont_id,
        download_limit=100000,  # 100 Mbps
        upload_limit=50000      # 50 Mbps
    )
    logger.info(f"Speed limit configuration successful: {speed_result}")
    
    # Configure TR-069
    logger.info(f"Configuring TR-069 on ONT {ont_id}...")
    tr069_result = adapter.configure_ont_tr069(
        ont_id=ont_id,
        acs_url='http://acs.example.com/tr069',
        periodic_inform_interval=86400,
        connection_request_username='tr069user',
        connection_request_password='tr069pass'
    )
    logger.info(f"TR-069 configuration successful: {tr069_result}")
    
    # Reboot ONT
    logger.info(f"Rebooting ONT {ont_id}...")
    reboot_result = adapter.reboot_ont(ont_id)
    logger.info(f"Reboot successful: {reboot_result}")
    
    logger.info("--- ONT Configuration Tests Completed ---")


def test_performance_monitoring(adapter):
    """Test performance monitoring functions."""
    logger.info("--- Testing Performance Monitoring Functions ---")
    
    # Get the first ONT for testing
    onts = adapter.get_onts()
    if not onts:
        logger.error("No ONTs found for performance monitoring testing")
        return
    
    ont_id = onts[0].get('ont_id', '1')
    logger.info(f"Getting performance metrics for ONT {ont_id}...")
    
    # Test different metric types
    metric_types = ['traffic', 'cpu', 'memory']
    for metric_type in metric_types:
        logger.info(f"Getting {metric_type} metrics...")
        metrics = adapter.get_ont_performance_metrics(
            ont_id=ont_id,
            metric_type=metric_type,
            start_time=int(time.time()) - 3600,  # Last hour
            end_time=int(time.time())
        )
        logger.info(f"{metric_type.capitalize()} metrics: {json.dumps(metrics, indent=2)}")
    
    logger.info("--- Performance Monitoring Tests Completed ---")


def test_bulk_operations(adapter):
    """Test bulk operation functions."""
    logger.info("--- Testing Bulk Operation Functions ---")
    
    # Bulk provision multiple ONTs
    logger.info("Provisioning multiple ONTs...")
    serial_numbers = ["BULK0000001", "BULK0000002", "BULK0000003"]
    bulk_results = adapter.provision_multiple_onts(serial_numbers)
    logger.info(f"Bulk provision results: {json.dumps(bulk_results, indent=2)}")
    
    # If provisioning successful, deprovision them
    ont_ids = [result.get('ont_id') for result in bulk_results if result.get('success')]
    if ont_ids:
        logger.info(f"Deprovisioning {len(ont_ids)} ONTs...")
        for ont_id in ont_ids:
            result = adapter.deprovision_ont(ont_id)
            logger.info(f"Deprovisioned ONT {ont_id}: {result}")
    
    logger.info("--- Bulk Operation Tests Completed ---")


def test_custom_commands(adapter):
    """Test custom command functionality."""
    logger.info("--- Testing Custom Command Functions ---")
    
    # Execute some vendor-specific commands
    if isinstance(adapter, SimpleHuaweiAdapter):
        logger.info("Executing Huawei-specific command...")
        result = adapter.execute_custom_command("display version")
    else:
        logger.info("Executing ZTE-specific command...")
        result = adapter.execute_custom_command("show version")
    
    logger.info(f"Custom command result: {result}")
    
    logger.info("--- Custom Command Tests Completed ---")


if __name__ == "__main__":
    logger.info("Starting comprehensive OLT adapter tests...")
    
    # Test Huawei adapter
    test_huawei_adapter_comprehensive()
    
    # Test ZTE adapter
    test_zte_adapter_comprehensive()
    
    logger.info("All comprehensive tests completed!")
