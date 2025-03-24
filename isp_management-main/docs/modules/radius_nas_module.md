# RADIUS & NAS Module Documentation

## Overview

The RADIUS & NAS module provides comprehensive functionality for managing RADIUS authentication, authorization, and accounting (AAA) services within the ISP Management Platform. This module enables ISPs to control user access to network resources, manage sessions, apply bandwidth policies, and integrate with various Network Access Server (NAS) devices.

## Key Features

- **RADIUS Profile Management**: Create and manage RADIUS profiles for users
- **Authentication**: Validate user credentials against RADIUS profiles
- **Accounting**: Track user sessions, including start, update, and stop events
- **NAS Device Management**: Configure and manage Network Access Server devices
- **Vendor-Specific Attributes**: Support for vendor-specific RADIUS attributes
- **Bandwidth Policies**: Define and apply bandwidth limitations to user profiles
- **Dynamic CoA (Change of Authorization)**: Modify active sessions or disconnect users
- **Session Statistics**: Retrieve detailed statistics about user sessions

## API Endpoints

### RADIUS Profile Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/profiles` | Create a new RADIUS profile |
| GET | `/radius/profiles` | List all RADIUS profiles |
| GET | `/radius/profiles/{profile_id}` | Get a specific RADIUS profile |
| PUT | `/radius/profiles/{profile_id}` | Update a RADIUS profile |
| DELETE | `/radius/profiles/{profile_id}` | Delete a RADIUS profile |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/auth` | Authenticate a RADIUS user |

### Accounting

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/accounting/start` | Start a RADIUS accounting session |
| POST | `/radius/accounting/update` | Update a RADIUS accounting session |
| POST | `/radius/accounting/stop` | Stop a RADIUS accounting session |
| GET | `/radius/accounting/sessions` | List RADIUS accounting sessions |
| GET | `/radius/accounting/sessions/{session_id}` | Get a specific accounting session |
| GET | `/radius/accounting/statistics` | Get session statistics |
| GET | `/radius/accounting/user/{username}/sessions` | Get sessions for a specific user |

### NAS Device Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/nas` | Create a new NAS device |
| GET | `/radius/nas` | List all NAS devices |
| GET | `/radius/nas/{device_id}` | Get a specific NAS device |
| PUT | `/radius/nas/{device_id}` | Update a NAS device |
| DELETE | `/radius/nas/{device_id}` | Delete a NAS device |

### Vendor-Specific Attributes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/nas/vendor-attributes` | Create a new vendor-specific attribute |
| GET | `/radius/nas/vendor-attributes` | List vendor-specific attributes |
| GET | `/radius/nas/vendor-attributes/{attr_id}` | Get a specific vendor attribute |
| PUT | `/radius/nas/vendor-attributes/{attr_id}` | Update a vendor attribute |
| DELETE | `/radius/nas/vendor-attributes/{attr_id}` | Delete a vendor attribute |

### Bandwidth Policies

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/bandwidth-policies` | Create a new bandwidth policy |
| GET | `/radius/bandwidth-policies` | List all bandwidth policies |
| GET | `/radius/bandwidth-policies/{policy_id}` | Get a specific bandwidth policy |
| PUT | `/radius/bandwidth-policies/{policy_id}` | Update a bandwidth policy |
| DELETE | `/radius/bandwidth-policies/{policy_id}` | Delete a bandwidth policy |

### Profile Attributes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/profile-attributes` | Create a new profile attribute |
| GET | `/radius/profile-attributes` | Get all attributes for a profile |
| PUT | `/radius/profile-attributes/{attr_id}` | Update a profile attribute |
| DELETE | `/radius/profile-attributes/{attr_id}` | Delete a profile attribute |

### CoA (Change of Authorization)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/radius/coa` | Send a CoA request to a NAS device |
| POST | `/radius/disconnect-session/{session_id}` | Disconnect a specific user session |
| POST | `/radius/disconnect-user/{username}` | Disconnect all sessions for a user |
| GET | `/radius/coa-logs` | Get CoA logs |

## Authentication and Authorization

All administrative endpoints in this module require authentication using JWT tokens. The following roles have access:

- **Admin Users**: Full access to all endpoints
- **Regular Users**: Read-only access to their own profiles and sessions

## Data Models

### RadiusProfile

The `RadiusProfile` model represents a user's RADIUS authentication profile.

```python
class RadiusProfile(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    service_type = Column(String, nullable=True)
    simultaneous_use = Column(Integer, nullable=True)
    interim_interval = Column(Integer, nullable=True)
    session_timeout = Column(Integer, nullable=True)
    idle_timeout = Column(Integer, nullable=True)
    bandwidth_policy_id = Column(Integer, ForeignKey("radius_bandwidth_policies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### RadiusAccounting

The `RadiusAccounting` model tracks user session information.

```python
class RadiusAccounting(Base):
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("radius_profiles.id"), nullable=False)
    session_id = Column(String, unique=True, index=True, nullable=False)
    nas_id = Column(Integer, ForeignKey("nas_devices.id"), nullable=True)
    nas_ip_address = Column(String, nullable=False)
    nas_port_id = Column(String, nullable=True)
    framed_ip_address = Column(String, nullable=True)
    framed_protocol = Column(String, nullable=True)
    acct_status_type = Column(String, nullable=False)
    acct_authentic = Column(String, nullable=True)
    acct_session_time = Column(Integer, nullable=True)
    acct_input_octets = Column(BigInteger, nullable=True)
    acct_output_octets = Column(BigInteger, nullable=True)
    acct_input_packets = Column(BigInteger, nullable=True)
    acct_output_packets = Column(BigInteger, nullable=True)
    acct_terminate_cause = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=False)
    update_time = Column(DateTime, nullable=True)
    stop_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### NasDevice

The `NasDevice` model represents a Network Access Server device.

```python
class NasDevice(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip_address = Column(String, nullable=False, unique=True, index=True)
    type = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    model = Column(String, nullable=True)
    secret = Column(String, nullable=False)  # Encrypted shared secret
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### RadiusBandwidthPolicy

The `RadiusBandwidthPolicy` model defines bandwidth limitations for user profiles.

```python
class RadiusBandwidthPolicy(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    download_rate = Column(Integer, nullable=False)  # in kbps
    upload_rate = Column(Integer, nullable=False)    # in kbps
    burst_download_rate = Column(Integer, nullable=True)  # in kbps
    burst_upload_rate = Column(Integer, nullable=True)    # in kbps
    burst_threshold = Column(Integer, nullable=True)      # in bytes
    burst_time = Column(Integer, nullable=True)           # in seconds
    priority = Column(Integer, nullable=True)
    time_based_limits = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Usage Examples

### Creating a RADIUS Profile

```python
from modules.radius.schemas import RadiusProfileCreate
from modules.radius.services import RadiusService

profile_data = RadiusProfileCreate(
    user_id=1,
    username="user123",
    password="secure_password",
    service_type="Framed-User",
    simultaneous_use=1,
    session_timeout=3600,  # 1 hour
    bandwidth_policy_id=1
)

radius_service = RadiusService(db_session)
profile = radius_service.create_radius_profile(profile_data)
```

### Authenticating a User

```python
from modules.radius.schemas import RadiusAuthRequest
from modules.radius.services import RadiusService

auth_request = RadiusAuthRequest(
    username="user123",
    password="secure_password",
    nas_ip_address="192.168.1.1"
)

radius_service = RadiusService(db_session)
auth_response = radius_service.authenticate_user(auth_request)

if auth_response.status == "accept":
    # Authentication successful
    attributes = auth_response.attributes
else:
    # Authentication failed
    error_message = auth_response.message
```

### Creating a Bandwidth Policy

```python
from modules.radius.schemas import RadiusBandwidthPolicyCreate
from modules.radius.services import RadiusService

policy_data = RadiusBandwidthPolicyCreate(
    name="Basic Plan",
    description="10 Mbps download, 2 Mbps upload",
    download_rate=10240,  # 10 Mbps in kbps
    upload_rate=2048,     # 2 Mbps in kbps
    burst_download_rate=15360,  # 15 Mbps in kbps
    burst_upload_rate=3072,     # 3 Mbps in kbps
    burst_threshold=10485760,   # 10 MB in bytes
    burst_time=60,              # 60 seconds
    priority=5,
    is_active=True
)

radius_service = RadiusService(db_session)
policy = radius_service.create_bandwidth_policy(policy_data)
```

### Sending a CoA Request

```python
from modules.radius.schemas import RadiusCoARequest
from modules.radius.services import RadiusService

coa_request = RadiusCoARequest(
    profile_id=1,
    nas_id=2,
    session_id="session123",
    coa_type="update",
    attributes={
        "Session-Timeout": 7200,  # Update session timeout to 2 hours
        "Idle-Timeout": 1800      # Update idle timeout to 30 minutes
    }
)

radius_service = RadiusService(db_session)
coa_response = radius_service.send_coa_request(coa_request)

if coa_response.result == "success":
    # CoA request successful
    pass
else:
    # CoA request failed
    error_message = coa_response.error_message
```

### Disconnecting a User

```python
from modules.radius.services import RadiusService

radius_service = RadiusService(db_session)
result = radius_service.disconnect_user("user123")

print(f"Total sessions: {result['total_sessions']}")
print(f"Successful disconnects: {result['successful_disconnects']}")
print(f"Failed disconnects: {result['failed_disconnects']}")
```

## Security Considerations

1. **Shared Secrets**: RADIUS shared secrets are encrypted in the database using the `RADIUS_SECRET_KEY` environment variable.
2. **Password Hashing**: User passwords are securely hashed before storage.
3. **Access Control**: Role-based access control ensures that only authorized users can access sensitive operations.
4. **Input Validation**: All user input is validated to prevent SQL injection and other vulnerabilities.

## Integration with Other Modules

The RADIUS & NAS module integrates with the following modules:

- **User Management**: Links RADIUS profiles to user accounts
- **Billing**: Provides usage data for billing calculations
- **Monitoring**: Supplies session statistics for monitoring dashboards

## Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Verify that the username and password are correct
   - Check if the user's profile is active
   - Ensure the NAS device is properly configured with the correct shared secret

2. **CoA Failures**:
   - Verify that the NAS device supports CoA
   - Check if the NAS device is reachable on the network
   - Ensure the correct shared secret is being used

3. **Session Management Issues**:
   - Verify that accounting start/stop packets are being received
   - Check for duplicate session IDs
   - Ensure that the NAS device is properly configured to send accounting updates

### Logging

The module uses structured logging to facilitate troubleshooting:

- Authentication attempts are logged with username and result
- Accounting events are logged with session ID and status
- CoA requests are logged with target NAS, profile, and result

## Performance Considerations

1. **Database Indexing**: Key fields are indexed to ensure fast lookups
2. **Connection Pooling**: Database connections are pooled for efficient resource usage
3. **Caching**: Frequently accessed data can be cached using Redis
4. **Batch Processing**: Bulk operations are used where appropriate to minimize database round-trips

## Future Enhancements

1. **RADIUS Server Integration**: Direct integration with FreeRADIUS or other RADIUS servers
2. **Multi-factor Authentication**: Support for additional authentication factors
3. **Enhanced Reporting**: More detailed reports on user sessions and bandwidth usage
4. **Policy-based Routing**: Support for policy-based routing based on user attributes
5. **IPv6 Support**: Full support for IPv6 addressing in all components
