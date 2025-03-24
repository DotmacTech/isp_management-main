# Webhooks and External Services Documentation

This document provides comprehensive documentation for the webhook and external service functionality in the ISP Management Platform's Communications module.

## Table of Contents

1. [Introduction](#introduction)
2. [Webhooks](#webhooks)
   - [Webhook Registration](#webhook-registration)
   - [Webhook Events](#webhook-events)
   - [Webhook Payload Structure](#webhook-payload-structure)
   - [Webhook Security](#webhook-security)
   - [Webhook Logs](#webhook-logs)
3. [External Services](#external-services)
   - [Supported Service Types](#supported-service-types)
   - [Service Registration](#service-registration)
   - [Service Configuration](#service-configuration)
4. [API Reference](#api-reference)
   - [Webhook Endpoints](#webhook-endpoints)
   - [External Service Endpoints](#external-service-endpoints)
5. [Integration Examples](#integration-examples)
   - [Registering a Webhook](#registering-a-webhook)
   - [Configuring an External Service](#configuring-an-external-service)
   - [Testing Webhooks](#testing-webhooks)

## Introduction

The ISP Management Platform provides robust integration capabilities through webhooks and external services. Webhooks allow external systems to receive real-time notifications about events occurring within the platform, while external services enable the platform to communicate through various channels such as SMS, email, and chat platforms.

## Webhooks

Webhooks are HTTP callbacks that are triggered when specific events occur in the ISP Management Platform. They allow for real-time integration with external systems.

### Webhook Registration

To use webhooks, you must first register a webhook endpoint with the platform. This involves specifying:

- A name for the webhook
- The URL where webhook payloads should be sent
- The events you want to subscribe to
- Optional security settings (secret for payload signing)
- Optional custom headers to include with webhook requests

### Webhook Events

The platform supports the following webhook events:

| Event | Description |
|-------|-------------|
| `message.created` | Triggered when a new message is created |
| `message.updated` | Triggered when a message is updated |
| `message.deleted` | Triggered when a message is deleted |
| `notification.created` | Triggered when a new notification is created |
| `notification.updated` | Triggered when a notification is updated |
| `notification.deleted` | Triggered when a notification is deleted |
| `announcement.created` | Triggered when a new announcement is created |
| `announcement.updated` | Triggered when an announcement is updated |
| `announcement.deleted` | Triggered when an announcement is deleted |
| `ticket.created` | Triggered when a new support ticket is created |
| `ticket.updated` | Triggered when a support ticket is updated |
| `ticket.response_added` | Triggered when a response is added to a support ticket |

### Webhook Payload Structure

Webhook payloads are sent as JSON objects with the following structure:

```json
{
  "event": "event.name",
  "timestamp": "2023-06-15T12:34:56.789Z",
  ... event-specific data ...
}
```

Each event type includes specific data relevant to that event. For example, a `message.created` event includes the message ID, subject, content, sender, recipient, etc.

### Webhook Security

To ensure the security and authenticity of webhook payloads, the platform supports payload signing. When you register a webhook with a secret, each payload is signed using HMAC-SHA256. The signature is included in the `X-Webhook-Signature` header.

To verify the signature:

1. Get the signature from the `X-Webhook-Signature` header
2. Compute the HMAC-SHA256 of the raw request body using your secret
3. Compare the computed signature with the one in the header

Example in Python:
```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    computed_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)
```

### Webhook Logs

The platform maintains detailed logs of all webhook deliveries, including:

- Request payload
- Request headers
- Response status code
- Response payload
- Success/failure status
- Error messages (if any)

These logs can be accessed through the API to troubleshoot webhook delivery issues.

## External Services

External services enable the platform to communicate through various channels such as SMS, email, and chat platforms.

### Supported Service Types

The platform supports the following service types:

| Service Type | Description | Supported Providers |
|--------------|-------------|---------------------|
| `sms` | SMS messaging | Twilio, Nexmo, AWS SNS |
| `email` | Email messaging | SendGrid, Mailgun, AWS SES |
| `push` | Push notifications | Firebase, OneSignal |
| `chat` | Chat platform integration | Slack, Microsoft Teams, Discord |

### Service Registration

To use an external service, you must register it with the platform. This involves specifying:

- A name for the service
- The service type (sms, email, etc.)
- The provider (Twilio, SendGrid, etc.)
- Configuration details (API keys, credentials, etc.)

### Service Configuration

Each service type and provider requires specific configuration parameters:

#### SMS Configuration

**Twilio:**
```json
{
  "account_sid": "your_account_sid",
  "auth_token": "your_auth_token",
  "from_number": "+1234567890"
}
```

**Nexmo:**
```json
{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "from_number": "+1234567890"
}
```

#### Email Configuration

**SendGrid:**
```json
{
  "api_key": "your_api_key",
  "from_email": "noreply@yourdomain.com",
  "from_name": "Your Company Name"
}
```

**Mailgun:**
```json
{
  "api_key": "your_api_key",
  "domain": "mail.yourdomain.com",
  "from_email": "noreply@yourdomain.com",
  "from_name": "Your Company Name"
}
```

#### Push Configuration

**Firebase:**
```json
{
  "project_id": "your_project_id",
  "private_key": "your_private_key",
  "client_email": "your_client_email"
}
```

**OneSignal:**
```json
{
  "app_id": "your_app_id",
  "api_key": "your_api_key"
}
```

## API Reference

### Webhook Endpoints

#### Register a webhook

```
POST /api/communications/webhooks/
```

Request body:
```json
{
  "name": "Customer Portal Webhook",
  "url": "https://portal.example.com/webhooks/isp",
  "events": ["message.created", "notification.created"],
  "is_active": true,
  "secret": "your_webhook_secret",
  "headers": {
    "X-Custom-Header": "Custom Value"
  },
  "description": "Webhook for the customer portal"
}
```

#### Get all webhooks

```
GET /api/communications/webhooks/
```

Query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)
- `event`: Filter by event type
- `active_only`: If true, only return active webhooks

#### Get a specific webhook

```
GET /api/communications/webhooks/{webhook_id}
```

#### Update a webhook

```
PUT /api/communications/webhooks/{webhook_id}
```

Request body:
```json
{
  "name": "Updated Webhook Name",
  "is_active": false
}
```

#### Delete a webhook

```
DELETE /api/communications/webhooks/{webhook_id}
```

#### Get webhook logs

```
GET /api/communications/webhooks/{webhook_id}/logs
```

Query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)
- `success_only`: Filter by success status

#### Test a webhook

```
POST /api/communications/webhooks/{webhook_id}/test
```

### External Service Endpoints

#### Register an external service

```
POST /api/communications/external-services/
```

Request body:
```json
{
  "name": "Company SMS Service",
  "service_type": "sms",
  "provider": "twilio",
  "config": {
    "account_sid": "your_account_sid",
    "auth_token": "your_auth_token",
    "from_number": "+1234567890"
  },
  "is_active": true,
  "description": "SMS service for customer notifications"
}
```

#### Get all external services

```
GET /api/communications/external-services/
```

Query parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)
- `service_type`: Filter by service type
- `provider`: Filter by provider
- `active_only`: If true, only return active services

#### Get a specific external service

```
GET /api/communications/external-services/{service_id}
```

#### Update an external service

```
PUT /api/communications/external-services/{service_id}
```

Request body:
```json
{
  "name": "Updated Service Name",
  "config": {
    "account_sid": "new_account_sid",
    "auth_token": "new_auth_token",
    "from_number": "+1987654321"
  }
}
```

#### Delete an external service

```
DELETE /api/communications/external-services/{service_id}
```

#### Test an external service

```
POST /api/communications/external-services/{service_id}/test
```

Request body:
```json
{
  "recipient": "+1234567890",  // for SMS
  // or
  "recipient": "user@example.com",  // for email
  "subject": "Test Message",
  "content": "This is a test message from the ISP Management Platform."
}
```

## Integration Examples

### Registering a Webhook

Here's an example of how to register a webhook using cURL:

```bash
curl -X POST "https://api.example.com/api/communications/webhooks/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Portal Webhook",
    "url": "https://portal.example.com/webhooks/isp",
    "events": ["message.created", "notification.created"],
    "is_active": true,
    "secret": "your_webhook_secret",
    "headers": {
      "X-Custom-Header": "Custom Value"
    },
    "description": "Webhook for the customer portal"
  }'
```

### Configuring an External Service

Here's an example of how to configure an email service using cURL:

```bash
curl -X POST "https://api.example.com/api/communications/external-services/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Company Email Service",
    "service_type": "email",
    "provider": "sendgrid",
    "config": {
      "api_key": "your_sendgrid_api_key",
      "from_email": "noreply@example.com",
      "from_name": "Example ISP"
    },
    "is_active": true,
    "description": "Email service for customer communications"
  }'
```

### Testing Webhooks

Here's an example of how to set up a simple webhook receiver using Node.js and Express:

```javascript
const express = require('express');
const bodyParser = require('body-parser');
const crypto = require('crypto');

const app = express();
app.use(bodyParser.json());

// Webhook secret from registration
const webhookSecret = 'your_webhook_secret';

// Verify webhook signature
function verifySignature(payload, signature) {
  const hmac = crypto.createHmac('sha256', webhookSecret);
  hmac.update(JSON.stringify(payload));
  const computedSignature = hmac.digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(computedSignature),
    Buffer.from(signature)
  );
}

app.post('/webhooks/isp', (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const event = req.headers['x-webhook-event'];
  const payload = req.body;
  
  console.log(`Received webhook: ${event}`);
  
  // Verify signature if secret is set
  if (webhookSecret && signature) {
    if (!verifySignature(payload, signature)) {
      console.error('Invalid webhook signature');
      return res.status(401).json({ error: 'Invalid signature' });
    }
  }
  
  // Process the webhook based on event type
  switch (event) {
    case 'message.created':
      console.log(`New message: ${payload.subject}`);
      break;
    case 'notification.created':
      console.log(`New notification: ${payload.title}`);
      break;
    // Handle other event types
    default:
      console.log(`Unhandled event type: ${event}`);
  }
  
  // Acknowledge receipt
  res.status(200).json({ status: 'success' });
});

app.listen(3000, () => {
  console.log('Webhook receiver listening on port 3000');
});
```
