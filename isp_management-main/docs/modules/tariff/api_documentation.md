# Tariff Enforcement Module API Documentation

## Overview

The Tariff Enforcement Module provides a comprehensive set of API endpoints for managing tariff plans, user assignments, usage tracking, and policy enforcement. This document outlines the available endpoints, their parameters, and expected responses.

## Base URL

All API endpoints are relative to the base URL of the ISP Management Platform API:

```
http://localhost:8000/tariff
```

## Authentication

All API endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <token>
```

## Endpoints

### Tariff Plans

#### List All Tariff Plans

```
GET /plans
```

**Description**: Retrieves a list of all available tariff plans.

**Query Parameters**:
- `active_only` (boolean, optional): If true, returns only active plans.
- `page` (integer, optional): Page number for pagination.
- `page_size` (integer, optional): Number of items per page.

**Response**:
```json
{
  "items": [
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
      "radius_policy_id": 101,
      "throttled_radius_policy_id": 102,
      "time_restrictions": null,
      "features": {
        "static_ip": false,
        "priority_support": false
      },
      "is_active": true,
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "pages": 1
}
```

#### Get Tariff Plan

```
GET /plans/{plan_id}
```

**Description**: Retrieves a specific tariff plan by ID.

**Path Parameters**:
- `plan_id` (integer, required): ID of the tariff plan.

**Response**:
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
  "radius_policy_id": 101,
  "throttled_radius_policy_id": 102,
  "time_restrictions": null,
  "features": {
    "static_ip": false,
    "priority_support": false
  },
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

#### Create Tariff Plan

```
POST /plans
```

**Description**: Creates a new tariff plan.

**Permissions**: Requires admin role.

**Request Body**:
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
  "radius_policy_id": 103,
  "throttled_radius_policy_id": 104,
  "time_restrictions": null,
  "features": {
    "static_ip": true,
    "priority_support": true
  },
  "is_active": true
}
```

**Response**:
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
  "radius_policy_id": 103,
  "throttled_radius_policy_id": 104,
  "time_restrictions": null,
  "features": {
    "static_ip": true,
    "priority_support": true
  },
  "is_active": true,
  "created_at": "2023-01-02T00:00:00Z",
  "updated_at": "2023-01-02T00:00:00Z"
}
```

#### Update Tariff Plan

```
PUT /plans/{plan_id}
```

**Description**: Updates an existing tariff plan.

**Permissions**: Requires admin role.

**Path Parameters**:
- `plan_id` (integer, required): ID of the tariff plan.

**Request Body**:
```json
{
  "name": "Premium Plan Plus",
  "description": "Enhanced high-speed internet plan",
  "price": 69.99,
  "billing_cycle": "monthly",
  "download_speed": 150,
  "upload_speed": 30,
  "data_cap": 750000000000,
  "fup_threshold": 600000000000,
  "throttle_speed_download": 15,
  "throttle_speed_upload": 7,
  "radius_policy_id": 105,
  "throttled_radius_policy_id": 106,
  "time_restrictions": null,
  "features": {
    "static_ip": true,
    "priority_support": true,
    "premium_content": true
  },
  "is_active": true
}
```

**Response**:
```json
{
  "id": 2,
  "name": "Premium Plan Plus",
  "description": "Enhanced high-speed internet plan",
  "price": 69.99,
  "billing_cycle": "monthly",
  "download_speed": 150,
  "upload_speed": 30,
  "data_cap": 750000000000,
  "fup_threshold": 600000000000,
  "throttle_speed_download": 15,
  "throttle_speed_upload": 7,
  "radius_policy_id": 105,
  "throttled_radius_policy_id": 106,
  "time_restrictions": null,
  "features": {
    "static_ip": true,
    "priority_support": true,
    "premium_content": true
  },
  "is_active": true,
  "created_at": "2023-01-02T00:00:00Z",
  "updated_at": "2023-01-03T00:00:00Z"
}
```

#### Delete Tariff Plan

```
DELETE /plans/{plan_id}
```

**Description**: Deletes a tariff plan. This will set the plan as inactive rather than permanently deleting it.

**Permissions**: Requires admin role.

**Path Parameters**:
- `plan_id` (integer, required): ID of the tariff plan.

**Response**:
```json
{
  "message": "Tariff plan deactivated successfully"
}
```

### User Tariff Plans

#### Assign Plan to User

```
POST /plans/{plan_id}/assign
```

**Description**: Assigns a tariff plan to a user.

**Permissions**: Requires admin role.

**Path Parameters**:
- `plan_id` (integer, required): ID of the tariff plan.

**Request Body**:
```json
{
  "user_id": 123,
  "start_date": "2023-02-01T00:00:00Z",
  "end_date": "2024-02-01T00:00:00Z"
}
```

**Response**:
```json
{
  "id": 1,
  "user_id": 123,
  "tariff_plan_id": 2,
  "status": "active",
  "start_date": "2023-02-01T00:00:00Z",
  "end_date": "2024-02-01T00:00:00Z",
  "current_cycle_start": "2023-02-01T00:00:00Z",
  "current_cycle_end": "2023-03-01T00:00:00Z",
  "data_used": 0,
  "is_throttled": false,
  "throttled_at": null,
  "created_at": "2023-02-01T00:00:00Z",
  "updated_at": "2023-02-01T00:00:00Z"
}
```

#### Get User's Tariff Plan

```
GET /users/{user_id}/plan
```

**Description**: Retrieves the active tariff plan for a user.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Response**:
```json
{
  "id": 1,
  "user_id": 123,
  "tariff_plan_id": 2,
  "plan_id": 2,
  "plan_name": "Premium Plan Plus",
  "plan_description": "Enhanced high-speed internet plan",
  "price": 69.99,
  "billing_cycle": "monthly",
  "download_speed": 150,
  "upload_speed": 30,
  "data_cap": 750000000000,
  "fup_threshold": 600000000000,
  "status": "active",
  "start_date": "2023-02-01T00:00:00Z",
  "end_date": "2024-02-01T00:00:00Z",
  "current_cycle_start": "2023-02-01T00:00:00Z",
  "current_cycle_end": "2023-03-01T00:00:00Z",
  "data_used": 25000000000,
  "percentage_used": 3.33,
  "is_throttled": false,
  "throttled_at": null,
  "days_remaining": 28
}
```

#### Update User's Tariff Plan

```
PUT /users/{user_id}/plan/{assignment_id}
```

**Description**: Updates a user's tariff plan assignment.

**Permissions**: Requires admin role.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.
- `assignment_id` (integer, required): ID of the tariff plan assignment.

**Request Body**:
```json
{
  "status": "suspended",
  "end_date": "2023-12-01T00:00:00Z"
}
```

**Response**:
```json
{
  "id": 1,
  "user_id": 123,
  "tariff_plan_id": 2,
  "status": "suspended",
  "start_date": "2023-02-01T00:00:00Z",
  "end_date": "2023-12-01T00:00:00Z",
  "current_cycle_start": "2023-02-01T00:00:00Z",
  "current_cycle_end": "2023-03-01T00:00:00Z",
  "data_used": 25000000000,
  "is_throttled": false,
  "throttled_at": null,
  "created_at": "2023-02-01T00:00:00Z",
  "updated_at": "2023-02-15T00:00:00Z"
}
```

#### Cancel User's Tariff Plan

```
DELETE /users/{user_id}/plan
```

**Description**: Cancels a user's active tariff plan.

**Permissions**: Requires admin role.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Response**:
```json
{
  "message": "User tariff plan cancelled successfully"
}
```

#### Change User's Tariff Plan

```
POST /users/{user_id}/change-plan
```

**Description**: Changes a user's tariff plan to a new plan.

**Permissions**: Requires admin role or user can change their own plan.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Request Body**:
```json
{
  "new_plan_id": 3,
  "effective_date": "2023-03-01T00:00:00Z",
  "reason": "User requested upgrade"
}
```

**Response**:
```json
{
  "id": 1,
  "user_id": 123,
  "previous_plan_id": 2,
  "new_plan_id": 3,
  "change_type": "upgrade",
  "requested_at": "2023-02-15T00:00:00Z",
  "effective_date": "2023-03-01T00:00:00Z",
  "processed_at": null,
  "status": "pending",
  "reason": "User requested upgrade",
  "prorated_credit": null,
  "prorated_charge": 15.00
}
```

#### Reset User's Usage Cycle

```
POST /users/{user_id}/reset-cycle
```

**Description**: Resets the usage cycle for a user's tariff plan.

**Permissions**: Requires admin role.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Response**:
```json
{
  "message": "Usage cycle reset successfully",
  "previous_cycle_start": "2023-02-01T00:00:00Z",
  "previous_cycle_end": "2023-03-01T00:00:00Z",
  "new_cycle_start": "2023-03-01T00:00:00Z",
  "new_cycle_end": "2023-04-01T00:00:00Z",
  "previous_data_used": 25000000000,
  "new_data_used": 0
}
```

#### Get User's Usage History

```
GET /users/{user_id}/usage-history
```

**Description**: Retrieves the usage history for a user.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Query Parameters**:
- `start_date` (string, optional): Start date for filtering (ISO format).
- `end_date` (string, optional): End date for filtering (ISO format).
- `page` (integer, optional): Page number for pagination.
- `page_size` (integer, optional): Number of items per page.

**Response**:
```json
{
  "items": [
    {
      "id": 1,
      "user_tariff_plan_id": 1,
      "download_bytes": 15000000000,
      "upload_bytes": 5000000000,
      "total_bytes": 20000000000,
      "source": "radius",
      "session_id": "session123",
      "timestamp": "2023-02-10T12:00:00Z"
    },
    {
      "id": 2,
      "user_tariff_plan_id": 1,
      "download_bytes": 3000000000,
      "upload_bytes": 2000000000,
      "total_bytes": 5000000000,
      "source": "radius",
      "session_id": "session124",
      "timestamp": "2023-02-11T14:30:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 10,
  "pages": 1
}
```

#### Get User's Scheduled Plan Changes

```
GET /users/{user_id}/scheduled-changes
```

**Description**: Retrieves the scheduled plan changes for a user.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Response**:
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 123,
      "previous_plan_id": 2,
      "previous_plan_name": "Premium Plan Plus",
      "new_plan_id": 3,
      "new_plan_name": "Ultimate Plan",
      "change_type": "upgrade",
      "requested_at": "2023-02-15T00:00:00Z",
      "effective_date": "2023-03-01T00:00:00Z",
      "processed_at": null,
      "status": "pending",
      "reason": "User requested upgrade",
      "prorated_credit": null,
      "prorated_charge": 15.00
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "pages": 1
}
```

#### Cancel Scheduled Plan Change

```
DELETE /scheduled-changes/{change_id}
```

**Description**: Cancels a scheduled plan change.

**Permissions**: Requires admin role or user can cancel their own scheduled changes.

**Path Parameters**:
- `change_id` (integer, required): ID of the scheduled change.

**Response**:
```json
{
  "message": "Scheduled plan change cancelled successfully"
}
```

### Usage Tracking

#### Record Usage

```
POST /usage/record
```

**Description**: Records usage data for a user's tariff plan.

**Permissions**: Requires system role.

**Request Body**:
```json
{
  "user_tariff_plan_id": 1,
  "download_bytes": 2000000000,
  "upload_bytes": 500000000,
  "source": "radius",
  "session_id": "session125"
}
```

**Response**:
```json
{
  "id": 3,
  "user_tariff_plan_id": 1,
  "download_bytes": 2000000000,
  "upload_bytes": 500000000,
  "total_bytes": 2500000000,
  "source": "radius",
  "session_id": "session125",
  "timestamp": "2023-02-15T10:00:00Z",
  "policy_actions": [
    {
      "action_type": "notify",
      "trigger_type": "usage_threshold",
      "threshold_value": 25000000000,
      "message": "User has reached 25% of data cap"
    }
  ]
}
```

#### Check Usage

```
POST /usage/check
```

**Description**: Checks a user's usage against their plan limits.

**Request Body**:
```json
{
  "user_id": 123,
  "additional_bytes": 5000000000
}
```

**Response**:
```json
{
  "user_id": 123,
  "plan_id": 2,
  "plan_name": "Premium Plan Plus",
  "data_cap": 750000000000,
  "current_usage": 27500000000,
  "percentage_used": 3.67,
  "additional_bytes": 5000000000,
  "projected_usage": 32500000000,
  "projected_percentage": 4.33,
  "is_throttled": false,
  "would_exceed_cap": false,
  "would_exceed_fup": false,
  "would_trigger_actions": []
}
```

#### Check FUP Threshold

```
POST /check-fup
```

**Description**: Checks if a user has crossed the Fair Usage Policy threshold.

**Permissions**: Requires system role.

**Request Body**:
```json
{
  "user_id": 123,
  "additional_bytes": 400000000000
}
```

**Response**:
```json
{
  "user_id": 123,
  "plan_id": 2,
  "plan_name": "Premium Plan Plus",
  "fup_threshold": 600000000000,
  "current_usage": 27500000000,
  "percentage_used": 4.58,
  "additional_bytes": 400000000000,
  "projected_usage": 427500000000,
  "projected_percentage": 71.25,
  "would_exceed_fup": false,
  "would_trigger_throttling": false
}
```

#### Get User's Bandwidth Policy

```
GET /users/{user_id}/bandwidth-policy
```

**Description**: Retrieves the bandwidth policy for a user.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Response**:
```json
{
  "user_id": 123,
  "plan_id": 2,
  "plan_name": "Premium Plan Plus",
  "download_speed": 150,
  "upload_speed": 30,
  "is_throttled": false,
  "throttled_download_speed": 15,
  "throttled_upload_speed": 7,
  "time_restrictions": null,
  "radius_policy_id": 105,
  "throttled_radius_policy_id": 106
}
```

### Administrative Operations

#### Process Scheduled Plan Changes

```
POST /process-scheduled-changes
```

**Description**: Processes all scheduled tariff plan changes that are due.

**Permissions**: Requires admin role.

**Response**:
```json
{
  "message": "Scheduled plan changes processed successfully",
  "processed_count": 2,
  "failed_count": 0,
  "details": [
    {
      "change_id": 1,
      "user_id": 123,
      "status": "processed",
      "message": "Plan changed from 'Premium Plan Plus' to 'Ultimate Plan'"
    },
    {
      "change_id": 2,
      "user_id": 456,
      "status": "processed",
      "message": "Plan changed from 'Basic Plan' to 'Standard Plan'"
    }
  ]
}
```

#### Calculate Overage Fee

```
POST /users/{user_id}/calculate-overage
```

**Description**: Calculates the overage fee for a user based on their usage.

**Permissions**: Requires admin role.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Request Body**:
```json
{
  "usage_mb": 5000
}
```

**Response**:
```json
{
  "user_id": 123,
  "plan_id": 2,
  "plan_name": "Premium Plan Plus",
  "data_cap_mb": 715255,
  "usage_mb": 5000,
  "overage_mb": 0,
  "rate_per_mb": 0.01,
  "overage_fee": 0.00,
  "currency": "USD"
}
```

## RADIUS Integration Endpoints

### Apply RADIUS Policy

```
POST /radius/apply-policy
```

**Description**: Applies a specific RADIUS policy to a user.

**Permissions**: Requires admin or support role.

**Request Body**:
```json
{
  "username": "user123",
  "policy_id": 101
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Policy applied successfully",
  "details": {
    "username": "user123",
    "policy_id": 101,
    "applied_at": "2025-03-14T19:41:21Z"
  }
}
```

### Update Bandwidth Limits

```
POST /radius/update-bandwidth
```

**Description**: Updates the bandwidth limits for a specific user.

**Permissions**: Requires admin or support role.

**Request Body**:
```json
{
  "username": "user123",
  "download_speed": 50,
  "upload_speed": 10,
  "burst_enabled": true,
  "burst_ratio": 1.5
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Bandwidth limits updated successfully",
  "details": {
    "username": "user123",
    "download_speed": 50,
    "upload_speed": 10,
    "burst_enabled": true,
    "burst_ratio": 1.5,
    "updated_at": "2025-03-14T19:41:21Z"
  }
}
```

### Throttle User

```
POST /radius/throttle
```

**Description**: Throttles a user's bandwidth due to exceeding data cap or other policy violations.

**Permissions**: Requires admin or support role.

**Request Body**:
```json
{
  "username": "user123",
  "download_speed": 5,
  "upload_speed": 2,
  "reason": "data_cap_exceeded",
  "duration_hours": 72
}
```

**Response**:
```json
{
  "status": "success",
  "message": "User throttled successfully",
  "details": {
    "username": "user123",
    "download_speed": 5,
    "upload_speed": 2,
    "reason": "data_cap_exceeded",
    "throttled_at": "2025-03-14T19:41:21Z",
    "throttle_end": "2025-03-17T19:41:21Z"
  }
}
```

### Synchronize Policies

```
POST /radius/sync-policies
```

**Description**: Synchronizes tariff plan policies with the RADIUS server.

**Permissions**: Requires admin role.

**Request Body**:
```json
{
  "plan_ids": [1, 2, 3],
  "force_update": false
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Policies synchronized successfully",
  "details": {
    "updated_plans": 3,
    "failed_plans": 0,
    "sync_time": "2025-03-14T19:41:21Z"
  }
}
```

### Get User Bandwidth Policy

```
GET /radius/user/{username}/policy
```

**Description**: Retrieves the current bandwidth policy for a specific user.

**Permissions**: Requires admin or support role.

**Path Parameters**:
- `username` (string, required): Username of the user.

**Response**:
```json
{
  "username": "user123",
  "policy_id": 101,
  "download_speed": 50,
  "upload_speed": 10,
  "burst_enabled": true,
  "burst_ratio": 1.5,
  "is_throttled": false,
  "throttle_reason": null,
  "throttle_end": null,
  "last_updated": "2025-03-14T19:41:21Z"
}
```

## Billing Integration Endpoints

### Create Invoice Item

```
POST /billing/invoice-item
```

**Description**: Creates a new invoice item for a user.

**Permissions**: Requires admin or billing role.

**Request Body**:
```json
{
  "user_id": 123,
  "amount": 29.99,
  "description": "Monthly subscription - Basic Plan",
  "prorate": false,
  "tax_rate": 0.07
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Invoice item created successfully",
  "details": {
    "invoice_item_id": 456,
    "user_id": 123,
    "amount": 29.99,
    "description": "Monthly subscription - Basic Plan",
    "tax_amount": 2.10,
    "total_amount": 32.09,
    "created_at": "2025-03-14T19:41:21Z"
  }
}
```

### Calculate Prorated Amount

```
POST /billing/calculate-prorate
```

**Description**: Calculates the prorated amount for a plan change.

**Permissions**: Requires admin or billing role.

**Request Body**:
```json
{
  "user_id": 123,
  "old_plan_id": 1,
  "new_plan_id": 2,
  "change_date": "2025-03-14T19:41:21Z"
}
```

**Response**:
```json
{
  "user_id": 123,
  "old_plan": {
    "id": 1,
    "name": "Basic Plan",
    "price": 29.99
  },
  "new_plan": {
    "id": 2,
    "name": "Premium Plan",
    "price": 59.99
  },
  "billing_cycle_start": "2025-03-01T00:00:00Z",
  "billing_cycle_end": "2025-03-31T23:59:59Z",
  "days_remaining": 17,
  "days_in_cycle": 31,
  "prorated_refund": 16.48,
  "prorated_charge": 32.95,
  "net_charge": 16.47
}
```

### Handle Plan Change

```
POST /billing/handle-plan-change
```

**Description**: Handles the billing aspects of a plan change.

**Permissions**: Requires admin or billing role.

**Request Body**:
```json
{
  "user_id": 123,
  "old_plan_id": 1,
  "new_plan_id": 2,
  "change_date": "2025-03-14T19:41:21Z",
  "prorate": true,
  "charge_immediately": true
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Plan change handled successfully",
  "details": {
    "user_id": 123,
    "old_plan": {
      "id": 1,
      "name": "Basic Plan",
      "price": 29.99
    },
    "new_plan": {
      "id": 2,
      "name": "Premium Plan",
      "price": 59.99
    },
    "prorated_refund": 16.48,
    "prorated_charge": 32.95,
    "net_charge": 16.47,
    "invoice_item_id": 457,
    "effective_date": "2025-03-14T19:41:21Z"
  }
}
```

### Charge Overage Fee

```
POST /billing/charge-overage
```

**Description**: Charges a user for exceeding their data cap.

**Permissions**: Requires admin or billing role.

**Request Body**:
```json
{
  "user_id": 123,
  "plan_id": 1,
  "excess_bytes": 5000000000,
  "rate_per_gb": 1.00,
  "description": "Data cap overage for March 2025"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Overage fee charged successfully",
  "details": {
    "user_id": 123,
    "plan_id": 1,
    "excess_gb": 4.66,
    "rate_per_gb": 1.00,
    "overage_amount": 4.66,
    "tax_amount": 0.33,
    "total_amount": 4.99,
    "invoice_item_id": 458,
    "charged_at": "2025-03-14T19:41:21Z"
  }
}
```

### Reset Billing Cycle

```
POST /billing/reset-cycle
```

**Description**: Resets the billing cycle for a user.

**Permissions**: Requires admin or billing role.

**Request Body**:
```json
{
  "user_id": 123,
  "plan_id": 1,
  "reset_date": "2025-03-14T19:41:21Z",
  "generate_invoice": true
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Billing cycle reset successfully",
  "details": {
    "user_id": 123,
    "plan_id": 1,
    "previous_cycle_start": "2025-02-14T00:00:00Z",
    "previous_cycle_end": "2025-03-13T23:59:59Z",
    "new_cycle_start": "2025-03-14T00:00:00Z",
    "new_cycle_end": "2025-04-13T23:59:59Z",
    "invoice_id": 789,
    "reset_at": "2025-03-14T19:41:21Z"
  }
}
```

### Get User Billing Information

```
GET /billing/user/{user_id}/info
```

**Description**: Retrieves billing information for a specific user.

**Permissions**: Requires admin, billing, or support role.

**Path Parameters**:
- `user_id` (integer, required): ID of the user.

**Response**:
```json
{
  "user_id": 123,
  "current_plan": {
    "id": 1,
    "name": "Basic Plan",
    "price": 29.99,
    "billing_cycle": "monthly"
  },
  "billing_cycle_start": "2025-03-14T00:00:00Z",
  "billing_cycle_end": "2025-04-13T23:59:59Z",
  "next_invoice_date": "2025-04-14T00:00:00Z",
  "payment_method": {
    "type": "credit_card",
    "last_four": "1234",
    "expiry": "12/27"
  },
  "account_balance": 0.00,
  "last_payment": {
    "amount": 29.99,
    "date": "2025-03-14T10:15:30Z",
    "status": "completed"
  },
  "auto_pay_enabled": true
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
  "detail": "Invalid request parameters",
  "errors": [
    {
      "field": "username",
      "message": "Username is required"
    }
  ]
}
```

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "trace_id": "abc123xyz456"
}
```

## Rate Limiting

API endpoints are subject to rate limiting to prevent abuse. The current limits are:

- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated users

When rate limits are exceeded, the API will return a 429 Too Many Requests response:

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 30
}
```

## Webhooks

The Tariff Enforcement Module can send webhook notifications for various events. To configure webhooks, use the Webhook Management API in the core platform.

Events that trigger webhooks include:

- `tariff.plan.created`
- `tariff.plan.updated`
- `tariff.plan.deleted`
- `tariff.user.plan_assigned`
- `tariff.user.plan_changed`
- `tariff.user.plan_cancelled`
- `tariff.user.fup_exceeded`
- `tariff.user.throttled`
- `tariff.user.unthrottled`
- `tariff.billing.invoice_created`
- `tariff.billing.payment_received`
- `tariff.billing.payment_failed`

## Client Libraries

Client libraries for the Tariff Enforcement Module API are available in the following languages:

- Python: [isp-management-python](https://github.com/your-org/isp-management-python)
- JavaScript: [isp-management-js](https://github.com/your-org/isp-management-js)
- PHP: [isp-management-php](https://github.com/your-org/isp-management-php)

## Conclusion

This documentation provides a comprehensive overview of the Tariff Enforcement Module's API endpoints. For additional assistance or to report issues, please contact the system administrator.
