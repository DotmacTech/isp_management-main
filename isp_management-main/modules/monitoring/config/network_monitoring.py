"""
Network Monitoring Configuration for the ISP Management Platform

This module defines configuration settings for network performance monitoring.
"""

import os
from typing import List, Dict, Any, Optional

# Network Performance Monitoring Settings
PING_COUNT = int(os.getenv('PING_COUNT', '5'))
PING_TIMEOUT = int(os.getenv('PING_TIMEOUT', '2'))
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '300'))  # 5 minutes in seconds

# SNMP Settings
SNMP_COMMUNITY = os.getenv('SNMP_COMMUNITY', 'public')
SNMP_VERSION = os.getenv('SNMP_VERSION', '2c')
SNMP_TIMEOUT = int(os.getenv('SNMP_TIMEOUT', '5'))

# Bandwidth Monitoring Settings
BANDWIDTH_INTERFACES = os.getenv('BANDWIDTH_INTERFACES', 'eth0,eth1').split(',')
BANDWIDTH_POLL_INTERVAL = int(os.getenv('BANDWIDTH_POLL_INTERVAL', '60'))  # 1 minute in seconds

# Service Monitoring Settings
SERVICE_CHECK_TIMEOUT = int(os.getenv('SERVICE_CHECK_TIMEOUT', '5'))  # 5 seconds
SERVICE_CHECK_INTERVAL = int(os.getenv('SERVICE_CHECK_INTERVAL', '60'))  # 1 minute in seconds

# Customer Usage Monitoring Settings
CUSTOMER_USAGE_POLL_INTERVAL = int(os.getenv('CUSTOMER_USAGE_POLL_INTERVAL', '300'))  # 5 minutes in seconds

# Alert Thresholds
LATENCY_THRESHOLD_WARNING = float(os.getenv('LATENCY_THRESHOLD_WARNING', '50'))  # 50 ms
LATENCY_THRESHOLD_CRITICAL = float(os.getenv('LATENCY_THRESHOLD_CRITICAL', '100'))  # 100 ms
PACKET_LOSS_THRESHOLD_WARNING = float(os.getenv('PACKET_LOSS_THRESHOLD_WARNING', '2'))  # 2%
PACKET_LOSS_THRESHOLD_CRITICAL = float(os.getenv('PACKET_LOSS_THRESHOLD_CRITICAL', '5'))  # 5%
BANDWIDTH_UTILIZATION_THRESHOLD_WARNING = float(os.getenv('BANDWIDTH_UTILIZATION_THRESHOLD_WARNING', '70'))  # 70%
BANDWIDTH_UTILIZATION_THRESHOLD_CRITICAL = float(os.getenv('BANDWIDTH_UTILIZATION_THRESHOLD_CRITICAL', '85'))  # 85%
CONNECTION_COUNT_THRESHOLD_WARNING = int(os.getenv('CONNECTION_COUNT_THRESHOLD_WARNING', '3000'))
CONNECTION_COUNT_THRESHOLD_CRITICAL = int(os.getenv('CONNECTION_COUNT_THRESHOLD_CRITICAL', '5000'))
CUSTOMER_QUOTA_THRESHOLD_WARNING = float(os.getenv('CUSTOMER_QUOTA_THRESHOLD_WARNING', '80'))  # 80%
CUSTOMER_QUOTA_THRESHOLD_CRITICAL = float(os.getenv('CUSTOMER_QUOTA_THRESHOLD_CRITICAL', '95'))  # 95%

# Elasticsearch Index Settings
NETWORK_METRICS_INDEX = os.getenv('NETWORK_METRICS_INDEX', 'isp-network-metrics')
SERVICE_METRICS_INDEX = os.getenv('SERVICE_METRICS_INDEX', 'isp-service-metrics')
CUSTOMER_USAGE_INDEX = os.getenv('CUSTOMER_USAGE_INDEX', 'isp-customer-usage')

# Default Network Nodes to Monitor
# These can be overridden by adding nodes through the API
DEFAULT_NETWORK_NODES = [
    {
        'id': 'main-router',
        'name': 'Main Router',
        'ip_address': os.getenv('MAIN_ROUTER_IP', '192.168.1.1'),
        'type': 'router',
        'location': 'Main Office',
        'is_active': True,
        'snmp_community': SNMP_COMMUNITY,
        'snmp_version': SNMP_VERSION
    },
    {
        'id': 'backup-router',
        'name': 'Backup Router',
        'ip_address': os.getenv('BACKUP_ROUTER_IP', '192.168.1.2'),
        'type': 'router',
        'location': 'Main Office',
        'is_active': True,
        'snmp_community': SNMP_COMMUNITY,
        'snmp_version': SNMP_VERSION
    },
    {
        'id': 'core-switch',
        'name': 'Core Switch',
        'ip_address': os.getenv('CORE_SWITCH_IP', '192.168.1.3'),
        'type': 'switch',
        'location': 'Main Office',
        'is_active': True,
        'snmp_community': SNMP_COMMUNITY,
        'snmp_version': SNMP_VERSION
    }
]

# Default Services to Monitor
DEFAULT_SERVICES = [
    {
        'id': 'radius',
        'name': 'RADIUS Service',
        'type': 'radius',
        'host': os.getenv('RADIUS_HOST', 'localhost'),
        'port': int(os.getenv('RADIUS_PORT', '1812')),
        'is_active': True
    },
    {
        'id': 'dhcp',
        'name': 'DHCP Service',
        'type': 'dhcp',
        'host': os.getenv('DHCP_HOST', 'localhost'),
        'port': int(os.getenv('DHCP_PORT', '67')),
        'is_active': True
    },
    {
        'id': 'dns',
        'name': 'DNS Service',
        'type': 'dns',
        'host': os.getenv('DNS_HOST', 'localhost'),
        'port': int(os.getenv('DNS_PORT', '53')),
        'is_active': True
    },
    {
        'id': 'web-portal',
        'name': 'Web Portal',
        'type': 'http',
        'url': os.getenv('WEB_PORTAL_URL', 'http://localhost:8000'),
        'is_active': True
    }
]

# Network Performance Metrics to Collect
NETWORK_METRICS = [
    'latency',
    'packet_loss',
    'bandwidth_utilization',
    'connection_count',
    'interface_errors',
    'interface_discards'
]

# Service Metrics to Collect
SERVICE_METRICS = [
    'availability',
    'response_time',
    'error_rate',
    'request_count'
]

# Customer Usage Metrics to Collect
CUSTOMER_USAGE_METRICS = [
    'data_usage',
    'session_count',
    'session_duration',
    'authentication_events'
]
