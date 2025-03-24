# Tariff Enforcement Module

## Overview

The Tariff Enforcement Module is responsible for managing service plans, enforcing usage policies, and integrating with billing and RADIUS systems. It enables ISPs to define different service tiers, track customer usage, enforce Fair Usage Policies (FUP), and handle plan upgrades/downgrades.

## Features

### Plan Management
- Define and manage service plans with different attributes (speed, data caps, pricing)
- Create, update, and delete tariff plans
- Assign plans to users and track plan history

### Usage Capping
- Enforce data limits and Fair Usage Policies (FUP)
- Track user bandwidth consumption
- Apply throttling when thresholds are exceeded

### Billing Integration
- Calculate usage-based charges and overage fees
- Handle prorated billing for plan changes
- Support different billing cycles (monthly, quarterly, yearly)

### Bandwidth Throttling
- Apply speed limits based on plan tiers
- Synchronize RADIUS policies with tariff plans
- Support for time-based restrictions

### Plan Upgrades/Downgrades
- Handle plan changes with appropriate billing adjustments
- Track tariff plan changes for users
- Schedule future plan changes

### Notification System
- Alert users when approaching data limits
- Notify about plan changes and billing events

## API Endpoints

### Tariff Plan Management

#### GET `/tariff/plans`
List all available tariff plans.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Basic Plan",
    "description": "Entry-level internet plan",
    "price": 29.99,
    "billing_cycle": "monthly",
    "download_speed": 10,
    "upload_speed": 2,
    "data_cap": 100000000000,
    "is_active": true,
    "created_at": "2023-06-01T12:00:00",
    "updated_at": "2023-06-01T12:00:00"
  }
]
```

#### GET `/tariff/plans/{plan_id}`
Get details of a specific tariff plan.

**Response:**
```json
{
  "id": 1,
  "name": "Basic Plan",
  "description": "Entry-level internet plan",
  "price": 29.99,
  "billing_cycle": "monthly",
  "download_speed": 10,
  "upload_speed": 2,
  "data_cap": 100000000000,
  "fup_threshold": 80000000000,
  "throttle_speed_download": 2,
  "throttle_speed_upload": 1,
  "radius_policy_id": 1,
  "throttled_radius_policy_id": 2,
  "time_restrictions": null,
  "features": {
    "overage_rate": 10.0,
    "static_ip": false
  },
  "is_active": true,
  "created_at": "2023-06-01T12:00:00",
  "updated_at": "2023-06-01T12:00:00"
}
```

#### POST `/tariff/plans`
Create a new tariff plan.

**Request:**
```json
{
  "name": "Premium Plan",
  "description": "High-speed internet plan",
  "price": 59.99,
  "billing_cycle": "monthly",
  "download_speed": 100,
  "upload_speed": 20,
  "data_cap": 500000000000,
  "fup_threshold": 400000000000,
  "throttle_speed_download": 10,
  "throttle_speed_upload": 5,
  "radius_policy_id": 3,
  "throttled_radius_policy_id": 4,
  "features": {
    "overage_rate": 5.0,
    "static_ip": true
  }
}
```

**Response:**
```json
{
  "id": 2,
  "name": "Premium Plan",
  "description": "High-speed internet plan",
  "price": 59.99,
  "billing_cycle": "monthly",
  "download_speed": 100,
  "upload_speed": 20,
  "data_cap": 500000000000,
  "fup_threshold": 400000000000,
  "throttle_speed_download": 10,
  "throttle_speed_upload": 5,
  "radius_policy_id": 3,
  "throttled_radius_policy_id": 4,
  "time_restrictions": null,
  "features": {
    "overage_rate": 5.0,
    "static_ip": true
  },
  "is_active": true,
  "created_at": "2023-06-01T12:00:00",
  "updated_at": "2023-06-01T12:00:00"
}
```

#### PUT `/tariff/plans/{plan_id}`
Update an existing tariff plan.

**Request:**
```json
{
  "price": 69.99,
  "download_speed": 150,
  "upload_speed": 30
}
```

**Response:**
```json
{
  "id": 2,
  "name": "Premium Plan",
  "description": "High-speed internet plan",
  "price": 69.99,
  "billing_cycle": "monthly",
  "download_speed": 150,
  "upload_speed": 30,
  "data_cap": 500000000000,
  "fup_threshold": 400000000000,
  "throttle_speed_download": 10,
  "throttle_speed_upload": 5,
  "radius_policy_id": 3,
  "throttled_radius_policy_id": 4,
  "time_restrictions": null,
  "features": {
    "overage_rate": 5.0,
    "static_ip": true
  },
  "is_active": true,
  "created_at": "2023-06-01T12:00:00",
  "updated_at": "2023-06-02T10:30:00"
}
```

#### DELETE `/tariff/plans/{plan_id}`
Delete a tariff plan (soft delete).

**Response:**
```json
{
  "status": "success",
  "message": "Tariff plan deleted successfully"
}
```

### User Plan Management

#### POST `/tariff/plans/{plan_id}/assign`
Assign a tariff plan to a user.

**Request:**
```json
{
  "user_id": 123,
  "status": "active",
  "start_date": "2023-06-01T00:00:00",
  "end_date": null
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Plan assigned successfully",
  "user_plan_id": 45,
  "user_id": 123,
  "plan_id": 2,
  "start_date": "2023-06-01T00:00:00",
  "end_date": null
}
```

#### GET `/tariff/users/{user_id}/plan`
Get the active tariff plan for a user.

**Response:**
```json
{
  "user_id": 123,
  "plan_id": 2,
  "plan_name": "Premium Plan",
  "plan_description": "High-speed internet plan",
  "price": 69.99,
  "billing_cycle": "monthly",
  "download_speed": 150,
  "upload_speed": 30,
  "data_cap": 500000000000,
  "data_used": 125000000000,
  "percentage_used": 25.0,
  "is_throttled": false,
  "status": "active",
  "current_cycle_start": "2023-06-01T00:00:00",
  "current_cycle_end": "2023-07-01T00:00:00"
}
```

#### PUT `/tariff/users/{user_id}/plan/{plan_id}`
Update a user's tariff plan.

**Request:**
```json
{
  "status": "suspended",
  "end_date": "2023-07-15T00:00:00"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "User tariff plan updated successfully",
  "user_plan_id": 45,
  "user_id": 123,
  "plan_id": 2,
  "updated_fields": ["status", "end_date"]
}
```

#### DELETE `/tariff/users/{user_id}/plan`
Cancel a user's active tariff plan.

**Response:**
```json
{
  "status": "success",
  "message": "User tariff plan cancelled successfully",
  "user_id": 123
}
```

### Usage Tracking and Policy Enforcement

#### POST `/tariff/usage/record`
Record usage data for a user's tariff plan.

**Request:**
```json
{
  "user_tariff_plan_id": 45,
  "download_bytes": 1500000000,
  "upload_bytes": 500000000,
  "source": "radius",
  "session_id": "RADIUS-SESSION-12345"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Usage data recorded successfully",
  "record_id": 789,
  "user_tariff_plan_id": 45,
  "download_bytes": 1500000000,
  "upload_bytes": 500000000,
  "total_bytes": 2000000000
}
```

#### POST `/tariff/usage/check`
Check a user's usage against their plan limits.

**Request:**
```json
{
  "user_id": 123,
  "download_bytes": 0,
  "upload_bytes": 0,
  "session_id": "RADIUS-SESSION-12345"
}
```

**Response:**
```json
{
  "user_id": 123,
  "tariff_plan_id": 2,
  "plan_name": "Premium Plan",
  "status": "ok",
  "current_usage": 127000000000,
  "data_cap": 500000000000,
  "percentage_used": 25.4,
  "actions_triggered": [],
  "message": "Using 127.00 GB of 500.00 GB (25.4%)"
}
```

#### GET `/tariff/users/{user_id}/bandwidth-policy`
Get the bandwidth policy for a user based on their tariff plan.

**Response:**
```json
{
  "user_id": 123,
  "download_speed": 150,
  "upload_speed": 30,
  "is_throttled": false,
  "session_timeout": null,
  "additional_attributes": {}
}
```

#### POST `/tariff/users/{user_id}/reset-cycle`
Reset the usage cycle for a user's tariff plan.

**Response:**
```json
{
  "status": "success",
  "message": "Usage cycle reset successfully",
  "user_id": 123
}
```

#### POST `/tariff/process-scheduled-changes`
Process scheduled tariff plan changes that are due.

**Response:**
```json
{
  "status": "success",
  "message": "Processed 3 of 5 scheduled changes",
  "results": {
    "total": 5,
    "processed": 3,
    "failed": 2,
    "errors": [
      "Error processing change 12: User not found",
      "Error processing change 15: Plan not found"
    ]
  }
}
```

#### POST `/tariff/users/{user_id}/calculate-overage`
Calculate any overage fees based on usage and plan.

**Request:**
```json
{
  "usage_mb": 550000
}
```

**Response:**
```json
{
  "user_id": 123,
  "usage_mb": 550000,
  "overage_fee": 250.0
}
```

#### POST `/tariff/check-fup`
Check if a user has crossed the FUP threshold and should be throttled.

**Request:**
```json
{
  "user_id": 123,
  "current_usage_bytes": 410000000000
}
```

**Response:**
```json
{
  "user_id": 123,
  "plan_id": 2,
  "fup_threshold": 400000000000,
  "current_usage": 410000000000,
  "threshold_exceeded": true,
  "action": "throttle",
  "message": "FUP threshold exceeded. Connection will be throttled."
}
```

## Data Models

### TariffPlan
Represents a service plan with pricing, bandwidth, and usage limits.

```python
class TariffPlan(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    billing_cycle = Column(String, default="monthly")  # monthly, quarterly, yearly
    download_speed = Column(Integer, nullable=False)  # Mbps
    upload_speed = Column(Integer, nullable=False)  # Mbps
    data_cap = Column(BigInteger, nullable=True)  # bytes, null means unlimited
    fup_threshold = Column(BigInteger, nullable=True)  # bytes
    throttle_speed_download = Column(Integer, nullable=True)  # Mbps
    throttle_speed_upload = Column(Integer, nullable=True)  # Mbps
    radius_policy_id = Column(Integer, nullable=True)
    throttled_radius_policy_id = Column(Integer, nullable=True)
    time_restrictions = Column(JSON, nullable=True)
    features = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### UserTariffPlan
Represents the assignment of a tariff plan to a user.

```python
class UserTariffPlan(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tariff_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    status = Column(String, default="active")  # active, suspended, cancelled
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    current_cycle_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_cycle_end = Column(DateTime, nullable=True)
    data_used = Column(BigInteger, default=0)  # bytes
    is_throttled = Column(Boolean, default=False)
    throttled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="tariff_plans")
    tariff_plan = relationship("TariffPlan")
    usage_records = relationship("UserUsageRecord", back_populates="user_tariff_plan")
```

### UserUsageRecord
Represents a usage record for a user's tariff plan.

```python
class UserUsageRecord(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_tariff_plan_id = Column(Integer, ForeignKey("user_tariff_plans.id"), nullable=False)
    download_bytes = Column(BigInteger, default=0)
    upload_bytes = Column(BigInteger, default=0)
    total_bytes = Column(BigInteger, default=0)
    source = Column(String, nullable=False)  # radius, manual, etc.
    session_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user_tariff_plan = relationship("UserTariffPlan", back_populates="usage_records")
```

### TariffPlanChange
Represents a change in a user's tariff plan.

```python
class TariffPlanChange(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    previous_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    new_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    change_type = Column(String, nullable=False)  # upgrade, downgrade, switch
    requested_at = Column(DateTime, default=datetime.utcnow)
    effective_date = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending, processed, cancelled
    reason = Column(String, nullable=True)
    prorated_credit = Column(Numeric(10, 2), nullable=True)
    prorated_charge = Column(Numeric(10, 2), nullable=True)
    
    user = relationship("User")
    previous_plan = relationship("TariffPlan", foreign_keys=[previous_plan_id])
    new_plan = relationship("TariffPlan", foreign_keys=[new_plan_id])
```

### TariffPolicyAction
Represents a policy action to be triggered based on usage.

```python
class TariffPolicyAction(Base):
    id = Column(Integer, primary_key=True, index=True)
    tariff_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    trigger_type = Column(String, nullable=False)  # data_cap, fup, time_restriction
    threshold_value = Column(BigInteger, nullable=True)  # bytes
    action_type = Column(String, nullable=False)  # notify, throttle, block, charge
    action_params = Column(JSON, nullable=True)
    notification_template_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tariff_plan = relationship("TariffPlan")
```

## Usage Examples

### Creating a New Tariff Plan

```python
from modules.tariff.services import TariffService
from modules.tariff.schemas import TariffPlanCreate

# Create a new tariff plan
plan_data = TariffPlanCreate(
    name="Gold Plan",
    description="High-speed internet with unlimited data",
    price=79.99,
    billing_cycle="monthly",
    download_speed=250,
    upload_speed=50,
    data_cap=None,  # Unlimited data
    features={
        "static_ip": True,
        "priority_support": True
    }
)

tariff_service = TariffService(db_session)
new_plan = tariff_service.create_tariff_plan(plan_data)
print(f"Created plan: {new_plan.name} with ID: {new_plan.id}")
```

### Assigning a Plan to a User

```python
from modules.tariff.services import TariffService
from modules.tariff.schemas import UserTariffPlanCreate
from datetime import datetime, timedelta

# Assign a plan to a user
start_date = datetime.utcnow()
assignment_data = UserTariffPlanCreate(
    user_id=123,
    tariff_plan_id=2,
    status="active",
    start_date=start_date,
    end_date=start_date + timedelta(days=365)  # 1-year contract
)

tariff_service = TariffService(db_session)
user_plan = tariff_service.assign_plan_to_user(assignment_data)
print(f"Assigned plan {user_plan.tariff_plan_id} to user {user_plan.user_id}")
```

### Recording Usage and Checking FUP

```python
from modules.tariff.services import TariffService
from modules.tariff.schemas import UserUsageRecordCreate, FUPThresholdCheck

# Record usage
usage_data = UserUsageRecordCreate(
    user_tariff_plan_id=45,
    download_bytes=2000000000,  # 2 GB
    upload_bytes=500000000,     # 500 MB
    source="radius",
    session_id="SESSION-12345"
)

tariff_service = TariffService(db_session)
usage_record = tariff_service.record_usage(usage_data)
print(f"Recorded {usage_record.total_bytes} bytes of usage")

# Check FUP threshold
check_data = FUPThresholdCheck(
    user_id=123,
    current_usage_bytes=user_plan.data_used
)

fup_result = tariff_service.check_fup_threshold(check_data)
if fup_result.threshold_exceeded:
    print(f"FUP threshold exceeded. Action: {fup_result.action}")
else:
    print("FUP threshold not exceeded")
```

### Processing Scheduled Plan Changes

```python
from modules.tariff.services import TariffService

# Process scheduled plan changes
tariff_service = TariffService(db_session)
results = tariff_service.process_scheduled_plan_changes()

print(f"Processed {results['processed']} of {results['total']} scheduled changes")
if results['failed'] > 0:
    print(f"Failed to process {results['failed']} changes:")
    for error in results['errors']:
        print(f"  - {error}")
```

## Integration with Other Modules

### RADIUS Integration

The Tariff Enforcement Module integrates with the RADIUS & NAS Module to enforce bandwidth policies and usage limits:

1. When a user is assigned a tariff plan, the corresponding RADIUS policy is applied to their profile
2. When a user exceeds their FUP threshold, throttling is applied via RADIUS CoA (Change of Authorization)
3. Usage data from RADIUS accounting is recorded and used to track data consumption

### Billing Integration

The module integrates with the Billing Module to handle:

1. Plan charges based on the tariff plan price and billing cycle
2. Overage charges when users exceed their data caps
3. Prorated billing when users change plans mid-cycle

## Security Considerations

1. **Access Control**: Only administrators and staff members can create, update, or delete tariff plans
2. **Data Validation**: All input data is validated using Pydantic schemas
3. **Audit Logging**: All changes to tariff plans and user assignments are logged
4. **Rate Limiting**: API endpoints are rate-limited to prevent abuse

## Performance Considerations

1. **Caching**: Frequently accessed tariff plan data is cached to reduce database load
2. **Batch Processing**: Usage records are processed in batches to improve performance
3. **Indexing**: Database tables are properly indexed for efficient queries
4. **Asynchronous Processing**: Long-running tasks like plan changes are processed asynchronously

## Troubleshooting

### Common Issues

1. **Throttling Not Applied**: Check if the tariff plan has a valid throttled_radius_policy_id
2. **Usage Not Recorded**: Verify that the RADIUS accounting integration is properly configured
3. **Plan Changes Not Processed**: Check the scheduled tasks configuration and logs

### Logging

The module uses structured logging to facilitate troubleshooting:

```python
# Example log output
{
    "timestamp": "2023-06-01T12:34:56",
    "level": "INFO",
    "message": "Applied throttling for user 123, session RADIUS-SESSION-12345",
    "module": "tariff.services",
    "function": "_apply_throttling",
    "user_id": 123,
    "plan_id": 2,
    "policy_id": 4
}
```

## Future Enhancements

1. **Time-Based Policies**: Implement time-of-day restrictions and different speeds during peak/off-peak hours
2. **Family Plans**: Support for shared data caps across multiple users
3. **Usage Forecasting**: Predict when users will exceed their data caps based on usage patterns
4. **Self-Service Portal**: Allow users to view their usage and upgrade/downgrade plans themselves
5. **Rollover Data**: Support for unused data to roll over to the next billing cycle
