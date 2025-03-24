# Integration Management Module API Documentation

This document provides comprehensive documentation for the Integration Management Module API endpoints, including request/response formats, authentication requirements, and examples.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL](#base-url)
4. [Integration Endpoints](#integration-endpoints)
   - [Create Integration](#create-integration)
   - [List Integrations](#list-integrations)
   - [Get Integration](#get-integration)
   - [Update Integration](#update-integration)
   - [Delete Integration](#delete-integration)
   - [Test Integration Connection](#test-integration-connection)
   - [Get Integration Status](#get-integration-status)
5. [Webhook Endpoints](#webhook-endpoints)
   - [Create Webhook Endpoint](#create-webhook-endpoint)
   - [List Webhook Endpoints](#list-webhook-endpoints)
   - [Get Webhook Endpoint](#get-webhook-endpoint)
   - [Update Webhook Endpoint](#update-webhook-endpoint)
   - [Delete Webhook Endpoint](#delete-webhook-endpoint)
   - [Rotate Webhook Secret](#rotate-webhook-secret)
   - [Receive Webhook](#receive-webhook)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Monitoring and Metrics](#monitoring-and-metrics)

## Overview

The Integration Management Module provides a centralized system for managing integrations with third-party services and external systems. It supports various integration types, including payment gateways, SMS providers, email providers, and more.

Key features include:
- Secure credential storage with encryption
- Version control for integration configurations
- Webhook handling for receiving notifications
- Activity logging for auditing
- Monitoring and metrics collection

## Authentication

All API endpoints (except for webhook receivers) require authentication using JWT tokens with OAuth2. Include the token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

Access to integration management endpoints is controlled by role-based access control (RBAC). The following roles are supported:
- `admin`: Full access to all endpoints
- `integration_manager`: Access to manage integrations but not delete them

## Base URL

The base URL for all Integration Management Module API endpoints is:

```
/integration-management
```

## Integration Endpoints

### Create Integration

Create a new integration.

**Endpoint:** `POST /integration-management/integrations/`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Request Body:**

```json
{
  "name": "Stripe Payment Gateway",
  "description": "Integration with Stripe for payment processing",
  "type": "PAYMENT_GATEWAY",
  "environment": "production",
  "configuration": {
    "base_url": "https://api.stripe.com",
    "webhook_url": "https://api.example.com/webhooks/stripe"
  },
  "credentials": {
    "api_key": "sk_live_51AbCdEfGhIjKlMnOpQrStUvWxYz"
  }
}
```

**Response:** (201 Created)

```json
{
  "id": 1,
  "name": "Stripe Payment Gateway",
  "description": "Integration with Stripe for payment processing",
  "type": "PAYMENT_GATEWAY",
  "status": "PENDING",
  "environment": "production",
  "configuration": {
    "base_url": "https://api.stripe.com",
    "webhook_url": "https://api.example.com/webhooks/stripe"
  },
  "created_at": "2025-03-15T06:30:45.123Z",
  "updated_at": "2025-03-15T06:30:45.123Z",
  "last_connection_test": null
}
```

**Notes:**
- The `credentials` field is encrypted and not returned in the response
- The integration status is initially set to `PENDING` until the connection is tested

### List Integrations

List integrations with optional filtering.

**Endpoint:** `GET /integration-management/integrations/`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Query Parameters:**
- `type` (optional): Filter by integration type (e.g., `PAYMENT_GATEWAY`)
- `status` (optional): Filter by integration status (e.g., `ACTIVE`)
- `environment` (optional): Filter by integration environment (e.g., `production`)
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100)

**Response:** (200 OK)

```json
{
  "items": [
    {
      "id": 1,
      "name": "Stripe Payment Gateway",
      "description": "Integration with Stripe for payment processing",
      "type": "PAYMENT_GATEWAY",
      "status": "ACTIVE",
      "environment": "production",
      "configuration": {
        "base_url": "https://api.stripe.com",
        "webhook_url": "https://api.example.com/webhooks/stripe"
      },
      "created_at": "2025-03-15T06:30:45.123Z",
      "updated_at": "2025-03-15T06:35:12.456Z",
      "last_connection_test": "2025-03-15T06:35:12.456Z"
    },
    {
      "id": 2,
      "name": "Twilio SMS",
      "description": "Integration with Twilio for SMS messaging",
      "type": "SMS_PROVIDER",
      "status": "ACTIVE",
      "environment": "production",
      "configuration": {
        "base_url": "https://api.twilio.com",
        "default_from_number": "+15551234567"
      },
      "created_at": "2025-03-15T07:15:30.789Z",
      "updated_at": "2025-03-15T07:20:45.012Z",
      "last_connection_test": "2025-03-15T07:20:45.012Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 100
}
```

### Get Integration

Get a specific integration by ID.

**Endpoint:** `GET /integration-management/integrations/{integration_id}`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `integration_id`: The ID of the integration to get

**Response:** (200 OK)

```json
{
  "id": 1,
  "name": "Stripe Payment Gateway",
  "description": "Integration with Stripe for payment processing",
  "type": "PAYMENT_GATEWAY",
  "status": "ACTIVE",
  "environment": "production",
  "configuration": {
    "base_url": "https://api.stripe.com",
    "webhook_url": "https://api.example.com/webhooks/stripe"
  },
  "created_at": "2025-03-15T06:30:45.123Z",
  "updated_at": "2025-03-15T06:35:12.456Z",
  "last_connection_test": "2025-03-15T06:35:12.456Z"
}
```

### Update Integration

Update an existing integration.

**Endpoint:** `PUT /integration-management/integrations/{integration_id}`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `integration_id`: The ID of the integration to update

**Request Body:**

```json
{
  "name": "Stripe Payment Gateway (Updated)",
  "description": "Updated integration with Stripe for payment processing",
  "status": "ACTIVE",
  "environment": "production",
  "configuration": {
    "base_url": "https://api.stripe.com",
    "webhook_url": "https://api.example.com/webhooks/stripe",
    "webhook_secret": "whsec_abcdefghijklmnopqrstuvwxyz"
  },
  "credentials": {
    "api_key": "sk_live_updated_key_51AbCdEfGhIjKlMnOpQrStUvWxYz"
  }
}
```

**Response:** (200 OK)

```json
{
  "id": 1,
  "name": "Stripe Payment Gateway (Updated)",
  "description": "Updated integration with Stripe for payment processing",
  "type": "PAYMENT_GATEWAY",
  "status": "ACTIVE",
  "environment": "production",
  "configuration": {
    "base_url": "https://api.stripe.com",
    "webhook_url": "https://api.example.com/webhooks/stripe",
    "webhook_secret": "whsec_abcdefghijklmnopqrstuvwxyz"
  },
  "created_at": "2025-03-15T06:30:45.123Z",
  "updated_at": "2025-03-15T08:45:30.789Z",
  "last_connection_test": "2025-03-15T06:35:12.456Z"
}
```

**Notes:**
- All fields in the request body are optional
- If `credentials` or `configuration` are updated, a new version is created
- If `credentials` or `configuration` are updated, the connection is automatically tested in the background

### Delete Integration

Delete an integration.

**Endpoint:** `DELETE /integration-management/integrations/{integration_id}`

**Authentication:** Required (Role: `admin`)

**Path Parameters:**
- `integration_id`: The ID of the integration to delete

**Response:** (204 No Content)

**Notes:**
- Only users with the `admin` role can delete integrations
- Deleting an integration will also delete all associated webhook endpoints and versions

### Test Integration Connection

Test the connection to an integration.

**Endpoint:** `POST /integration-management/integrations/{integration_id}/test`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `integration_id`: The ID of the integration to test

**Response:** (200 OK)

```json
{
  "success": true,
  "message": null
}
```

**Error Response:** (200 OK, but with error details)

```json
{
  "success": false,
  "message": "Failed to connect: 401 - Invalid API key"
}
```

### Get Integration Status

Get the status of an integration.

**Endpoint:** `GET /integration-management/integrations/{integration_id}/status`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `integration_id`: The ID of the integration to get status for

**Response:** (200 OK)

```json
{
  "service_type": "payment_gateway",
  "provider": "stripe",
  "is_connected": true,
  "last_checked": "2025-03-15T08:50:15.123Z",
  "details": {
    "account": {
      "name": "Example Company",
      "email": "billing@example.com",
      "country": "US"
    }
  },
  "integration_id": 1,
  "integration_name": "Stripe Payment Gateway (Updated)",
  "integration_type": "PAYMENT_GATEWAY",
  "integration_status": "ACTIVE",
  "integration_environment": "production",
  "last_connection_test": "2025-03-15T06:35:12.456Z"
}
```

## Webhook Endpoints

### Create Webhook Endpoint

Create a new webhook endpoint.

**Endpoint:** `POST /integration-management/webhooks/`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Request Body:**

```json
{
  "integration_id": 1,
  "name": "Stripe Payment Events",
  "description": "Webhook for Stripe payment events",
  "path": "stripe-payments",
  "secret": "whsec_custom_secret_abcdefghijklmnopqrstuvwxyz",
  "active": true,
  "verify_signature": true,
  "signature_header": "Stripe-Signature"
}
```

**Response:** (201 Created)

```json
{
  "id": 1,
  "integration_id": 1,
  "name": "Stripe Payment Events",
  "description": "Webhook for Stripe payment events",
  "path": "stripe-payments",
  "active": true,
  "verify_signature": true,
  "signature_header": "Stripe-Signature",
  "created_at": "2025-03-15T09:00:00.000Z",
  "updated_at": "2025-03-15T09:00:00.000Z"
}
```

**Notes:**
- The `secret` field is not returned in the response for security reasons
- If `path` is not provided, a unique path is generated
- If `secret` is not provided, a secure secret is generated

### List Webhook Endpoints

List webhook endpoints with optional filtering.

**Endpoint:** `GET /integration-management/webhooks/`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Query Parameters:**
- `integration_id` (optional): Filter by integration ID
- `active` (optional): Filter by active status

**Response:** (200 OK)

```json
[
  {
    "id": 1,
    "integration_id": 1,
    "name": "Stripe Payment Events",
    "description": "Webhook for Stripe payment events",
    "path": "stripe-payments",
    "active": true,
    "verify_signature": true,
    "signature_header": "Stripe-Signature",
    "created_at": "2025-03-15T09:00:00.000Z",
    "updated_at": "2025-03-15T09:00:00.000Z"
  },
  {
    "id": 2,
    "integration_id": 2,
    "name": "Twilio SMS Status",
    "description": "Webhook for Twilio SMS status updates",
    "path": "twilio-sms-status",
    "active": true,
    "verify_signature": true,
    "signature_header": "X-Twilio-Signature",
    "created_at": "2025-03-15T09:15:00.000Z",
    "updated_at": "2025-03-15T09:15:00.000Z"
  }
]
```

### Get Webhook Endpoint

Get a specific webhook endpoint by ID.

**Endpoint:** `GET /integration-management/webhooks/{webhook_id}`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `webhook_id`: The ID of the webhook endpoint to get

**Response:** (200 OK)

```json
{
  "id": 1,
  "integration_id": 1,
  "name": "Stripe Payment Events",
  "description": "Webhook for Stripe payment events",
  "path": "stripe-payments",
  "active": true,
  "verify_signature": true,
  "signature_header": "Stripe-Signature",
  "created_at": "2025-03-15T09:00:00.000Z",
  "updated_at": "2025-03-15T09:00:00.000Z"
}
```

### Update Webhook Endpoint

Update an existing webhook endpoint.

**Endpoint:** `PUT /integration-management/webhooks/{webhook_id}`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `webhook_id`: The ID of the webhook endpoint to update

**Request Body:**

```json
{
  "name": "Stripe Payment Events (Updated)",
  "description": "Updated webhook for Stripe payment events",
  "path": "stripe-payments-updated",
  "active": true,
  "verify_signature": true,
  "signature_header": "Stripe-Signature"
}
```

**Response:** (200 OK)

```json
{
  "id": 1,
  "integration_id": 1,
  "name": "Stripe Payment Events (Updated)",
  "description": "Updated webhook for Stripe payment events",
  "path": "stripe-payments-updated",
  "active": true,
  "verify_signature": true,
  "signature_header": "Stripe-Signature",
  "created_at": "2025-03-15T09:00:00.000Z",
  "updated_at": "2025-03-15T09:30:00.000Z"
}
```

**Notes:**
- All fields in the request body are optional
- The `secret` field can be updated, but it's not returned in the response

### Delete Webhook Endpoint

Delete a webhook endpoint.

**Endpoint:** `DELETE /integration-management/webhooks/{webhook_id}`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `webhook_id`: The ID of the webhook endpoint to delete

**Response:** (204 No Content)

### Rotate Webhook Secret

Rotate the secret for a webhook endpoint.

**Endpoint:** `POST /integration-management/webhooks/{webhook_id}/rotate-secret`

**Authentication:** Required (Role: `admin` or `integration_manager`)

**Path Parameters:**
- `webhook_id`: The ID of the webhook endpoint to rotate secret for

**Response:** (200 OK)

```json
{
  "secret": "whsec_new_secret_abcdefghijklmnopqrstuvwxyz"
}
```

**Notes:**
- This is the only time the secret is returned in the response
- Make sure to save the secret, as it won't be retrievable later

### Receive Webhook

Receive and process a webhook event.

**Endpoint:** `POST /integration-management/webhooks/receive/{webhook_path}`

**Authentication:** Not required (public endpoint)

**Path Parameters:**
- `webhook_path`: The path of the webhook endpoint

**Request Body:**
- Any JSON or form data sent by the external service

**Headers:**
- May include signature headers for verification

**Response:** (200 OK)

```json
{
  "status": "success",
  "event_id": 123
}
```

**Notes:**
- This endpoint is public and does not require authentication
- If signature verification is enabled, the request must include the appropriate signature header
- The webhook event is processed asynchronously

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of a request:

- `200 OK`: The request was successful
- `201 Created`: The resource was created successfully
- `204 No Content`: The request was successful, but there is no content to return
- `400 Bad Request`: The request was invalid
- `401 Unauthorized`: Authentication is required or failed
- `403 Forbidden`: The authenticated user does not have permission to access the resource
- `404 Not Found`: The requested resource was not found
- `500 Internal Server Error`: An error occurred on the server

Error responses include a JSON object with details about the error:

```json
{
  "detail": "Error message"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse. The rate limits are:

- 100 requests per minute for authenticated users
- 10 requests per minute for webhook endpoints

Rate limit headers are included in the response:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1615789245
```

## Monitoring and Metrics

The Integration Management Module collects metrics for monitoring integration performance and reliability. The following metrics are available:

- `integrations_by_status`: Number of integrations by status
- `integrations_by_type`: Number of integrations by type
- `total_webhooks`: Total number of webhook endpoints
- `active_webhooks`: Number of active webhook endpoints
- `total_webhook_events`: Total number of webhook events
- `processed_webhook_events`: Number of processed webhook events
- `pending_webhook_events`: Number of pending webhook events
- `webhook_events_last_24h`: Number of webhook events in the last 24 hours
- `webhook_processing_time`: Time taken to process webhook events
- `integration_connection_tests`: Number of integration connection tests
- `webhook_events_processed`: Number of webhook events processed

These metrics are available through the monitoring dashboard and can be exported to external monitoring systems like Prometheus, StatsD, or Elasticsearch.
