# Network Management Module

The Network Management Module is a comprehensive solution for managing network resources and device configurations within the ISP Management Platform. This module provides tools for IP pool management, device configuration, firmware updates, and network topology visualization.

## Features

### Device Management
- Create, update, and delete network devices
- Track device status and connectivity
- Group devices for easier management
- Store device credentials securely

### IP Pool Management
- Create and manage IP address pools
- Allocate and release IP addresses
- Track IP address usage and assignment
- Support for different pool types (customer, infrastructure, etc.)

### Configuration Management
- Create and manage configuration templates
- Generate device configurations from templates
- Apply configurations to devices
- Track configuration history and changes

### Firmware Management
- Upload and manage firmware versions
- Schedule firmware updates for devices
- Backup device configurations before updates
- Track update history and status

### Network Topology
- Discover network topology automatically
- Visualize network infrastructure
- Analyze network metrics and identify bottlenecks
- Export topology in various formats

## Installation

The Network Management Module is integrated into the ISP Management Platform. No separate installation is required.

## Dependencies

- SQLAlchemy for database interactions
- Jinja2 for configuration templating
- NetworkX for topology visualization and analysis
- Netmiko for device connectivity
- NAPALM for multi-vendor device management

## Usage

### Device Management

```python
from modules.network.services import DeviceService
from modules.network.models import DeviceType

# Create a device service
device_service = DeviceService()

# Create a new device
device = await device_service.create_device(
    session=session,
    name="Router-01",
    hostname="router01.example.com",
    ip_address="192.168.1.1",
    device_type=DeviceType.ROUTER,
    username="admin",
    password="secure_password"
)

# Get a device by ID
device = await device_service.get_device(session, device_id=1)

# Update a device
updated_device = await device_service.update_device(
    session=session,
    device_id=1,
    name="Updated-Router-01"
)

# Delete a device
await device_service.delete_device(session, device_id=1)
```

### IP Pool Management

```python
from modules.network.ip_pool_service import IPPoolService
from modules.network.models import IPPoolType

# Create an IP pool service
ip_pool_service = IPPoolService()

# Create a new IP pool
pool = await ip_pool_service.create_pool(
    session=session,
    name="Customer Network",
    network="192.168.0.0/24",
    pool_type=IPPoolType.CUSTOMER,
    gateway="192.168.0.1",
    dns_servers=["8.8.8.8", "8.8.4.4"]
)

# Allocate an IP address
ip_address = await ip_pool_service.allocate_ip(
    session=session,
    pool_id=1,
    assigned_to_id=123,
    assigned_to_type="customer"
)

# Release an IP address
released_ip = await ip_pool_service.release_ip(
    session=session,
    ip_address="192.168.0.10"
)

# Get pool usage statistics
usage = await ip_pool_service.get_pool_usage(session, pool_id=1)
```

### Configuration Management

```python
from modules.network.configuration_service import ConfigurationService
from modules.network.models import DeviceType

# Create a configuration service
config_service = ConfigurationService()

# Create a configuration template
template = await config_service.create_template(
    session=session,
    name="Cisco Router Base Config",
    device_type=DeviceType.ROUTER,
    template_content="hostname {{ hostname }}\ninterface GigabitEthernet0/0\n ip address {{ ip }} {{ mask }}",
    version="1.0.0",
    variables={"hostname": "string", "ip": "ipv4", "mask": "ipv4_netmask"}
)

# Generate a configuration from a template
config = await config_service.generate_configuration(
    session=session,
    template_id=1,
    variables={"hostname": "router01", "ip": "192.168.1.1", "mask": "255.255.255.0"}
)

# Create a device configuration
device_config = await config_service.create_device_configuration(
    session=session,
    device_id=1,
    config_content=config,
    version="1.0.0"
)

# Apply a configuration to a device
applied_config = await config_service.apply_configuration(
    session=session,
    config_id=1,
    applied_by="admin"
)
```

### Firmware Management

```python
from modules.network.firmware_service import FirmwareService
from modules.network.models import DeviceType

# Create a firmware service
firmware_service = FirmwareService(firmware_storage_path="/data/firmware")

# Upload a firmware version
with open("firmware.bin", "rb") as f:
    firmware = await firmware_service.upload_firmware(
        session=session,
        version="16.9.3",
        device_type=DeviceType.ROUTER,
        manufacturer="Cisco",
        model="ASR-9000",
        firmware_file=f,
        release_notes="Bug fixes and security updates"
    )

# Schedule a firmware update
update_task = await firmware_service.schedule_update(
    session=session,
    device_id=1,
    firmware_id=1,
    scheduled_time=datetime(2023, 1, 1, 12, 0, 0)
)

# Get firmware update status
status = await firmware_service.get_update_status(session, task_id=1)
```

### Network Topology

```python
from modules.network.topology_service import TopologyService

# Create a topology service
topology_service = TopologyService()

# Discover network topology
topology = await topology_service.discover_topology(
    session=session,
    root_device_id=1,
    max_depth=5
)

# Export topology
export_data = await topology_service.export_topology(
    session=session,
    format="json"
)

# Analyze topology
analysis = await topology_service.analyze_topology(session)

# Get device neighbors
neighbors = await topology_service.get_device_neighbors(
    session=session,
    device_id=1,
    max_depth=1
)
```

## API Endpoints

The Network Management Module exposes RESTful API endpoints for all its functionality. See the API documentation for details.

## Testing

The module includes comprehensive unit tests to ensure reliability and functionality. Run the tests using pytest:

```bash
pytest tests/modules/network/
```

## Security Considerations

- Device credentials are stored securely and not exposed in API responses
- Access to network management functionality is controlled by role-based permissions
- All API endpoints require authentication
- Sensitive operations (e.g., applying configurations, scheduling firmware updates) are logged for audit purposes

## Integration with Other Modules

The Network Management Module integrates with other modules in the ISP Management Platform:

- **Billing Module**: Associates IP addresses with customer accounts
- **RADIUS Module**: Uses IP pools for DHCP and PPPoE services
- **Monitoring Module**: Collects and analyzes network performance data
- **Reseller Module**: Allows resellers to manage their own network segments

## Future Enhancements

- Automated network discovery
- Configuration compliance checking
- Network traffic analysis
- Bandwidth management
- Integration with cloud networking services
