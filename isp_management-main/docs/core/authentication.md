# Authentication & Authorization System

This document provides comprehensive information about the authentication and authorization system used in the ISP Management Platform.

## Table of Contents

1. [Overview](#overview)
2. [Authentication Flow](#authentication-flow)
3. [Token Management](#token-management)
4. [Session Management](#session-management)
5. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
6. [Multi-Factor Authentication (MFA)](#multi-factor-authentication-mfa)
7. [API Reference](#api-reference)
8. [Testing](#testing)

## Overview

The authentication system is built using JWT (JSON Web Tokens) with OAuth2 for secure user authentication and authorization. It provides:

- Secure password hashing
- JWT token creation and validation
- Token blacklisting
- Session management
- Role-based access control
- Multi-factor authentication

The system is implemented primarily in the `AuthService` class located in `backend_core/auth_service.py`.

## Authentication Flow

### 1. User Login

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Client │────▶│ Authenticate │────▶│ Create JWT  │────▶│ Create User │
│         │     │    User      │     │   Tokens    │     │   Session   │
└─────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. User provides username/email and password
2. System authenticates user with `AuthService.authenticate_user()`
3. System creates JWT access and refresh tokens with `AuthService.create_access_token()` and `AuthService.create_refresh_token()`
4. System creates a user session with `AuthService.create_user_session()`

### 2. Token Validation

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Client │────▶│  Decode JWT │────▶│ Check Token │────▶│ Get Current │
│ Request │     │    Token    │     │ Blacklist   │     │    User     │
└─────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. Client includes JWT token in Authorization header
2. System decodes token with `AuthService.decode_token()`
3. System checks if token is blacklisted with `AuthService.is_token_blacklisted()`
4. System retrieves current user based on token payload

### 3. Token Refresh

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Client │────▶│ Validate    │────▶│ Blacklist   │────▶│ Create New  │
│ Refresh │     │ Refresh     │     │ Old Token   │     │ Access Token│
└─────────┘     │ Token       │     └─────────────┘     └─────────────┘
                └─────────────┘
```

1. Client provides refresh token
2. System validates refresh token
3. System blacklists old access token
4. System creates new access token

### 4. Logout

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐
│  Client │────▶│ Blacklist   │────▶│ Terminate   │
│ Logout  │     │ Tokens      │     │ Session     │
└─────────┘     └─────────────┘     └─────────────┘
```

1. Client requests logout
2. System blacklists access and refresh tokens
3. System terminates the user session

## Token Management

### Token Creation

The system uses JWT tokens for authentication. Two types of tokens are created:

1. **Access Token**: Short-lived token used for API access
2. **Refresh Token**: Longer-lived token used to obtain new access tokens

```python
# Create access token
access_token = AuthService.create_access_token(
    data={"sub": user.username, "id": user.id, "role": user.role}
)

# Create refresh token
refresh_token = AuthService.create_refresh_token(
    data={"sub": user.username, "id": user.id}
)
```

### Token Validation

Tokens are validated using the `decode_token` method:

```python
# Decode and validate token
payload = AuthService.decode_token(token)
```

### Token Blacklisting

To prevent the use of revoked tokens, the system maintains a token blacklist:

```python
# Blacklist a token
AuthService.blacklist_token(token)

# Check if a token is blacklisted
is_blacklisted = AuthService.is_token_blacklisted(token)
```

## Session Management

The system maintains user sessions to track active logins and provide enhanced security features.

### Creating Sessions

```python
# Create a new user session
session = AuthService.create_user_session(
    db=db,
    user_id=user.id,
    request=request,
    access_token=access_token,
    refresh_token=refresh_token
)
```

### Managing Sessions

```python
# Get all active sessions for a user
sessions = AuthService.get_user_sessions(db, user_id)

# Update session activity
AuthService.update_session_activity(db, session_id)

# Terminate a session
AuthService.terminate_session(db, session_id, reason="user_terminated")

# Terminate all sessions for a user
AuthService.terminate_all_sessions(db, user_id)

# Terminate all sessions except the current one
AuthService.terminate_other_sessions(db, user_id, current_session_id)
```

## Role-Based Access Control (RBAC)

The system implements role-based access control to restrict access to resources based on user roles.

### Role Checking

```python
# Define a dependency to check if the user is an admin
def admin_required(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return user

# Use the dependency in an endpoint
@app.post("/users/")
def create_user(current_user: User = Depends(admin_required)):
    # Only admins can access this endpoint
    ...
```

### Access Control Patterns

1. **Role-Based Endpoints**: Restrict entire endpoints based on user role
2. **Resource-Based Access**: Allow access to specific resources based on ownership or role
3. **Field-Level Access**: Restrict access to specific fields based on user role

## Multi-Factor Authentication (MFA)

The system supports Time-based One-Time Password (TOTP) multi-factor authentication.

### Enabling MFA

```python
# Generate a new MFA secret
mfa_secret = AuthService.generate_mfa_secret()

# Get provisioning URI for QR code generation
uri = AuthService.get_mfa_provisioning_uri(username, mfa_secret)

# Enable MFA for a user
AuthService.enable_mfa(db, user, mfa_secret)
```

### Verifying MFA

```python
# Verify a TOTP code
is_valid = AuthService.verify_mfa_code(user.mfa_secret, code)

# Create a device token for remembered devices
token = AuthService.create_mfa_device_token(db, user.id)

# Verify a device token
is_valid = AuthService.verify_mfa_device_token(db, user.id, token)
```

## API Reference

### AuthService Methods

#### Password Management

- `get_password_hash(password: str) -> str`: Hash a password
- `verify_password(plain_password: str, hashed_password: str) -> bool`: Verify a password against a hash

#### User Authentication

- `authenticate_user(db: Session, username: str, password: str) -> Optional[User]`: Authenticate a user

#### Token Management

- `create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str`: Create a JWT access token
- `create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str`: Create a JWT refresh token
- `decode_token(token: str) -> Dict[str, Any]`: Decode a JWT token
- `blacklist_token(token: str) -> None`: Add a token to the blacklist
- `is_token_blacklisted(token: str) -> bool`: Check if a token is blacklisted

#### Session Management

- `create_user_session(db: Session, user_id: int, request: Request, access_token: str, refresh_token: str = None) -> UserSession`: Create a new user session
- `update_session_activity(db: Session, session_id: str) -> bool`: Update the last activity timestamp for a session
- `get_user_sessions(db: Session, user_id: int) -> List[UserSession]`: Get all active sessions for a user
- `terminate_session(db: Session, session_id: str, reason: str = "user_terminated") -> bool`: Terminate a user session
- `terminate_all_sessions(db: Session, user_id: int, reason: str = "user_terminated") -> int`: Terminate all active sessions for a user
- `terminate_other_sessions(db: Session, user_id: int, current_session_id: str, reason: str = "user_terminated") -> int`: Terminate all active sessions for a user except the current one
- `get_session_by_id(db: Session, session_id: str) -> Optional[UserSession]`: Get a session by ID
- `update_last_login(db: Session, user: User, ip_address: str) -> None`: Update the last login information for a user

#### Multi-Factor Authentication

- `verify_mfa_code(mfa_secret: str, code: str) -> bool`: Verify a TOTP MFA code
- `generate_mfa_secret() -> str`: Generate a new MFA secret key
- `get_mfa_provisioning_uri(username: str, mfa_secret: str, issuer: str = "ISP Management") -> str`: Get the provisioning URI for MFA setup
- `create_mfa_device_token(db: Session, user_id: int) -> str`: Create a token for remembering a device for MFA
- `verify_mfa_device_token(db: Session, user_id: int, token: str) -> bool`: Verify a device token for MFA
- `enable_mfa(db: Session, user: User, mfa_secret: str) -> None`: Enable MFA for a user
- `disable_mfa(db: Session, user: User) -> None`: Disable MFA for a user

#### Email Verification

- `verify_email(db: Session, token: str) -> Optional[User]`: Verify a user's email using the verification token
- `set_email_verification_token(db: Session, user: User, token: str) -> None`: Set email verification token for a user

## Testing

The authentication system is tested using pytest. The following test files are available:

- `tests/auth/test_auth_service.py`: Tests for basic authentication functionality
- `tests/auth/test_rbac.py`: Tests for role-based access control
- `tests/auth/test_mfa.py`: Tests for multi-factor authentication
- `tests/auth/test_session_management.py`: Tests for session management

To run the tests:

```bash
# Run all authentication tests
python -m pytest tests/auth/

# Run specific test file
python -m pytest tests/auth/test_auth_service.py

# Run tests with verbose output
python -m pytest tests/auth/ -v
```

## Security Best Practices

1. **Password Storage**: Passwords are hashed using bcrypt
2. **Token Expiry**: Access tokens have a short lifespan
3. **Token Blacklisting**: Revoked tokens are blacklisted
4. **Session Management**: User sessions are tracked and can be terminated
5. **Account Lockout**: Accounts are locked after multiple failed login attempts
6. **MFA Support**: Multi-factor authentication is available for enhanced security
7. **HTTPS**: All API endpoints should be accessed over HTTPS
8. **CSRF Protection**: Cross-Site Request Forgery protection is implemented
