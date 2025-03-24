# Authentication API Reference

This document provides detailed information about the authentication API endpoints, request/response formats, and error handling.

## Base URL

All API endpoints are relative to the base URL of your API server:

```
https://api.example.com/
```

## Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## API Endpoints

### User Registration and Authentication

#### Register a New User

```
POST /auth/register
```

Register a new user in the system.

**Request Body:**

```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "confirm_password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "role": "customer"
}
```

**Response (201 Created):**

```json
{
  "id": 123,
  "username": "newuser",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "customer",
  "is_active": true,
  "created_at": "2025-03-14T09:30:00Z"
}
```

**Errors:**

- `400 Bad Request`: Invalid input data
- `409 Conflict`: Username or email already exists

---

#### User Login

```
POST /auth/login
```

Authenticate a user and receive access and refresh tokens.

**Request Body:**

```json
{
  "username": "newuser",
  "password": "SecurePassword123!",
  "remember_me": true
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 123,
    "username": "newuser",
    "email": "user@example.com",
    "role": "customer"
  },
  "requires_mfa": false
}
```

**Errors:**

- `400 Bad Request`: Invalid credentials
- `401 Unauthorized`: Account locked due to too many failed attempts
- `403 Forbidden`: Account inactive

---

#### Refresh Token

```
POST /auth/refresh
```

Get a new access token using a refresh token.

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**

- `401 Unauthorized`: Invalid or expired refresh token

---

#### Logout

```
POST /auth/logout
```

Logout and blacklist the current tokens.

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**

```json
{
  "message": "Successfully logged out"
}
```

**Errors:**

- `401 Unauthorized`: Invalid token

---

### Password Management

#### Request Password Reset

```
POST /auth/password-reset
```

Request a password reset email.

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**

```json
{
  "message": "Password reset email sent"
}
```

**Note:** For security reasons, this endpoint always returns a 200 OK response, even if the email does not exist in the system.

---

#### Confirm Password Reset

```
POST /auth/password-reset/confirm
```

Reset a password using a reset token.

**Request Body:**

```json
{
  "token": "reset-token-from-email",
  "password": "NewSecurePassword123!",
  "confirm_password": "NewSecurePassword123!"
}
```

**Response (200 OK):**

```json
{
  "message": "Password reset successful"
}
```

**Errors:**

- `400 Bad Request`: Invalid or mismatched passwords
- `401 Unauthorized`: Invalid or expired token

---

#### Change Password

```
POST /auth/password-change
```

Change a user's password (requires authentication).

**Request Body:**

```json
{
  "current_password": "CurrentPassword123!",
  "new_password": "NewSecurePassword123!",
  "confirm_password": "NewSecurePassword123!"
}
```

**Response (200 OK):**

```json
{
  "message": "Password changed successfully"
}
```

**Errors:**

- `400 Bad Request`: Invalid or mismatched passwords
- `401 Unauthorized`: Incorrect current password

---

### Two-Factor Authentication

#### Set Up Two-Factor Authentication

```
POST /auth/2fa/setup
```

Set up two-factor authentication for a user (requires authentication).

**Request Body:**

```json
{
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**

```json
{
  "secret_key": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "recovery_codes": [
    "1234-5678-9012",
    "2345-6789-0123",
    "3456-7890-1234"
  ]
}
```

**Errors:**

- `401 Unauthorized`: Incorrect password

---

#### Verify Two-Factor Authentication

```
POST /auth/2fa/verify
```

Verify a two-factor authentication code during login.

**Request Body:**

```json
{
  "code": "123456",
  "remember_device": true,
  "session_id": "login-session-id"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_token": "device-token-for-future-logins"
}
```

**Errors:**

- `401 Unauthorized`: Invalid code
- `404 Not Found`: Invalid session ID

---

#### Disable Two-Factor Authentication

```
POST /auth/2fa/disable
```

Disable two-factor authentication for a user (requires authentication).

**Request Body:**

```json
{
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**

```json
{
  "message": "Two-factor authentication disabled"
}
```

**Errors:**

- `401 Unauthorized`: Incorrect password

---

### User Management

#### Get Current User

```
GET /auth/users/me
```

Get the current authenticated user's profile.

**Response (200 OK):**

```json
{
  "id": 123,
  "username": "newuser",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "role": "customer",
  "is_active": true,
  "created_at": "2025-03-14T09:30:00Z",
  "last_login": "2025-03-14T10:45:00Z",
  "has_mfa_enabled": true
}
```

---

#### Update Current User

```
PUT /auth/users/me
```

Update the current authenticated user's profile.

**Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+1987654321",
  "email": "john.smith@example.com"
}
```

**Response (200 OK):**

```json
{
  "id": 123,
  "username": "newuser",
  "email": "john.smith@example.com",
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+1987654321",
  "role": "customer",
  "is_active": true,
  "created_at": "2025-03-14T09:30:00Z",
  "last_login": "2025-03-14T10:45:00Z"
}
```

**Errors:**

- `400 Bad Request`: Invalid input data
- `409 Conflict`: Email already exists

---

#### Get User Sessions

```
GET /auth/sessions
```

Get all active sessions for the current user.

**Response (200 OK):**

```json
{
  "sessions": [
    {
      "id": "session-id-1",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "device_type": "desktop",
      "location": "New York, US",
      "created_at": "2025-03-14T09:30:00Z",
      "last_activity": "2025-03-14T10:45:00Z",
      "is_current": true
    },
    {
      "id": "session-id-2",
      "ip_address": "192.168.1.2",
      "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
      "device_type": "mobile",
      "location": "New York, US",
      "created_at": "2025-03-13T15:20:00Z",
      "last_activity": "2025-03-13T16:30:00Z",
      "is_current": false
    }
  ]
}
```

---

#### Terminate Session

```
DELETE /auth/sessions/{session_id}
```

Terminate a specific session.

**Response (200 OK):**

```json
{
  "message": "Session terminated successfully"
}
```

**Errors:**

- `404 Not Found`: Session not found
- `403 Forbidden`: Not authorized to terminate this session

---

#### Terminate All Other Sessions

```
DELETE /auth/sessions
```

Terminate all sessions except the current one.

**Response (200 OK):**

```json
{
  "message": "All other sessions terminated successfully",
  "count": 3
}
```

---

### Admin Endpoints

#### Get All Users

```
GET /auth/admin/users
```

Get a list of all users (admin only).

**Query Parameters:**

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)
- `role`: Filter by role
- `is_active`: Filter by active status
- `search`: Search by username or email

**Response (200 OK):**

```json
{
  "users": [
    {
      "id": 123,
      "username": "user1",
      "email": "user1@example.com",
      "role": "customer",
      "is_active": true,
      "created_at": "2025-03-14T09:30:00Z"
    },
    {
      "id": 124,
      "username": "user2",
      "email": "user2@example.com",
      "role": "staff",
      "is_active": true,
      "created_at": "2025-03-13T10:20:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

**Errors:**

- `403 Forbidden`: Not authorized (non-admin user)

---

#### Get User by ID

```
GET /auth/admin/users/{user_id}
```

Get a specific user by ID (admin only).

**Response (200 OK):**

```json
{
  "id": 123,
  "username": "user1",
  "email": "user1@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "role": "customer",
  "is_active": true,
  "created_at": "2025-03-14T09:30:00Z",
  "last_login": "2025-03-14T10:45:00Z",
  "failed_login_attempts": 0,
  "account_locked_until": null,
  "has_mfa_enabled": true
}
```

**Errors:**

- `403 Forbidden`: Not authorized (non-admin user)
- `404 Not Found`: User not found

---

#### Update User

```
PUT /auth/admin/users/{user_id}
```

Update a specific user (admin only).

**Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+1987654321",
  "email": "john.smith@example.com",
  "role": "staff",
  "is_active": true
}
```

**Response (200 OK):**

```json
{
  "id": 123,
  "username": "user1",
  "email": "john.smith@example.com",
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+1987654321",
  "role": "staff",
  "is_active": true,
  "created_at": "2025-03-14T09:30:00Z",
  "last_login": "2025-03-14T10:45:00Z"
}
```

**Errors:**

- `400 Bad Request`: Invalid input data
- `403 Forbidden`: Not authorized (non-admin user)
- `404 Not Found`: User not found
- `409 Conflict`: Email already exists

---

#### Create User (Admin)

```
POST /auth/admin/users
```

Create a new user (admin only).

**Request Body:**

```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "role": "staff",
  "is_active": true,
  "send_welcome_email": true
}
```

**Response (201 Created):**

```json
{
  "id": 125,
  "username": "newuser",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "role": "staff",
  "is_active": true,
  "created_at": "2025-03-14T11:30:00Z"
}
```

**Errors:**

- `400 Bad Request`: Invalid input data
- `403 Forbidden`: Not authorized (non-admin user)
- `409 Conflict`: Username or email already exists

---

#### Deactivate User

```
POST /auth/admin/users/{user_id}/deactivate
```

Deactivate a user (admin only).

**Response (200 OK):**

```json
{
  "message": "User deactivated successfully"
}
```

**Errors:**

- `403 Forbidden`: Not authorized (non-admin user)
- `404 Not Found`: User not found

---

#### Activate User

```
POST /auth/admin/users/{user_id}/activate
```

Activate a user (admin only).

**Response (200 OK):**

```json
{
  "message": "User activated successfully"
}
```

**Errors:**

- `403 Forbidden`: Not authorized (non-admin user)
- `404 Not Found`: User not found

---

#### Reset User Password

```
POST /auth/admin/users/{user_id}/reset-password
```

Reset a user's password (admin only).

**Request Body:**

```json
{
  "send_reset_email": true
}
```

**Response (200 OK):**

```json
{
  "message": "Password reset email sent",
  "reset_token": "reset-token" // Only included if send_reset_email is false
}
```

**Errors:**

- `403 Forbidden`: Not authorized (non-admin user)
- `404 Not Found`: User not found

---

### Audit Logs

#### Get Authentication Audit Logs

```
GET /auth/audit-logs
```

Get authentication audit logs (admin only).

**Query Parameters:**

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)
- `user_id`: Filter by user ID
- `action`: Filter by action type
- `from_date`: Filter from date
- `to_date`: Filter to date

**Response (200 OK):**

```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 123,
      "username": "user1",
      "action": "login",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "status": "success",
      "details": {},
      "timestamp": "2025-03-14T10:45:00Z"
    },
    {
      "id": 2,
      "user_id": 124,
      "username": "user2",
      "action": "password_reset",
      "ip_address": "192.168.1.2",
      "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
      "status": "success",
      "details": {},
      "timestamp": "2025-03-13T15:20:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

**Errors:**

- `403 Forbidden`: Not authorized (non-admin user)

## Error Responses

All API errors follow a standard format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_code": "invalid_input"
}
```

### Common Error Codes

- `invalid_credentials`: Invalid username or password
- `account_locked`: Account is locked due to too many failed attempts
- `account_inactive`: User account is not active
- `token_expired`: JWT token has expired
- `token_invalid`: JWT token is invalid
- `token_blacklisted`: JWT token has been blacklisted
- `insufficient_permissions`: User does not have permission for this action
- `invalid_input`: Invalid input data
- `resource_exists`: Resource already exists (e.g., username or email)
- `resource_not_found`: Resource not found
- `mfa_required`: Multi-factor authentication is required
- `mfa_invalid`: Invalid MFA code
- `password_policy`: Password does not meet policy requirements

## Rate Limiting

API endpoints are rate-limited to prevent abuse. The rate limits vary by endpoint:

- Login: 5 requests per minute per IP address
- Password reset: 3 requests per hour per email address
- API endpoints: 60 requests per minute per user

When rate limited, the API will respond with a 429 Too Many Requests status code and headers indicating the rate limit and when it will reset:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1583172600
```

## Webhooks

The authentication system can send webhooks for important events:

### Webhook Events

- `user.created`: A new user has been created
- `user.updated`: A user has been updated
- `user.activated`: A user has been activated
- `user.deactivated`: A user has been deactivated
- `user.login`: A user has logged in
- `user.login_failed`: A login attempt has failed
- `user.logout`: A user has logged out
- `user.password_changed`: A user has changed their password
- `user.password_reset`: A user has reset their password
- `user.mfa_enabled`: A user has enabled MFA
- `user.mfa_disabled`: A user has disabled MFA

### Webhook Payload

```json
{
  "event": "user.created",
  "timestamp": "2025-03-14T10:45:00Z",
  "data": {
    "user_id": 123,
    "username": "newuser",
    "email": "user@example.com",
    "role": "customer"
  }
}
```

## Security Considerations

- Always use HTTPS in production
- Store tokens securely (e.g., HttpOnly cookies)
- Implement proper CORS headers
- Validate all input data
- Use secure password policies
- Monitor for suspicious activities
- Implement proper error logging
