# Authentication Workflow - ISP Management Platform

This document defines the authentication workflow for the ISP Management Platform, detailing the steps and processes involved in user authentication, session management, and security features.

## 1. User Registration and Account Creation

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database
    participant Email as Email Service

    Client->>API: POST /auth/register (username, email, password)
    API->>API: Validate input
    API->>API: Hash password
    API->>DB: Create user (inactive)
    API->>API: Generate verification token
    API->>Email: Send verification email
    API->>Client: 201 Created (User registered)
```

- User submits registration with username, email, password, and profile information
- System validates input data (username uniqueness, email format, password strength)
- Password is hashed using secure algorithm
- User account is created in an "inactive" state
- Verification email is sent to user's email address
- API responds with success message

## 2. Email Verification

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database

    Client->>API: GET /auth/verify-email/{token}
    API->>API: Validate verification token
    API->>DB: Update user (active=true)
    API->>Client: 200 OK (Email verified)
```

- User clicks verification link in email
- System validates the verification token
- If valid, user account is updated to "active" status
- User is redirected to login page with success message

## 3. User Login (Standard Flow)

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database
    participant Audit as Audit Log

    Client->>API: POST /auth/token (username, password)
    API->>DB: Query user
    DB->>API: User data
    API->>API: Verify password
    API->>API: Generate access and refresh tokens
    API->>DB: Create session
    API->>Audit: Log successful login
    API->>Client: 200 OK (access_token, refresh_token as cookie)
```

- User submits username/email and password
- System validates credentials against database
- If valid, system generates:
  - JWT access token (short-lived, typically 30 minutes)
  - JWT refresh token (longer-lived, typically 7 days)
- Refresh token is stored as HTTP-only cookie
- Session information is recorded (IP address, user agent)
- Access token is returned to client for subsequent API calls

## 4. User Login (With MFA)

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database
    participant Audit as Audit Log

    Client->>API: POST /auth/token (username, password)
    API->>DB: Query user
    DB->>API: User data (MFA enabled)
    API->>API: Verify password
    API->>Client: 200 OK (requires_mfa=true, mfa_token)
    Client->>API: POST /auth/verify-mfa (mfa_token, mfa_code)
    API->>API: Verify MFA code
    API->>API: Generate access and refresh tokens
    API->>DB: Create session
    API->>Audit: Log successful login
    API->>Client: 200 OK (access_token, refresh_token as cookie)
```

- User submits username/email and password
- System validates credentials
- If MFA is enabled for user, system requires additional verification
- User is prompted to enter MFA code from authenticator app
- User submits MFA code
- System validates MFA code
- If valid, system generates tokens as in standard flow
- Optional: "Remember this device" feature to skip MFA for trusted devices

## 5. Token-based Authentication

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant Resource as Resource API

    Client->>Resource: Request with Authorization header
    Resource->>API: Validate token
    API->>Resource: Token valid (user data)
    Resource->>Client: 200 OK (requested resource)
```

- Client includes access token in Authorization header for API requests
- System validates token on each request:
  - Token format and signature
  - Token expiration
  - Token not blacklisted
- If token is valid, request is processed
- If token is expired, client must use refresh token to get new access token

## 6. Token Refresh

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API

    Client->>API: POST /auth/refresh-token (with refresh token cookie)
    API->>API: Validate refresh token
    API->>API: Generate new access token
    API->>Client: 200 OK (new access_token)
```

- When access token expires, client requests new token using refresh token
- System validates refresh token
- If valid, system issues new access token
- Refresh token remains valid (sliding expiration optional)
- If refresh token is invalid or expired, user must log in again

## 7. Session Management

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database

    Client->>API: GET /auth/sessions
    API->>DB: Retrieve user sessions
    API->>Client: 200 OK (sessions list)
    
    Client->>API: POST /auth/sessions/terminate
    API->>DB: Delete specified session
    API->>Client: 200 OK (session terminated)
```

- System tracks user sessions with device info and timestamps
- User can view all active sessions
- User can terminate individual sessions or all sessions except current
- Sessions are automatically expired after inactivity period

## 8. Password Management

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database
    participant Email as Email Service

    Client->>API: POST /auth/request-password-reset (email)
    API->>DB: Verify email exists
    API->>API: Generate reset token
    API->>Email: Send reset email
    API->>Client: 200 OK (email sent)
    
    Client->>API: POST /auth/reset-password (token, new_password)
    API->>API: Validate token
    API->>DB: Update password
    API->>Client: 200 OK (password updated)
    
    Client->>API: POST /auth/change-password (current_password, new_password)
    API->>API: Verify current password
    API->>DB: Update password
    API->>Client: 200 OK (password updated)
```

- User can change password (requires current password verification)
- User can request password reset via email
- System sends email with password reset link
- Password reset token has short expiration (typically 15-60 minutes)
- Password reset requires valid token from email

## 9. Multi-Factor Authentication (MFA)

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database

    Client->>API: POST /auth/mfa/setup
    API->>API: Generate TOTP secret
    API->>API: Create QR code URI
    API->>Client: 200 OK (QR code, secret)
    
    Client->>API: POST /auth/mfa/verify (mfa_code)
    API->>API: Verify MFA code
    API->>DB: Enable MFA, store secret
    API->>Client: 200 OK (MFA enabled)
    
    Client->>API: POST /auth/mfa/disable (password, mfa_code)
    API->>API: Verify password and MFA code
    API->>DB: Disable MFA, remove secret
    API->>Client: 200 OK (MFA disabled)
```

- User can enable MFA using authenticator app
- MFA setup process:
  1. System generates TOTP secret
  2. System creates QR code for authenticator app
  3. User scans QR code with app
  4. User verifies setup by entering code from app
  5. System stores MFA secret securely
- User can disable MFA (requires password and MFA code verification)

## 10. Logout

```mermaid
sequenceDiagram
    participant Client
    participant API as Auth API
    participant DB as Database
    participant Audit as Audit Log

    Client->>API: POST /auth/logout
    API->>DB: Terminate session
    API->>API: Blacklist tokens
    API->>Audit: Log logout
    API->>Client: 200 OK (cookies cleared)
```

- User requests logout
- System invalidates current session
- System blacklists current access and refresh tokens
- Refresh token cookie is cleared
- User is redirected to login page

## Security Considerations

- All authentication traffic uses HTTPS
- Passwords are hashed using bcrypt or Argon2
- Rate limiting is applied to sensitive endpoints
- JWT tokens have appropriate expiration times
- HTTP-only cookies are used for refresh tokens
- CSRF protection is implemented for cookie-based auth
- Audit logging captures authentication events
- Account lockout occurs after multiple failed attempts
