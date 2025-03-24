# API Improvements Documentation

This document provides detailed information about the API improvements implemented in the ISP Management Platform, including HATEOAS support, enhanced error responses, and rate limiting headers.

## Table of Contents

1. [HATEOAS Support](#hateoas-support)
2. [Rate Limiting Headers](#rate-limiting-headers)
3. [Enhanced Error Responses](#enhanced-error-responses)
4. [Client Integration Guide](#client-integration-guide)

## HATEOAS Support

HATEOAS (Hypermedia as the Engine of Application State) is a constraint of the REST application architecture that keeps the RESTful style architecture unique from other network application architectures. With HATEOAS, a client interacts with a network application whose application servers provide information dynamically through hypermedia.

### Benefits of HATEOAS

- **Discoverability**: Clients can dynamically discover available actions without prior knowledge of the API structure
- **Self-documentation**: The API becomes more self-documenting
- **Loose coupling**: Reduces the coupling between client and server
- **Evolvability**: The API can evolve without breaking clients

### Link Structure

Each link in the HATEOAS response follows this structure:

```json
{
  "rel": "self",
  "href": "/api/v1/customers/123",
  "method": "GET",
  "title": "Get customer details"
}
```

Where:
- `rel`: Relationship type (e.g., self, collection, next, prev)
- `href`: URL for the related resource
- `method`: HTTP method to use (GET, POST, PUT, DELETE)
- `title`: Human-readable description of the link

### Resource Links

Individual resources include links for:

- `self`: Link to the current resource
- `collection`: Link to the collection this resource belongs to
- Related resources (e.g., a customer might have links to addresses, contacts)
- Available actions (e.g., update, delete)

Example for a customer resource:

```json
{
  "id": 123,
  "name": "Example Customer",
  "email": "customer@example.com",
  "_links": {
    "self": {
      "href": "/api/v1/customers/123",
      "method": "GET",
      "title": "Get customer details"
    },
    "update": {
      "href": "/api/v1/customers/123",
      "method": "PUT",
      "title": "Update this customer"
    },
    "delete": {
      "href": "/api/v1/customers/123",
      "method": "DELETE",
      "title": "Delete this customer"
    },
    "addresses": {
      "href": "/api/v1/customers/123/addresses",
      "method": "GET",
      "title": "Get customer addresses"
    }
  }
}
```

### Collection Links

Collection resources include links for:

- `self`: Link to the current collection with current filters
- `first`: Link to the first page
- `last`: Link to the last page
- `prev`: Link to the previous page (if applicable)
- `next`: Link to the next page (if applicable)
- `create`: Link to create a new resource in this collection

Example for a customer collection:

```json
{
  "items": [...],
  "total": 100,
  "skip": 20,
  "limit": 10,
  "_links": {
    "self": {
      "href": "/api/v1/customers?skip=20&limit=10",
      "method": "GET",
      "title": "Current page of customers"
    },
    "first": {
      "href": "/api/v1/customers?skip=0&limit=10",
      "method": "GET",
      "title": "First page of customers"
    },
    "prev": {
      "href": "/api/v1/customers?skip=10&limit=10",
      "method": "GET",
      "title": "Previous page of customers"
    },
    "next": {
      "href": "/api/v1/customers?skip=30&limit=10",
      "method": "GET",
      "title": "Next page of customers"
    },
    "last": {
      "href": "/api/v1/customers?skip=90&limit=10",
      "method": "GET",
      "title": "Last page of customers"
    },
    "create": {
      "href": "/api/v1/customers",
      "method": "POST",
      "title": "Create new customer"
    }
  }
}
```

## Rate Limiting Headers

Rate limiting is implemented to prevent abuse of the API and ensure fair usage. The API now includes rate limiting headers in all responses to help clients understand their rate limit status.

### Rate Limit Headers

The following headers are included in all API responses:

- `X-RateLimit-Limit`: The maximum number of requests allowed in the current time window
- `X-RateLimit-Remaining`: The number of requests remaining in the current time window
- `X-RateLimit-Reset`: The time (in Unix timestamp format) when the rate limit window resets

Example:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1615560000
```

### Rate Limit Exceeded Response

When a rate limit is exceeded, the API returns a `429 Too Many Requests` response with a JSON body explaining the limit and when it will reset:

```json
{
  "status": "error",
  "code": 429,
  "message": "Rate limit exceeded",
  "details": {
    "limit": 100,
    "reset_at": "2023-03-12T15:00:00Z"
  }
}
```

### Rate Limit Configuration

Rate limits are configured per endpoint and can vary based on:

- The specific endpoint being accessed
- The authentication status of the request
- The user's role or subscription level

## Enhanced Error Responses

The API now provides standardized error responses with detailed information to help clients understand and resolve issues.

### Error Response Structure

All error responses follow this structure:

```json
{
  "status": "error",
  "code": 400,
  "message": "Validation error",
  "details": {
    "field_errors": [
      {
        "field": "email",
        "message": "Invalid email format",
        "code": "invalid_format"
      }
    ]
  }
}
```

Where:
- `status`: Always "error" for error responses
- `code`: HTTP status code
- `message`: Human-readable error message
- `details`: Additional information about the error, which may include:
  - `field_errors`: For validation errors
  - `resource_id`: For resource not found errors
  - Other context-specific details

### Common Error Types

#### Validation Errors (400 Bad Request)

```json
{
  "status": "error",
  "code": 400,
  "message": "Validation error",
  "details": {
    "field_errors": [
      {
        "field": "email",
        "message": "Invalid email format",
        "code": "invalid_format"
      },
      {
        "field": "phone",
        "message": "Phone number is required",
        "code": "required_field"
      }
    ]
  }
}
```

#### Resource Not Found (404 Not Found)

```json
{
  "status": "error",
  "code": 404,
  "message": "Resource not found",
  "details": {
    "resource_type": "customer",
    "resource_id": "123"
  }
}
```

#### Authentication Errors (401 Unauthorized)

```json
{
  "status": "error",
  "code": 401,
  "message": "Authentication required",
  "details": {
    "reason": "Invalid or expired token"
  }
}
```

#### Authorization Errors (403 Forbidden)

```json
{
  "status": "error",
  "code": 403,
  "message": "Permission denied",
  "details": {
    "required_permission": "customer.update"
  }
}
```

## Client Integration Guide

This section provides guidance on how to integrate with the improved API features.

### Working with HATEOAS Links

To take full advantage of HATEOAS, clients should:

1. Parse the `_links` object in API responses
2. Use the links to navigate the API instead of hardcoding URLs
3. Check for the presence of links to determine available actions

Example client code (JavaScript):

```javascript
async function getCustomerDetails(customerId) {
  const response = await fetch(`/api/v1/customers/${customerId}`);
  const customer = await response.json();
  
  // Store links for later use
  const links = customer._links;
  
  // Check if we can update this customer
  if (links.update) {
    // Enable update button in UI
    enableUpdateButton(links.update.href, links.update.method);
  }
  
  // Load related resources if available
  if (links.addresses) {
    loadAddresses(links.addresses.href);
  }
  
  return customer;
}
```

### Handling Rate Limits

Clients should:

1. Check rate limit headers in each response
2. Implement backoff strategies when limits are approaching
3. Display appropriate messages to users when limits are reached

Example client code (JavaScript):

```javascript
async function makeApiRequest(url, options = {}) {
  const response = await fetch(url, options);
  
  // Store rate limit info
  const rateLimit = {
    limit: parseInt(response.headers.get('X-RateLimit-Limit') || '0'),
    remaining: parseInt(response.headers.get('X-RateLimit-Remaining') || '0'),
    reset: parseInt(response.headers.get('X-RateLimit-Reset') || '0')
  };
  
  // Update UI with rate limit info
  updateRateLimitDisplay(rateLimit);
  
  // Implement backoff if needed
  if (rateLimit.remaining < rateLimit.limit * 0.1) {
    // Less than 10% remaining, slow down requests
    enableRequestThrottling();
  }
  
  return response;
}
```

### Processing Error Responses

Clients should:

1. Check for error status in responses
2. Display appropriate error messages to users
3. Handle field-level validation errors by highlighting specific form fields

Example client code (JavaScript):

```javascript
async function submitForm(formData) {
  try {
    const response = await fetch('/api/v1/customers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    
    const data = await response.json();
    
    if (data.status === 'error') {
      // Handle error response
      displayErrorMessage(data.message);
      
      // Handle field-level validation errors
      if (data.details && data.details.field_errors) {
        data.details.field_errors.forEach(error => {
          highlightFormField(error.field, error.message);
        });
      }
      
      return null;
    }
    
    return data;
  } catch (error) {
    displayErrorMessage('Network error occurred');
    return null;
  }
}
```

## Conclusion

These API improvements enhance the developer experience by providing more discoverable, self-documenting, and informative APIs. By following the guidelines in this document, clients can take full advantage of these features to build more robust and maintainable integrations.
